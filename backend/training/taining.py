from vibevoice.training.trainer import Trainer

class FakeTrainer(Trainer):
    def __init__(self):
        pass

    def train(self, *args, **kwargs):
        # Simulate a forward pass and return fake losses
        pass


class TrainBase:
    def __init__(self, trainer: Trainer):
        self.trainer = trainer

    def run_training(self):
        # Simulate training process
        pass

