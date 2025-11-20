import os
import torch
import ast
import json

from typing import Optional
from pathlib import Path
from dataclasses import dataclass
from torch.utils.data import DataLoader

from config.configuration_vibevoice import VibeVoiceConfig, DEFAULT_CONFIG
from vibevoice.modular.modeling_vibevoice_inference import VibeVoiceForConditionalInference
from vibevoice.modular.adaptive_offload import OffloadConfig
from vibevoice.lora.lora_network import create_network
from util.logger import get_logger
from vibevoice.processor.vibevoice_processor import VibeVoiceProcessor

from dataset import VibeVoiceCollator, VibeVoiceDataset

logger = get_logger(__name__)

@dataclass
class TrainConfig:
    epochs: int = 10
    batch_size: int = 1
    learning_rate: float = 1e-4
    dataset_path: Optional[str] = None
    output_dir: Optional[str] = None
    multiplier: float = 1.0
    lora_dim: int = 4
    lora_alpha: Optional[float] = None
    lora_dropout: Optional[float] = None
    model_path: Optional[str] = None
    number_of_layers: int = 0
    dtype: str = "bfloat16"
    model_config_path: Optional[str] = None
    optimizer_type: str = "AdamW8bit"
    optimizer_args: Optional[list[str]] = None
    seeds: Optional[int] = 42
    dataset_repeats: int = 1
    speech_compress_ratio: int = 3200
    semantic_dim: int = 128
    diffusion_loss_weight: float = 1.4 
    ce_loss_weight: float = 0.04 


class VibeVoiceTrainer:

    def __init__(self, train_config: TrainConfig):
        if not os.path.exists(train_config.model_path):
            raise FileNotFoundError(f"Model file {train_config.model_path} does not exist.")

        self.train_config = train_config
        if train_config.number_of_layers > 0:
            self.offload_config = OffloadConfig(
                enabled=True,
                num_layers_on_gpu=train_config.number_of_layers,
                offload_kv_cache=True,
                pin_memory=True,
            )
        else:
            self.offload_config = None
        self.dtype = torch.bfloat16 if train_config.dtype == "bfloat16" else torch.float8_e4m3fn

    def train(self):

        train_dataloader = self._get_dataloader()

        model_file = Path(self.train_config.model_path) / Path(f"vibevoice7b_{'bf16' if self.dtype == torch.bfloat16 else 'float8_e4m3fn'}.safetensors")
        config_dict = self.get_model_config()
        model = self._load_model(model_file, self.dtype, config_dict)
        model.requires_grad_(False)  # Freeze the model parameters
        network = create_network(model,
                                 self.train_config.multiplier,
                                 self.train_config.lora_dim,
                                 self.train_config.lora_alpha,
                                 self.train_config.lora_dropout)
        network.apply_to()
        network.prepare_optimizer_params(self.train_config.learning_rate)
        optimizer_name, optimizer_args, optimizer, optimizer_train_fn, optimizer_eval_fn = self._get_optimizer(network.get_trainable_params())

        optimizer.zero_grad()
        for epoch in range(self.train_config.epochs):
            logger.info(f"\nepoch {epoch + 1}/{self.train_config.epochs}")
            for _ in range(self.train_config.dataset_repeats):
                for step, inputs in enumerate(train_dataloader):
                    optimizer.step()
                
    def get_model_config(self) -> dict:
        config_dict = {}
        config = self.train_config.model_config_path
        if config:
            try:
                with open(config, 'r') as f:
                    import json
                    config_dict = json.load(f)
            except Exception as e:
                logger.warning(f"read config file {config} error {e}, fallback to default config.")
                config_dict = DEFAULT_CONFIG
        else:
            # Use default configuration
            logger.info(f"Using default configuration: {DEFAULT_CONFIG}")
            config_dict = DEFAULT_CONFIG
        return config_dict


    def _load_model(self, model_file: str,
                    dtype: torch.dtype = torch.bfloat16,
                    config_dict: dict = DEFAULT_CONFIG) -> VibeVoiceForConditionalInference:
        config = VibeVoiceConfig.from_dict(config_dict,
                                           torch_dtype=dtype,
                                           device_map="cuda",
                                           attn_implementation=self.generation.attn_implementation)

        # Use offload config if provided
        if self.offload_config and self.offload_config.enabled:
            logger.info(f"Layer offloading enabled: {self.offload_config.num_layers_on_gpu} layers on GPU")
        else:
            logger.info("Layer offloading disabled")

        # Load model with device-specific logic
        model = VibeVoiceForConditionalInference.from_pretrain(
            str(model_file.resolve()),
            config,
            device=self.device,
            offload_config=self.offload_config
        )

        model.eval()
        return model

    def _get_optimizer(self, trainable_params: list[torch.nn.Parameter]) -> tuple[str, str, torch.optim.Optimizer, callable, callable]:
        # adamw, adamw8bit, adafactor

        optimizer_type = self.train_config.optimizer_type.lower()

        # split optimizer_type and optimizer_args
        optimizer_kwargs = {}
        if self.train_config.optimizer_args is not None and len(self.train_config.optimizer_args) > 0:
            for arg in self.train_config.optimizer_args:
                key, value = arg.split("=")
                value = ast.literal_eval(value)
                optimizer_kwargs[key] = value

        lr = self.train_config.learning_rate
        optimizer = None
        optimizer_class = None

        if optimizer_type.endswith("8bit".lower()):
            try:
                import bitsandbytes as bnb
            except ImportError:
                raise ImportError("No bitsandbytes installed. Please install bitsandbytes to use 8-bit optimizers.")

            if optimizer_type == "AdamW8bit".lower():
                logger.info(f"use 8-bit AdamW optimizer | {optimizer_kwargs}")
                optimizer_class = bnb.optim.AdamW8bit
                optimizer = optimizer_class(trainable_params, lr=lr, **optimizer_kwargs)

        elif optimizer_type == "AdamW".lower():
            logger.info(f"use AdamW optimizer | {optimizer_kwargs}")
            optimizer_class = torch.optim.AdamW
            optimizer = optimizer_class(trainable_params, lr=lr, **optimizer_kwargs)

        if optimizer is None:
            raise ValueError(f"Unsupported optimizer type: {self.train_config.optimizer_type}"
                             ", only support AdamW, AdamW8bit")

        # for logging
        optimizer_name = optimizer_class.__module__ + "." + optimizer_class.__name__
        optimizer_args = ",".join([f"{k}={v}" for k, v in optimizer_kwargs.items()])

        # get train and eval functions
        def default_train_fn():
            return None

        def default_eval_fn():
            return None

        train_fn = default_train_fn
        eval_fn = default_eval_fn

        if hasattr(optimizer, "train") and callable(optimizer.train):
            train_fn = optimizer.train
            eval_fn = optimizer.eval

        return optimizer_name, optimizer_args, optimizer, train_fn, eval_fn
    
    def _get_dataloader(self) -> DataLoader:
        processor = VibeVoiceProcessor.from_pretrained(None)
        compute_semantics_flag = hasattr(processor, "semantic_tokenizer") and processor.semantic_tokenizer is not None

        dataset = []
        try:
            with open(self.train_config.dataset_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        dataset.append(json.loads(line))

        except Exception as e:
            raise RuntimeError(f"Failed to load dataset from {self.train_config.dataset_path}: {e}")
       
        if len(dataset) == 0:
            raise ValueError(f"Dataset is empty. Please check the dataset jsonl file at {self.train_config.dataset_path}.")

        train_dataset = VibeVoiceDataset(dataset)
        data_collator = VibeVoiceCollator(processor=processor,
                                          speech_compress_ratio=self.train_config.speech_compress_ratio,
                                          semantic_vae_dim=self.train_config.semantic_dim,
                                          compute_semantics=compute_semantics_flag,
                                          debug_checks=False)
        return DataLoader(train_dataset,
                          batch_size=1,
                          shuffle=True,
                          collate_fn=data_collator,
                          num_workers=1,
                          persistent_workers=1)
