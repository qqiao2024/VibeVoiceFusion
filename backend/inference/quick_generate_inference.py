"""
Quick Generate Inference Engine - handles voice generation without project setup
"""
import base64
import copy
import random
import time
import torch
import gc
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

from flask import current_app

from backend.models.quick_generate import QuickGenerate, QuickGenerateItem, detect_mode, parse_dialogue_speakers
from config.configuration_vibevoice import DEFAULT_CONFIG, VibeVoiceConfig, InferencePhase
from util.logger import get_logger

# DUAL-GPU PATCH: new import
from vibevoice.modular.dual_gpu_offloading import (
    DualGPULayerSplitter, is_dual_gpu_available, make_dual_gpu_config
)

logger = get_logger(__name__)


def _get_model_classes():
    from vibevoice.modular.modeling_vibevoice_inference import VibeVoiceForConditionalInference, VibeVoiceGenerationOutput
    from vibevoice.modular.custom_offloading_utils import OffloadConfig
    from vibevoice.processor.vibevoice_processor import VibeVoiceProcessor
    return VibeVoiceForConditionalInference, VibeVoiceGenerationOutput, OffloadConfig, VibeVoiceProcessor


def _get_offload_presets():
    _, _, OffloadConfig, _ = _get_model_classes()
    return {
        "balanced": OffloadConfig(enabled=True, num_layers_on_gpu=12, pin_memory=True, prefetch_next_layer=True, profile=True),
        "aggressive": OffloadConfig(enabled=True, num_layers_on_gpu=8, pin_memory=True, prefetch_next_layer=True, profile=True),
        "extreme": OffloadConfig(enabled=True, num_layers_on_gpu=4, pin_memory=True, prefetch_next_layer=True, profile=True),
        "dual_gpu": None,  # DUAL-GPU PATCH: sentinel
    }


class FakeQuickGenerateModel:
    def generate(self, **kwargs) -> Any:
        visitor = kwargs.get("generation_visitor", None)
        steps = random.randint(20, 100)
        for i in range(steps):
            if visitor is not None:
                visitor.visit_inference_step_start(current_step=i + 1, total_steps=steps)
            time.sleep(random.uniform(0.1, 0.5))
            if visitor is not None:
                visitor.visit_inference_step_end(current_step=i + 1, total_steps=steps)
        return torch.randn(1, 16000 * 5)


class QuickGenerateVisitor:
    def __init__(self, quick_gen: QuickGenerate):
        self._quick_gen = quick_gen
        self.preprocess_begin = None

    def visit_preprocessing(self, timestamp: float = None):
        self._quick_gen.status = InferencePhase.PREPROCESSING
        self.preprocess_begin = timestamp
        self._quick_gen.updated_at = datetime.utcnow().isoformat()

    def visit_inference_start(self, scripts: List[str] = None, **kwargs):
        self._quick_gen.status = InferencePhase.INFERENCING
        if self.preprocess_begin:
            self._quick_gen.details.preprocessing_duration = datetime.now().timestamp() - self.preprocess_begin
        self._quick_gen.updated_at = datetime.utcnow().isoformat()

    def visit_inference_batch_start(self, batch_index: int, seeds: int):
        self._quick_gen.current_batch_index = batch_index
        self._quick_gen.details.generation_items.append(
            QuickGenerateItem(batch_index=batch_index, audio_path="", seeds=seeds, generation_time=0)
        )
        self._quick_gen.seeds = seeds
        self._batch_start_at = datetime.utcnow()
        self._quick_gen.updated_at = datetime.utcnow().isoformat()

    def visit_inference_batch_end(self, batch_index: int):
        if hasattr(self, '_batch_start_at'):
            duration = (datetime.utcnow() - self._batch_start_at).total_seconds()
            self._quick_gen.details.generation_items[batch_index].generation_time = duration
        self._quick_gen.updated_at = datetime.utcnow().isoformat()

    def visit_inference_save_audio_file(self, output_audio_path: str = None,
                                        generation_time: float = None,
                                        audio_duration_seconds: float = None,
                                        real_time_factor: float = None, **kwargs):
        current_item = self._quick_gen.details.generation_items[self._quick_gen.current_batch_index]
        current_item.audio_path = output_audio_path
        if generation_time:
            current_item.generation_time = generation_time
        current_item.audio_duration_seconds = audio_duration_seconds
        current_item.real_time_factor = real_time_factor
        if output_audio_path:
            self._quick_gen.output_files.append(output_audio_path)
        self._quick_gen.updated_at = datetime.utcnow().isoformat()

    def visit_inference_step_start(self, current_step: int, total_steps: int):
        if self._quick_gen.current_batch_index is not None:
            current_item = self._quick_gen.details.generation_items[self._quick_gen.current_batch_index]
            current_item.current_step = current_step
            current_item.total_steps = total_steps
            batch_progress = current_step / total_steps if total_steps > 0 else 0
            batch_weight = 1.0 / self._quick_gen.batch_size if self._quick_gen.batch_size > 0 else 1.0
            overall_progress = (self._quick_gen.current_batch_index + batch_progress) * batch_weight
            self._quick_gen.percentage = overall_progress * 100
        self._quick_gen.updated_at = datetime.utcnow().isoformat()

    def visit_inference_step_end(self, current_step: int, total_steps: int):
        self.visit_inference_step_start(current_step, total_steps)

    def visit_completed(self, message: str = None):
        self._quick_gen.status = InferencePhase.COMPLETED
        self._quick_gen.percentage = 100.0
        self._quick_gen.completed_at = datetime.utcnow().isoformat()
        self._quick_gen.updated_at = datetime.utcnow().isoformat()

    def visit_failed(self, message: str, failure_type: str = None):
        self._quick_gen.status = InferencePhase.FAILED
        self._quick_gen.error_message = message
        self._quick_gen.updated_at = datetime.utcnow().isoformat()


class QuickGenerateInferenceBase(ABC):
    def __init__(self, quick_gen: QuickGenerate, voice_paths: List[str], output_dir: str):
        self._quick_gen = quick_gen
        self.visitor = QuickGenerateVisitor(quick_gen)
        self.voice_paths = voice_paths
        self.output_dir = Path(output_dir)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_dtype = quick_gen.model_dtype
        self.attn_implementation = quick_gen.attn_implementation
        self.batch_size = quick_gen.batch_size
        self.seeds = quick_gen.seeds
        self.cfg_scale = quick_gen.cfg_scale
        self.request_id = quick_gen.request_id
        self.text = quick_gen.text
        self.detected_mode = quick_gen.detected_mode

    def get_quick_generate(self) -> QuickGenerate:
        return copy.deepcopy(self._quick_gen)

    @staticmethod
    def create(quick_gen: QuickGenerate, voice_paths: List[str], output_dir: str,
               offload_config: Optional[Dict[str, Any]] = None,
               fake: bool = False) -> 'QuickGenerateInferenceBase':
        offload_config_obj = None
        use_dual_gpu = False  # DUAL-GPU PATCH

        if offload_config and offload_config.get('enabled', False):
            _, _, OffloadConfig, _ = _get_model_classes()
            mode = offload_config.get('mode', 'preset')

            if mode == 'preset':
                preset = offload_config.get('preset', 'balanced')
                # DUAL-GPU PATCH
                if preset == 'dual_gpu':
                    use_dual_gpu = True
                    offload_config_obj = None
                else:
                    presets = _get_offload_presets()
                    offload_config_obj = presets.get(preset)
                    if not offload_config_obj:
                        logger.warning(f"Unknown preset '{preset}', using 'balanced'")
                        offload_config_obj = presets['balanced']

            elif mode == 'manual':
                num_gpu_layers = offload_config.get('num_gpu_layers', 20)
                offload_config_obj = OffloadConfig(
                    enabled=True, num_layers_on_gpu=num_gpu_layers,
                    pin_memory=True, prefetch_next_layer=True, profile=True,
                )

        if fake:
            return FakeQuickGenerateInferenceEngine(
                quick_gen, voice_paths, output_dir, offload_config=offload_config_obj
            )

        return QuickGenerateInferenceEngine(
            quick_gen, voice_paths, output_dir,
            offload_config=offload_config_obj,
            use_dual_gpu=use_dual_gpu,  # DUAL-GPU PATCH
        )

    @abstractmethod
    def _load_model(self, dtype: torch.dtype):
        pass

    @abstractmethod
    def _save_audio(self, outputs, processor, generation_time: float, input_tokens: int,
                    batch_index: int, **kwargs) -> None:
        pass

    def failure(self, message: str, failure_type: str = None):
        self.visitor.visit_failed(message, failure_type)

    def success(self, message: str = None):
        self.visitor.visit_completed(message)

    def generation_info(self) -> Dict[str, Any]:
        return self.get_quick_generate().to_dict()

    def _prepare_script_and_voices(self) -> tuple:
        if self.detected_mode == "dialogue":
            speakers = parse_dialogue_speakers(self.text)
            if not speakers:
                logger.warning("Dialogue mode detected but no speakers found, treating as narration")
                full_script = self._convert_narration_to_script(self.text)
                return full_script, [self.voice_paths[0]]
            voice_samples = [self.voice_paths[i % len(self.voice_paths)] for i in range(len(speakers))]
            full_script = self.text.replace("\u2019", "'")
            logger.info(f"Dialogue mode: {len(speakers)} speakers detected: {speakers}")
            return full_script, voice_samples
        else:
            full_script = self._convert_narration_to_script(self.text)
            logger.info("Narration mode: converted to dialog format")
            return full_script, [self.voice_paths[0]]

    def _convert_narration_to_script(self, text: str) -> str:
        lines = text.strip().split('\n')
        paragraphs = []
        current_paragraph = []
        for line in lines:
            stripped = line.strip()
            if stripped:
                current_paragraph.append(stripped)
            elif current_paragraph:
                paragraphs.append(' '.join(current_paragraph))
                current_paragraph = []
        if current_paragraph:
            paragraphs.append(' '.join(current_paragraph))
        scripts = [f"Speaker 1: {p}" for p in paragraphs]
        return '\n'.join(scripts).replace("\u2019", "'")

    def run_inference(self):
        from util.rand_init import get_generator

        self.visitor.visit_preprocessing(datetime.now().timestamp())
        full_script, voice_sample = self._prepare_script_and_voices()
        logger.info(f"Quick generate mode: {self.detected_mode}")
        logger.info(f"Voice samples ({len(voice_sample)}): {voice_sample}")

        load_dtype = torch.bfloat16
        if self.model_dtype == "float8_e4m3fn":
            load_dtype = torch.float8_e4m3fn

        logger.info(f"Loading model with dtype: {load_dtype}, attn_implementation: {self.attn_implementation}")
        model = self._load_model(dtype=load_dtype)
        self.visitor.visit_inference_start(scripts=[full_script])

        _, _, _, VibeVoiceProcessor = _get_model_classes()
        processor = VibeVoiceProcessor.from_pretrained(None)

        for batch_idx in range(self.batch_size):
            get_generator(self.seeds, force_set=True)
            self.visitor.visit_inference_batch_start(batch_index=batch_idx, seeds=self.seeds)
            inputs = processor(text=[full_script], voice_samples=[voice_sample],
                               padding=True, return_tensors="pt", return_attention_mask=True)
            for k, v in inputs.items():
                if torch.is_tensor(v):
                    inputs[k] = v.to(self.device)
            start_time = time.time()
            outputs = model.generate(**inputs, max_new_tokens=None, cfg_scale=self.cfg_scale,
                                     tokenizer=processor.tokenizer,
                                     generation_config={'do_sample': False},
                                     verbose=False, generation_visitor=self.visitor)
            generation_time = time.time() - start_time
            self._save_audio(outputs, processor, generation_time,
                             inputs['input_ids'].shape[1], batch_index=batch_idx)
            self.visitor.visit_inference_batch_end(batch_index=batch_idx)
            self.seeds = random.randint(0, 2**64 - 1)

        self.visitor.visit_completed()
        del model, processor, inputs, outputs

    def finalize(self):
        if hasattr(self, 'model') and self.model is not None:
            if hasattr(self.model, 'offloader') and self.model.offloader is not None:
                try:
                    self.model.offloader.cleanup()
                    self.model.offloader = None
                except Exception as e:
                    logger.warning(f"Failed to cleanup offloader: {e}")

            # DUAL-GPU PATCH: cleanup splitter
            if hasattr(self, 'dual_gpu_splitter') and self.dual_gpu_splitter is not None:
                try:
                    self.dual_gpu_splitter.cleanup()
                    self.dual_gpu_splitter = None
                except Exception as e:
                    logger.warning(f"Failed to cleanup dual_gpu_splitter: {e}")

            try:
                self.model.to('cpu')
            except Exception:
                pass
            del self.model
            self.model = None

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.synchronize()
            torch.cuda.empty_cache()
        logger.info("GPU memory cleanup completed")


class QuickGenerateInferenceEngine(QuickGenerateInferenceBase):
    def __init__(self, quick_gen: QuickGenerate, voice_paths: List[str], output_dir: str,
                 offload_config=None, use_dual_gpu: bool = False):  # DUAL-GPU PATCH
        super().__init__(quick_gen, voice_paths, output_dir)
        self.offload_config = offload_config
        self.use_dual_gpu = use_dual_gpu        # DUAL-GPU PATCH
        self.dual_gpu_splitter = None           # DUAL-GPU PATCH
        self.model_file = current_app.config['MODEL_PATH']

    def _load_model(self, dtype: torch.dtype):
        VibeVoiceForConditionalInference, _, _, _ = _get_model_classes()

        vibevoice_config = VibeVoiceConfig.from_dict(
            DEFAULT_CONFIG, torch_dtype=dtype, device_map="cuda",
            attn_implementation=self.attn_implementation
        )

        # DUAL-GPU PATCH: auto-enable when two GPUs present and no CPU offload
        effective_dual_gpu = self.use_dual_gpu or (
            not (self.offload_config and self.offload_config.enabled)
            and is_dual_gpu_available()
        )

        model_file = Path(self.model_file) / f"vibevoice7b_{'bf16' if dtype == torch.bfloat16 else 'float8_e4m3fn'}.safetensors"

        if effective_dual_gpu and is_dual_gpu_available():
            logger.info("Two GPUs detected — using dual-GPU layer split.")
            model = VibeVoiceForConditionalInference.from_pretrain(
                str(model_file.resolve()), vibevoice_config,
                device=self.device, offload_config=None,
                lora_model_path=None, lora_weight=1.0,
            )
            dual_cfg = make_dual_gpu_config(total_layers=28)
            self.dual_gpu_splitter = DualGPULayerSplitter(
                language_model=model.language_model.model,
                config=dual_cfg,
                primary_device=self.device,
                logger=logger,
            )
        else:
            if self.offload_config and self.offload_config.enabled:
                logger.info(f"CPU offloading enabled: {self.offload_config.num_layers_on_gpu} layers on GPU")
            else:
                logger.info("Single GPU, no offloading.")
            model = VibeVoiceForConditionalInference.from_pretrain(
                str(model_file.resolve()), vibevoice_config,
                device=self.device, offload_config=self.offload_config,
                lora_model_path=None, lora_weight=1.0,
            )

        model.eval()
        self.model = model
        return model

    def _save_audio(self, outputs, processor, generation_time: float, input_tokens: int,
                    batch_index: int, **kwargs) -> None:
        if outputs.speech_outputs is None or len(outputs.speech_outputs) == 0:
            raise RuntimeError("No audio output generated.")
        sample_rate = 24000
        audio_samples = outputs.speech_outputs[0].shape[-1] \
            if len(outputs.speech_outputs[0].shape) > 0 else len(outputs.speech_outputs[0])
        audio_duration = audio_samples / sample_rate
        rtf = generation_time / audio_duration if audio_duration > 0 else float('inf')
        output_filename = f"{self.request_id}_{batch_index}.wav"
        output_audio_path = self.output_dir / output_filename
        processor.save_audio(outputs.speech_outputs[0], output_path=output_audio_path)
        self.visitor.visit_inference_save_audio_file(
            output_audio_path=str(output_audio_path),
            generation_time=generation_time,
            audio_duration_seconds=audio_duration,
            real_time_factor=rtf
        )
        logger.info(f"Saving generated audio to {output_audio_path}")


class FakeQuickGenerateInferenceEngine(QuickGenerateInferenceBase):
    def __init__(self, quick_gen, voice_paths, output_dir, offload_config=None):
        super().__init__(quick_gen, voice_paths, output_dir)
        self.offload_config = offload_config

    def _load_model(self, dtype: torch.dtype):
        if self.offload_config and self.offload_config.enabled:
            logger.info(f"[FAKE] Layer offloading enabled: {self.offload_config.num_layers_on_gpu} layers on GPU")
        else:
            logger.info("[FAKE] Layer offloading disabled")
        return FakeQuickGenerateModel()

    def _save_audio(self, outputs, processor, generation_time: float, input_tokens: int,
                    batch_index: int, **kwargs) -> None:
        base64_wav_audio = "UklGRiUAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQEAAACA"
        audio_data = base64.b64decode(base64_wav_audio)
        output_filename = f"{self.request_id}_{batch_index}.wav"
        output_audio_path = self.output_dir / output_filename
        with open(output_audio_path, 'wb') as f:
            f.write(audio_data)
        self.visitor.visit_inference_save_audio_file(
            output_audio_path=str(output_audio_path),
            generation_time=generation_time,
            audio_duration_seconds=5.0,
            real_time_factor=1.0
        )
        logger.info(f"[FAKE] Saving generated audio to {output_audio_path}")
