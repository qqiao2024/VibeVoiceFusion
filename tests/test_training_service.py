"""
Unit tests for TrainingService - specifically testing datetime JSON serialization
"""
import json
import pytest
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

from backend.utils.file_handler import FileHandler, DateTimeEncoder
from backend.training.state import TrainingState


class TestDateTimeEncoder:
    """Test the DateTimeEncoder class for proper datetime serialization"""

    def test_datetime_serialization(self):
        """Test that datetime objects are properly serialized to ISO format"""
        test_datetime = datetime(2025, 12, 13, 10, 30, 45, tzinfo=timezone.utc)
        data = {"timestamp": test_datetime}
        
        result = json.dumps(data, cls=DateTimeEncoder)
        parsed = json.loads(result)
        
        assert parsed["timestamp"] == "2025-12-13T10:30:45+00:00"

    def test_nested_datetime_serialization(self):
        """Test that nested datetime objects are properly serialized"""
        test_datetime = datetime(2025, 12, 13, 10, 30, 45, tzinfo=timezone.utc)
        data = {
            "job_id": "test123",
            "metadata": {
                "start_time": test_datetime,
                "current_timestamp": test_datetime
            }
        }
        
        result = json.dumps(data, cls=DateTimeEncoder)
        parsed = json.loads(result)
        
        assert parsed["metadata"]["start_time"] == "2025-12-13T10:30:45+00:00"
        assert parsed["metadata"]["current_timestamp"] == "2025-12-13T10:30:45+00:00"

    def test_non_datetime_objects_still_work(self):
        """Test that non-datetime objects are still handled correctly"""
        data = {
            "string": "hello",
            "number": 42,
            "float": 3.14,
            "list": [1, 2, 3],
            "nested": {"key": "value"}
        }
        
        result = json.dumps(data, cls=DateTimeEncoder)
        parsed = json.loads(result)
        
        assert parsed == data


class TestFileHandlerJsonSerialization:
    """Test FileHandler JSON methods with datetime objects"""

    def setup_method(self):
        """Create a temporary directory for each test"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.file_handler = FileHandler()

    def teardown_method(self):
        """Clean up temporary directory after each test"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_write_json_with_datetime(self):
        """Test that write_json properly handles datetime objects"""
        test_file = self.temp_dir / "test.json"
        test_datetime = datetime(2025, 12, 13, 10, 30, 45, tzinfo=timezone.utc)
        
        data = {
            "task_id": "abc123",
            "start_time": test_datetime,
            "status": "completed"
        }
        
        # This should not raise TypeError
        self.file_handler.write_json(test_file, data)
        
        # Verify the file was written correctly
        loaded = self.file_handler.read_json(test_file)
        assert loaded["task_id"] == "abc123"
        assert loaded["start_time"] == "2025-12-13T10:30:45+00:00"
        assert loaded["status"] == "completed"

    def test_write_json_atomic_with_datetime(self):
        """Test that write_json_atomic properly handles datetime objects"""
        test_file = self.temp_dir / "test_atomic.json"
        test_datetime = datetime(2025, 12, 13, 10, 30, 45, tzinfo=timezone.utc)
        
        data = {
            "task_id": "def456",
            "current_timestamp": test_datetime,
            "status": "training"
        }
        
        # This should not raise TypeError
        self.file_handler.write_json_atomic(test_file, data)
        
        # Verify the file was written correctly
        loaded = self.file_handler.read_json(test_file)
        assert loaded["task_id"] == "def456"
        assert loaded["current_timestamp"] == "2025-12-13T10:30:45+00:00"
        assert loaded["status"] == "training"


class TestTrainingStateJsonSerialization:
    """Test TrainingState serialization and deserialization with datetime"""

    def setup_method(self):
        """Create a temporary directory for each test"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.file_handler = FileHandler()

    def teardown_method(self):
        """Clean up temporary directory after each test"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_training_state_round_trip(self):
        """Test that TrainingState can be serialized and deserialized correctly"""
        start_time = datetime(2025, 12, 13, 10, 0, 0, tzinfo=timezone.utc)
        current_time = datetime(2025, 12, 13, 11, 30, 45, tzinfo=timezone.utc)
        
        state = TrainingState(
            task_id="test_task_123",
            job_name="test_job",
            project_id="test_project",
            status="Training",
            start_time=start_time,
            current_timestamp=current_time,
            current_step=100,
            estimated_total_steps=1000
        )
        
        # Convert to dict and save
        state_dict = state.to_dict()
        test_file = self.temp_dir / "training_state.json"
        self.file_handler.write_json_atomic(test_file, {"test_task_123": state_dict})
        
        # Load and reconstruct
        loaded = self.file_handler.read_json(test_file)
        reconstructed = TrainingState.from_dict(loaded["test_task_123"])
        
        assert reconstructed.task_id == "test_task_123"
        assert reconstructed.job_name == "test_job"
        assert reconstructed.status == "Training"
        assert reconstructed.start_time == start_time
        assert reconstructed.current_timestamp == current_time

    def test_training_state_with_datetime_objects_in_dict(self):
        """Test saving TrainingState that still has datetime objects (before to_dict conversion)"""
        start_time = datetime(2025, 12, 13, 10, 0, 0, tzinfo=timezone.utc)
        current_time = datetime(2025, 12, 13, 11, 30, 45, tzinfo=timezone.utc)
        
        # Simulate what happens when from_dict is called - it creates datetime objects
        state = TrainingState(
            task_id="orphan_task_456",
            job_name="orphan_job",
            project_id="test_project",
            status="Failed",
            start_time=start_time,
            current_timestamp=current_time,
            error_message="Training interrupted (server restart or crash)"
        )
        
        # to_dict should convert datetime to strings
        state_dict = state.to_dict()
        
        # Verify datetime objects are converted to strings
        assert isinstance(state_dict["start_time"], str)
        assert isinstance(state_dict["current_timestamp"], str)
        
        # Save the dict - this should work without TypeError
        test_file = self.temp_dir / "training_history.json"
        states_meta = {"orphan_task_456": state_dict}
        self.file_handler.write_json_atomic(test_file, states_meta)
        
        # Verify it was saved correctly
        loaded = self.file_handler.read_json(test_file)
        assert loaded["orphan_task_456"]["status"] == "Failed"
        assert loaded["orphan_task_456"]["error_message"] == "Training interrupted (server restart or crash)"

    def test_fallback_datetime_encoder_handles_raw_datetime(self):
        """Test that even if datetime objects slip through, the encoder handles them"""
        start_time = datetime(2025, 12, 13, 10, 0, 0, tzinfo=timezone.utc)
        current_time = datetime(2025, 12, 13, 11, 30, 45, tzinfo=timezone.utc)
        
        # Simulate a case where datetime objects might slip through
        # (e.g., if to_dict didn't catch all cases)
        raw_data = {
            "task_id": "raw_datetime_task",
            "start_time": start_time,  # Raw datetime object
            "current_timestamp": current_time,  # Raw datetime object
            "status": "Training"
        }
        
        test_file = self.temp_dir / "raw_datetime.json"
        
        # This should NOT raise TypeError thanks to DateTimeEncoder
        self.file_handler.write_json_atomic(test_file, {"raw_task": raw_data})
        
        # Verify the data was saved correctly
        loaded = self.file_handler.read_json(test_file)
        assert loaded["raw_task"]["start_time"] == "2025-12-13T10:30:45+00:00" or \
               loaded["raw_task"]["start_time"] == "2025-12-13T10:00:00+00:00"


class TestTrainingServiceListJobs:
    """Test the list_jobs method that was causing the original error"""

    def setup_method(self):
        """Create a temporary directory for each test"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.file_handler = FileHandler()

    def teardown_method(self):
        """Clean up temporary directory after each test"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_list_jobs_with_orphaned_training_status(self):
        """
        Test the scenario that caused the original error:
        - Job has status 'Training' but no active task
        - list_jobs marks it as Failed and saves back to metadata
        - This should not raise TypeError for datetime serialization
        """
        # Create initial training history with a "Training" status job
        start_time = datetime(2025, 12, 12, 13, 25, 40, tzinfo=timezone.utc)
        current_time = datetime(2025, 12, 12, 17, 10, 21, tzinfo=timezone.utc)
        
        training_history = {
            "b5693f0d7e8a478faff05c9c8cc681f8": {
                "task_id": "b5693f0d7e8a478faff05c9c8cc681f8",
                "job_name": "Cantonese100000",
                "project_id": "videoscripts",
                "config": {"epochs": 40},
                "created_at": "2025-12-12T13:25:26.012347+00:00",
                "current_step": 49084,
                "estimated_total_steps": 1000000,
                "current_epoch": 2,
                "total_epochs": 40,
                "learning_rate": 0.0001,
                "batch_size": 4,
                "accumlate_grad_steps": 16,
                "current_loss": 0.14110904932022095,
                "current_diffusion_loss": 0.007511611562222242,
                "current_ce_loss": 15.6875,
                "average_epoch_diffusion_loss": 0.00711188757462427,
                "average_epoch_ce_loss": 15.7548625,
                "average_epoch_loss": 0.1370680615773797,
                "start_time": "2025-12-12T13:25:40.405451+00:00",
                "current_timestamp": "2025-12-12T17:10:21.812708+00:00",
                "estimated_total_elpase": 274827.1902810506,
                "latest_epoch_elapsed": 6870.907219,
                "latest_step_elapsed": 0.369964,
                "average_step_time": 0.2746543191810125,
                "steps_per_second": 3.6409403754577188,
                "steps_per_epoch": 25000,
                "steps_in_epoch": 24085,
                "status": "Training",  # This will be marked as Failed
                "error_message": "",
                "tensorboard_logdir": "./tensorboard_logs/vibevoice_lora_test",
                "lora_files": [],
                "final_lora_file": ""
            }
        }
        
        # Save initial data
        meta_file = self.temp_dir / "training_history.json"
        self.file_handler.write_json_atomic(meta_file, training_history)
        
        # Simulate what list_jobs does: load, modify, and save back
        states_meta = self.file_handler.read_json(meta_file)
        
        for task_id, state_dict in states_meta.items():
            state = TrainingState.from_dict(state_dict)
            
            # After from_dict, start_time and current_timestamp are datetime objects
            assert isinstance(state.start_time, datetime)
            assert isinstance(state.current_timestamp, datetime)
            
            # Simulate orphan detection - mark as Failed
            if state.status == "Training":
                state.status = "Failed"
                state.error_message = "Training interrupted (server restart or crash)"
                
                # Update metadata with the modified state
                states_meta[task_id] = state.to_dict()
        
        # This is the line that was failing before the fix
        # It should now work because DateTimeEncoder handles any remaining datetime objects
        self.file_handler.write_json_atomic(meta_file, states_meta)
        
        # Verify the data was saved correctly
        loaded = self.file_handler.read_json(meta_file)
        job = loaded["b5693f0d7e8a478faff05c9c8cc681f8"]
        
        assert job["status"] == "Failed"
        assert job["error_message"] == "Training interrupted (server restart or crash)"
        # Ensure datetime fields are strings
        assert isinstance(job["start_time"], str)
        assert isinstance(job["current_timestamp"], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
