"""
Dataset data models and schemas
"""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any, List


@dataclass
class Dataset:
    """Dataset metadata model"""
    id: str  # Dataset directory name / unique identifier
    name: str  # Display name
    description: str  # Dataset description
    item_count: int  # Number of items in dataset
    created_at: str  # ISO format timestamp
    updated_at: str  # ISO format timestamp

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataset to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Dataset':
        """Create dataset from dictionary"""
        return cls(**data)

    @classmethod
    def create(cls, dataset_id: str, name: str, description: str = "") -> 'Dataset':
        """Create a new dataset with timestamps"""
        now = datetime.utcnow().isoformat()
        return cls(
            id=dataset_id,
            name=name,
            description=description,
            item_count=0,
            created_at=now,
            updated_at=now
        )

    def update(self, name: Optional[str] = None, description: Optional[str] = None,
               item_count: Optional[int] = None) -> None:
        """Update dataset metadata"""
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if item_count is not None:
            self.item_count = item_count
        self.updated_at = datetime.utcnow().isoformat()


@dataclass
class DatasetItem:
    """Dataset item model"""
    text: str  # Text content
    audio: str  # Relative path to audio file (e.g., "./audio/file.wav")
    voice_prompts: List[str]  # List of relative paths to voice prompt files (e.g., ["./voice_prompts/prompt.wav"])

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataset item to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DatasetItem':
        """Create dataset item from dictionary"""
        return cls(**data)

    def validate(self) -> None:
        """Validate dataset item"""
        if not self.text or not self.text.strip():
            raise ValueError("Text cannot be empty")
        if not self.audio or not self.audio.strip():
            raise ValueError("Audio filename cannot be empty")
        if not self.voice_prompts or len(self.voice_prompts) == 0:
            raise ValueError("At least one voice prompt is required")
