from abc import ABC, abstractmethod

class TrainerVisitor(ABC):
    @abstractmethod
    def visit_training_begin(self, timestamp: float, batch_size: int, total_epochs: int, lr_rate: float, accumlate_grad_steps: int, data_repeat: int):
        pass

    @abstractmethod
    def visit_training_end(self, timestamp: float, loss: float, diffusion_loss: float, ce_loss: float, total_elapsed: float, total_run_steps: int, total_run_epochs: int):
        pass

    @abstractmethod
    def visit_step_begin(self, timestemp: float, step: int, epoch: int, step_in_epoch: int, lr: float, global_step: int):
        pass

    @abstractmethod
    def visit_step_end(self, timestamp: float, step: int, epoch: int, step_in_epoch: int, lr: float, global_step: int, loss: float, diffusion_loss: float, ce_loss: float, step_elapsed: float):
        pass

    @abstractmethod
    def visit_epoch_begin(self, timestamp: float, epoch: int, lr: float):
        pass

    @abstractmethod
    def visit_epoch_end(self, timestamp: float, epoch: int, epoch_elapsed: float, loss: float, diffusion_loss: float, ce_loss: float, total_run_steps: int):
        pass
    
    @abstractmethod
    def visit_training_failed(self, timestamp: float, error_msg: str):
        pass

    @abstractmethod
    def lora_file_saved(self, lora_file: str):
        pass

    @abstractmethod
    def final_lora_file_saved(self, lora_file: str):
        pass


class VisitorManager(TrainerVisitor):
    def __init__(self):
        self.visitors = []

    def register_visitor(self, visitor: TrainerVisitor):
        self.visitors.append(visitor)

    def visit_training_begin(self, timestamp: float, batch_size: int, total_epochs: int, lr_rate: float, accumlate_grad_steps: int, data_repeat: int):
        for visitor in self.visitors:
            visitor.visit_training_begin(timestamp, batch_size, total_epochs, lr_rate, accumlate_grad_steps, data_repeat)

    def visit_training_end(self, timestamp: float, loss: float, diffusion_loss: float, ce_loss: float, total_elapsed: float, total_run_steps: int, total_run_epochs: int):
        for visitor in self.visitors:
            visitor.visit_training_end(timestamp, loss, diffusion_loss, ce_loss, total_elapsed, total_run_steps, total_run_epochs)

    def visit_step_begin(self, timestemp: float, step: int, epoch: int, step_in_epoch: int, lr: float, global_step: int):
        for visitor in self.visitors:
            visitor.visit_step_begin(timestemp, step, epoch, step_in_epoch, lr, global_step)

    def visit_step_end(self, timestamp: float, step: int, epoch: int, step_in_epoch: int, lr: float, global_step: int, loss: float, diffusion_loss: float, ce_loss: float, step_elapsed: float):
        for visitor in self.visitors:
            visitor.visit_step_end(timestamp, step, epoch, step_in_epoch, lr, global_step, loss, diffusion_loss, ce_loss, step_elapsed)

    def visit_epoch_begin(self, timestamp: float, epoch: int, lr: float):
        for visitor in self.visitors:
            visitor.visit_epoch_begin(timestamp, epoch, lr)

    def visit_epoch_end(self, timestamp: float, epoch: int, epoch_elapsed: float, loss: float, diffusion_loss: float, ce_loss: float, total_run_steps: int):
        for visitor in self.visitors:
            visitor.visit_epoch_end(timestamp, epoch, epoch_elapsed, loss, diffusion_loss, ce_loss, total_run_steps)

    def visit_training_failed(self, timestamp: float, error_msg: str):
        for visitor in self.visitors:
            visitor.visit_training_failed(timestamp, error_msg)

    def lora_file_saved(self, lora_file: str):
        for visitor in self.visitors:
            visitor.lora_file_saved(lora_file)

    def final_lora_file_saved(self, lora_file: str):
        for visitor in self.visitors:
            visitor.final_lora_file_saved(lora_file)