"""
Quick Generate data models
"""
import re
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional, Dict, Any, List

from config.configuration_vibevoice import InferencePhase


@dataclass
class QuickGenerateItem:
    """Individual generation item for multi-generation"""
    audio_path: str
    seeds: int
    generation_time: float
    batch_index: int = 0
    audio_duration_seconds: Optional[float] = None
    real_time_factor: Optional[float] = None


@dataclass
class QuickGenerateDetails:
    """Detailed information about quick generation"""
    preprocessing_duration: Optional[float] = None
    generation_items: List[QuickGenerateItem] = field(default_factory=list)
    offloading_config: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class QuickGenerate:
    """Quick generate metadata model"""
    request_id: str
    voice_file: str  # Path to uploaded voice file
    text: str  # Original text input
    detected_mode: str  # "dialogue" or "narration"
    status: str  # InferencePhase constant (e.g., 'pending', 'completed')
    seeds: int
    batch_size: int
    cfg_scale: float
    model_dtype: str
    attn_implementation: str
    created_at: str
    updated_at: str
    output_files: List[str] = field(default_factory=list)
    percentage: Optional[float] = None
    current_batch_index: Optional[int] = None
    details: Optional[QuickGenerateDetails] = None
    error_message: Optional[str] = None
    completed_at: Optional[str] = None
    offloading: Optional[Dict[str, Any]] = None
    is_multi_generation: bool = False
    text_preview: Optional[str] = None  # First 100 chars for history display

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        # Status is already a string (InferencePhase constants are strings)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QuickGenerate':
        """Create from dictionary"""
        # Status is stored as string, keep it as-is (InferencePhase is a class with string constants)
        # No conversion needed - status is already a string like 'pending', 'completed', etc.
        # Handle details
        if 'details' in data and isinstance(data['details'], dict):
            items = data['details'].get('generation_items', [])
            data['details'] = QuickGenerateDetails(
                preprocessing_duration=data['details'].get('preprocessing_duration'),
                generation_items=[QuickGenerateItem(**item) if isinstance(item, dict) else item for item in items],
                offloading_config=data['details'].get('offloading_config', {})
            )
        return cls(**data)

    @classmethod
    def create(cls, request_id: str, voice_file: str, text: str,
               seeds: int = 42,
               batch_size: int = 1,
               cfg_scale: float = 1.3,
               model_dtype: str = "bf16",
               attn_implementation: str = "sdpa",
               offloading: Optional[Dict[str, Any]] = None) -> 'QuickGenerate':
        """Create a new quick generate request"""
        now = datetime.utcnow().isoformat()
        detected_mode = detect_mode(text)
        text_preview = text[:100] + "..." if len(text) > 100 else text

        return cls(
            request_id=request_id,
            voice_file=voice_file,
            text=text,
            detected_mode=detected_mode,
            status=InferencePhase.PENDING,
            seeds=seeds,
            batch_size=batch_size,
            cfg_scale=cfg_scale,
            model_dtype=model_dtype,
            attn_implementation=attn_implementation,
            created_at=now,
            updated_at=now,
            output_files=[],
            details=QuickGenerateDetails(),
            offloading=offloading,
            is_multi_generation=batch_size > 1,
            text_preview=text_preview
        )


def detect_mode(text: str) -> str:
    """
    Detect if text is dialogue or narration format.

    Dialogue format: Lines starting with "Speaker N:" pattern (e.g., "Speaker 1:", "Speaker 2:")
    Narration format: Plain text without speaker prefixes

    Args:
        text: Input text to analyze

    Returns:
        "dialogue" or "narration"
    """
    lines = text.strip().split('\n')
    # Pattern to match "Speaker N:" where N is a number (case-insensitive)
    # This is the standard format used in the application
    speaker_pattern = re.compile(r'^Speaker\s+\d+\s*:', re.IGNORECASE)

    for line in lines:
        line = line.strip()
        if line and speaker_pattern.match(line):
            return "dialogue"

    return "narration"


def parse_dialogue_speakers(text: str) -> List[str]:
    """
    Extract unique speaker names from dialogue text.

    Args:
        text: Dialogue text in "Speaker N: content" format

    Returns:
        List of unique speaker names found (e.g., ["Speaker 1", "Speaker 2"])
    """
    speakers = []
    # Pattern to match "Speaker N:" where N is a number (case-insensitive)
    speaker_pattern = re.compile(r'^(Speaker\s+\d+)\s*:', re.IGNORECASE)

    for line in text.strip().split('\n'):
        line = line.strip()
        if line:
            match = speaker_pattern.match(line)
            if match:
                speaker_name = match.group(1).strip()
                if speaker_name not in speakers:
                    speakers.append(speaker_name)

    return speakers
