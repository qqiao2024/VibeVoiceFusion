from backend.task_manager.task import FAILURE_TYPE_GENERAL, Task
from typing import Any, Dict, List
from backend.inference.inference import InferenceBase
from config.configuration_vibevoice import InferencePhase
from utils.file_handler import FileHandler
from pathlib import Path

from util.logger import get_logger

logger = get_logger(__name__)

class InferenceTask(Task):

    def __init__(self, inference: InferenceBase, file_handler: FileHandler, meta_file_path: str):
        super().__init__(task_id=inference.request_id)
        self.inference = inference
        self.file_handler = file_handler
        self.meta_file_path = meta_file_path

    @classmethod
    def from_inference(cls, inference: InferenceBase, file_handler: FileHandler, meta_file_path: str) -> 'Task':
        return cls(inference, file_handler, meta_file_path)

    def run(self):
        logger.info(f"generation id{self.inference.request_id} is created, "
                    "now running")
        self.inference.run_inference()

    def task_failure(self, error_msg: str, failure_type: str = FAILURE_TYPE_GENERAL):
        logger.error(f"generation id{self.inference.request_id} running failed, error: {error_msg}")
        self.inference.failure(error_msg, failure_type)

    def task_success(self, message: str):
        logger.info(f"Inference task completed successfully: {message}")
        self.inference.success(message)

    def unwrap(self) -> InferenceBase:
        return self.inference

    def task_appended(self, message: str):
        generations = self._load_metadata()
        generations.append(self.inference.generation_info())
        self._save_metadata(generations)

    def _task_finalize(self):
        try:
            self._update_metadata(self.inference.generation_info())
        except Exception as e:
            logger.warning(f"Ignored with the inference task finalize failed for task {self.task_id}:", exc_info=e)
            pass

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
