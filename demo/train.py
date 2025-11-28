import argparse
from uuid import uuid4
from vibevoice.training.trainer import TrainConfig, VibeVoiceTrainer
from vibevoice.training.summary_visitor import SummaryVisitor


parser = argparse.ArgumentParser(description="VibeVoice Training Script")
parser.add_argument('--train_config', type=str, required=True, help='Path to the training configuration file.')
parser.add_argument('--tensorboard_logdir', type=str, default="./tensorboard_logs", help='Directory for TensorBoard logs.')
args = parser.parse_args()

def main():
    train_config = TrainConfig.from_toml(args.train_config)
    visitor = SummaryVisitor(log_prefix=f"{args.tensorboard_logdir}/{uuid4().hex}", step_loss_interval=100)
    trainer = VibeVoiceTrainer(train_config, visitor=visitor)
    trainer.train()


if __name__ == "__main__":
    main()
