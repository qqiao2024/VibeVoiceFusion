"""
Dialog session data models and schemas
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, Literal

# Session mode type
SessionMode = Literal["dialogue", "narration"]


@dataclass
class DialogSession:
    """Dialog session metadata model"""
    session_id: str  # Unique identifier
    name: str  # Session name
    description: str  # Session description
    text_filename: str  # Text file name (stored in scripts/ directory)
    created_at: str  # ISO format timestamp
    updated_at: str  # ISO format timestamp
    mode: SessionMode = "dialogue"  # "dialogue" or "narration"
    narrator_speaker_id: Optional[str] = None  # Required when mode="narration", e.g., "Speaker 1"

    def to_dict(self) -> Dict[str, Any]:
        """Convert dialog session to dictionary"""
        return {
            "session_id": self.session_id,
            "name": self.name,
            "description": self.description,
            "text_filename": self.text_filename,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "mode": self.mode,
            "narrator_speaker_id": self.narrator_speaker_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DialogSession':
        """Create dialog session from dictionary"""
        # Handle backward compatibility - default mode to "dialogue" if not present
        return cls(
            session_id=data["session_id"],
            name=data["name"],
            description=data["description"],
            text_filename=data["text_filename"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            mode=data.get("mode", "dialogue"),
            narrator_speaker_id=data.get("narrator_speaker_id"),
        )

    @classmethod
    def create(cls, session_id: str, name: str, description: str, text_filename: str,
               mode: SessionMode = "dialogue", narrator_speaker_id: Optional[str] = None) -> 'DialogSession':
        """Create a new dialog session with timestamps"""
        now = datetime.utcnow().isoformat()
        return cls(
            session_id=session_id,
            name=name,
            description=description,
            text_filename=text_filename,
            created_at=now,
            updated_at=now,
            mode=mode,
            narrator_speaker_id=narrator_speaker_id,
        )

    def update(self, name: Optional[str] = None, description: Optional[str] = None,
               mode: Optional[SessionMode] = None, narrator_speaker_id: Optional[str] = None) -> None:
        """Update dialog session metadata"""
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if mode is not None:
            self.mode = mode
        if narrator_speaker_id is not None:
            self.narrator_speaker_id = narrator_speaker_id
        self.updated_at = datetime.utcnow().isoformat()
