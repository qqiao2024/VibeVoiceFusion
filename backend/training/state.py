from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path

from backend.utils.file_handler import FileHandler
from typing import Any, Dict, List, Optional

@dataclass
class TrainingState:
    # Job metadata (added for API compatibility)
    task_id: str = ""
    job_name: str = ""
    project_id: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None  # ISO format timestamp

    # Progress tracking
    current_step: int = 0
    estimated_total_steps: int = 0
    current_epoch: int = 0
    total_epochs: int = 0

    # Training parameters
    learning_rate: float = 0.0
    batch_size: int = 1
    accumlate_grad_steps: int = 1

    # Loss metrics
    current_loss: float = 0.0
    current_diffusion_loss: float = 0.0
    current_ce_loss: float = 0.0

    average_epoch_diffusion_loss: float = 0.0
    average_epoch_ce_loss: float = 0.0
    average_epoch_loss: float = 0.0

    # Timing information
    start_time: Optional[datetime] = None
    current_timestamp: Optional[datetime] = None
    estimated_total_elpase: float = 0.0
    latest_epoch_elapsed: float = 0.0
    latest_step_elapsed: float = 0.0
    average_step_time: float = 0.0
    steps_per_second: float = 0.0
    steps_per_epoch: int = 0
    steps_in_epoch: int = 0

    # Training status
    status: str = "Prepare"  # Prepare, Training, Completed, Failed
    error_message: str = ""

    # TensorBoard
    tensorboard_logdir: str = ""

    # Output files
    lora_files: List[str] = field(default_factory=list)
    final_lora_file: str = ""

    def get_all_lora_files(self) -> List[str]:
        """
        Get all LoRA files (both temporary checkpoints and final model)

        Returns:
            List of all LoRA file paths
        """
        all_files = list(self.lora_files)  # Copy the list
        if self.final_lora_file:
            all_files.append(self.final_lora_file)
        return all_files

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with datetime serialization"""
        result = asdict(self)
        # Convert datetime objects to ISO string for JSON serialization
        if isinstance(self.start_time, datetime):
            result['start_time'] = self.start_time.isoformat()
        if isinstance(self.current_timestamp, datetime):
            result['current_timestamp'] = self.current_timestamp.isoformat()

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrainingState':
        """Create TrainingState from dictionary"""

        # Convert ISO strings back to datetime
        if 'start_time' in data and isinstance(data['start_time'], str):
            try:
                data['start_time'] = datetime.fromisoformat(data['start_time'])
            except (ValueError, TypeError):
                data['start_time'] = None
        if 'current_timestamp' in data and isinstance(data['current_timestamp'], str):
            try:
                data['current_timestamp'] = datetime.fromisoformat(data['current_timestamp'])
            except (ValueError, TypeError):
                data['current_timestamp'] = None
        return cls(**data)

class TrainingStateWriter:

    def __init__(self, file_handler: FileHandler, task_id: str, path: str):
        self.file_handler = file_handler
        self.task_id = task_id
        self.path = path

    def update_state(self, train_state: TrainingState) -> None:
        states = self.file_handler.read_json(self.path)
        states[self.task_id] = train_state.to_dict()
        self.file_handler.write_json_atomic(Path(self.path), states)
