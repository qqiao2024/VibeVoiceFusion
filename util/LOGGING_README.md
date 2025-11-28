# VibeVoice Logging System

A flexible, production-ready logging system that follows software design principles:
- **Convention over Configuration**: Sensible defaults, minimal setup
- **Open-Closed Principle**: Extensible without modifying core code

## Quick Start

```python
from backend.utils.logger import get_logger

# Basic usage - just works!
logger = get_logger(__name__)
logger.info("Hello, world!")
```

## Design Principles

### 1. Convention over Configuration

**Default behavior requires minimal code:**
- INFO level logging to console
- Formatted with timestamp, logger name, and level
- No configuration files needed

```python
# This is all you need for 90% of use cases
logger = get_logger(__name__)
```

### 2. Open-Closed Principle

**Extend functionality through configuration, not modification:**
- Custom handlers can be injected
- Format can be customized per logger
- Environment variables provide global overrides
- No need to modify the core logging module

## Usage Examples

### Basic Logging (Convention)

```python
from backend.utils.logger import get_logger

logger = get_logger(__name__)
logger.debug("Debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical issue")
```

### Custom Log Level

```python
# Debug logging for development
logger = get_logger(__name__, level='DEBUG')

# Or using logging constants
import logging
logger = get_logger(__name__, level=logging.DEBUG)
```

### Custom Format

```python
# Simple format
logger = get_logger(__name__, format='[%(levelname)s] %(message)s')

# Detailed format
logger = get_logger(
    __name__,
    format='%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s'
)
```

### File Logging

```python
# Enable file logging
logger = get_logger(__name__, log_to_file=True)

# Custom log directory
logger = get_logger(
    __name__,
    log_to_file=True,
    log_dir='./logs/my_service'
)

# Time-based rotation (daily)
logger = get_logger(
    __name__,
    log_to_file=True,
    file_rotation='time'  # rotates daily at midnight
)

# Size-based rotation (default)
logger = get_logger(
    __name__,
    log_to_file=True,
    file_rotation='size',
    max_bytes=10*1024*1024,  # 10MB
    backup_count=5           # keep 5 backup files
)
```

### Custom Handlers (Extension Point)

```python
# Create custom handler
class SlackHandler(logging.Handler):
    def emit(self, record):
        # Send log to Slack
        send_to_slack(self.format(record))

# Use custom handler
slack_handler = SlackHandler()
slack_handler.setLevel(logging.ERROR)

logger = get_logger(__name__, handlers=[slack_handler])
```

### Multiple Handlers

```python
# Combine console and file logging with custom handler
import logging
from logging.handlers import RotatingFileHandler

console_handler = logging.StreamHandler()
file_handler = RotatingFileHandler('app.log', maxBytes=1024*1024)
custom_handler = MyCustomHandler()

logger = get_logger(
    __name__,
    handlers=[console_handler, file_handler, custom_handler]
)
```

## Environment Variables

Override defaults globally without code changes:

```bash
# Set global log level
export LOG_LEVEL=DEBUG

# Enable file logging for all loggers
export LOG_TO_FILE=true

# Set log directory
export LOG_DIR=/var/log/vibevoice
```

## Configuration

### Application-Wide Configuration

```python
from backend.utils.logger import configure_root_logger

# Configure once at application startup
configure_root_logger(
    level='INFO',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    log_to_file=True
)
```

### Per-Module Configuration

```python
# Different configuration for different modules
api_logger = get_logger('backend.api', level='DEBUG')
service_logger = get_logger('backend.services', level='INFO')
db_logger = get_logger('backend.database', level='WARNING')
```

## Best Practices

### 1. Use `__name__` for Logger Names

```python
# ✓ Good - creates hierarchical logger names
logger = get_logger(__name__)

# ✗ Avoid - loses context
logger = get_logger('my_logger')
```

### 2. Set Debug Level in Development

```python
# development.py
if app.config['DEBUG']:
    logger = get_logger(__name__, level='DEBUG')
else:
    logger = get_logger(__name__, level='INFO')
```

### 3. Use Structured Logging

```python
# ✓ Good - structured data
logger.info(f"User {user_id} performed {action} at {timestamp}")

# ✓ Better - easy to parse
logger.info("User action completed", extra={
    'user_id': user_id,
    'action': action,
    'timestamp': timestamp
})
```

### 4. File Logging in Production

```python
# production.py
logger = get_logger(
    __name__,
    log_to_file=True,
    log_dir='/var/log/vibevoice',
    file_rotation='time',  # daily rotation
    backup_count=30        # keep 30 days
)
```

## Real-World Examples

### API Endpoint

```python
from backend.utils.logger import get_logger

logger = get_logger(__name__)

@app.route('/api/generate', methods=['POST'])
def generate_voice():
    logger.info("Voice generation request received")
    try:
        data = request.get_json()
        logger.debug(f"Request data: {data}")
        
        result = voice_service.generate(data)
        logger.info(f"Generation completed: {result['id']}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Generation failed: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500
```

### Service Layer

```python
from backend.utils.logger import get_logger

class VoiceGenerationService:
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def generate(self, text, speaker_id):
        self.logger.info(f"Generating voice for speaker {speaker_id}")
        self.logger.debug(f"Text length: {len(text)} characters")
        
        try:
            result = self._process(text, speaker_id)
            self.logger.info("Generation successful")
            return result
        except Exception as e:
            self.logger.error("Generation failed", exc_info=True)
            raise
```

### Background Task

```python
from backend.utils.logger import get_logger

logger = get_logger(__name__, log_to_file=True)

def process_queue():
    logger.info("Starting queue processor")
    while True:
        try:
            task = queue.get()
            logger.debug(f"Processing task: {task.id}")
            
            result = task.execute()
            logger.info(f"Task {task.id} completed")
        except Exception as e:
            logger.error(f"Task {task.id} failed", exc_info=True)
```

## Advanced Usage

### Logger Reset

```python
from backend.utils.logger import reset_logger, reset_all_loggers

# Reset single logger
reset_logger('backend.api')

# Reset all loggers (useful in tests)
reset_all_loggers()
```

### Force Reconfiguration

```python
# Reconfigure existing logger
logger = get_logger(
    __name__,
    level='DEBUG',
    force_reconfigure=True
)
```

### Disable Propagation

```python
# Prevent logs from propagating to parent loggers
logger = get_logger(__name__, propagate=False)
```

## Testing

```python
# test_logging.py
def test_logging():
    logger = get_logger('test.logger')
    logger.info("Test message")
    
    # Reset after test
    reset_logger('test.logger')
```

Run the test suite:

```bash
python backend/utils/test_logging.py
```

## API Reference

### `get_logger(name, **kwargs)`

Get or create a logger with flexible configuration.

**Parameters:**
- `name` (str): Logger name (typically `__name__`)
- `level` (int|str, optional): Log level
- `format` (str, optional): Log message format
- `date_format` (str, optional): Date format string
- `handlers` (List[Handler], optional): Custom handlers
- `propagate` (bool): Whether to propagate to parent loggers
- `log_to_file` (bool, optional): Enable file logging
- `log_dir` (str|Path, optional): Directory for log files
- `file_rotation` (str): 'size' or 'time' based rotation
- `max_bytes` (int): Max file size before rotation
- `backup_count` (int): Number of backup files
- `force_reconfigure` (bool): Force reconfiguration

**Returns:** `logging.Logger`

### `configure_root_logger(level, format, log_to_file)`

Configure the root logger for application-wide settings.

### `reset_logger(name)`

Reset a logger configuration.

### `reset_all_loggers()`

Reset all configured loggers.

## Migration Guide

If you're currently using `transformers.utils.logging`:

```python
# Before
from transformers.utils import logging
logging.set_verbosity_info()
logger = logging.get_logger(__name__)

# After
from util.logger import get_logger
logger = get_logger(__name__, level='INFO')
```

## License

Part of the VibeVoice project.


# Logger Quick Reference

## Import
```python
from backend.utils.logger import get_logger
```

## Basic Usage (Convention over Configuration)
```python
logger = get_logger(__name__)
logger.info("Message")
```

## Common Patterns

### Debug Logging
```python
logger = get_logger(__name__, level='DEBUG')
```

### Custom Format
```python
logger = get_logger(__name__, format='[%(levelname)s] %(message)s')
```

### File Logging
```python
logger = get_logger(__name__, log_to_file=True)
```

### Custom Handler (Open-Closed Principle)
```python
logger = get_logger(__name__, handlers=[my_handler])
```

## Log Levels
- `DEBUG`: Detailed diagnostic info
- `INFO`: General informational messages (default)
- `WARNING`: Warning messages
- `ERROR`: Error messages
- `CRITICAL`: Critical issues

## Environment Variables

```bash
export LOG_LEVEL=DEBUG        # Set global log level
export LOG_TO_FILE=true       # Enable file logging
export LOG_DIR=/var/log/app   # Set log directory
```

## Design Principles

✅ **Convention over Configuration**
- Minimal code for common cases
- Sensible defaults
- No config files needed

✅ **Open-Closed Principle**
- Extend through parameters
- Inject custom handlers
- No need to modify core code

## When to Use What

| Scenario | Solution |
|----------|----------|
| Development | `level='DEBUG'` |
| Production | `log_to_file=True` |
| Custom destination | `handlers=[...]` |
| Per-module config | Create multiple loggers |
| Global config | Use environment variables |

## Tips

1. Always use `__name__` for logger name
2. Set DEBUG level only in development
3. Enable file logging in production
4. Use custom handlers for external services
5. Reset loggers in tests: `reset_logger(name)`

