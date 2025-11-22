import argparse
from vibevoice.training.trainer import TrainConfig, VibeVoiceTrainer


parser = argparse.ArgumentParser(description="VibeVoice Training Script")
parser.add_argument('--train_config', type=str, required=True, help='Path to the training configuration file.')
args = parser.parse_args()

def main():
    train_config = TrainConfig.from_toml(args.train_config)
    trainer = VibeVoiceTrainer(train_config)
    trainer.train()


if __name__ == "__main__":
    main()
