"""
Logging utilities for the Django application.
Converted from app/utils/logging.py.
"""

import json
import logging
import time
from datetime import datetime
from django.conf import settings


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    Equivalent to FastAPI's JSON logging utility.
    """
    
    def format(self, record):
        """Format log record as JSON."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add thread and process info
        if hasattr(record, 'thread'):
            log_entry['thread_id'] = record.thread
        if hasattr(record, 'process'):
            log_entry['process_id'] = record.process
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'lineno', 'funcName', 'created',
                'msecs', 'relativeCreated', 'thread', 'threadName',
                'processName', 'process', 'getMessage', 'exc_info',
                'exc_text', 'stack_info'
            }:
                log_entry[key] = value
        
        return json.dumps(log_entry)


class RequestLoggingMiddleware:
    """
    Middleware to log HTTP requests and responses.
    Equivalent to FastAPI's request logging middleware.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('django.request')
    
    def __call__(self, request):
        start_time = time.time()
        
        # Log request
        request_data = {
            'method': request.method,
            'path': request.get_full_path(),
            'remote_addr': self.get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'request_id': getattr(request, 'request_id', None),
        }
        
        # Add user info if authenticated
        if hasattr(request, 'user') and request.user.is_authenticated:
            request_data['user_id'] = request.user.id
            request_data['username'] = request.user.username
        
        self.logger.info(f"Request started: {request.method} {request.path}", extra=request_data)
        
        # Process request
        response = self.get_response(request)
        
        # Calculate duration
        duration = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Log response
        response_data = {
            **request_data,
            'status_code': response.status_code,
            'duration_ms': round(duration, 2),
            'response_size': len(response.content) if hasattr(response, 'content') else 0,
        }
        
        level = logging.ERROR if response.status_code >= 500 else logging.WARNING if response.status_code >= 400 else logging.INFO
        self.logger.log(
            level,
            f"Request completed: {request.method} {request.path} - {response.status_code} ({duration:.2f}ms)",
            extra=response_data
        )
        
        return response
    
    def get_client_ip(self, request):
        """Get client IP address considering proxies."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


def get_logger(name):
    """
    Get a logger instance with the specified name.
    Equivalent to FastAPI's get_logger utility.
    """
    return logging.getLogger(name)


def log_structured(logger, level, message, **kwargs):
    """
    Log a structured message with additional context.
    """
    extra = kwargs
    logger.log(level, message, extra=extra)


class PerformanceLogger:
    """
    Logger for performance monitoring.
    Equivalent to FastAPI's performance logging.
    """
    
    def __init__(self, logger_name='performance'):
        self.logger = logging.getLogger(logger_name)
    
    def log_slow_query(self, query, duration, params=None):
        """Log slow database queries."""
        self.logger.warning(
            f"Slow query detected: {duration:.2f}ms",
            extra={
                'query': query,
                'duration_ms': duration,
                'params': params,
                'type': 'slow_query'
            }
        )
    
    def log_api_call(self, endpoint, method, duration, status_code, user_id=None):
        """Log API performance metrics."""
        extra = {
            'endpoint': endpoint,
            'method': method,
            'duration_ms': duration,
            'status_code': status_code,
            'type': 'api_call'
        }
        
        if user_id:
            extra['user_id'] = user_id
        
        level = logging.WARNING if duration > 1000 else logging.INFO
        self.logger.log(
            level,
            f"API call: {method} {endpoint} - {duration:.2f}ms",
            extra=extra
        )
    
    def log_task_execution(self, task_name, duration, success=True, error=None):
        """Log background task performance."""
        extra = {
            'task_name': task_name,
            'duration_ms': duration,
            'success': success,
            'type': 'task_execution'
        }
        
        if error:
            extra['error'] = str(error)
        
        level = logging.ERROR if not success else logging.WARNING if duration > 5000 else logging.INFO
        self.logger.log(
            level,
            f"Task execution: {task_name} - {duration:.2f}ms - {'SUCCESS' if success else 'FAILED'}",
            extra=extra
        )


# Create a global performance logger instance
performance_logger = PerformanceLogger()


def audit_log(action, user, resource=None, details=None, ip_address=None):
    """
    Log audit events for security and compliance.
    Equivalent to FastAPI's audit logging.
    """
    logger = logging.getLogger('audit')
    
    audit_data = {
        'action': action,
        'user_id': user.id if hasattr(user, 'id') else None,
        'username': getattr(user, 'username', None),
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'resource': resource,
        'details': details or {},
        'ip_address': ip_address,
        'type': 'audit'
    }
    
    logger.info(f"Audit: {action} by {getattr(user, 'username', 'anonymous')}", extra=audit_data)