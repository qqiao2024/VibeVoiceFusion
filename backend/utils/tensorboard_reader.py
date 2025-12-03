"""
Utility to read and parse TensorBoard event files
"""
import os
from typing import Dict, List, Optional
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator


class TensorBoardReader:
    """
    Reader for extracting metrics from TensorBoard event files
    """

    def __init__(self, logdir: str):
        """
        Initialize the reader with a log directory

        Args:
            logdir: Path to the tensorboard log directory
        """
        self.logdir = logdir
        self.event_acc = None

        if os.path.exists(logdir):
            self._load_events()

    def _load_events(self):
        """Load events from the log directory"""
        try:
            # Initialize EventAccumulator with size guidance
            # size_guidance controls how many events to keep in memory
            self.event_acc = EventAccumulator(
                self.logdir,
                size_guidance={
                    'scalars': 0,  # 0 means load all
                }
            )
            self.event_acc.Reload()
        except Exception as e:
            print(f"Error loading tensorboard events: {e}")
            self.event_acc = None

    def get_scalar_tags(self) -> List[str]:
        """Get all available scalar tags"""
        if not self.event_acc:
            return []
        return self.event_acc.Tags().get('scalars', [])

    def get_scalar_data(self, tag: str, max_points: Optional[int] = None) -> List[Dict]:
        """
        Get scalar data for a specific tag

        Args:
            tag: The scalar tag name (e.g., 'train/loss')
            max_points: Optional maximum number of points to return (for downsampling)

        Returns:
            List of dicts with 'step', 'value', 'wall_time' keys
        """
        if not self.event_acc or tag not in self.get_scalar_tags():
            return []

        try:
            events = self.event_acc.Scalars(tag)

            # Convert to list of dicts
            data = [
                {
                    'step': event.step,
                    'value': float(event.value),
                    'wall_time': event.wall_time
                }
                for event in events
            ]

            # Downsample if requested
            if max_points and len(data) > max_points:
                # Simple downsampling: take evenly spaced points
                step_size = len(data) / max_points
                indices = [int(i * step_size) for i in range(max_points)]
                data = [data[i] for i in indices]

            return data
        except Exception as e:
            print(f"Error reading scalar data for {tag}: {e}")
            return []

    def get_loss_metrics(self, max_points: Optional[int] = 500) -> Dict:
        """
        Get all loss-related metrics

        Args:
            max_points: Maximum number of points per metric

        Returns:
            Dict with loss metrics organized by type
        """
        metrics = {
            'train_loss': self.get_scalar_data('train/loss', max_points),
            'train_diffusion_loss': self.get_scalar_data('train/diffusion_loss', max_points),
            'train_ce_loss': self.get_scalar_data('train/ce_loss', max_points),
            'epoch_loss': self.get_scalar_data('epoch/loss', max_points),
            'epoch_diffusion_loss': self.get_scalar_data('epoch/diffusion_loss', max_points),
            'epoch_ce_loss': self.get_scalar_data('epoch/ce_loss', max_points),
        }
        return metrics

    def get_learning_rate(self, max_points: Optional[int] = 500) -> List[Dict]:
        """Get learning rate over time"""
        return self.get_scalar_data('train/learning_rate', max_points)

    def get_timing_metrics(self, max_points: Optional[int] = 500) -> Dict:
        """Get timing-related metrics"""
        metrics = {
            'step_time': self.get_scalar_data('timing/step_time', max_points),
            'steps_per_second': self.get_scalar_data('timing/steps_per_second', max_points),
            'epoch_time': self.get_scalar_data('timing/epoch_time', max_points),
        }
        return metrics

    def get_all_metrics(self, max_points: Optional[int] = 500) -> Dict:
        """
        Get all available metrics

        Args:
            max_points: Maximum number of points per metric

        Returns:
            Dict with all metrics organized by category
        """
        return {
            'loss': self.get_loss_metrics(max_points),
            'learning_rate': self.get_learning_rate(max_points),
            'timing': self.get_timing_metrics(max_points),
            'available_tags': self.get_scalar_tags()
        }
