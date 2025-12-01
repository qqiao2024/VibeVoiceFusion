import threading

from abc import ABC, abstractmethod
from pathlib import Path

from time import sleep
from typing import Any, Dict, List
from backend.inference.inference import InferenceBase
from backend.models.generation import Generation
from config.configuration_vibevoice import InferencePhase
from utils.file_handler import FileHandler
from util.logger import get_logger

logger = get_logger(__name__)

class Task(ABC):

    def __init__(self, task_id: str = None):
        self.task_id = task_id

    def id(self) -> str:
        return self.task_id

    @abstractmethod
    def run(self):
        pass

    @abstractmethod
    def task_failure(self, error_msg: str):
        pass

    @abstractmethod
    def task_success(self, message: str):
        pass

    @abstractmethod
    def task_appended(self, message: str):
        pass

    @abstractmethod
    def unwrap(self) -> Any:
        pass

    def task_finalize(self):
        try:
            self._task_finalize()
        except Exception as e:
            logger.warning(f"Task finalized failed {self.task_id} finalize failed:", exc_info=e)
        pass

    @abstractmethod
    def _task_finalize(self):
        pass

class InferenceTask(Task):

    def __init__(self, inference: InferenceBase, file_handler: FileHandler, meta_file_path: str):
        super().__init__(task_id=inference.generation.request_id)
        self.inference = inference
        self.file_handler = file_handler
        self.meta_file_path = meta_file_path

    @classmethod
    def from_inference(cls, inference: InferenceBase, file_handler: FileHandler, meta_file_path: str) -> 'Task':
        return cls(inference, file_handler, meta_file_path)

    def run(self):
        logger.info(f"generation id{self.inference.generation.request_id} is created, "
                    "now running")
        self.inference.run_inference(status_update=self.inference.generation.update_status)

    def task_failure(self, error_msg: str):
        logger.error(f"generation id{self.inference.generation.request_id} running failed, error: {error_msg}")
        self.inference.generation.status = InferencePhase.FAILED

    def task_success(self, message: str):
        logger.info(f"Inference task completed successfully: {message}")
        self.inference.generation.status = InferencePhase.COMPLETED

    def unwrap(self) -> InferenceBase:
        return self.inference

    def task_appended(self, message: str):
        generations = self._load_metadata()
        generations.append(self.inference.generation.to_dict())
        self._save_metadata(generations)

    def _task_finalize(self):
        self._update_metadata(self.inference.generation.to_dict())

    def _load_metadata(self) -> List[Dict[str, Any]]:
        """
        Load generation metadata from JSON file

        Returns:
            List of generation dictionaries
        """
        try:
            data = self.file_handler.read_json(self.meta_file_path)
            # Ensure it's a list
            if isinstance(data, list):
                return data
            return []
        except FileNotFoundError:
            return []
        except Exception as e:
            raise RuntimeError(f"Failed to load generation metadata: {str(e)}")

    def _save_metadata(self, generations: List[Dict[str, Any]]) -> None:
        """
        Atomically save generation metadata to JSON file

        Args:
            generations: List of generation dictionaries
        """
        try:
            self.file_handler.write_json(Path(self.meta_file_path), generations)
        except Exception as e:
            raise RuntimeError(f"Failed to save generation metadata: {str(e)}")

    def _update_metadata(self, generation_dict: Dict[str, Any]) -> None:
        generations = self._load_metadata()
        for i, gen in enumerate(generations):
            if gen['request_id'] == generation_dict['request_id']:
                generations[i] = generation_dict
                break
        self._save_metadata(generations)

class Manager:
    def __init__(self):
        self.task: Task = None

    def task_run_loop(self):
        while True:
            try:
                if self.task is not None:
                    self.task.run()
                    self.task.task_success("Task run completed successfully.")
            except Exception as e:
                logger.error("TaskManager task_run_loop error:", exc_info=e)
                if self.task is not None:
                    self.task.task_failure(str(e))
            finally:
                if self.task is not None:
                    self.task._task_finalize()
                self.task = None

            sleep(0.5)

    def add_task(self, task: Task) -> bool:
        if self.task is None:
            self.task = task
            self.task.task_appended("Task added to the manager.")
            logger.info(f"Added task id{self.task.id()} to current inference")
            return True
        else:
            logger.warning(f"Cannot add task id{self.task.id()}, another "
                           f"inference {self.task.id()} is in progress")
            return False

    def get_current_task(self) -> Task:
        if self.task is not None:
            return self.task
        return None


gm = Manager()
threading.Thread(target=gm.task_run_loop, daemon=True).start()
