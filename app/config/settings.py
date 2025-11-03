"""
Application settings and configuration management.

This module provides centralized configuration management using Pydantic settings
for type safety and validation. It handles environment variables, default values,
and configuration validation.
"""

import os
import secrets
from pathlib import Path
from typing import List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    url: str = Field(default="sqlite:///./database.db", env="DATABASE_URL")
    """Database connection URL."""

    echo: bool = Field(default=False, env="DATABASE_ECHO")
    """Enable SQL query logging."""

    pool_size: int = Field(default=5, env="DATABASE_POOL_SIZE")
    """Database connection pool size."""

    max_overflow: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")
    """Maximum number of connections to allow beyond pool_size."""

    class Config:
        env_prefix = "DB_"


class FileStorageSettings(BaseSettings):
    """File storage configuration settings."""

    base_dir: Path = Field(default=Path("./customization"), env="FILE_STORAGE_BASE_DIR")
    """Base directory for file storage."""

    upload_dir: Path = Field(default=Path("./customization/static"), env="FILE_STORAGE_UPLOAD_DIR")
    """Directory for uploaded files."""

    max_file_size: int = Field(default=10 * 1024 * 1024, env="FILE_STORAGE_MAX_SIZE")  # 10MB
    """Maximum file size in bytes."""

    allowed_extensions: List[str] = Field(
        default=[
            ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
            ".css", ".js", ".json", ".html", ".txt", ".md"
        ],
        env="FILE_STORAGE_ALLOWED_EXTENSIONS"
    )
    """List of allowed file extensions."""

    @validator("base_dir", "upload_dir", pre=True)
    def convert_to_path(cls, v):
        """Convert string paths to Path objects."""
        return Path(v) if isinstance(v, str) else v

    class Config:
        env_prefix = "STORAGE_"


class APISettings(BaseSettings):
    """API configuration settings."""

    host: str = Field(default="127.0.0.1", env="API_HOST")
    """API server host."""

    port: int = Field(default=8000, env="API_PORT")
    """API server port."""

    reload: bool = Field(default=False, env="API_RELOAD")
    """Enable auto-reload for development."""

    workers: int = Field(default=1, env="API_WORKERS")
    """Number of API workers."""

    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32), env="API_SECRET_KEY")
    """Secret key for JWT tokens and other cryptographic operations."""

    debug: bool = Field(default=False, env="API_DEBUG")
    """Enable debug mode."""

    cors_origins: List[str] = Field(default=["http://localhost:3000", "http://localhost:8000"], env="API_CORS_ORIGINS")
    """List of allowed CORS origins."""

    class Config:
        env_prefix = "API_"


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""

    level: str = Field(default="INFO", env="LOG_LEVEL")
    """Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)."""

    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    """Log message format."""

    file_path: Optional[Path] = Field(default=None, env="LOG_FILE_PATH")
    """Path to log file. If None, logs to console only."""

    max_file_size: int = Field(default=10 * 1024 * 1024, env="LOG_MAX_SIZE")  # 10MB
    """Maximum log file size before rotation."""

    backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")
    """Number of backup log files to keep."""

    class Config:
        env_prefix = "LOG_"


class BrandingSettings(BaseSettings):
    """Branding-specific configuration settings."""

    default_template_name: str = Field(default="Default Branding", env="BRANDING_DEFAULT_TEMPLATE")
    """Default branding template name."""

    supported_file_types: List[str] = Field(
        default=["logo", "favicon", "theme", "manifest", "other"],
        env="BRANDING_SUPPORTED_TYPES"
    )
    """Supported branding file types."""

    text_file_extensions: List[str] = Field(
        default=[".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".scss", ".json", ".md", ".txt", ".py"],
        env="BRANDING_TEXT_EXTENSIONS"
    )
    """File extensions that should be processed for text replacements."""

    max_replacement_rules: int = Field(default=100, env="BRANDING_MAX_RULES")
    """Maximum number of replacement rules per template."""

    class Config:
        env_prefix = "BRANDING_"


class PipelineSettings(BaseSettings):
    """Pipeline execution configuration settings."""

    default_steps: List[str] = Field(default=["clone", "branding", "build"], env="PIPELINE_DEFAULT_STEPS")
    """Default pipeline steps to execute."""

    timeout_seconds: int = Field(default=3600, env="PIPELINE_TIMEOUT")  # 1 hour
    """Maximum execution time for pipeline runs."""

    max_concurrent_runs: int = Field(default=3, env="PIPELINE_MAX_CONCURRENT")
    """Maximum number of concurrent pipeline runs."""

    working_directory: Path = Field(default=Path("."), env="PIPELINE_WORK_DIR")
    """Working directory for pipeline operations."""

    @validator("working_directory", pre=True)
    def convert_to_path(cls, v):
        """Convert string paths to Path objects."""
        return Path(v) if isinstance(v, str) else v

    class Config:
        env_prefix = "PIPELINE_"


class Settings(BaseSettings):
    """
    Main application settings.

    This class combines all configuration settings and provides a single
    point of access for application configuration.
    """

    # Sub-settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    file_storage: FileStorageSettings = Field(default_factory=FileStorageSettings)
    api: APISettings = Field(default_factory=APISettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    branding: BrandingSettings = Field(default_factory=BrandingSettings)
    pipeline: PipelineSettings = Field(default_factory=PipelineSettings)

    # Application metadata
    app_name: str = Field(default="Open WebUI Customizer", env="APP_NAME")
    version: str = Field(default="1.0.0", env="APP_VERSION")
    environment: str = Field(default="development", env="APP_ENV")

    # Project paths
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)
    """Root directory of the project."""

    @validator("project_root", pre=True)
    def set_project_root(cls, v):
        """Set the project root directory."""
        if v is None:
            return Path(__file__).parent.parent.parent
        return Path(v) if isinstance(v, str) else v

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get the global application settings instance.

    This function implements the singleton pattern to ensure only one
    settings instance exists throughout the application lifecycle.

    Returns:
        Settings: The global application settings instance.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """
    Reload settings from environment variables.

    This function forces a reload of settings, useful for testing
    or when environment variables change during runtime.

    Returns:
        Settings: A new settings instance with current environment values.
    """
    global _settings
    _settings = Settings()
    return _settings