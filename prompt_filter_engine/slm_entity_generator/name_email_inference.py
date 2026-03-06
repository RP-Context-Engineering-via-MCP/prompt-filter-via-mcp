import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import os

class NameEmailAnonymizer:
    def __init__(self, base_model_id="Qwen/Qwen2.5-0.5B-Instruct", adapter_path=None):
        if adapter_path is None:
             adapter_path = r"d:\SLIIIT\Research\Dev\chatApp\traning-dataset\Qwen2.5-0.5B-Name-Address-Finetune"
        
        print(f"Loading tokenizer from {base_model_id}...")
        self.tokenizer = AutoTokenizer.from_pretrained(base_model_id)
        
        print(f"Loading base model from {base_model_id}...")
        if torch.cuda.is_available():
            self.device = "cuda"
            torch_dtype = torch.float16
        else:
            self.device = "cpu"
            torch_dtype = torch.float32
        
        self.base_model = AutoModelForCausalLM.from_pretrained(
            base_model_id,
            device_map=None,
            torch_dtype=torch_dtype,
        )
        self.base_model.to(self.device)

        print(f"Loading adapter from {adapter_path}...")
        self.model = PeftModel.from_pretrained(self.base_model, adapter_path)
        self.model.eval()

    def predict_name(self, original_name, cultural_origin="SL_SINHALA", gender="unknown"):
        system_prompt = "You are a context-aware name anonymizer. Replace the input name with a structurally identical but fake one. Maintain cultural origin and gender context. Return ONLY the replacement name."
        user_prompt = f"Input: {original_name} [SEP] Context: {cultural_origin} [SEP] Gender: {gender}"
        return self._generate(system_prompt, user_prompt)

    def predict_email(self, original_email, domain_type="personal", region="INTL"):
        system_prompt = "You are a context-aware email anonymizer. Replace the input email with a structurally identical but fake one. Preserve the domain type and regional TLD. Return ONLY the replacement email."
        user_prompt = f"Input: {original_email} [SEP] Context: {domain_type} [SEP] Region: {region}"
        return self._generate(system_prompt, user_prompt)

    def _generate(self, system_prompt, user_prompt):
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        text_input = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        model_inputs = self.tokenizer([text_input], return_tensors="pt").to(self.model.device)

        with torch.no_grad():
            generated_ids = self.model.generate(
                **model_inputs,
                max_new_tokens=60,
                temperature=0.1,
                do_sample=True
            )

        generated_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        # The model might output trailing [SEP] with context. Split and take the first part.
        if "[SEP]" in response:
            response = response.split("[SEP]")[0]

        response = response.strip()
        # Remove any trailing context words that were emitted without a [SEP]
        import re
        response = re.sub(r'\s+(?i:INTL|SL|SL_SINHALA|SL_TAMIL|SL_MUSLIM|unknown|male|female|personal|work|educational|government)$', '', response)
        
        return response.strip()

if __name__ == "__main__":
    try:
        engine = NameEmailAnonymizer()
        
        print("\n--- Test 1: Name Generation ---")
        output_name = engine.predict_name("Tharushi Wickramasinghe", cultural_origin="SL_SINHALA", gender="female")
        print(f"Original: Tharushi Wickramasinghe [SL_SINHALA, female]")
        print(f"Anonymized: {output_name}")

        print("\n--- Test 2: Name Generation ---")
        output_name2 = engine.predict_name("Robert Harris", cultural_origin="INTL", gender="male")
        print(f"Original: Robert Harris [INTL, male]")
        print(f"Anonymized: {output_name2}")

        print("\n--- Test 3: Email Generation ---")
        output_email = engine.predict_email("charlesjohn@oxford.ac.uk", domain_type="educational", region="INTL")
        print(f"Original: charlesjohn@oxford.ac.uk [educational, INTL]")
        print(f"Anonymized: {output_email}")

        print("\n--- Test 4: Email Generation ---")
        output_email2 = engine.predict_email("aaron45@moe.gov.lk", domain_type="government", region="SL")
        print(f"Original: aaron45@moe.gov.lk [government, SL]")
        print(f"Anonymized: {output_email2}")

    except Exception as e:
        print(f"Error during initialization or inference: {e}")
