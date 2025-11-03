"""
Utility functions and helpers for the Open WebUI Customizer application.

This package contains various utility modules for logging, file operations,
validation, and other common functionality used throughout the application.
"""

from .logging import setup_logging, get_logger

__all__ = ["setup_logging", "get_logger"]