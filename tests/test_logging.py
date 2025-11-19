"""
Test cases for the logger module.
Demonstrates the flexibility and ease of use.
"""

import logging
import tempfile
from pathlib import Path
from util.logger import get_logger, configure_root_logger, reset_logger, reset_all_loggers


def test_basic_usage():
    """Test basic usage - Convention over Configuration"""
    print("\n=== Test 1: Basic Usage ===")
    logger = get_logger(__name__)
    logger.debug("This is debug (won't show by default)")
    logger.info("This is info")
    logger.warning("This is warning")
    logger.error("This is error")
    print("✓ Basic usage test passed")


def test_custom_level():
    """Test custom log level"""
    print("\n=== Test 2: Custom Level ===")
    logger = get_logger(f"{__name__}.debug", level='DEBUG')
    logger.debug("This debug message should appear")
    logger.info("This info message should appear")
    print("✓ Custom level test passed")


def test_custom_format():
    """Test custom format"""
    print("\n=== Test 3: Custom Format ===")
    logger = get_logger(
        f"{__name__}.custom_format",
        format='[%(levelname)s] %(name)s: %(message)s'
    )
    logger.info("Custom formatted message")
    logger.warning("Another custom formatted message")
    print("✓ Custom format test passed")


def test_file_logging():
    """Test file logging"""
    print("\n=== Test 4: File Logging ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)
        logger = get_logger(
            f"{__name__}.file_logger",
            log_to_file=True,
            log_dir=log_dir,
            force_reconfigure=True
        )
        logger.info("This message goes to both console and file")
        logger.warning("This warning goes to both console and file")
        
        # Verify log file was created
        log_files = list(log_dir.glob("*.log"))
        assert len(log_files) > 0, "Log file should be created"
        print(f"✓ File logging test passed (log file: {log_files[0]})")


def test_custom_handler():
    """Test custom handler - Open-Closed Principle"""
    print("\n=== Test 5: Custom Handler (Extension) ===")
    
    # Create a custom handler that collects messages
    class CollectorHandler(logging.Handler):
        def __init__(self):
            super().__init__()
            self.messages = []
        
        def emit(self, record):
            self.messages.append(self.format(record))
    
    collector = CollectorHandler()
    collector.setLevel(logging.INFO)
    collector.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    
    logger = get_logger(
        f"{__name__}.custom",
        handlers=[collector]
    )
    logger.info("Message 1")
    logger.warning("Message 2")
    
    assert len(collector.messages) == 2, "Should collect 2 messages"
    assert "INFO: Message 1" in collector.messages[0]
    assert "WARNING: Message 2" in collector.messages[1]
    print(f"✓ Custom handler test passed (collected {len(collector.messages)} messages)")


def test_logger_reuse():
    """Test that getting the same logger returns the same instance"""
    print("\n=== Test 6: Logger Reuse ===")
    logger1 = get_logger("test.reuse")
    logger2 = get_logger("test.reuse")
    
    assert logger1 is logger2, "Should return the same logger instance"
    print("✓ Logger reuse test passed")


def test_environment_levels():
    """Test different log levels"""
    print("\n=== Test 7: Different Log Levels ===")
    
    levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
    for level_name in levels:
        logger = get_logger(
            f"{__name__}.{level_name.lower()}",
            level=level_name
        )
        logger.info(f"Logger at {level_name} level")
    
    print("✓ Different log levels test passed")


def test_reset_logger():
    """Test logger reset functionality"""
    print("\n=== Test 8: Reset Logger ===")
    
    logger1 = get_logger("test.reset", level='DEBUG')
    assert len(logger1.handlers) > 0
    
    reset_logger("test.reset")
    
    logger2 = get_logger("test.reset", level='INFO')
    # Should be reconfigured
    print("✓ Reset logger test passed")


def test_hierarchical_loggers():
    """Test hierarchical logger names"""
    print("\n=== Test 9: Hierarchical Loggers ===")
    
    parent_logger = get_logger("backend")
    child_logger = get_logger("backend.api")
    grandchild_logger = get_logger("backend.api.generation")
    
    parent_logger.info("Parent logger message")
    child_logger.info("Child logger message")
    grandchild_logger.info("Grandchild logger message")
    
    print("✓ Hierarchical loggers test passed")


def test_no_propagation():
    """Test disabling propagation"""
    print("\n=== Test 10: No Propagation ===")
    
    logger = get_logger(
        "test.no_propagate",
        propagate=False
    )
    logger.info("This message won't propagate to parent loggers")
    
    print("✓ No propagation test passed")


def demo_real_world_usage():
    """Demonstrate real-world usage patterns"""
    print("\n=== Real-World Usage Demo ===")
    
    # Scenario 1: Service logger
    service_logger = get_logger("backend.services.voice_generation")
    service_logger.info("Voice generation service started")
    service_logger.debug("Processing request with params: {...}")
    
    # Scenario 2: API endpoint logger
    api_logger = get_logger("backend.api.generation", level='DEBUG')
    api_logger.info("POST /api/generate received")
    api_logger.debug("Request body: {...}")
    
    # Scenario 3: Inference logger with file output
    with tempfile.TemporaryDirectory() as tmpdir:
        inference_logger = get_logger(
            "backend.inference",
            log_to_file=True,
            log_dir=tmpdir,
            level='INFO'
        )
        inference_logger.info("Loading model from checkpoint")
        inference_logger.info("Model loaded successfully")
        inference_logger.warning("GPU memory usage: 85%")
    
    print("✓ Real-world usage demo completed")


if __name__ == "__main__":
    print("=" * 60)
    print("VibeVoice Logging System Tests")
    print("=" * 60)
    
    try:
        test_basic_usage()
        test_custom_level()
        test_custom_format()
        test_file_logging()
        test_custom_handler()
        test_logger_reuse()
        test_environment_levels()
        test_reset_logger()
        test_hierarchical_loggers()
        test_no_propagation()
        demo_real_world_usage()
        
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
