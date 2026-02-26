import json
import re
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel


class HealthEntityClassifier:
    """
    Loads the fine-tuned Qwen2.5-0.5B-Health-Lora-Finetune LoRA adapter and
    classifies a detected health entity into:
      - tier            (1 = Critical, 2 = High, 3 = Standard OTC, null = not medical)
      - therapeutic_area (e.g. "mental_health", "metabolic", ...)
      - drug_class       (e.g. "antidepressant", null for conditions)
      - confidence       (0.0 – 1.0)
    """

    BASE_MODEL   = "Qwen/Qwen2.5-0.5B-Instruct"
    ADAPTER_PATH = r"d:\SLIIIT\Research\Dev\chatApp\traning-dataset\Qwen2.5-0.5B-Health-Lora-Finetune"

    SYSTEM_PROMPT = (
        "You are a medical entity classifier. Given an entity and its surrounding context, "
        "output ONLY valid JSON with exactly these fields: "
        "\"tier\" (integer 1, 2, 3, or null), "
        "\"therapeutic_area\" (string or null), "
        "\"drug_class\" (string or null — for medications only), "
        "\"confidence\" (float between 0.0 and 1.0). "
        "Do not include any explanation outside the JSON."
    )

    # If confidence falls below this threshold → default to Tier 1 (safe)
    CONFIDENCE_THRESHOLD = 0.85

    def __init__(self):
        print("Initializing Health Entity Classifier...")
        try:
            if torch.cuda.is_available():
                self.device     = "cuda"
                torch_dtype     = torch.float16
            else:
                self.device     = "cpu"
                torch_dtype     = torch.float32

            print(f"  Loading tokenizer from {self.BASE_MODEL}...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.BASE_MODEL)

            print(f"  Loading base model from {self.BASE_MODEL}...")
            base_model = AutoModelForCausalLM.from_pretrained(
                self.BASE_MODEL,
                device_map=None,
                torch_dtype=torch_dtype,
            )
            base_model.to(self.device)

            print(f"  Loading health LoRA adapter from {self.ADAPTER_PATH}...")
            self.model = PeftModel.from_pretrained(base_model, self.ADAPTER_PATH)
            self.model.eval()
            self._available = True
            print("  Health Entity Classifier ready.")
        except Exception as e:
            print(f"  Warning: Could not load Health SLM ({e}). Rule-based fallback will be used.")
            self.model     = None
            self.tokenizer = None
            self._available = False

    # ------------------------------------------------------------------
    def classify(self, entity_text: str, entity_label: str,
                 context_window: str) -> dict:
        """
        Classify a health entity.

        Args:
            entity_text:    The raw entity string (e.g. "Duloxetine")
            entity_label:   "medical_condition" or "medication_name"
            context_window: ±30-token window around the entity in original text

        Returns:
            dict with keys: tier, therapeutic_area, drug_class, confidence
        """
        if not self._available:
            return self._fallback(entity_label)

        prompt = (
            f"Entity: {entity_text}\n"
            f"Label: {entity_label}\n"
            f"Context: {context_window}"
        )

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ]

        try:
            text_input = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
            model_inputs = self.tokenizer([text_input], return_tensors="pt").to(self.device)

            with torch.no_grad():
                generated_ids = self.model.generate(
                    **model_inputs,
                    max_new_tokens=80,
                    temperature=0.1,
                    do_sample=True,
                )

            new_ids = [
                out[len(inp):]
                for inp, out in zip(model_inputs.input_ids, generated_ids)
            ]
            raw_output = self.tokenizer.batch_decode(new_ids, skip_special_tokens=True)[0].strip()

            result = self._parse_output(raw_output)

            # Safety: low confidence → force Tier 1
            if (result.get("confidence") or 0.0) < self.CONFIDENCE_THRESHOLD:
                result["tier"] = 1

            return result

        except Exception as e:
            print(f"  [HealthClassifier] Inference error: {e}")
            return self._fallback(entity_label)

    # ------------------------------------------------------------------
    def _parse_output(self, raw: str) -> dict:
        """Extract JSON from model output, with graceful fallback."""
        # Try to find a JSON block in the output
        match = re.search(r'\{.*?\}', raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                return {
                    "tier":             data.get("tier"),
                    "therapeutic_area": data.get("therapeutic_area"),
                    "drug_class":       data.get("drug_class"),
                    "confidence":       float(data.get("confidence", 0.0)),
                }
            except (json.JSONDecodeError, ValueError):
                pass

        print(f"  [HealthClassifier] Could not parse JSON from: {raw!r}")
        # Unparseable → safest fallback
        return {"tier": 1, "therapeutic_area": None, "drug_class": None, "confidence": 0.0}

    def _fallback(self, entity_label: str) -> dict:
        """Rule-based fallback when SLM is unavailable."""
        return {
            "tier":             1,
            "therapeutic_area": "mental_health" if entity_label == "medical_condition" else None,
            "drug_class":       None,
            "confidence":       0.0,
        }
