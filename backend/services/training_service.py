from flask import current_app

from pathlib import Path
from uuid import uuid4
from typing import List, Optional
from datetime import datetime, timezone
import shutil

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

    def __init__(self, project_training_dir: Path, project_id: str = None, fake_engine: bool = False):
        """
        Initialize training service for a specific project

        Args:
            project_training_dir: Path to project's training directory
            project_id: Project identifier (used to filter current job)
            fake_engine: Use FakeTrainingEngine for development
        """
        self.output_dir = Path(project_training_dir)
        self.meta_file_path = self.output_dir / self.TRAINING_META_FILE
        self.file_handler = FileHandler()
        self.fake_engine = fake_engine
        self.project_id = project_id

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

    def _is_job_name_unique(self, job_name: str) -> bool:
        """
        Check if job name is unique across all training jobs

        Args:
            job_name: Job name to check

        Returns:
            True if unique, False if duplicate exists
        """
        states_meta = self._load_metadata()
        for state_dict in states_meta.values():
            if state_dict.get('job_name') == job_name:
                return False
        return True

    def create_training_job(self, job_name: str, train_config: TrainConfig,
                            project_id: str) -> Optional[TrainingState]:
        """
        Create and start a new training job

        Args:
            job_name: Human-readable job name (must be unique)
            train_config: Training configuration
            project_id: Project identifier

        Returns:
            TrainingState if successful, None if task queue is busy

        Raises:
            ValueError: If job_name is not unique
        """
        # Check if job name is unique
        if not self._is_job_name_unique(job_name):
            raise ValueError(f"Job name '{job_name}' already exists. Please choose a unique name.")

        # Check if task manager is busy
        if gm.has_task():
            logger.warning("Task manager is busy, cannot start new training job")
            return None

        # Create task_id
        task_id = uuid4().hex
        train_config.model_path = f"{current_app.config['MODEL_PATH']}/vibevoice7b_{'bf16' if train_config.dtype == 'bfloat16' else 'float8_e4m3fn'}.safetensors"

        # Auto-generate output_dir based on workspace/project/job_name
        # Path format: {workspace}/{project}/training/lora_output/{job_name}
        lora_output_dir = self.output_dir / "lora_output" / job_name
        train_config.output_dir = str(lora_output_dir)

        # Initialize TrainingState with metadata
        initial_state = TrainingState(
            task_id=task_id,
            job_name=job_name,
            project_id=project_id,
            config=train_config.to_dict(),
            created_at=datetime.now(timezone.utc).isoformat(),
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
        List all training jobs and detect orphaned 'Training' status jobs

        If a job has status 'Training' but there's no active training task,
        it means the job was interrupted (e.g., server restart). Mark it as 'Failed'.

        Returns:
            List of TrainingState objects
        """
        states_meta = self._load_metadata()
        current_task = gm.get_current_task()
        current_training_task_id = None

        # Check if there's a current training task
        if current_task:
            engine = current_task.unwrap()
            if isinstance(engine, BaseTrainingEngine):
                current_training_task_id = current_task.task_id

        jobs = []
        states_updated = False

        for task_id, state_dict in states_meta.items():
            try:
                state = TrainingState.from_dict(state_dict)

                # Detect orphaned 'Training' status jobs
                if (state.status == "Training" or state.status == "Prepare") and task_id != current_training_task_id:
                    logger.warning(f"Detected orphaned training job {task_id}, marking as Failed")
                    state.status = "Failed"
                    state.error_message = "Training interrupted (server restart or crash)"

                    # Update metadata
                    states_meta[task_id] = state.to_dict()
                    states_updated = True

                jobs.append(state)
            except Exception as e:
                logger.error(f"Failed to parse training state for task {task_id}: {e}")
                continue

        # Save updated metadata if any jobs were marked as failed
        if states_updated:
            self._save_metadata(states_meta)

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
        Get the currently running training job from task manager, or the most recent
        completed/failed job if it finished within the last 10 seconds.

        Only returns jobs that belong to this service's project_id.

        Returns:
            TrainingState with live metrics if training is active,
            or recently completed/failed state, None otherwise
        """
        task = gm.get_current_task()

        # If there's an active task, return its live state (if it belongs to this project)
        if task:
            engine = task.unwrap()
            if isinstance(engine, BaseTrainingEngine):
                live_state = engine.get_state()
                # Only return if the task belongs to this project
                if self.project_id and live_state.project_id != self.project_id:
                    # Task is running but for a different project
                    return None
                return live_state
            elif engine is not None:
                # current is inference task, ignored for training
                return None

        # No active task - check if there's a recently completed/failed job
        # This helps the frontend catch the final state in fast-completing jobs (FAKE_MODEL)
        states_meta = self._load_metadata()
        if not states_meta:
            return None

        # Find the most recent completed or failed job (for this project)
        recent_jobs = []
        for state_dict in states_meta.values():
            try:
                state = TrainingState.from_dict(state_dict)
                if state.status in ['Completed', 'Failed'] and state.current_timestamp:
                    recent_jobs.append(state)
            except Exception:
                continue

        if not recent_jobs:
            return None

        # Sort by current_timestamp (most recent first)
        recent_jobs.sort(key=lambda x: x.current_timestamp or datetime.min, reverse=True)
        most_recent = recent_jobs[0]

        # Only return if completed within the last 10 seconds (to catch fast completions)
        if most_recent.current_timestamp:
            elapsed = (datetime.now(timezone.utc) - most_recent.current_timestamp).total_seconds()
            if elapsed <= 10:
                return most_recent

        return None

    def get_lora_file_path(self, job_id: str, filename: str) -> Optional[Path]:
        """
        Get the full path to a LoRA file for a specific job

        Args:
            job_id: Job identifier (task_id)
            filename: LoRA filename from state.lora_files (can be full path or just filename)

        Returns:
            Path to the LoRA file if exists, None otherwise
        """
        state = self.get_job(job_id)
        if not state or state.status != "Completed":
            return None

        if not state.config or not state.config.get('output_dir'):
            return None

        # Extract just the filename in case full path is stored
        filename_only = Path(filename).name

        lora_file_path = Path(state.config['output_dir']) / filename_only
        if lora_file_path.exists() and lora_file_path.is_file():
            return lora_file_path

        return None

    def delete_job(self, job_id: str) -> bool:
        """
        Delete a training job (only if completed)

        Args:
            job_id: Job identifier (task_id)

        Returns:
            True if deleted, False if not found, not completed, or currently running
        """
        # Get job state
        states_meta = self._load_metadata()
        if job_id not in states_meta:
            return False

        try:
            state = TrainingState.from_dict(states_meta[job_id])
        except Exception as e:
            logger.error(f"Failed to parse training state for job {job_id}: {e}")
            return False

        # Only allow deletion of completed jobs
        if state.status == "Prepare" or state.status == "Training":
            logger.warning(f"Cannot delete job {job_id}: status is {state.status}, only Completed jobs can be deleted")
            return False

        # Delete LoRA files if they exist
        if state.config and state.config.get('output_dir'):
            lora_output_path = Path(state.config['output_dir'])
            if lora_output_path.exists() and lora_output_path.is_dir():
                try:
                    shutil.rmtree(lora_output_path)
                    logger.info(f"Deleted LoRA files for job {job_id} at {lora_output_path}")
                except Exception as e:
                    logger.error(f"Failed to delete LoRA files for job {job_id}: {e}")
                    # Continue with metadata deletion even if file deletion fails

        # Delete from training state metadata
        del states_meta[job_id]
        self._save_metadata(states_meta)

        return True

    def list_available_lora_files(self) -> List[dict]:
        """
        List all available LoRA files in the project's lora_output directory

        Returns:
            List of dictionaries with display_name (relative path) and full_path (absolute path)
        """
        lora_output_dir = self.output_dir / "lora_output"

        if not lora_output_dir.exists():
            return []

        lora_files = []

        # Iterate through subdirectories in lora_output
        for lora_dir in lora_output_dir.iterdir():
            if not lora_dir.is_dir():
                continue

            # Find all safetensors files in the directory
            safetensors_files = list(lora_dir.glob("*.safetensors"))
            if not safetensors_files:
                continue

            # Add ALL safetensors files, sorted with _final files first
            for target_file in sorted(safetensors_files,
                                       key=lambda f: (0 if f.name.endswith("_final.safetensors") else 1, f.name)):
                # Create display name: lora_name/filename.safetensors
                display_name = f"{lora_dir.name}/{target_file.name}"

                lora_files.append({
                    'display_name': display_name,
                    'full_path': str(target_file),
                    'lora_name': lora_dir.name,
                    'filename': target_file.name
                })

        # Sort by lora_name, then by filename (with _final first)
        lora_files.sort(key=lambda x: (x['lora_name'], 0 if x['filename'].endswith("_final.safetensors") else 1, x['filename']))

        return lora_files

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
