"""
Logging utilities for the Open WebUI Customizer application.

This module provides a centralized logging system with structured logging
support for better monitoring and debugging.

Author: Open WebUI Customizer Team
"""

import logging
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from pathlib import Path
from functools import wraps

try:
    from flask import request
except ImportError:
    # Flask not available, use None for request
    request = None


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    
    Formats log records as JSON objects with metadata for better parsing
    and analysis in log management systems.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON string representation of the log record
        """
        # Create base log entry
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add stack trace if present
        if record.stack_info:
            log_entry['stack_trace'] = record.stack_info
        
        # Add extra fields
        if hasattr(record, '__dict__'):
            extra_fields = {
                k: v for k, v in record.__dict__.items()
                if k not in [
                    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                    'filename', 'module', 'lineno', 'funcName', 'created',
                    'msecs', 'relativeCreated', 'thread', 'threadName',
                    'processName', 'process', 'getMessage', 'exc_info',
                    'exc_text', 'stack_info'
                ]
            }
            if extra_fields:
                log_entry['extra'] = extra_fields
        
        return json.dumps(log_entry, default=str)


class ColoredFormatter(logging.Formatter):
    """
    Console formatter with colors for better readability.
    
    Uses ANSI color codes to highlight different log levels for
    development and local testing.
    """
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record with colors.
        
        Args:
            record: Log record to format
            
        Returns:
            Colored string representation of the log record
        """
        # Add color to level name
        level_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Custom format with colors
        formatter = logging.Formatter(
            f'{level_color}%(levelname)s{reset} '
            f'%(asctime)s '
            f'%(name)s '
            f'%(message)s'
        )
        
        return formatter.format(record)


def setup_logging(
    level: str = 'INFO',
    format_type: str = 'json',
    log_file: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> None:
    """
    Set up application logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: 'json' for structured logs, 'console' for colored output
        log_file: Optional file to write logs to
        max_file_size: Maximum log file size in bytes
        backup_count: Number of backup log files to keep
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    if format_type.lower() == 'json':
        console_formatter = JSONFormatter()
    else:
        console_formatter = ColoredFormatter()
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if configured)
    if log_file:
        from logging.handlers import RotatingFileHandler
        
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        
        # Always use JSON format for file logs
        file_formatter = JSONFormatter()
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Configure specific loggers
    
    # Suppress noisy third-party loggers
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    # Set application loggers to debug if requested
    if numeric_level <= logging.DEBUG:
        logging.getLogger('app').setLevel(logging.DEBUG)
        logging.getLogger('app.services').setLevel(logging.DEBUG)
        logging.getLogger('app.api').setLevel(logging.DEBUG)
    
    logging.info(f"Logging configured: level={level}, format={format_type}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_function_call(func):
    """
    Decorator to automatically log function calls and returns.
    
    This decorator logs when a function is called, its arguments,
    execution time, and return value or exception.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    import functools
    import time
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        func_name = f"{func.__module__}.{func.__name__}"
        
        # Log function call
        logger.info(f"Calling {func_name}", extra={
            'function_args': str(args)[:200],  # Limit length
            'function_kwargs': str(kwargs)[:200]
        })
        
        start_time = time.time()
        
        try:
            # Execute function
            result = func(*args, **kwargs)
            
            # Log successful execution
            execution_time = time.time() - start_time
            logger.info(f"Completed {func_name}", extra={
                'execution_time_seconds': execution_time,
                'result_type': type(result).__name__
            })
            
            return result
            
        except Exception as e:
            # Log exception
            execution_time = time.time() - start_time
            logger.error(f"Failed {func_name}", exc_info=True, extra={
                'execution_time_seconds': execution_time,
                'error_type': type(e).__name__,
                'error_message': str(e)
            })
            
            raise
    
    return wrapper


class LogContext:
    """
    Context manager for adding structured context to log records.
    
    This allows adding temporary context (like request ID, user ID, etc.)
    to all log messages within a specific block of code.
    """
    
    def __init__(self, logger: logging.Logger, **context):
        """
        Initialize log context.
        
        Args:
            logger: Logger to add context to
            **context: Key-value pairs to add to log records
        """
        self.logger = logger
        self.context = context
        self.adapter = None
    
    def __enter__(self):
        """Enter context and create logger adapter."""
        self.adapter = logging.LoggerAdapter(self.logger, self.context)
        return self.adapter
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and clean up."""
        self.adapter = None


def log_api_request(func: Callable) -> Callable:
    """
    Decorator to log API requests with request context.
    
    Args:
        func: The Flask route function to decorate
        
    Returns:
        Decorated function that logs request information
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        
        # Extract request information
        request_info = {
            'method': request.method if request else 'unknown',
            'path': request.path if request else 'unknown',
            'remote_addr': request.remote_addr if request else 'unknown',
            'user_agent': str(request.user_agent) if request and hasattr(request, 'user_agent') else 'unknown',
            'function': func.__name__,
            'module': func.__module__
        }
        
        # Add query parameters if available
        if request and request.args:
            request_info['query_params'] = dict(request.args)
        
        logger.info("API request", extra=request_info)
        
        return func(*args, **kwargs)
    
    return wrapper


# Initialize logging with default configuration
if not logging.getLogger().handlers:
    setup_logging()