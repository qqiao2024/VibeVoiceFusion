from typing import Optional
from dataclasses import dataclass
from torch import nn
    

@dataclass
class TrainConfig:
    epochs: int = 10
    batch_size: int = 1
    learning_rate: float = 1e-4
    dataset_path: Optional[str] = None
    output_dir: Optional[str] = None
    lora_dim: int = 4
    lora_alpha: Optional[float] = None
    lora_dropout: Optional[float] = None


class VibeVoiceTrainer:

    def __init__(self, train_config):
        self.train_config = train_config
    
    def train(self):
        pass
    
    
    
    