import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import os

class FineTunedAnonymizer:
    def __init__(self, base_model_id="Qwen/Qwen2.5-0.5B-Instruct", adapter_path=None):
        if adapter_path is None:
             # Default to the path found in the user's workspace
             adapter_path = r"d:\SLIIIT\Research\Dev\chatApp\traning-dataset\Qwen2.5-0.5B-Anonymizer-SLM"
        
        print(f"Loading tokenizer from {base_model_id}...")
        self.tokenizer = AutoTokenizer.from_pretrained(base_model_id)
        
        print(f"Loading base model from {base_model_id}...")
        # Load in fp16 if cuda is available, else float32 for CPU
        if torch.cuda.is_available():
            self.device = "cuda"
            torch_dtype = torch.float16
        else:
            self.device = "cpu"
            torch_dtype = torch.float32
        
        self.base_model = AutoModelForCausalLM.from_pretrained(
            base_model_id,
            device_map=None, # Disable auto device map
            torch_dtype=torch_dtype,
            # low_cpu_mem_usage=True # Requires accelerate
        )
        self.base_model.to(self.device)

        print(f"Loading adapter from {adapter_path}...")
        self.model = PeftModel.from_pretrained(self.base_model, adapter_path)
        self.model.eval()

    def predict(self, raw_value, context="SL"):
        prompt = f"Input: {raw_value} [SEP] Context: {context}"

        messages = [
            {"role": "system", "content": "You are a context-aware address anonymizer. Replace the input address with a structurally identical but fake one while maintaining the regional context (SL or INTL). Return ONLY the output address."},
            {"role": "user", "content": prompt}
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

        return response.strip()

if __name__ == "__main__":
    # Test block
    try:
        engine = FineTunedAnonymizer()
        
        print("\n--- Test 1: Sri Lanka Context ---")
        output_sl = engine.predict("Walauwa Road, Mahawela, Matale", context="SL")
        print(f"Original: Walauwa Road, Mahawela, Matale")
        print(f"Anonymized: {output_sl}")

        print("\n--- Test 2: International Context ---")
        output_intl = engine.predict("10 Downing St, London", context="INTL")
        print(f"Original: 10 Downing St, London")
        print(f"Anonymized: {output_intl}")

    except Exception as e:
        print(f"Error during initialization or inference: {e}")
