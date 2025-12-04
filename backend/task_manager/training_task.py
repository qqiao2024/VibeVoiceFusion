
from backend.task_manager.task import Task
from backend.training.engine import BaseTrainingEngine

class TrainingTask(Task):

    def __init__(self, task_id: str, training_engine: BaseTrainingEngine):
        super().__init__(task_id=task_id)
        self.training_engine = training_engine

    @classmethod
    def from_engine(cls, task_id: str, training_engine: BaseTrainingEngine) -> 'Task':
        return cls(task_id, training_engine)

    def run(self):
        self.training_engine.train()

    def task_failure(self, error_msg: str):
        # Handle training failure logic here
        pass

    def task_success(self, message: str):
        # Handle training success logic here
        pass

    def unwrap(self) -> BaseTrainingEngine:
        return self.training_engine

    def task_appended(self, message: str):
        pass

    def _task_finalize(self):
        self.training_engine.finalize()
