import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

class SharedSLMManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SharedSLMManager, cls).__new__(cls, *args, **kwargs)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
            
        self.base_model_id = "Qwen/Qwen2.5-0.5B-Instruct"
        print(f"[SharedSLM] Loading tokenizer from {self.base_model_id}...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.base_model_id)

        if torch.cuda.is_available():
            self.device = "cuda"
            self.torch_dtype = torch.float16
        else:
            self.device = "cpu"
            self.torch_dtype = torch.float32

        print(f"[SharedSLM] Loading shared base model from {self.base_model_id}...")
        self.base_model = AutoModelForCausalLM.from_pretrained(
            self.base_model_id,
            device_map=None,
            torch_dtype=self.torch_dtype,
        )
        self.base_model.to(self.device)

        self.model = None
        self.loaded_adapters = set()
        self.initialized = True

    def load_adapter(self, adapter_name, adapter_path):
        """Loads an adapter if not already loaded."""
        if self.model is None:
            print(f"[SharedSLM] Loading first adapter '{adapter_name}' from {adapter_path}...")
            self.model = PeftModel.from_pretrained(self.base_model, adapter_path, adapter_name=adapter_name)
            self.loaded_adapters.add(adapter_name)
        elif adapter_name not in self.loaded_adapters:
            print(f"[SharedSLM] Loading adapter '{adapter_name}' from {adapter_path}...")
            self.model.load_adapter(adapter_path, adapter_name=adapter_name)
            self.loaded_adapters.add(adapter_name)

    def activate_adapter(self, adapter_name):
        """Switches the active adapter."""
        if self.model is not None and adapter_name in self.loaded_adapters:
            self.model.set_adapter(adapter_name)
            self.model.eval()
        else:
            raise ValueError(f"Adapter error: '{adapter_name}' is not loaded.")
