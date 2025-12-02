from pathlib import Path
from uuid import uuid4
from backend.task_manager.training_task import TrainingTask
from backend.utils.file_handler import FileHandler
from backend.task_manager.task import gm
from backend.training.engine import BaseTrainingEngine, FakeTrainingEngine, TrainingEngine, TrainingStateWriter

from vibevoice.training.trainer import TrainConfig

class VoiceGenerationService:

    TRAINING_META_FILE = 'training_history.json'

    def __init__(self, project_training_dir: Path, fake_engine: bool = False):
        """
        Initialize voice generation service for a specific project

        Args:
            project_training_dir: Path to project's training directory
        """
        self.output_dir = Path(project_training_dir)
        self.meta_file_path = self.output_dir / self.TRAINING_META_FILE
        self.file_handler = FileHandler()

        # Ensure output directory exists
        self.file_handler.ensure_directory(self.output_dir)
        self.fake_engine = fake_engine

        # Initialize metadata file if it doesn't exist
        if not self.meta_file_path.exists():
            self._save_metadata({})
    
    def _load_metadata(self) -> dict:
        """
        Load training metadata from JSON file

        Returns:
            Dictionary of training metadata
        """
        try:
            data = self.file_handler.read_json(self.meta_file_path)
            # Ensure it's a dict
            if isinstance(data, dict):
                return data
            return {}
        except FileNotFoundError:
            return {}
        except Exception as e:
            raise RuntimeError(f"Failed to load training metadata: {str(e)}")

    def train(self, train_config: TrainConfig) -> str:
        task_id = uuid4().hex
        writer = TrainingStateWriter(self.file_handler, task_id, str(self.meta_file_path))
        engine: BaseTrainingEngine = TrainingEngine(train_config,
                                                    task_id=task_id,
                                                    state_writer=writer)
        if self.fake_engine:
            engine = FakeTrainingEngine(train_config,
                                        task_id=task_id,
                                        state_writer=writer)
        training_task = TrainingTask.from_engine(task_id=task_id,
                                                 training_engine=engine)
        # Here you would typically add the task to a task manager or queue
        return task_id if gm.add_task(training_task) else None
