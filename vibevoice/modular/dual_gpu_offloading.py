"""
Dual-GPU layer splitting for VibeVoiceFusion.

Instead of offloading layers to CPU, this splits the 28 Qwen transformer layers
evenly across two GPUs (14 layers each), effectively doubling available VRAM.

With 2x RTX 3060 12GB:
  - GPU 0 (cuda:0): layers 0-13  (~4.3GB weights in Float8)
  - GPU 1 (cuda:1): layers 14-27 (~4.3GB weights in Float8)
  - Combined: ~24GB usable — enough for BFloat16 with no offloading penalty
  - No CPU transfers, no speed penalty

Drop-in alongside LayerOffloader; activated automatically when 2 GPUs detected.
"""

import torch
import torch.nn as nn
from typing import Dict, Optional, Any
from dataclasses import dataclass
import logging


@dataclass
class DualGPUConfig:
    """Configuration for dual-GPU layer splitting."""
    enabled: bool = False
    gpu0_layers: int = 14        # First N layers go on cuda:0
    gpu1_device: str = "cuda:1"  # Second GPU
    verbose: bool = False


class DualGPULayerSplitter:
    """
    Splits transformer layers across two GPUs using forward hooks.

    Layer assignment:
      cuda:0 -> layers 0 .. gpu0_layers-1
      cuda:1 -> layers gpu0_layers .. 27

    Two hooks handle the device boundary transparently:
      - pre_boundary_hook : moves hidden states cuda:0 -> cuda:1 before the
                            first cuda:1 layer runs
      - post_last_hook    : moves hidden states back cuda:1 -> cuda:0 so the
                            LM head (which lives on cuda:0) can consume them
    """

    def __init__(
        self,
        language_model: nn.Module,
        config: DualGPUConfig,
        primary_device: torch.device,
        logger: Optional[logging.Logger] = None,
    ):
        self.language_model = language_model
        self.config = config
        self.primary_device = primary_device
        self.secondary_device = torch.device(config.gpu1_device)
        self.logger = logger or logging.getLogger(__name__)
        self._hooks = []

        if config.enabled:
            self._setup()

    def _setup(self):
        total_layers = len(self.language_model.layers)
        split = self.config.gpu0_layers

        if split >= total_layers or split <= 0:
            self.logger.error(
                f"Invalid gpu0_layers={split} for total_layers={total_layers}. "
                "Dual-GPU split not applied."
            )
            return

        self.logger.info(
            f"Dual-GPU split: layers 0-{split-1} -> {self.primary_device}, "
            f"layers {split}-{total_layers-1} -> {self.secondary_device}"
        )

        # Move layers to their respective GPUs
        for i, layer in enumerate(self.language_model.layers):
            target = self.primary_device if i < split else self.secondary_device
            layer.to(target)
            if self.config.verbose:
                self.logger.info(f"  Layer {i:2d} -> {target}")

        # Hook 1: move activations to cuda:1 before the boundary layer
        boundary_layer = self.language_model.layers[split]

        def pre_boundary_hook(module, args, kwargs):
            new_args = tuple(
                a.to(self.secondary_device) if isinstance(a, torch.Tensor) else a
                for a in args
            )
            new_kwargs = {
                k: v.to(self.secondary_device) if isinstance(v, torch.Tensor) else v
                for k, v in kwargs.items()
            }
            return new_args, new_kwargs

        self._hooks.append(
            boundary_layer.register_forward_pre_hook(pre_boundary_hook, with_kwargs=True)
        )

        # Hook 2: move activations back to cuda:0 after the last layer
        last_layer = self.language_model.layers[-1]

        def post_last_hook(module, inputs, outputs):
            if isinstance(outputs, tuple):
                return tuple(
                    o.to(self.primary_device) if isinstance(o, torch.Tensor) else o
                    for o in outputs
                )
            if isinstance(outputs, torch.Tensor):
                return outputs.to(self.primary_device)
            return outputs

        self._hooks.append(last_layer.register_forward_hook(post_last_hook))

        self.logger.info("Dual-GPU hooks registered successfully.")
        self._print_vram_summary()

    def _print_vram_summary(self):
        for dev in [self.primary_device, self.secondary_device]:
            props = torch.cuda.get_device_properties(dev)
            total = props.total_memory / 1024 ** 3
            used = torch.cuda.memory_allocated(dev) / 1024 ** 3
            self.logger.info(
                f"  {dev} ({props.name}): {used:.1f}/{total:.1f} GB used"
            )

    def get_stats(self) -> Dict[str, Any]:
        stats = {}
        for i, dev in enumerate([self.primary_device, self.secondary_device]):
            stats[f"gpu{i}_allocated_gb"] = torch.cuda.memory_allocated(dev) / 1024 ** 3
            stats[f"gpu{i}_reserved_gb"] = torch.cuda.memory_reserved(dev) / 1024 ** 3
        return stats

    def cleanup(self):
        for h in self._hooks:
            h.remove()
        self._hooks.clear()
        self.logger.info("DualGPULayerSplitter cleaned up.")

    def __del__(self):
        if self._hooks:
            self.cleanup()


def is_dual_gpu_available() -> bool:
    """Return True when at least two CUDA GPUs are present."""
    return torch.cuda.device_count() >= 2


def make_dual_gpu_config(total_layers: int = 28) -> DualGPUConfig:
    """Balanced split: first half on GPU 0, second half on GPU 1."""
    return DualGPUConfig(
        enabled=True,
        gpu0_layers=total_layers // 2,
        gpu1_device="cuda:1",
        verbose=False,
    )
