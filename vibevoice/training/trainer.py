import os
import torch
import ast
import json
import toml

from typing import Any, Dict, Optional
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from torch.utils.data import DataLoader

from config.configuration_vibevoice import VibeVoiceConfig, DEFAULT_CONFIG
from util.rand_init import get_generator
from vibevoice.modular.modeling_vibevoice_inference import VibeVoiceForConditionalInference
from vibevoice.modular.adaptive_offload import OffloadConfig
from vibevoice.lora.lora_network import create_network
from util.logger import get_logger
from vibevoice.modular.modular_vibevoice_tokenizer import VibeVoiceTokenizerEncoderOutput
from vibevoice.processor.vibevoice_processor import VibeVoiceProcessor

from vibevoice.training.dataset import VibeVoiceCollator, VibeVoiceDataset

logger = get_logger(__name__)

@dataclass
class TrainConfig:
    epochs: int = 10
    batch_size: int = 1
    learning_rate: float = 1e-4
    dataset_path: Optional[str] = None
    output_dir: Optional[str] = "./lora_output"
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
    device : str = "cuda"
    gradient_accumulation_steps: int = 16
    dataload_workers: int = 2

    @classmethod
    def from_dict(cls, config_dict: dict) -> "TrainConfig":
        return cls(
            epochs=config_dict.get("epochs", 10),
            batch_size=config_dict.get("batch_size", 1),
            learning_rate=config_dict.get("learning_rate", 1e-4),
            dataset_path=config_dict.get("dataset_path"),
            output_dir=config_dict.get("output_dir", "./lora_output"),
            multiplier=config_dict.get("multiplier", 1.0),
            lora_dim=config_dict.get("lora_dim", 4),
            lora_alpha=config_dict.get("lora_alpha"),
            lora_dropout=config_dict.get("lora_dropout"),
            model_path=config_dict.get("model_path"),
            number_of_layers=config_dict.get("number_of_layers", 0),
            dtype=config_dict.get("dtype", "bfloat16"),
            model_config_path=config_dict.get("model_config_path"),
            optimizer_type=config_dict.get("optimizer_type", "AdamW8bit"),
            optimizer_args=config_dict.get("optimizer_args"),
            seeds=config_dict.get("seeds", 42),
            dataset_repeats=config_dict.get("dataset_repeats", 1),
            speech_compress_ratio=config_dict.get("speech_compress_ratio", 3200),
            semantic_dim=config_dict.get("semantic_dim", 128),
            diffusion_loss_weight=config_dict.get("diffusion_loss_weight", 1.4),
            ce_loss_weight=config_dict.get("ce_loss_weight", 0.04),
            device=config_dict.get("device", "cuda"),
            gradient_accumulation_steps=config_dict.get("gradient_accumulation_steps", 16),
            dataload_workers=config_dict.get("dataload_workers", 2),
        )
    
    @classmethod
    def from_toml(cls, toml_path: str) -> "TrainConfig":
        config_dict = {}
        with open(toml_path, 'r') as f:
            config_dict = toml.load(f)
        return cls.from_dict(config_dict)
    
    def to_metadata(self) -> Dict[str, Any]:
        return {
            "epochs": str(self.epochs),
            "batch_size": str(self.batch_size),
            "learning_rate": str(self.learning_rate),
            "dataset_path": self.dataset_path,
            "output_dir": self.output_dir,
            "multiplier": str(self.multiplier),
            "lora_dim": str(self.lora_dim),
            "lora_alpha": str(self.lora_alpha),
            "lora_dropout": str(self.lora_dropout),
            "model_path": self.model_path,
            "number_of_layers": str(self.number_of_layers),
            "dtype": self.dtype,
            "model_config_path": self.model_config_path,
            "optimizer":  self.optimizer_type + (f"({self.optimizer_args})" if len(self.optimizer_args) > 0 else ""),
            "seeds": str(self.seeds),
            "dataset_repeats": str(self.dataset_repeats),
            "speech_compress_ratio": str(self.speech_compress_ratio),
            "semantic_dim": str(self.semantic_dim),
            "diffusion_loss_weight": str(self.diffusion_loss_weight),
            "ce_loss_weight": str(self.ce_loss_weight),
            "gradient_accumulation_steps": str(self.gradient_accumulation_steps),
            "dataload_workers": str(self.dataload_workers),
        }   


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
        self.device = torch.device(train_config.device)

    def train(self):

        metadata = self.train_config.to_metadata()
        logger.info(f"Training configuration: {metadata}")
        get_generator(seeds = self.train_config.seeds)
        model_file = Path(self.train_config.model_path) / Path(f"vibevoice7b_{'bf16' if self.dtype == torch.bfloat16 else 'float8_e4m3fn'}.safetensors")
        config_dict = self.get_model_config()
        model = self._load_model(model_file, self.dtype, config_dict)
        model.requires_grad_(False)  # Freeze the model parameters

        processor = VibeVoiceProcessor.from_pretrained(None)
        train_dataloader = self._get_dataloader(processor, model)

        network = create_network(model,
                                 self.train_config.multiplier,
                                 self.train_config.lora_dim,
                                 self.train_config.lora_alpha,
                                 self.train_config.lora_dropout)
        network.apply_to()
        network.to(device=self.device, dtype=torch.bfloat16)  # only support cuda and bfloat16 for training
        trainable_parameter, _ = network.prepare_optimizer_params(self.train_config.learning_rate)
        optimizer_name, optimizer_args, optimizer, optimizer_train_fn, optimizer_eval_fn = self._get_optimizer(trainable_parameter)

        self._patch_acoustic_encode_for_legacy_indexing(model)  # 

        optimizer.zero_grad()
        gradient_accumulation_steps = self.train_config.gradient_accumulation_steps
        current_step = 0
        time = datetime.now()
        logger.info(f"Optimizer: {optimizer_name}({optimizer_args}) | Learning Rate: {self.train_config.learning_rate}")
        total_steps = self.train_config.epochs * len(train_dataloader) // (self.train_config.batch_size) * self.train_config.dataset_repeats
        logger.info(f"Starting training for {self.train_config.epochs} epochs | total_steps is approx. {total_steps} | batch_size: {self.train_config.batch_size} | gradient_accumulation_steps: {gradient_accumulation_steps}")
        for epoch in range(self.train_config.epochs):
            logger.info(f"\nepoch {epoch + 1}/{self.train_config.epochs}")
            for _ in range(self.train_config.dataset_repeats):
                for step, inputs in enumerate(train_dataloader):
                    inputs = self._preprocess_inputs(inputs)
                    output = model.call_for_train(**inputs)
                    real_loss = self.train_config.ce_loss_weight * output.loss + self.train_config.diffusion_loss_weight * output.diffusion_loss
                    real_loss.backward()
                    current_step += 1
                    if current_step % gradient_accumulation_steps == 0:
                        optimizer.step()
                        optimizer.zero_grad()
            logger.info(f"Epoch {epoch + 1} completed, and current loss is {real_loss.item():.4f}, ce_loss: {output.loss.item():.4f}, diffusion_loss: {output.diffusion_loss.item():.4f}")
        end_time = datetime.now()
        elapsed_time = end_time - time
        elapsed_seconds = elapsed_time.total_seconds()
        metadata["last_loss"] = real_loss.item()
        metadata["last_ce_loss"] = output.loss.item()
        metadata["last_diffusion_loss"] = output.diffusion_loss.item()  

        logger.info(f"Training completed. Final loss: {real_loss.item():.4f}, ce_loss: {output.loss.item():.4f}, "
                    f"diffusion_loss: {output.diffusion_loss.item():.4f}, total training steps: {current_step}, "
                    f"total time elapsed: {elapsed_seconds:.2f} seconds")
    
    def _preprocess_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        inputs = self._to_device(inputs)
        labels = inputs.get("input_ids")
        attention_mask = inputs.get("attention_mask")
        acoustic_input_mask = inputs.get("acoustic_input_mask")

        # Ensure semantic tensors exist and have correct dtype/device
        sem = inputs.get("speech_semantic_tensors", None)
        target_dtype = torch.bfloat16 # all data must be bfloat16 for training

        if sem is None:
            sm = inputs.get("speech_masks")
            if sm is not None:
                zeros = torch.zeros(
                    sm.size(0), sm.size(1),
                    getattr(self.model.config, "semantic_vae_dim", 128),
                    dtype=target_dtype,
                    device=sm.device,
                )
                inputs["speech_semantic_tensors"] = zeros
        else:
            if isinstance(sem, torch.Tensor):
                inputs["speech_semantic_tensors"] = sem.to(dtype=target_dtype)        

        return inputs

    def _to_device(self, inputs: dict) -> dict:
        for k, v in inputs.items():
            if torch.is_tensor(v):
                inputs[k] = v.to(self.device)
        return inputs

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
                                           attn_implementation="sdpa")

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
    
    def _get_dataloader(self, processor: VibeVoiceProcessor, model: VibeVoiceForConditionalInference) -> DataLoader:

        processor.semantic_tokenizer = getattr(model.model, "semantic_tokenizer", None)

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
                                          debug_checks=False, 
                                          dataset_root_path=os.path.dirname(self.train_config.dataset_path))
        return DataLoader(train_dataset,
                          batch_size=self.train_config.batch_size,
                          shuffle=True,
                          collate_fn=data_collator,
                          num_workers=self.train_config.dataload_workers,
                          persistent_workers=1)

    def _patch_acoustic_encode_for_legacy_indexing(self, model_obj):
        try:
            acoustic = getattr(getattr(model_obj, "model", model_obj), "acoustic_tokenizer", None)
            if acoustic is None or not hasattr(acoustic, "encode"):
                logger.warning("No acoustic_tokenizer.encode() found to patch.")
                return
            base_encode = acoustic.encode
            def encode_wrapped(*args, **kwargs):
                out = base_encode(*args, **kwargs)
                try:
                    if isinstance(out, VibeVoiceTokenizerEncoderOutput):
                        return [[out]]
                except Exception:
                    pass
                if isinstance(out, dict):
                    for k in ("frames", "codes", "tokens", "latents", "hidden_states"):
                        if k in out:
                            return [[out[k]]]
                    if len(out) > 0:
                        return [[next(iter(out.values()))]]
                for attr in ("frames", "codes", "tokens", "latents", "hidden_states"):
                    if hasattr(out, attr):
                        return [[getattr(out, attr)]]
                try:
                    if isinstance(out, torch.Tensor):
                        return [[out]]
                except Exception:
                    pass
                return [[out]]
            acoustic.encode = encode_wrapped
            logger.info("Patched acoustic_tokenizer.encode() to return [[...]] for legacy indexing.")
        except Exception as e:
            logger.warning(f"Failed to patch acoustic_tokenizer.encode(): {e}")
