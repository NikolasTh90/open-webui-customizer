"""
Custom exceptions for the Open WebUI Customizer application.

This module defines custom exception classes for different types of errors
that can occur in the application, providing better error handling and
more informative error messages.
"""

from .base import (
    OpenWebUICustomizerError,
    ValidationError,
    NotFoundError,
    ConfigurationError,
    FileOperationError,
    DatabaseError,
    PipelineError,
    BrandingError,
)

__all__ = [
    "OpenWebUICustomizerError",
    "ValidationError",
    "NotFoundError",
    "ConfigurationError",
    "FileOperationError",
    "DatabaseError",
    "PipelineError",
    "BrandingError",
]