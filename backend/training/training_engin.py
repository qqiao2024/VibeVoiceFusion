
from datetime import datetime
from vibevoice.training.summary_visitor import SummaryVisitor
from vibevoice.training.trainer import TrainConfig, VibeVoiceTrainer
from vibevoice.training.trainer_visitor import TrainerVisitor, VisitorManager

class TrainingStatus:
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
    estimated_end_time: datetime = None

    latest_epoch_elapsed: float = 0.0
    latest_step_elapsed: float = 0.0

    status: str = "Prepare"  # Prepare, Training, Completed, Failed
    average_step_time: float = 0.0
    steps_per_second: float = 0.0
    

class BaseTrainingEngine(TrainerVisitor):


    def __init__(self, trainer):
        self.trainer = trainer

    def train(self):
        self.trainer.train()

    def visit_training_begin(self, timestamp: float, batch_size: int, total_epochs: int, lr_rate: float, accumlate_grad_steps: int, data_repeat: int):
        pass

    def visit_training_end(self, timestamp: float, loss: float, diffusion_loss: float, ce_loss: float, total_elapsed: float, total_run_steps: int, total_run_epochs: int):
        pass

    def visit_step_begin(self, timestemp: float, step: int, epoch: int, step_in_epoch: int, lr: float, global_step: int):
        pass

    def visit_step_end(self, timestamp: float, step: int, epoch: int, step_in_epoch: int, lr: float, global_step: int, loss: float, diffusion_loss: float, ce_loss: float, step_elapsed: float):
        pass

    def visit_epoch_begin(self, timestamp: float, epoch: int, lr: float):
        pass
   

class TrainingEngine(BaseTrainingEngine):
    """
    Visitor for updating training status.

    This visitor updates the training status including:
    - Current step and epoch
    - Learning rate
    - Loss values (total, diffusion, cross-entropy)
    """

    def __init__(self, training_config: TrainConfig, task_id: str):
        vm = VisitorManager()
        vm.register_visitors(self)

        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_prefix = f"./tensorboard_logs/{training_config.lora_name}_{task_id}_{now}"
        vm.register_visitors(SummaryVisitor(
            log_prefix=log_prefix,
            step_loss_interval=training_config.step_loss_interval
        ))
        trainer = VibeVoiceTrainer(training_config, vm)
        super().__init__(trainer)

    

