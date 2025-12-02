from pathlib import Path
from uuid import uuid4
from typing import List, Optional
from datetime import datetime
from backend.task_manager.training_task import TrainingTask
from backend.utils.file_handler import FileHandler
from backend.task_manager.task import gm
from backend.training.engine import BaseTrainingEngine, FakeTrainingEngine, TrainingEngine, TrainingStateWriter
from backend.training.state import TrainingState
from util.logger import get_logger

from vibevoice.training.trainer import TrainConfig

logger = get_logger(__name__)


class TrainingService:
    """Training service for managing training jobs using TrainingState"""

    TRAINING_META_FILE = 'training_history.json'

    def __init__(self, project_training_dir: Path, fake_engine: bool = False):
        """
        Initialize training service for a specific project

        Args:
            project_training_dir: Path to project's training directory
            fake_engine: Use FakeTrainingEngine for development
        """
        self.output_dir = Path(project_training_dir)
        self.meta_file_path = self.output_dir / self.TRAINING_META_FILE
        self.file_handler = FileHandler()
        self.fake_engine = fake_engine

        # Ensure output directory exists
        self.file_handler.ensure_directory(self.output_dir)

        # Initialize metadata file if it doesn't exist
        if not self.meta_file_path.exists():
            self._save_metadata({})

    def _save_metadata(self, data: dict) -> None:
        """Save training state metadata to JSON file"""
        self.file_handler.write_json_atomic(self.meta_file_path, data)

    def _load_metadata(self) -> dict:
        """
        Load training state metadata from JSON file

        Returns:
            Dictionary of training states keyed by task_id
        """
        try:
            data = self.file_handler.read_json(self.meta_file_path)
            if isinstance(data, dict):
                return data
            return {}
        except FileNotFoundError:
            return {}
        except Exception as e:
            logger.error(f"Failed to load training metadata: {e}")
            return {}

    def create_training_job(self, job_name: str, train_config: TrainConfig,
                            project_id: str) -> Optional[TrainingState]:
        """
        Create and start a new training job

        Args:
            job_name: Human-readable job name
            train_config: Training configuration
            project_id: Project identifier

        Returns:
            TrainingState if successful, None if task queue is busy
        """
        # Check if task manager is busy
        if gm.has_task():
            logger.warning("Task manager is busy, cannot start new training job")
            return None

        # Create task_id
        task_id = uuid4().hex

        # Initialize TrainingState with metadata
        initial_state = TrainingState(
            task_id=task_id,
            job_name=job_name,
            project_id=project_id,
            config=train_config.to_dict(),
            created_at=datetime.utcnow().isoformat(),
            status="Prepare"
        )

        # Save initial state to metadata
        states_meta = self._load_metadata()
        states_meta[task_id] = initial_state.to_dict()
        self._save_metadata(states_meta)

        # Create training engine
        writer = TrainingStateWriter(self.file_handler, task_id, str(self.meta_file_path))

        if self.fake_engine:
            logger.warning("Using FakeTrainingEngine for dev environment !!!!")
            engine = FakeTrainingEngine(train_config, task_id, writer, initial_state=initial_state)
        else:
            engine = TrainingEngine(train_config, task_id, writer, initial_state=initial_state)

        # Create and add training task
        training_task = TrainingTask.from_engine(task_id=task_id, training_engine=engine)

        if not gm.add_task(training_task):
            logger.error(f"Failed to add training task {task_id} to task manager")
            return None

        # Return the initial state
        return initial_state

    def list_jobs(self) -> List[TrainingState]:
        """
        List all training jobs

        Returns:
            List of TrainingState objects
        """
        states_meta = self._load_metadata()

        jobs = []
        for task_id, state_dict in states_meta.items():
            try:
                state = TrainingState.from_dict(state_dict)
                jobs.append(state)
            except Exception as e:
                logger.error(f"Failed to parse training state for task {task_id}: {e}")
                continue

        # Sort by created_at descending (newest first)
        jobs.sort(key=lambda x: x.created_at or "", reverse=True)
        return jobs

    def get_job(self, job_id: str) -> Optional[TrainingState]:
        """
        Get a specific training job by ID

        Args:
            job_id: Job identifier (task_id)

        Returns:
            TrainingState if found, None otherwise
        """
        states_meta = self._load_metadata()
        state_dict = states_meta.get(job_id)

        if not state_dict:
            return None

        try:
            return TrainingState.from_dict(state_dict)
        except Exception as e:
            logger.error(f"Failed to parse training state for job {job_id}: {e}")
            return None

    def get_current_job(self) -> Optional[TrainingState]:
        """
        Get the currently running training job from task manager

        Returns:
            TrainingState with live metrics if training is active, None otherwise
        """
        task = gm.get_current_task()
        if not task:
            return None

        # Check if it's a training task
        engine = task.unwrap()
        if not isinstance(engine, BaseTrainingEngine):
            return None

        # Get live state from engine
        live_state = engine.get_state()

        return live_state

    def delete_job(self, job_id: str) -> bool:
        """
        Delete a training job (only if not currently running)

        Args:
            job_id: Job identifier (task_id)

        Returns:
            True if deleted, False if not found or currently running
        """
        # Check if this job is currently running
        current_job = self.get_current_job()
        if current_job and current_job.task_id == job_id:
            logger.warning(f"Cannot delete job {job_id}: currently running")
            return False

        # Delete from training state metadata
        states_meta = self._load_metadata()
        if job_id not in states_meta:
            return False

        del states_meta[job_id]
        self._save_metadata(states_meta)

        # TODO: Delete saved LoRA files if needed
        # lora_files = state.get('lora_files', [])
        # for lora_file in lora_files:
        #     # Delete lora_file

        return True

    def delete_jobs_batch(self, job_ids: List[str]) -> dict:
        """
        Delete multiple training jobs in batch

        Args:
            job_ids: List of job identifiers (task_ids)

        Returns:
            Dictionary with deletion results
        """
        deleted_ids = []
        failed_ids = []

        for job_id in job_ids:
            if self.delete_job(job_id):
                deleted_ids.append(job_id)
            else:
                failed_ids.append(job_id)

        return {
            'deleted_count': len(deleted_ids),
            'failed_count': len(failed_ids),
            'deleted_ids': deleted_ids,
            'failed_ids': failed_ids
        }
