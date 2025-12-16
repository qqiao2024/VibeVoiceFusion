
from datetime import datetime, timezone
from backend.training.state import TrainingState, TrainingStateWriter

from vibevoice.training.summary_visitor import SummaryVisitor
from vibevoice.training.trainer import TrainConfig, VibeVoiceTrainer, Trainer
from vibevoice.training.fake_trainer import FakeTrainer
from vibevoice.training.trainer_visitor import TrainerVisitor, VisitorManager
from util.logger import get_logger

logger = get_logger(__name__)

class BaseTrainingEngine(TrainerVisitor):

    def __init__(self, trainer: Trainer, task_id: str, state_writer: TrainingStateWriter,
                 update_step_interval: int = 5,
                 initial_state: TrainingState = None):
        self.trainer = trainer
        self.state = initial_state if initial_state else TrainingState()
        self.epoch_start_time = None
        self.step_start_time = None
        self.state_writer = state_writer
        self.update_step_interval = update_step_interval
        self.task_id = task_id
        self.estimated_time_by_epoch = 0.0

    def train(self):
        self.trainer.train()

    def visit_training_begin(self, timestamp: float, batch_size: int, total_epochs: int,
                             lr_rate: float, accumlate_grad_steps: int, data_repeat: int):
        self.state.status = "Training"
        self.state.start_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        self.state.current_timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        self.state.current_step = 0
        self.state.learning_rate = lr_rate
        self.state.total_epochs = total_epochs
        self.state.batch_size = batch_size
        self.state.accumlate_grad_steps = accumlate_grad_steps

    def visit_training_end(self, timestamp: float, loss: float, diffusion_loss: float,
                           ce_loss: float, total_elapsed: float, total_run_steps: int,
                           total_run_epochs: int):
        self.state.status = "Completed"
        self.state.current_timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        self.state.current_loss = loss
        self.state.current_diffusion_loss = diffusion_loss
        self.state.current_ce_loss = ce_loss
        self.state.estimated_total_steps = total_run_steps
        self.state.estimated_total_elpase = total_elapsed
        self.state_writer.update_state(self.state)

    def visit_step_begin(self, timestamp: float, step: int, epoch: int,
                         step_in_epoch: int, lr: float, global_step: int):
        self.step_start_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        self.state.current_step = global_step
        self.state.learning_rate = lr
        self.state.current_timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        self.state.current_epoch = epoch

    def visit_step_end(self, timestamp: float, step: int, epoch: int, step_in_epoch: int, lr: float,
                       global_step: int, loss: float, diffusion_loss: float, ce_loss: float, step_elapsed: float):
        self.state.current_timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        self.state.current_loss = loss
        self.state.current_diffusion_loss = diffusion_loss
        self.state.current_ce_loss = ce_loss
        if step_elapsed is not None and step_elapsed > 0:
            self.state.latest_step_elapsed = step_elapsed
        else:
            self.state.latest_step_elapsed = (self.state.current_timestamp - self.step_start_time).total_seconds()

        self.state.average_step_time = (self.state.current_timestamp - self.state.start_time).total_seconds() / global_step
        self.state.steps_per_second = global_step / (self.state.current_timestamp - self.state.start_time).total_seconds()
        self.state.steps_in_epoch = step_in_epoch

        if epoch > 1:
            estimated_total_elpase_by_epoch = (self.state.current_timestamp - self.state.start_time).total_seconds() + self.estimated_time_by_epoch
            remaining_steps_in_epoch = self.state.steps_per_epoch - step_in_epoch
            self.state.estimated_total_elpase = estimated_total_elpase_by_epoch + remaining_steps_in_epoch * self.state.average_step_time


        if global_step % self.update_step_interval == 0:
            self.state_writer.update_state(self.state)

    def visit_epoch_begin(self, timestamp: float, epoch: int, lr: float):
        self.state.current_epoch = epoch
        self.state.learning_rate = lr
        self.epoch_start_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)

    def visit_epoch_end(self, timestamp: float, epoch: int, lr: float, avg_loss: float, avg_diffusion_loss: float, avg_ce_loss: float, epoch_elapsed: float, steps_in_epoch: int):
        self.state.current_timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        self.state.latest_epoch_elapsed = (self.state.current_timestamp - self.epoch_start_time).total_seconds()
        self.state.average_epoch_loss = avg_loss
        self.state.average_epoch_diffusion_loss = avg_diffusion_loss
        self.state.average_epoch_ce_loss = avg_ce_loss
        self.state.current_epoch = epoch
        self.state_writer.update_state(self.state)
        self.state.steps_per_epoch = steps_in_epoch
        self.state.estimated_total_steps = self.state.total_epochs * steps_in_epoch
        self.state.lr = lr
        self.state_writer.update_state(self.state)
        remaining_epochs = self.state.total_epochs - epoch - 1
        if remaining_epochs > 0:
            self.estimated_time_by_epoch = remaining_epochs * self.state.latest_epoch_elapsed
        else:
            self.estimated_time_by_epoch = 0.0

    def visit_training_failed(self, timestamp, error_msg: str, failure_type: str = "general"):
        self.state.status = "Failed"
        if failure_type == "out_of_memory":
            self.state.is_oom_failure = True
        self.state_writer.update_state(self.state)

    def get_state(self) -> TrainingState:
        return self.state

    def visit_lora_file_saved(self, lora_file):
        return self.state.lora_files.append(lora_file)

    def visit_final_lora_file_saved(self, lora_file):
        self.state.final_lora_file = lora_file

    def finalize(self):
        self.state_writer.update_state(self.state)


class TrainingEngine(BaseTrainingEngine):
    """
    Visitor for updating training status.

    This visitor updates the training status including:
    - Current step and epoch
    - Learning rate
    - Loss values (total, diffusion, cross-entropy)
    """

    def __init__(self,
                 training_config: TrainConfig,
                 task_id: str,
                 state_writer: TrainingStateWriter,
                 update_step_interval: int = 5,
                 initial_state: TrainingState = None):
        vm = VisitorManager()
        vm.register_visitor(self)

        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_prefix = f"./tensorboard_logs/{training_config.lora_name}_{task_id}_{now}"
        vm.register_visitor(SummaryVisitor(
            log_prefix=log_prefix,
        ))
        trainer = VibeVoiceTrainer(training_config, vm)
        initial_state.tensorboard_logdir = log_prefix
        super().__init__(trainer, task_id, state_writer, update_step_interval, initial_state)

    def finalize(self):
        super().finalize()
        self.trainer.training_cleanup()


class FakeTrainingEngine(BaseTrainingEngine):
    """
    A fake training engine for testing purposes.
    """

    def __init__(self,
                 training_config: TrainConfig,
                 task_id: str,
                 state_writer: TrainingStateWriter,
                 update_step_interval: int = 5,
                 initial_state: TrainingState = None):
        vm = VisitorManager()
        vm.register_visitor(self)

        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_prefix = f"./tensorboard_logs/{training_config.lora_name}_{task_id}_{now}"
        vm.register_visitor(SummaryVisitor(
            log_prefix=log_prefix,
        ))
        trainer = FakeTrainer(training_config, vm)
        initial_state.tensorboard_logdir = log_prefix

        super().__init__(trainer, task_id, state_writer, update_step_interval, initial_state)
