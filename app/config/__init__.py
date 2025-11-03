"""
Configuration package for Open WebUI Customizer.

This package provides centralized configuration management for the application,
including settings for database, file storage, logging, and other components.
"""

from .settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]