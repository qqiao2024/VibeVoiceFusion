import hashlib
import safetensors.torch
import torch

from io import BytesIO
from torch import nn
from util.logger import get_logger

logger = get_logger(__name__)

def addnet_hash_legacy(b):
    """Old model hash used by sd-webui-additional-networks for .safetensors format files"""
    m = hashlib.sha256()

    b.seek(0x100000)
    m.update(b.read(0x10000))
    return m.hexdigest()[0:8]

def addnet_hash_safetensors(b):
    """New model hash used by sd-webui-additional-networks for .safetensors format files"""
    hash_sha256 = hashlib.sha256()
    blksize = 1024 * 1024

    b.seek(0)
    header = b.read(8)
    n = int.from_bytes(header, "little")

    offset = n + 8
    b.seek(offset)
    for chunk in iter(lambda: b.read(blksize), b""):
        hash_sha256.update(chunk)

    return hash_sha256.hexdigest()


def precalculate_safetensors_hashes(tensors, metadata):
    """Precalculate the model hashes needed by sd-webui-additional-networks to
    save time on indexing the model later."""

    # Because writing user metadata to the file can change the result of
    # sd_models.model_hash(), only retain the training metadata for purposes of
    # calculating the hash, as they are meant to be immutable
    metadata = {k: v for k, v in metadata.items() if k.startswith("ss_")}

    bytes = safetensors.torch.save(tensors, metadata)
    b = BytesIO(bytes)

    model_hash = addnet_hash_safetensors(b)
    legacy_hash = addnet_hash_legacy(b)
    return model_hash, legacy_hash


def merge_lora_weights(model: nn.Module, lora_path: str, lora_weight: float = 1.0) -> nn.Module:
    """Merge LoRA weights into the original model.

    Args:
        model: The original model with base weights
        lora_path: Path to the LoRA safetensors file
        multiplier: Multiplier for LoRA weights (default: 1.0)

    Returns:
        The model with merged LoRA weights
    """
    import os
    from util.safetensors_util import MemoryEfficientSafeOpen

    # Check if LoRA file exists
    if not os.path.exists(lora_path):
        logger.warning(f"LoRA file not found: {lora_path}. Returning original model.")
        return model

    # Load LoRA weights
    try:
        logger.info(f"Loading LoRA weights from {lora_path}")
        with MemoryEfficientSafeOpen(lora_path) as safe:
            lora_sd = {key: safe.get_tensor(key) for key in safe.keys()}
            metadata = safe.metadata()

            # Try to read multiplier from metadata, fallback to parameter value
            if metadata and "multiplier" in metadata:
                try:
                    lora_weight = float(metadata["multiplier"])
                    logger.info(f"Using multiplier from metadata: {lora_weight}")
                except (ValueError, TypeError):
                    logger.warning(f"Invalid multiplier in metadata: {metadata['multiplier']}, using default: {lora_weight}")
    except Exception as e:
        logger.warning(f"Failed to load LoRA weights from {lora_path}, ignored and returning original model.", exc_info=e)
        return model

    # Build LoRA structure: map original keys to their LoRA components
    lora_structure = {}

    for key in lora_sd.keys():
        # Skip non-LoRA keys
        if not key.startswith("vibevoice_lora-"):
            continue

        # Remove prefix
        key_without_prefix = key[len("vibevoice_lora-"):]

        # Determine the type of LoRA component
        if key_without_prefix.endswith(".alpha"):
            # Alpha value
            original_key = key_without_prefix[:-len(".alpha")].replace("-", ".") + ".weight"
            if original_key not in lora_structure:
                lora_structure[original_key] = {}
            lora_structure[original_key]["alpha"] = lora_sd[key]

        elif key_without_prefix.endswith(".lora_down.weight"):
            # LoRA down weight
            original_key = key_without_prefix[:-len(".lora_down.weight")].replace("-", ".") + ".weight"
            if original_key not in lora_structure:
                lora_structure[original_key] = {}
            lora_structure[original_key]["lora_down.weight"] = lora_sd[key]

        elif key_without_prefix.endswith(".lora_up.weight"):
            # LoRA up weight
            original_key = key_without_prefix[:-len(".lora_up.weight")].replace("-", ".") + ".weight"
            if original_key not in lora_structure:
                lora_structure[original_key] = {}
            lora_structure[original_key]["lora_up.weight"] = lora_sd[key]

    # Validate and clean up lora_structure - each key must have all three components
    keys_to_remove = []
    for original_key, lora_components in lora_structure.items():
        if "alpha" not in lora_components or "lora_down.weight" not in lora_components or "lora_up.weight" not in lora_components:
            logger.warning(f"Incomplete LoRA components for key '{original_key}': missing one or more of [alpha, lora_down.weight, lora_up.weight]")
            keys_to_remove.append(original_key)

    # Remove incomplete entries
    for key in keys_to_remove:
        del lora_structure[key]

    logger.info(f"Found {len(lora_structure)} valid LoRA layers to merge")

    # Check if there are any valid LoRA layers
    if len(lora_structure) == 0:
        logger.warning(f"No valid LoRA layers found in {lora_path}. Returning original model.")
        return model

    # Merge LoRA weights into the model
    merged_count = 0
    missing_count = 0

    for original_key, lora_components in lora_structure.items():
        # All components are guaranteed to be present due to validation above
        down_weight = lora_components["lora_down.weight"]
        up_weight = lora_components["lora_up.weight"]
        alpha = lora_components["alpha"]

        # Calculate scale
        dim = down_weight.size()[0]
        if isinstance(alpha, torch.Tensor):
            alpha = alpha.item()
        scale = alpha / dim

        # Find the corresponding parameter in the model
        try:
            # Navigate through the model to find the parameter
            param = model
            for attr in original_key.split("."):
                param = getattr(param, attr)

            # Check if it's a parameter
            if not isinstance(param, nn.Parameter):
                logger.warning(f"Key {original_key} does not correspond to a model parameter")
                missing_count += 1
                continue

            # Compute LoRA delta: multiplier * (up @ down) * scale
            # Move LoRA weights to the same device as the model parameter
            device = param.device
            dtype = param.dtype

            up_weight = up_weight.to(device=device, dtype=dtype)
            down_weight = down_weight.to(device=device, dtype=dtype)

            lora_delta = lora_weight * (up_weight @ down_weight) * scale

            # Merge into original weights
            param.data = param.data + lora_delta

            merged_count += 1

        except AttributeError:
            logger.warning(f"Could not find parameter for key: {original_key}")
            missing_count += 1
            continue

    logger.info(f"Successfully merged {merged_count} LoRA layers")
    if missing_count > 0:
        logger.warning(f"Failed to merge {missing_count} LoRA layers (keys not found in model)")

    return model
