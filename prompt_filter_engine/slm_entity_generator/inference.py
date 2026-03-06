import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import os

class FineTunedAnonymizer:
    def __init__(self, base_model_id="Qwen/Qwen2.5-0.5B-Instruct", adapter_path=None):
        if adapter_path is None:
             # Default to the path found in the user's workspace
             adapter_path = r"d:\SLIIIT\Research\Dev\chatApp\traning-dataset\Qwen2.5-0.5B-Anonymizer-SLM"
        
        from prompt_filter_engine.slm_entity_generator.shared_slm import SharedSLMManager
        self.slm_manager = SharedSLMManager()
        self.slm_manager.load_adapter("address_anonymizer", adapter_path)
        self.tokenizer = self.slm_manager.tokenizer

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

        model_inputs = self.tokenizer([text_input], return_tensors="pt").to(self.slm_manager.device)

        self.slm_manager.activate_adapter("address_anonymizer")
        with torch.no_grad():
            generated_ids = self.slm_manager.model.generate(
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
