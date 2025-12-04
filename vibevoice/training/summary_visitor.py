import os
from torch.utils.tensorboard import SummaryWriter

from vibevoice.training.trainer_visitor import TrainerVisitor

class SummaryVisitor(TrainerVisitor):
    """
    Visitor for logging training metrics to TensorBoard.

    This visitor monitors and logs various training metrics including:
    - Loss values (total, diffusion, cross-entropy)
    - Learning rate
    - Training progress (steps, epochs)
    - Timing information
    """

    def __init__(self, log_prefix: str = None, step_loss_interval: int = 100):
        if log_prefix is None:
            raise ValueError("log_prefix must be provided for SummaryVisitor.")

        os.makedirs(log_prefix, exist_ok=True)
        # Add comment parameter to help TensorBoard identify the run properly
        self.writer: SummaryWriter = SummaryWriter(log_dir=log_prefix, comment="training")
        self.start_timestamp = None
        self.step_loss_interval = step_loss_interval

    def visit_training_begin(self, timestamp: float, batch_size: int, total_epochs: int, lr_rate: float, accumlate_grad_steps: int, data_repeat: int):
        """Log training hyperparameters at the beginning of training."""
        self.start_timestamp = timestamp

        # Log hyperparameters
        self.writer.add_text("hyperparameters/batch_size", str(batch_size), 0)
        self.writer.add_text("hyperparameters/total_epochs", str(total_epochs), 0)
        self.writer.add_text("hyperparameters/learning_rate", str(lr_rate), 0)
        self.writer.add_text("hyperparameters/gradient_accumulation_steps", str(accumlate_grad_steps), 0)
        self.writer.add_text("hyperparameters/data_repeat", str(data_repeat), 0)

        # Log as scalars for easy comparison
        self.writer.add_scalar("config/batch_size", batch_size, 0)
        self.writer.add_scalar("config/learning_rate", lr_rate, 0)
        self.writer.add_scalar("config/gradient_accumulation_steps", accumlate_grad_steps, 0)

        self.writer.flush()

    def visit_training_end(self, timestamp: float, loss: float, diffusion_loss: float, ce_loss: float, total_elapsed: float, total_run_steps: int, total_run_epochs: int):
        """Log final training statistics."""
        # Log final losses
        self.writer.add_scalar("final/total_loss", loss, total_run_steps)
        self.writer.add_scalar("final/diffusion_loss", diffusion_loss, total_run_steps)
        self.writer.add_scalar("final/ce_loss", ce_loss, total_run_steps)

        # Log training summary
        self.writer.add_text("summary/total_steps", str(total_run_steps), 0)
        self.writer.add_text("summary/total_epochs", str(total_run_epochs), 0)
        self.writer.add_text("summary/total_elapsed_seconds", f"{total_elapsed:.2f}", 0)
        self.writer.add_text("summary/final_loss", f"{loss:.6f}", 0)

        # Log timing metrics
        self.writer.add_scalar("timing/total_training_time", total_elapsed, total_run_steps)
        if total_run_steps > 0:
            avg_step_time = total_elapsed / total_run_steps
            self.writer.add_scalar("timing/avg_step_time", avg_step_time, total_run_steps)

        self.writer.flush()
        self.writer.close()

    def visit_step_begin(self, timestamp: float, step: int, epoch: int, step_in_epoch: int, lr: float, global_step: int):
        """Called at the beginning of each training step."""
        # Log learning rate at step begin
        self.writer.add_scalar("train/learning_rate", lr, global_step)

    def visit_step_end(self, timestamp: float, step: int, epoch: int, step_in_epoch: int, lr: float, global_step: int, loss: float, diffusion_loss: float, ce_loss: float, step_elapsed: float):
        """Log step-level training metrics."""
        if self.step_loss_interval > 0 and global_step % self.step_loss_interval != 0:
            return

        # Log losses
        self.writer.add_scalar("train/loss", loss, global_step)
        self.writer.add_scalar("train/diffusion_loss", diffusion_loss, global_step)
        self.writer.add_scalar("train/ce_loss", ce_loss, global_step)

        # Log timing
        self.writer.add_scalar("timing/step_time", step_elapsed, global_step)

        # Log steps per second
        if step_elapsed > 0:
            steps_per_sec = 1.0 / step_elapsed
            self.writer.add_scalar("timing/steps_per_second", steps_per_sec, global_step)

        # Log progress within epoch
        self.writer.add_scalar("progress/step_in_epoch", step_in_epoch, global_step)
        self.writer.add_scalar("progress/current_epoch", epoch, global_step)

        # Flush periodically (every 10 steps)
        if global_step % 10 == 0:
            self.writer.flush()

    def visit_epoch_begin(self, timestamp: float, epoch: int, lr: float):
        """Called at the beginning of each epoch."""
        # Log epoch start
        self.writer.add_scalar("epoch/learning_rate", lr, epoch)

        if self.start_timestamp is not None:
            elapsed = timestamp - self.start_timestamp
            self.writer.add_scalar("timing/elapsed_time_at_epoch_start", elapsed, epoch)

    def visit_epoch_end(self, timestamp: float, epoch: int, epoch_elapsed: float, loss: float, diffusion_loss: float, ce_loss: float, total_run_steps: int):
        """Log epoch-level training metrics."""
        # Log epoch losses (average over the epoch)
        self.writer.add_scalar("epoch/loss", loss, epoch)
        self.writer.add_scalar("epoch/diffusion_loss", diffusion_loss, epoch)
        self.writer.add_scalar("epoch/ce_loss", ce_loss, epoch)

        # Log epoch timing
        self.writer.add_scalar("timing/epoch_time", epoch_elapsed, epoch)

        # Log cumulative training time
        if self.start_timestamp is not None:
            cumulative_time = timestamp - self.start_timestamp
            self.writer.add_scalar("timing/cumulative_training_time", cumulative_time, epoch)

        # Log total steps completed
        self.writer.add_scalar("progress/total_steps", total_run_steps, epoch)
        self.writer.flush()

    def visit_training_failed(self, timestamp, error_msg):
        pass

    def visit_lora_file_saved(self, lora_file: str):
        pass

    def visit_final_lora_file_saved(self, lora_file: str):
        pass
