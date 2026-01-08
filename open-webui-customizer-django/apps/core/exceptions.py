"""
Custom exception handlers for Django REST Framework.
Converted from app/exceptions/base.py.
"""

import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404
from django.core.exceptions import PermissionDenied, ValidationError

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF.
    Provides consistent error responses matching FastAPI format.
    """
    # Call DRF's default exception handler first
    response = exception_handler(exc, context)
    
    # Add custom handling for specific exceptions
    if response is None:
        if isinstance(exc, Http404):
            response = Response(
                {
                    'error': 'Not Found',
                    'message': str(exc),
                    'status_code': status.HTTP_404_NOT_FOUND
                },
                status=status.HTTP_404_NOT_FOUND
            )
        elif isinstance(exc, PermissionDenied):
            response = Response(
                {
                    'error': 'Permission Denied',
                    'message': str(exc),
                    'status_code': status.HTTP_403_FORBIDDEN
                },
                status=status.HTTP_403_FORBIDDEN
            )
        elif isinstance(exc, ValidationError):
            response = Response(
                {
                    'error': 'Validation Error',
                    'message': 'Invalid data provided',
                    'details': dict(exc),
                    'status_code': status.HTTP_400_BAD_REQUEST
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        else:
            # Handle unexpected errors
            logger.error(f"Unhandled exception: {exc}", exc_info=True, extra={
                'request': context.get('request'),
                'view': context.get('view'),
            })
            
            response = Response(
                {
                    'error': 'Internal Server Error',
                    'message': 'An unexpected error occurred',
                    'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    else:
        # Enhance DRF's default response with additional details
        if hasattr(exc, 'detail'):
            if isinstance(exc.detail, dict):
                # Validation errors
                response.data = {
                    'error': 'Validation Error',
                    'message': 'Invalid data provided',
                    'details': exc.detail,
                    'status_code': response.status_code
                }
            elif isinstance(exc.detail, list):
                # Non-field errors
                response.data = {
                    'error': 'Validation Error',
                    'message': ' '.join(str(item) for item in exc.detail),
                    'status_code': response.status_code
                }
            else:
                # Single error message
                response.data = {
                    'error': 'Error',
                    'message': str(exc.detail),
                    'status_code': response.status_code
                }
    
    return response


class APIError(Exception):
    """Base API exception class."""
    
    def __init__(self, message, status_code=status.HTTP_400_BAD_REQUEST, details=None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(APIError):
    """Resource not found error."""
    
    def __init__(self, message="Resource not found", details=None):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details
        )


class ValidationError(APIError):
    """Validation error."""
    
    def __init__(self, message="Validation failed", details=None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class PermissionError(APIError):
    """Permission denied error."""
    
    def __init__(self, message="Permission denied", details=None):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )


class ConflictError(APIError):
    """Conflict error (e.g., duplicate resource)."""
    
    def __init__(self, message="Resource conflict", details=None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details
        )


class DatabaseError(APIError):
    """Database operation error."""
    
    def __init__(self, message="Database operation failed", details=None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )