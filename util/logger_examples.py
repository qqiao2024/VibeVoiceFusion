"""
Simple examples demonstrating the logger usage.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from util.logger import get_logger

# Example 1: Basic usage (Convention over Configuration)
print("=" * 60)
print("Example 1: Basic Usage")
print("=" * 60)
logger = get_logger(__name__)
logger.info("This is the simplest way to use the logger")
logger.warning("No configuration needed!")

# Example 2: Debug mode
print("\n" + "=" * 60)
print("Example 2: Debug Mode")
print("=" * 60)
debug_logger = get_logger(f"{__name__}.debug", level='DEBUG')
debug_logger.debug("This debug message will appear")
debug_logger.info("So will this info message")

# Example 3: Custom format
print("\n" + "=" * 60)
print("Example 3: Custom Format")
print("=" * 60)
simple_logger = get_logger(
    f"{__name__}.simple",
    format='[%(levelname)s] %(message)s'
)
simple_logger.info("Clean and simple format")
simple_logger.error("Easy to read")

# Example 4: Use in a class
print("\n" + "=" * 60)
print("Example 4: Class Usage")
print("=" * 60)

class VoiceGenerator:
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    def generate(self, text):
        self.logger.info(f"Generating voice for: {text[:30]}...")
        # Simulate processing
        self.logger.debug("Processing audio...")
        self.logger.info("Generation complete")

generator = VoiceGenerator()
generator.generate("Hello, this is a test of the voice generation system.")

print("\n" + "=" * 60)
print("All examples completed!")
print("=" * 60)
