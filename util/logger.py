"""
Logging configuration for VibeVoice backend.

This module provides a flexible logging system that follows:
- Convention over Configuration: Sensible defaults, minimal setup required
- Open-Closed Principle: Extensible through configuration without modifying core logic

Usage:
    Basic (uses defaults):
        from backend.utils.logging import get_logger
        logger = get_logger(__name__)
        logger.info("Hello world")

    Custom level:
        logger = get_logger(__name__, level=logging.DEBUG)

    Custom format:
        logger = get_logger(__name__, format='%(message)s')

    Custom handlers:
        logger = get_logger(__name__, handlers=[custom_handler])
"""

import logging
import os
import sys
from pathlib import Path
from typing import List, Optional, Union
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler


# Default configuration - Convention over Configuration
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
DEFAULT_LOG_DIR = Path('./logs')
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10MB
DEFAULT_BACKUP_COUNT = 5

# Environment-based overrides
LOG_LEVEL_ENV = os.environ.get('LOG_LEVEL', '').upper()
LOG_TO_FILE_ENV = os.environ.get('LOG_TO_FILE', 'false').lower() == 'true'
LOG_DIR_ENV = os.environ.get('LOG_DIR', str(DEFAULT_LOG_DIR))

# Logger registry to avoid duplicate configurations
_logger_registry = {}
_default_handlers_configured = False


def _get_log_level(level: Optional[Union[int, str]] = None) -> int:
    """
    Convert log level to integer format.
    
    Args:
        level: Log level as string or int
        
    Returns:
        Integer log level
    """
    if level is None:
        # Check environment variable first
        if LOG_LEVEL_ENV:
            level = LOG_LEVEL_ENV
        else:
            return DEFAULT_LOG_LEVEL
    
    if isinstance(level, str):
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL,
        }
        return level_map.get(level.upper(), DEFAULT_LOG_LEVEL)
    
    return level


def _create_console_handler(
    level: int,
    formatter: logging.Formatter,
    stream=None
) -> logging.StreamHandler:
    """
    Create a console handler with the specified configuration.
    
    Args:
        level: Log level
        formatter: Log formatter
        stream: Output stream (default: sys.stdout)
        
    Returns:
        Configured console handler
    """
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(formatter)
    return handler


def _create_file_handler(
    name: str,
    level: int,
    formatter: logging.Formatter,
    log_dir: Path,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
    rotation_type: str = 'size'
) -> Union[RotatingFileHandler, TimedRotatingFileHandler]:
    """
    Create a file handler with rotation.
    
    Args:
        name: Logger name (used for filename)
        level: Log level
        formatter: Log formatter
        log_dir: Directory for log files
        max_bytes: Max size before rotation (for size-based rotation)
        backup_count: Number of backup files to keep
        rotation_type: 'size' or 'time' based rotation
        
    Returns:
        Configured file handler
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Sanitize logger name for filename
    safe_name = name.replace('.', '_').replace('/', '_')
    log_file = log_dir / f"{safe_name}.log"
    
    if rotation_type == 'time':
        handler = TimedRotatingFileHandler(
            log_file,
            when='midnight',
            interval=1,
            backupCount=backup_count,
            encoding='utf-8'
        )
    else:
        handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
    
    handler.setLevel(level)
    handler.setFormatter(formatter)
    return handler


def get_logger(
    name: str,
    level: Optional[Union[int, str]] = None,
    format: Optional[str] = None,
    date_format: Optional[str] = None,
    handlers: Optional[List[logging.Handler]] = None,
    propagate: bool = True,
    log_to_file: Optional[bool] = None,
    log_dir: Optional[Union[str, Path]] = None,
    file_rotation: str = 'size',
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
    force_reconfigure: bool = False
) -> logging.Logger:
    """
    Get or create a logger with flexible configuration.
    
    This function follows Convention over Configuration principle:
    - By default, creates a console logger with INFO level
    - Environment variables can override defaults globally
    - Individual parameters can override for specific use cases
    
    Open-Closed Principle:
    - Extend behavior through configuration parameters
    - Custom handlers can be injected without modifying this function
    
    Args:
        name: Logger name (typically __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format: Log message format string
        date_format: Date format string
        handlers: Custom handlers (overrides default handlers)
        propagate: Whether to propagate to parent loggers
        log_to_file: Enable file logging (overrides LOG_TO_FILE env var)
        log_dir: Directory for log files
        file_rotation: 'size' or 'time' based rotation
        max_bytes: Max file size before rotation (size-based only)
        backup_count: Number of backup files to keep
        force_reconfigure: Force reconfiguration even if logger exists
        
    Returns:
        Configured logger instance
        
    Examples:
        # Basic usage (convention over configuration)
        logger = get_logger(__name__)
        
        # Debug logging for development
        logger = get_logger(__name__, level='DEBUG')
        
        # Custom format
        logger = get_logger(__name__, format='[%(levelname)s] %(message)s')
        
        # File logging
        logger = get_logger(__name__, log_to_file=True)
        
        # Custom handlers (open for extension)
        custom_handler = MyCustomHandler()
        logger = get_logger(__name__, handlers=[custom_handler])
    """
    # Return existing logger if already configured (avoid duplication)
    if name in _logger_registry and not force_reconfigure:
        return _logger_registry[name]
    
    # Get logger instance
    logger = logging.getLogger(name)
    
    # Avoid adding duplicate handlers
    if logger.handlers and not force_reconfigure:
        _logger_registry[name] = logger
        return logger
    
    # Clear existing handlers if force reconfiguring
    if force_reconfigure:
        logger.handlers.clear()
    
    # Set log level
    log_level = _get_log_level(level)
    logger.setLevel(log_level)
    logger.propagate = propagate
    
    # Create formatter
    log_format = format or DEFAULT_FORMAT
    log_date_format = date_format or DEFAULT_DATE_FORMAT
    formatter = logging.Formatter(log_format, log_date_format)
    
    # Configure handlers
    if handlers is not None:
        # Use custom handlers (Open-Closed Principle: open for extension)
        for handler in handlers:
            logger.addHandler(handler)
    else:
        # Use default handlers (Convention over Configuration)
        # Console handler (always added by default)
        console_handler = _create_console_handler(log_level, formatter)
        logger.addHandler(console_handler)
        
        # File handler (optional, based on configuration)
        should_log_to_file = log_to_file if log_to_file is not None else LOG_TO_FILE_ENV
        if should_log_to_file:
            file_log_dir = Path(log_dir) if log_dir else Path(LOG_DIR_ENV)
            file_handler = _create_file_handler(
                name=name,
                level=log_level,
                formatter=formatter,
                log_dir=file_log_dir,
                max_bytes=max_bytes,
                backup_count=backup_count,
                rotation_type=file_rotation
            )
            logger.addHandler(file_handler)
    
    # Register logger
    _logger_registry[name] = logger
    
    return logger


def configure_root_logger(
    level: Optional[Union[int, str]] = None,
    format: Optional[str] = None,
    log_to_file: bool = False
) -> None:
    """
    Configure the root logger for application-wide settings.
    
    Call this once at application startup to set global defaults.
    
    Args:
        level: Global log level
        format: Global log format
        log_to_file: Enable file logging globally
    """
    root_logger = get_logger(
        'root',
        level=level,
        format=format,
        log_to_file=log_to_file,
        force_reconfigure=True
    )
    
    # Set as root logger
    logging.root = root_logger


def reset_logger(name: str) -> None:
    """
    Reset a logger configuration.
    
    Args:
        name: Logger name to reset
    """
    if name in _logger_registry:
        logger = _logger_registry[name]
        logger.handlers.clear()
        del _logger_registry[name]


def reset_all_loggers() -> None:
    """Reset all configured loggers."""
    for name in list(_logger_registry.keys()):
        reset_logger(name)