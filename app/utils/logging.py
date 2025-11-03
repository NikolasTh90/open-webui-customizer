"""
Logging configuration and utilities.

This module provides centralized logging configuration and utilities
for the Open WebUI Customizer application. It supports both console
and file logging with proper formatting and log rotation.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

from app.config import get_settings


def setup_logging(
    level: Optional[str] = None,
    format_string: Optional[str] = None,
    log_file: Optional[Path] = None,
    max_file_size: Optional[int] = None,
    backup_count: Optional[int] = None
) -> logging.Logger:
    """
    Set up application logging configuration.

    This function configures the root logger with appropriate handlers
    for console and file logging based on the provided settings.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               If None, uses settings from configuration.
        format_string: Log message format string.
                      If None, uses settings from configuration.
        log_file: Path to log file. If None, uses settings from configuration.
        max_file_size: Maximum log file size before rotation.
                      If None, uses settings from configuration.
        backup_count: Number of backup log files to keep.
                     If None, uses settings from configuration.

    Returns:
        logging.Logger: The configured root logger.
    """
    settings = get_settings()

    # Use provided values or fall back to settings
    log_level = level or settings.logging.level
    log_format = format_string or settings.logging.format
    log_file_path = log_file or settings.logging.file_path
    max_size = max_file_size or settings.logging.max_file_size
    backups = backup_count or settings.logging.backup_count

    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create formatter
    formatter = logging.Formatter(log_format)

    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if configured)
    if log_file_path:
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=max_size,
            backupCount=backups,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module or component.

    This function returns a logger with the specified name, which will
    inherit the configuration from the root logger set up by setup_logging().

    Args:
        name: Name of the logger (typically __name__ for the module).

    Returns:
        logging.Logger: A logger instance for the specified name.
    """
    return logging.getLogger(name)


class LoggerMixin:
    """
    Mixin class that provides a logger property to classes.

    Classes that inherit from this mixin will have a logger property
    that returns a logger named after the class.
    """

    @property
    def logger(self) -> logging.Logger:
        """Get a logger instance for this class."""
        return get_logger(self.__class__.__name__)


def log_function_call(logger: logging.Logger, level: int = logging.DEBUG):
    """
    Decorator to log function calls.

    This decorator can be used to automatically log when functions
    are called and when they complete.

    Args:
        logger: Logger instance to use for logging.
        level: Logging level for the messages.

    Returns:
        Callable: The decorated function.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.log(level, f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
            try:
                result = func(*args, **kwargs)
                logger.log(level, f"{func.__name__} completed successfully")
                return result
            except Exception as e:
                logger.log(level, f"{func.__name__} failed with error: {e}")
                raise
        return wrapper
    return decorator


def log_execution_time(logger: logging.Logger, level: int = logging.DEBUG):
    """
    Decorator to log function execution time.

    This decorator measures and logs the execution time of functions.

    Args:
        logger: Logger instance to use for logging.
        level: Logging level for the timing messages.

    Returns:
        Callable: The decorated function.
    """
    import time

    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                end_time = time.time()
                execution_time = end_time - start_time
                logger.log(level, f"{func.__name__} executed in {execution_time:.4f} seconds")
                return result
            except Exception as e:
                end_time = time.time()
                execution_time = end_time - start_time
                logger.log(level, f"{func.__name__} failed after {execution_time:.4f} seconds with error: {e}")
                raise
        return wrapper
    return decorator