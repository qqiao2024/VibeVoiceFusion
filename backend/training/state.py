from dataclasses import dataclass, asdict
from datetime import datetime

from backend.utils.file_handler import FileHandler
from typing import Any, Dict

@dataclass
class TrainingState:
    current_step: int = 0
    estimated_total_steps: int = 0
    current_epoch: int = 0
    total_epochs: int = 0

    learning_rate: float = 0.0

    current_loss: float = 0.0
    current_diffusion_loss: float = 0.0
    current_ce_loss: float = 0.0

    average_epoch_diffusion_loss: float = 0.0
    average_epoch_ce_loss: float = 0.0
    average_epoch_loss: float = 0.0

    tensorboard_logdir: str = ""

    start_time: datetime = None
    current_timestamp: datetime = None
    estimated_total_elpase: float = 0.0

    latest_epoch_elapsed: float = 0.0
    latest_step_elapsed: float = 0.0

    status: str = "Prepare"  # Prepare, Training, Completed, Failed
    average_step_time: float = 0.0
    steps_per_second: float = 0.0

    batch_size: int = 1
    accumlate_grad_steps: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class TrainingStateWriter:

    def __init__(self, file_handler: FileHandler, task_id: str, path: str):
        self.file_handler = file_handler
        self.task_id = task_id
        self.path = path

    def update_state(self, train_state: TrainingState) -> None:
        states = self.file_handler.read_json(self.path)
        states[self.task_id] = train_state.to_dict()
        self.file_handler.write_json_atomic(self.path, states)
