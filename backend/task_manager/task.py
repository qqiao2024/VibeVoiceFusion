import threading

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from time import sleep

import torch
from util.logger import get_logger

logger = get_logger(__name__)

FAILURE_TYPE_GENERAL = "general"
FAILURE_TYPE_OOM = "out_of_memory"

class Task(ABC):

    def __init__(self, task_id: str = None):
        self.task_id = task_id

    def id(self) -> str:
        return self.task_id

    @abstractmethod
    def run(self):
        pass

    @abstractmethod
    def task_failure(self, error_msg: str, failure_type: str = FAILURE_TYPE_GENERAL):
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
            except torch.cuda.OutOfMemoryError as e:
                logger.error("TaskManager task_run_loop CUDA OOM error:", exc_info=e)
                if self.task is not None:
                    self.task.task_failure("CUDA Out of Memory Error", failure_type=FAILURE_TYPE_OOM)
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

    def has_task(self) -> bool:
        return self.task is not None


gm = Manager()
threading.Thread(target=gm.task_run_loop, daemon=True).start()
