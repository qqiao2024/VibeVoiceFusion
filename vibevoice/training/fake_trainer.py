import os

from typing import Optional
from datetime import datetime

from util.logger import get_logger

from vibevoice.training.trainer_visitor import TrainerVisitor
from vibevoice.training.trainer import Trainer, TrainConfig

logger = get_logger(__name__)

class FakeTrainer(Trainer):
    def __init__(self,
                 train_config: TrainConfig,
                 visitor: Optional[TrainerVisitor] = None,
                 simulated_steps_per_epoch: int = 1000):
        super().__init__(train_config, visitor)
        self.simulated_steps_per_epoch = simulated_steps_per_epoch  # Simulated number of steps per epoch

    def _train(self):
        import time
        import random

        logger.info("FakeTrainer: Starting simulated training...")

        metadata = self.train_config.to_metadata()
        logger.info(f"Training configuration: {metadata}")

        # Set random seed for reproducible simulation
        random.seed(self.train_config.seeds)

        start_time = datetime.now()
        gradient_accumulation_steps = self.train_config.gradient_accumulation_steps

        # Calculate total steps
        steps_per_epoch = self.simulated_steps_per_epoch * self.train_config.dataset_repeats
        total_steps = self.train_config.epochs * steps_per_epoch

        logger.info(f"Simulated training: {self.train_config.epochs} epochs | "
                    f"~{total_steps} total steps | batch_size: {self.train_config.batch_size} | "
                    f"gradient_accumulation_steps: {gradient_accumulation_steps}")

        # Notify training begin
        self.visitor.visit_training_begin(
            timestamp=start_time.timestamp(),
            batch_size=self.train_config.batch_size,
            total_epochs=self.train_config.epochs,
            lr_rate=self.train_config.learning_rate,
            accumlate_grad_steps=gradient_accumulation_steps,
            data_repeat=self.train_config.dataset_repeats
        )

        global_step = 0
        # Initialize loss values with typical starting values
        base_loss = 5.0 + random.uniform(-0.5, 0.5)
        base_ce_loss = 2.0 + random.uniform(-0.2, 0.2)
        base_diffusion_loss = 0.3 + random.uniform(-0.05, 0.05)

        # Loss decay factor per epoch (simulates learning)
        loss_decay = 0.85

        for epoch in range(self.train_config.epochs):
            logger.info(f"\nEpoch {epoch + 1}/{self.train_config.epochs}")
            epoch_start_time = datetime.now()

            # Notify epoch begin
            self.visitor.visit_epoch_begin(
                timestamp=epoch_start_time.timestamp(),
                epoch=epoch + 1,
                lr=self.train_config.learning_rate
            )

            epoch_loss_sum = 0.0
            epoch_ce_loss_sum = 0.0
            epoch_diffusion_loss_sum = 0.0
            epoch_steps = 0

            # Calculate current epoch's base losses (with decay)
            _ = base_loss * (loss_decay ** epoch)
            epoch_base_ce_loss = base_ce_loss * (loss_decay ** epoch)
            epoch_base_diffusion_loss = base_diffusion_loss * (loss_decay ** epoch)

            for repeat in range(self.train_config.dataset_repeats):
                for step in range(self.simulated_steps_per_epoch):
                    step_start_time = datetime.now()

                    # Notify step begin
                    self.visitor.visit_step_begin(
                        timestamp=step_start_time.timestamp(),
                        step=step + 1,
                        epoch=epoch + 1,
                        step_in_epoch=step + 1 + repeat * self.simulated_steps_per_epoch,
                        lr=self.train_config.learning_rate,
                        global_step=global_step
                    )

                    # Simulate step processing time (10-50ms)
                    time.sleep(random.uniform(0.01, 0.05))

                    global_step += 1
                    epoch_steps += 1

                    # Simulate losses with some noise
                    _ = random.uniform(-0.1, 0.1)
                    step_progress = global_step / total_steps

                    ce_loss = epoch_base_ce_loss * (1 - step_progress * 0.3) + random.uniform(-0.05, 0.05)
                    diffusion_loss = epoch_base_diffusion_loss * (1 - step_progress * 0.3) + random.uniform(-0.01, 0.01)
                    ce_component = self.train_config.ce_loss_weight * ce_loss
                    diff_component = self.train_config.diffusion_loss_weight * diffusion_loss
                    real_loss = ce_component + diff_component

                    # Accumulate for epoch averages
                    epoch_loss_sum += real_loss
                    epoch_ce_loss_sum += ce_loss
                    epoch_diffusion_loss_sum += diffusion_loss

                    step_end_time = datetime.now()
                    step_elapsed = (step_end_time - step_start_time).total_seconds()

                    # Notify step end
                    self.visitor.visit_step_end(
                        timestamp=step_end_time.timestamp(),
                        step=step + 1,
                        epoch=epoch + 1,
                        step_in_epoch=epoch_steps,
                        lr=self.train_config.learning_rate,
                        global_step=global_step,
                        loss=real_loss,
                        diffusion_loss=diffusion_loss,
                        ce_loss=ce_loss,
                        step_elapsed=step_elapsed
                    )

            # Calculate epoch averages
            epoch_avg_loss = epoch_loss_sum / epoch_steps if epoch_steps > 0 else 0.0
            epoch_avg_ce_loss = epoch_ce_loss_sum / epoch_steps if epoch_steps > 0 else 0.0
            epoch_avg_diffusion_loss = epoch_diffusion_loss_sum / epoch_steps if epoch_steps > 0 else 0.0

            epoch_end_time = datetime.now()
            epoch_elapsed = (epoch_end_time - epoch_start_time).total_seconds()

            logger.info(f"Epoch {epoch + 1} completed | loss: {epoch_avg_loss:.4f} | "
                        f"ce_loss: {epoch_avg_ce_loss:.4f} | diffusion_loss: {epoch_avg_diffusion_loss:.4f}")

            # Notify epoch end
            self.visitor.visit_epoch_end(
                timestamp=epoch_end_time.timestamp(),
                epoch=epoch + 1,
                epoch_elapsed=epoch_elapsed,
                loss=epoch_avg_loss,
                diffusion_loss=epoch_avg_diffusion_loss,
                ce_loss=epoch_avg_ce_loss,
                total_run_steps=global_step,
                steps_in_epoch=epoch_steps
            )

            # Simulate checkpoint saving
            if self.train_config.save_model_per_num_epoch > 0 and (epoch + 1) % self.train_config.save_model_per_num_epoch == 0:
                logger.info(f"FakeTrainer: Simulated checkpoint save at epoch {epoch + 1}")
                ckpt_file = self.mock_save_model(epoch + 1, global_step)
                self.visitor.visit_lora_file_saved(ckpt_file)

        end_time = datetime.now()
        elapsed_time = end_time - start_time
        elapsed_seconds = elapsed_time.total_seconds()

        # Final loss values
        final_ce_loss = epoch_avg_ce_loss
        final_diffusion_loss = epoch_avg_diffusion_loss
        final_loss = epoch_avg_loss

        logger.info(f"FakeTrainer: Simulated training completed. Final loss: {final_loss:.4f}, "
                    f"ce_loss: {final_ce_loss:.4f}, diffusion_loss: {final_diffusion_loss:.4f}, "
                    f"total steps: {global_step}, elapsed: {elapsed_seconds:.2f}s")

        # Notify training end
        self.visitor.visit_training_end(
            timestamp=end_time.timestamp(),
            loss=final_loss,
            diffusion_loss=final_diffusion_loss,
            ce_loss=final_ce_loss,
            total_elapsed=elapsed_seconds,
            total_run_steps=global_step,
            total_run_epochs=self.train_config.epochs
        )

        file_name = self.mock_save_model(epoch + 1, global_step, is_final=True)
        self.visitor.visit_final_lora_file_saved(file_name)

    def mock_save_model(self, epoch_no: int, steps: int, is_final: bool = False) -> str:
        """Save a placeholder file simulating LoRA weights.

        Args:
            epoch_no: Current epoch number
            steps: Total training steps completed
            is_final: Whether this is the final model save

        Returns:
            The path to the saved file
        """
        os.makedirs(self.train_config.output_dir, exist_ok=True)
        now = datetime.now()
        suffix = "_final" if is_final else ""
        ckpt_file = os.path.join(
            self.train_config.output_dir,
            f"{self.train_config.lora_name}_{now.strftime('%m%d%H%M')}_{epoch_no}_{steps}{suffix}.safetensors"
        )

        # Write 1024 placeholder bytes
        with open(ckpt_file, 'wb') as f:
            f.write(b'\x00' * 1024)

        logger.info(f"FakeTrainer: Mock model saved to {ckpt_file}")
        return ckpt_file

    def training_cleanup(self):
        """Cleanup resources after training if needed."""
        logger.info("FakeTrainer: Cleaning up resources after training.")
