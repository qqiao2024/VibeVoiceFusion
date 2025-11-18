import torch
from torch import nn
from util.safetensors_util import MemoryEfficientSafeOpen
from config.configuration_vibevoice import DEFAULT_CONFIG, VibeVoiceConfig
from vibevoice.modular.modeling_vibevoice_inference import VibeVoiceForConditionalInference

def list_moduels(model_path: str):
    config = VibeVoiceConfig.from_dict(DEFAULT_CONFIG, 
                                       torch_dtype=torch.bfloat16, 
                                       device_map="cpu", 
                                       attn_implementation="sdpa")

    # Load model with device-specific logic
    model = VibeVoiceForConditionalInference.from_pretrain(model_path, config)

    state_dict = {}
    with MemoryEfficientSafeOpen(model_path) as safe:
        for key in safe.keys():
            state_dict[key] = safe.get_tensor(key)

    model.load_state_dict(state_dict, strict=False, assign=True)


if __name__ == "__main__":
    list_moduels("./models/converted/vibevoice7b_bf16.safetensors")

