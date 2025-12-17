"""
Generation data models and schemas
"""
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional, Dict, Any, List

from config.configuration_vibevoice import InferencePhase
from vibevoice.generation.visitor import GenerationVisitor


def time_duration_in_sec(begin: datetime, end: datetime) -> float:
    """Convert timedelta to duration in seconds"""
    return (end - begin).total_seconds()


@dataclass
class GenerationItem:
    audio_path: str  # Path to generated audio file
    seeds: int  # Random seed used for this item
    generation_time: float  # Time taken for generation in seconds
    batch_index: int = 0  # Batch index
    prefilling_tokens: Optional[int] = None  # Number of prefilling tokens
    total_tokens: Optional[int] = None  # Total number of tokens generated
    generated_tokens: Optional[int] = None  # Number of tokens generated
    audio_duration_seconds: Optional[float] = None  # Duration of generated audio in seconds
    real_time_factor: Optional[float] = None  # Real-time factor for generation speed
    current_step: Optional[int] = None  # Current step in generation process
    total_steps: Optional[int] = None  # Total steps in generation process

@dataclass
class GenerationDetails:
    """Detailed information about the generation process"""
    scripts: Optional[List[str]] = field(default_factory=list)
    unique_speaker_names: Optional[List[str]] = field(default_factory=list)
    voice_sample: Optional[List[str]] = field(default_factory=list)
    max_speaker_id: Optional[int] = None
    preprocessing_duration: Optional[float] = None
    generation_items: Optional[List[GenerationItem]] = field(default_factory=list)

@dataclass
class Generation(GenerationVisitor):
    """Generation metadata model"""
    request_id: str  # Unique identifier
    session_id: str  # Speaker role identifier
    status: InferencePhase  # Status of the generation request
    output_filename: Optional[str]  # Generated audio file name
    percentage: Optional[float]  # Completion percentage
    model_dtype: str  # Type of model used for generation, e.g. "bf16" and "float8_e4m3fn"
    cfg_scale: Optional[float]  # Classifier-free guidance scale
    attn_implementation: Optional[str]  # Attention implementation used
    seeds: int  # Random seed used for generation
    created_at: str  # ISO format timestamp
    updated_at: str  # ISO format timestamp
    project_id: Optional[str] = None  # Project identifier
    project_dir: Optional[str] = None  # Output audio directory
    lora_model_path: Optional[str] = None  # Path to LoRA model file
    is_multi_generation: bool = False  # Flag for multi-generation
    fix_seed: bool = False  # Flag to fix the random seed
    lora_weight: float = 1.0  # Weight for LoRA model
    details: Optional[GenerationDetails] = GenerationDetails()
    current_batch_index: Optional[int] = None  # Current batch index for multi-generation
    batch_size: Optional[int] = None  # Total number of batches for multi-generation
    is_oom_failure: bool = False  # Flag for out-of-memory failure
    batch_start_at: datetime = None  # Timestamp when the current batch started

    def to_dict(self) -> Dict[str, Any]:
        """Convert generation request to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Generation':
        """Create generation request from dictionary"""
        return cls(**data)

    @classmethod
    def create(cls, request_id: str, session_id: str,
               seeds: int = 42,
               cfg_scale: float = 1.3,
               model_dtype: str = "float8_e4m3fn",
               attn_implementation: str = "sdpa",
               project_id: str = None,
               project_dir: str = "output/audio",
               lora_model_path: Optional[str] = None,
               lora_weight: float = 1.0,
               current_batch_index: Optional[int] = 0,
               batch_size: Optional[int] = 1) -> 'Generation':
        """Create a new generation request with timestamps"""
        now = datetime.utcnow().isoformat()
        return cls(
            request_id=request_id,
            session_id=session_id,
            status=InferencePhase.PENDING,
            output_filename=None,
            percentage=None,
            model_dtype=model_dtype,
            attn_implementation=attn_implementation,
            cfg_scale=cfg_scale,
            created_at=now,
            seeds=seeds,
            updated_at=now,
            project_id=project_id,
            project_dir=project_dir,
            details=GenerationDetails(),
            lora_model_path=lora_model_path,
            lora_weight=lora_weight,
            current_batch_index=current_batch_index,
            batch_size=batch_size,
            is_multi_generation=batch_size is not None and batch_size > 1,
            batch_start_at=None,
        )

    def visit_preprocessing(self, timestamp: float = None):
        self.status = InferencePhase.PREPROCESSING
        self.preprocess_begin = timestamp
        self.updated_at = datetime.utcnow().isoformat()

    def visit_inference_start(self, scripts: List[str] = None,
                              unique_speaker_names: List[str] = None,
                              voice_sample: List[str] = None,
                              max_speaker_id: int = None):
        self.status = InferencePhase.INFERENCING
        self.details.scripts = scripts
        self.details.unique_speaker_names = unique_speaker_names
        self.details.voice_sample = voice_sample
        self.details.max_speaker_id = max_speaker_id
        self.details.preprocessing_duration = datetime.now().timestamp() - self.preprocess_begin
        self.updated_at = datetime.utcnow().isoformat()

    def visit_inference_batch_start(self, batch_index: int, seeds: int):
        self.current_batch_index = batch_index
        self.details.generation_items.append(
            GenerationItem(
                batch_index=batch_index,
                audio_path="",
                seeds=seeds,
                generation_time=datetime.utcnow(),
            )
        )
        self.seeds = seeds
        self.batch_start_at = datetime.utcnow()
        self.updated_at = datetime.utcnow().isoformat()

    def visit_inference_batch_end(self, batch_index: int):
        begin = self.batch_start_at
        duration = time_duration_in_sec(begin, datetime.utcnow())
        self.details.generation_items[batch_index].generation_time = duration
        self.updated_at = datetime.utcnow().isoformat()

    def visit_inference_save_audio_file(self, output_audio_path: str = None,
                                        generation_time: float = None,
                                        prefilling_tokens: int = None,
                                        total_tokens: int = None,
                                        generated_tokens: int = None,
                                        audio_duration_seconds: float = None,
                                        real_time_factor: float = None,
                                        **kwargs):
        current_item = self.details.generation_items[self.current_batch_index]
        current_item.audio_path = output_audio_path
        current_item.generation_time = generation_time
        current_item.prefilling_tokens = prefilling_tokens
        current_item.total_tokens = total_tokens
        current_item.generated_tokens = generated_tokens
        current_item.audio_duration_seconds = audio_duration_seconds
        current_item.real_time_factor = real_time_factor
        self.updated_at = datetime.utcnow().isoformat()

    def visit_inference_step_start(self, current_step: int, total_steps: int):
        current_item = self.details.generation_items[self.current_batch_index]
        current_item.current_step = current_step
        current_item.total_steps = total_steps
        self.updated_at = datetime.utcnow().isoformat()

    def visit_inference_step_end(self, current_step: int, total_steps: int):
        current_item = self.details.generation_items[self.current_batch_index]
        current_item.current_step = current_step
        current_item.total_steps = total_steps
        self.updated_at = datetime.utcnow().isoformat()

    def visit_completed(self, message: str = None):
        self.status = InferencePhase.COMPLETED
        self.percentage = 100.0
        self.updated_at = datetime.utcnow().isoformat()

    def visit_failed(self, message: str, failure_type: str):
        self.status = InferencePhase.FAILED
        if failure_type == "oom":
            self.is_oom_failure = True
        self.updated_at = datetime.utcnow().isoformat()
