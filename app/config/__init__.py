"""
Configuration package for Open WebUI Customizer.

This package provides centralized configuration management for the application,
including settings for database, file storage, logging, and other components.

The configuration now uses a tiered approach with base, development, staging,
and production settings classes that inherit appropriate defaults.
"""

import os
from typing import Optional, Dict, Any
from .settings import get_settings as get_tiered_settings, BaseSettings

class LegacySettings:
    """
    Legacy compatibility wrapper for the new tiered settings system.
    
    This class provides backward compatibility for existing code that expects
    the old Settings interface while internally using the new tiered settings.
    """
    
    def __init__(self):
        """Initialize with the current tiered settings."""
        self._tiered = get_tiered_settings()
    
    # Database settings (legacy properties)
    @property
    def database_url(self) -> str:
        """Get the database URL."""
        return self._tiered.database.database_url
    
    @property
    def encryption_key(self) -> str:
        """Get the encryption key."""
        return self._tiered.security.encryption_key or ""
    
    @property
    def secret_key(self) -> str:
        """Get the secret key."""
        return self._tiered.security.secret_key
    
    # File storage settings
    @property
    def upload_dir(self) -> str:
        """Get the upload directory."""
        return os.getenv("UPLOAD_DIR", "./uploads")
    
    @property
    def static_dir(self) -> str:
        """Get the static directory."""
        return os.getenv("STATIC_DIR", "./static")
    
    # Logging settings
    @property
    def log_level(self) -> str:
        """Get the log level."""
        return self._tiered.logging.log_level
    
    @property
    def log_file(self) -> Optional[str]:
        """Get the log file path."""
        return self._tiered.logging.log_file
    
    # API settings
    @property
    def api_title(self) -> str:
        """Get the API title."""
        return self._tiered.api.api_title
    
    @property
    def api_version(self) -> str:
        """Get the API version."""
        return self._tiered.api.api_version
    
    # Pipeline settings
    @property
    def pipeline_timeout(self) -> int:
        """Get the pipeline timeout."""
        return self._tiered.pipeline.build_timeout
    
    @property
    def max_build_size(self) -> int:
        """Get the maximum build size."""
        return self._tiered.pipeline.max_output_size_mb * 1024 * 1024  # Convert MB to bytes
    
    @property
    def database_config(self) -> Dict[str, Any]:
        """Get database configuration."""
        return {
            "url": self.database_url,
            "echo": self._tiered.database.echo
        }
    
    @property
    def encryption_config(self) -> Dict[str, Any]:
        """Get encryption configuration."""
        key = self._tiered.security.encryption_key
        return {
            "key": key.encode() if key else None
        }
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self._tiered.environment == "development"
    
    @property
    def is_staging(self) -> bool:
        """Check if running in staging mode."""
        return self._tiered.environment == "staging"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self._tiered.environment == "production"
    
    @property
    def debug(self) -> bool:
        """Get debug mode status."""
        return self._tiered.debug

# Maintain backward compatibility
Settings = LegacySettings

# Global settings instance
_settings: Optional[LegacySettings] = None

def get_settings() -> LegacySettings:
    """
    Get the global settings instance.
    
    Returns:
        Settings: The application settings (legacy wrapper)
    """
    global _settings
    if _settings is None:
        _settings = LegacySettings()
    return _settings

def reload_settings() -> LegacySettings:
    """
    Reload settings from environment variables.
    
    Returns:
        Settings: The new settings instance (legacy wrapper)
    """
    global _settings
    from .settings import reload_settings as reload_tiered_settings
    reload_tiered_settings()
    _settings = LegacySettings()
    return _settings

# Export both legacy and new settings
__all__ = [
    "Settings", "get_settings", "reload_settings",  # Legacy exports
    "LegacySettings", "BaseSettings"  # New exports
]