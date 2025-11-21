import torch
import math
import re
import os

from typing import List, Optional, Union, Type, Dict
from torch import nn
from util.logger import get_logger

logger = get_logger(__name__)


class LoRAModule(nn.Module):
    """LoRA Module
    The codes is copied from the kohya-ss/musubi-tuner repoistory,
    changed few line to remove useless properties

    Args:
        lora_dim (int): LoRA dimension
        lora_alpha (int): LoRA alpha
        dropout (float): Dropout rate
        original_module (nn.Linear): The original linear module to be adapted
        rank_dropout (float): Rank dropout rate
    """
    def __init__(self,
                 lora_name: str,
                 original_name: str,
                 lora_dim: int = 16,
                 lora_alpha: int = 1,
                 dropout: float = 0.0,
                 multiplier: float = 1.0,
                 original_module: nn.Linear = None,
                 rank_dropout: int = 0.0,
                 module_dropout: Optional[float] = None,):
        super().__init__()

        self.lora_name = lora_name
        self.original_name = original_name
        self.multiplier = multiplier
        self.lora_dim = lora_dim
        in_dim = original_module.in_features
        out_dim = original_module.out_features
        self.lora_down = nn.Linear(in_dim, self.lora_dim, bias=False)
        self.lora_up = nn.Linear(self.lora_dim, out_dim, bias=False)
        alpha = self.lora_dim if lora_alpha is None or lora_alpha == 0 else lora_alpha
        self.scale = alpha / self.lora_dim
        self.register_buffer("alpha", torch.tensor(alpha))
        # same as microsoft's
        self.org_module = original_module  # remove in applying
        self.dropout = dropout
        self.rank_dropout = rank_dropout

        nn.init.kaiming_uniform_(self.lora_down.weight, a=math.sqrt(5))
        nn.init.zeros_(self.lora_up.weight)

    def apply_to(self):
        # Save the original forward method, the org_module will be deleted after this
        self.org_forward = self.org_module.forward
        self.org_module.forward = self.forward
        del self.org_module

    def forward(self, x):
        org_forwarded = self.org_forward(x)

        # module dropout
        if self.module_dropout is not None and self.training:
            if torch.rand(1) < self.module_dropout:
                return org_forwarded

        lx = self.lora_down(x)

        # normal dropout
        if self.dropout is not None and self.training:
            lx = torch.nn.functional.dropout(lx, p=self.dropout)

        # rank dropout
        if self.rank_dropout is not None and self.training:
            mask = torch.rand((lx.size(0), self.lora_dim), device=lx.device) > self.rank_dropout
            if len(lx.size()) == 3:
                mask = mask.unsqueeze(1)  # for Text Encoder
            elif len(lx.size()) == 4:
                mask = mask.unsqueeze(-1).unsqueeze(-1)  # for Conv2d
            lx = lx * mask

            # scaling for rank dropout: treat as if the rank is changed
            scale = self.scale * (1.0 / (1.0 - self.rank_dropout))  # redundant for readability
        else:
            scale = self.scale

        lx = self.lora_up(lx)
        return org_forwarded + lx * self.multiplier * scale

class LoRANetwork(nn.Module):
    # only supports U-Net (DiT), Text Encoders are not supported

    def __init__(
        self,
        model: nn.Module,
        multiplier: float = 1.0,
        lora_dim: int = 4,
        alpha: float = 1,
        dropout: Optional[float] = None,
        rank_dropout: Optional[float] = None,
        module_dropout: Optional[float] = None,
        verbose: Optional[bool] = False,
    ) -> None:
        super().__init__()
        self.multiplier = multiplier

        self.lora_dim = lora_dim
        self.alpha = alpha
        self.dropout = dropout
        self.rank_dropout = rank_dropout
        self.module_dropout = module_dropout
        self.verbose = verbose
        self.prefix = "vibevoice_lora"

        self.loraplus_lr_ratio = None
        self.fine_tuning_layers = self._includes_layers()

        logger.info(f"create LoRA network. base dim (rank): {lora_dim}, alpha: {alpha}")
        logger.info(f"neuron dropout: p={self.dropout}, rank dropout: p={self.rank_dropout}, "
                    f"module dropout: p={self.module_dropout}")

        # create module instances
        def create_modules(
            pfx: str,
            root_module: torch.nn.Module,
            default_dim: Optional[int] = None,
        ) -> List[LoRAModule]:
            loras = []
            for name, module in root_module.named_modules():
                if module.__class__.__name__ == "Linear":
                    original_name = (name + "." if name else "") + name
                    lora_name = f"{pfx}.{original_name}".replace(".", "_")

                    # exclude/include filter
                    matched = False
                    for pattern in self.fine_tuning_layers:
                        if pattern.match(original_name):
                            matched = True
                            break
                    if not matched:
                        continue

                    dim = None
                    alpha = None

                    dim = default_dim if default_dim is not None else self.lora_dim
                    alpha = self.alpha

                    if dim is None or dim == 0:
                        continue

                    lora = LoRAModule(lora_name, original_name,
                                      original_module=module,
                                      multiplier=self.multiplier,
                                      lora_dim=dim,
                                      lora_alpha=alpha,
                                      dropout=dropout,
                                      rank_dropout=rank_dropout,
                                      module_dropout=module_dropout)
                    loras.append(lora)

            return loras

        self.lora_layers: List[LoRAModule] = create_modules(self.prefix, model)

        logger.info(f"create LoRA for Vibevoice: {len(self.lora_layers)} modules.")
        if verbose:
            for lora in self.lora_layers:
                logger.info(f"\t{lora.lora_name:50} {lora.lora_dim}, {lora.lora_alpha}")

        # assertion
        names = set()
        for lora in self.lora_layers:
            assert lora.lora_name not in names, f"duplicated lora name: {lora.lora_name}"
            names.add(lora.lora_name)

    def _includes_layers(self) -> List[re.Pattern]:
        """
        Located at: model.model.language_model, architecture: Qwen2.5-7B layers:
        Transformer with self-attention,
        Key attention layers for LoRA:
            - model.language_model.layers.{i}.self_attn.q_proj
            - model.language_model.layers.{i}.self_attn.k_proj
            - model.language_model.layers.{i}.self_attn.v_proj
            - model.language_model.layers.{i}.self_attn.o_proj
        Feed-forward layers:
            - model.language_model.layers.{i}.mlp.gate_proj
            - model.language_model.layers.{i}.mlp.up_proj
            - model.language_model.layers.{i}.mlp.down_proj
        Located at: model.prediction_head, key layers:
            - model.prediction_head.cond_proj
            - model.prediction_head.layers.{i}.ffn.gate_proj
            - model.prediction_head.layers.{i}.ffn.up_proj
            - model.prediction_head.layers.{i}.ffn.down_proj
            - model.prediction_head.layers.{i}.adaLN_modulation.1
        Returns:
            List[re.Pattern]: _description_
        """
        patterns = [
            r"^model.language_model\.layers\.\d+\.self_attn\.(q_proj|k_proj|v_proj|o_proj)$",
            r"^model.language_model\.layers\.\d+\.mlp\.(gate_proj|up_proj|down_proj)$",
            r"^model.prediction_head\.cond_proj$",
            r"^model.prediction_head\.layers\.\d+\.ffn\.(gate_proj|up_proj|down_proj)$",
            r"^model.prediction_head\.layers\.\d+\.adaLN_modulation\.1$",
        ]
        return [re.compile(p) for p in patterns]

    def prepare_network(self, args):
        """
        called after the network is created
        """
        pass

    def set_multiplier(self, multiplier):
        self.multiplier = multiplier
        for lora in self.lora_layers:
            lora.multiplier = self.multiplier

    def set_enabled(self, is_enabled):
        for lora in self.lora_layers:
            lora.enabled = is_enabled

    def load_weights(self, file):
        if os.path.splitext(file)[1] == ".safetensors":
            from safetensors.torch import load_file

            weights_sd = load_file(file)
        else:
            weights_sd = torch.load(file, map_location="cpu")

        info = self.load_state_dict(weights_sd, False)
        return info

    def apply_to(self):

        if len(self.lora_layers) == 0:
            raise RuntimeError("No LoRA modules found")

        for lora in self.lora_layers:
            lora.apply_to()
            self.add_module(lora.lora_name, lora)

    def is_mergeable(self):
        return True

    def merge_to(self, weights_sd, dtype=None, device=None, non_blocking=False):
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=2) as executor:  # 2 workers is enough
            futures = []
            for lora in self.lora_layers:
                sd_for_lora = {}
                for key in weights_sd.keys():
                    if key.startswith(lora.lora_name):
                        sd_for_lora[key[len(lora.lora_name) + 1 :]] = weights_sd[key]
                if len(sd_for_lora) == 0:
                    logger.info(f"no weight for {lora.lora_name}")
                    continue

                # lora.merge_to(sd_for_lora, dtype, device)
                futures.append(executor.submit(lora.merge_to, sd_for_lora, dtype, device, non_blocking))

        for future in futures:
            future.result()

        logger.info("weights are merged")

    def set_loraplus_lr_ratio(self, loraplus_lr_ratio):
        self.loraplus_lr_ratio = loraplus_lr_ratio

        logger.info(f"LoRA+ UNet LR Ratio: {self.loraplus_lr_ratio}")

    def prepare_optimizer_params(self, learning_rate: float = 1e-4, **kwargs):
        self.requires_grad_(True)

        all_params = []
        lr_descriptions = []

        def assemble_params(loras, lr, loraplus_ratio):
            param_groups = {"lora": {}, "plus": {}}
            for lora in loras:
                for name, param in lora.named_parameters():
                    if loraplus_ratio is not None and "lora_up" in name:
                        param_groups["plus"][f"{lora.lora_name}.{name}"] = param
                    else:
                        param_groups["lora"][f"{lora.lora_name}.{name}"] = param

            params = []
            descriptions = []
            for key in param_groups.keys():
                param_data = {"params": param_groups[key].values()}

                if len(param_data["params"]) == 0:
                    continue

                if lr is not None:
                    if key == "plus":
                        param_data["lr"] = lr * loraplus_ratio
                    else:
                        param_data["lr"] = lr

                if param_data.get("lr", None) == 0 or param_data.get("lr", None) is None:
                    logger.info("NO LR skipping!")
                    continue

                params.append(param_data)
                descriptions.append("plus" if key == "plus" else "")

            return params, descriptions

        if self.lora_layers:
            params, descriptions = assemble_params(self.lora_layers, learning_rate, self.loraplus_lr_ratio)
            all_params.extend(params)
            lr_descriptions.extend(["vibevoice" + (" " + d if d else "") for d in descriptions])

        return all_params, lr_descriptions

    def enable_gradient_checkpointing(self):
        # not supported
        pass

    def prepare_grad_etc(self, unet):
        self.requires_grad_(True)

    def on_epoch_start(self, unet):
        self.train()

    def on_step_start(self):
        pass

    def get_trainable_params(self):
        return self.parameters()

    def save_weights(self, file, dtype, metadata):
        if metadata is not None and len(metadata) == 0:
            metadata = None

        state_dict = self.state_dict()

        if dtype is not None:
            for key in list(state_dict.keys()):
                v = state_dict[key]
                v = v.detach().clone().to("cpu").to(dtype)
                state_dict[key] = v

        if os.path.splitext(file)[1] == ".safetensors":
            from safetensors.torch import save_file
            from util import model_utils

            # Precalculate model hashes to save time on indexing
            if metadata is None:
                metadata = {}
            model_hash, legacy_hash = model_utils.precalculate_safetensors_hashes(state_dict, metadata)
            metadata["sshs_model_hash"] = model_hash
            metadata["sshs_legacy_hash"] = legacy_hash

            save_file(state_dict, file, metadata)
        else:
            torch.save(state_dict, file)


    def apply_max_norm_regularization(self, max_norm_value, device):
        downkeys = []
        upkeys = []
        alphakeys = []
        norms = []
        keys_scaled = 0

        state_dict = self.state_dict()
        for key in state_dict.keys():
            if "lora_down" in key and "weight" in key:
                downkeys.append(key)
                upkeys.append(key.replace("lora_down", "lora_up"))
                alphakeys.append(key.replace("lora_down.weight", "alpha"))

        for i in range(len(downkeys)):
            down = state_dict[downkeys[i]].to(device)
            up = state_dict[upkeys[i]].to(device)
            alpha = state_dict[alphakeys[i]].to(device)
            dim = down.shape[0]
            scale = alpha / dim

            if up.shape[2:] == (1, 1) and down.shape[2:] == (1, 1):
                updown = (up.squeeze(2).squeeze(2) @ down.squeeze(2).squeeze(2)).unsqueeze(2).unsqueeze(3)
            elif up.shape[2:] == (3, 3) or down.shape[2:] == (3, 3):
                updown = torch.nn.functional.conv2d(down.permute(1, 0, 2, 3), up).permute(1, 0, 2, 3)
            else:
                updown = up @ down

            updown *= scale

            norm = updown.norm().clamp(min=max_norm_value / 2)
            desired = torch.clamp(norm, max=max_norm_value)
            ratio = desired.cpu() / norm.cpu()
            sqrt_ratio = ratio**0.5
            if ratio != 1:
                keys_scaled += 1
                state_dict[upkeys[i]] *= sqrt_ratio
                state_dict[downkeys[i]] *= sqrt_ratio
            scalednorm = updown.norm() * ratio
            norms.append(scalednorm.item())

        return keys_scaled, sum(norms) / len(norms), max(norms)


def create_network(original_model: nn.Module,
                   multiplier: float,
                   network_dim: Optional[int],
                   network_alpha: Optional[float],
                   neuron_dropout: Optional[float] = None,
                   **kwargs) -> LoRANetwork:
    """architecture independent network creation"""
    if network_dim is None:
        network_dim = 4  # default
    if network_alpha is None:
        network_alpha = 1.0

    # rank/module dropout
    rank_dropout = kwargs.get("rank_dropout", None)
    if rank_dropout is not None:
        rank_dropout = float(rank_dropout)
    module_dropout = kwargs.get("module_dropout", None)
    if module_dropout is not None:
        module_dropout = float(module_dropout)

    # verbose
    verbose = kwargs.get("verbose", False)
    if verbose is not None:
        verbose = True if verbose == "True" else False

    # too many arguments ( ^ω^)･･･
    network = LoRANetwork(original_model,
                          multiplier=multiplier,
                          lora_dim=network_dim,
                          alpha=network_alpha,
                          dropout=neuron_dropout,
                          rank_dropout=rank_dropout,
                          module_dropout=module_dropout,
                          verbose=verbose)

    loraplus_lr_ratio = kwargs.get("loraplus_lr_ratio", None)
    # loraplus_unet_lr_ratio = kwargs.get("loraplus_unet_lr_ratio", None)
    # loraplus_text_encoder_lr_ratio = kwargs.get("loraplus_text_encoder_lr_ratio", None)
    loraplus_lr_ratio = float(loraplus_lr_ratio) if loraplus_lr_ratio is not None else None
    # loraplus_unet_lr_ratio = float(loraplus_unet_lr_ratio) if loraplus_unet_lr_ratio is not None else None
    # loraplus_text_encoder_lr_ratio = float(loraplus_text_encoder_lr_ratio) if loraplus_text_encoder_lr_ratio is not None else None
    if loraplus_lr_ratio is not None:  # or loraplus_unet_lr_ratio is not None or loraplus_text_encoder_lr_ratio is not None:
        network.set_loraplus_lr_ratio(loraplus_lr_ratio)  # , loraplus_unet_lr_ratio, loraplus_text_encoder_lr_ratio)

    return network
