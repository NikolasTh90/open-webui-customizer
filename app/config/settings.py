"""
Configuration settings management for Open WebUI Customizer.

This module provides centralized configuration management using Pydantic
for type validation and environment variable handling with tiered settings
for different environments (base, development, staging, production).

Author: Open WebUI Customizer Team
"""

import os
from typing import Optional, List, Dict, Any, Type
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field, validator

class BaseDatabaseSettings(BaseSettings):
    """Base database configuration settings."""
    
    # Database URL configuration
    database_url: str = Field(
        default="sqlite:///./customizer.db",
        description="Database connection URL"
    )
    
    # Database connection pool settings
    pool_size: int = Field(
        default=5,
        description="Database connection pool size"
    )
    
    max_overflow: int = Field(
        default=10,
        description="Maximum number of connections to allow beyond pool_size"
    )
    
    pool_timeout: int = Field(
        default=30,
        description="Timeout in seconds for getting a connection from the pool"
    )
    
    pool_recycle: int = Field(
        default=3600,
        description="Time in seconds after which a connection is recreated"
    )
    
    echo: bool = Field(
        default=False,
        description="Enable SQLAlchemy query logging"
    )

class DevDatabaseSettings(BaseDatabaseSettings):
    """Development database settings with relaxed restrictions."""
    
    echo: bool = True
    auto_create_tables: bool = Field(
        default=True,
        description="Automatically create tables on startup"
    )

class StagingDatabaseSettings(BaseDatabaseSettings):
    """Staging database settings."""
    
    auto_create_tables: bool = Field(
        default=True,
        description="Automatically create tables on startup"
    )

class ProductionDatabaseSettings(BaseDatabaseSettings):
    """Production database settings with strict security."""
    
    auto_create_tables: bool = Field(
        default=False,
        description="Require Alembic migrations for table creation"
    )

class BaseSecuritySettings(BaseSettings):
    """Base security configuration settings."""
    
    # JWT settings
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for JWT token signing"
    )
    
    algorithm: str = Field(
        default="HS256",
        description="JWT algorithm for token signing"
    )
    
    access_token_expire_minutes: int = Field(
        default=30,
        description="Access token expiration time in minutes"
    )
    
    # Encryption settings
    require_encryption_key: bool = Field(
        default=True,
        description="Require encryption key for credential storage"
    )
    
    encryption_key: Optional[str] = Field(
        default=None,
        description="Master encryption key for credential storage"
    )
    
    # CORS settings
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="Allowed CORS origins"
    )
    
    # Rate limiting
    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable API rate limiting"
    )
    
    rate_limit_requests: int = Field(
        default=100,
        description="Number of requests allowed per window"
    )
    
    rate_limit_window: int = Field(
        default=60,
        description="Rate limit time window in seconds"
    )
    
    # Error handling
    detailed_errors: bool = Field(
        default=False,
        description="Include detailed error information in API responses"
    )

class DevSecuritySettings(BaseSecuritySettings):
    """Development security settings with relaxed restrictions."""
    
    secret_key: str = "dev-secret-key-not-for-production"
    require_encryption_key: bool = False
    encryption_key: str = "dev-encryption-key-32-bytes-long"
    cors_origins: List[str] = ["*"]
    rate_limit_enabled: bool = False
    detailed_errors: bool = True

class StagingSecuritySettings(BaseSecuritySettings):
    """Staging security settings."""
    
    require_encryption_key: bool = False
    encryption_key: str = "staging-encryption-key-32-bytes"
    cors_origins: List[str] = ["https://staging.example.com", "http://localhost:3000"]
    detailed_errors: bool = True

class ProductionSecuritySettings(BaseSecuritySettings):
    """Production security settings with strict requirements."""
    
    cors_origins: List[str] = []
    detailed_errors: bool = False

class BaseGitSettings(BaseSettings):
    """Base Git operations configuration settings."""
    
    # Git authentication timeout
    git_timeout: int = Field(
        default=300,
        description="Git operation timeout in seconds"
    )
    
    # SSH settings
    ssh_key_size: int = Field(
        default=2048,
        description="Default SSH key size in bits"
    )
    
    ssh_known_hosts_file: Optional[str] = Field(
        default=None,
        description="Path to SSH known_hosts file"
    )
    
    # Repository validation
    max_repo_size_mb: int = Field(
        default=1000,
        description="Maximum repository size in MB for cloning"
    )
    
    allowed_git_hosts: List[str] = Field(
        default=["github.com", "gitlab.com", "bitbucket.org"],
        description="List of allowed Git hosts for repositories"
    )
    
    allow_any_git_host: bool = Field(
        default=False,
        description="Allow cloning from any Git host"
    )

class DevGitSettings(BaseGitSettings):
    """Development Git settings with relaxed restrictions."""
    
    git_timeout: int = 3600  # 1 hour for development
    max_repo_size_mb: int = 5000
    allow_any_git_host: bool = True

class StagingGitSettings(BaseGitSettings):
    """Staging Git settings."""
    
    allowed_git_hosts: List[str] = ["github.com", "gitlab.com", "bitbucket.org", "dev.example.com"]

class ProductionGitSettings(BaseGitSettings):
    """Production Git settings with strict host validation."""

class BasePipelineSettings(BaseSettings):
    """Base pipeline execution configuration settings."""
    
    # Build settings
    build_timeout: int = Field(
        default=1800,
        description="Pipeline build timeout in seconds (30 minutes)"
    )
    
    max_concurrent_builds: int = Field(
        default=3,
        description="Maximum number of concurrent pipeline builds"
    )
    
    # Workspace settings
    workspace_dir: str = Field(
        default="/tmp/open_webui_builds",
        description="Directory for temporary build workspaces"
    )
    
    workspace_cleanup_hours: int = Field(
        default=24,
        description="Hours after which build workspaces are automatically cleaned up"
    )
    
    # Output settings
    default_retention_days: int = Field(
        default=7,
        description="Default retention period for build outputs in days"
    )
    
    max_output_size_mb: int = Field(
        default=500,
        description="Maximum build output size in MB"
    )

class DevPipelineSettings(BasePipelineSettings):
    """Development pipeline settings with relaxed limits."""
    
    build_timeout: int = 3600
    max_concurrent_builds: int = 1
    workspace_cleanup_hours: int = 1
    default_retention_days: int = 1
    max_output_size_mb: int = 1000

class StagingPipelineSettings(BasePipelineSettings):
    """Staging pipeline settings."""
    
    build_timeout: int = 2700

class ProductionPipelineSettings(BasePipelineSettings):
    """Production pipeline settings."""

class BaseRegistrySettings(BaseSettings):
    """Base container registry configuration settings."""
    
    # Registry connection settings
    registry_timeout: int = Field(
        default=600,
        description="Container registry operation timeout in seconds"
    )
    
    # Docker settings
    docker_api_version: str = Field(
        default="auto",
        description="Docker API version to use"
    )
    
    docker_base_url: str = Field(
        default="unix://var/run/docker.sock",
        description="Docker daemon connection URL"
    )
    
    # Image settings
    max_image_size_gb: int = Field(
        default=5,
        description="Maximum Docker image size in GB"
    )
    
    image_pull_timeout: int = Field(
        default=900,
        description="Docker image pull timeout in seconds"
    )

class DevRegistrySettings(BaseRegistrySettings):
    """Development registry settings."""

class StagingRegistrySettings(BaseRegistrySettings):
    """Staging registry settings."""

class ProductionRegistrySettings(BaseRegistrySettings):
    """Production registry settings."""

class BaseLoggingSettings(BaseSettings):
    """Base logging configuration settings."""
    
    # Log level
    log_level: str = Field(
        default="INFO",
        description="Application log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    
    # Log format
    log_format: str = Field(
        default="json",
        description="Log format (json or text)"
    )
    
    # File logging
    log_file: Optional[str] = Field(
        default=None,
        description="Path to log file (if not specified, logs to console)"
    )
    
    log_max_size_mb: int = Field(
        default=100,
        description="Maximum log file size in MB before rotation"
    )
    
    log_backup_count: int = Field(
        default=5,
        description="Number of log backup files to keep"
    )
    
    # Structured logging
    enable_structured_logging: bool = Field(
        default=True,
        description="Enable structured logging with context"
    )

class DevLoggingSettings(BaseLoggingSettings):
    """Development logging settings."""
    
    log_level: str = "DEBUG"
    log_format: str = "text"
    enable_structured_logging: bool = False

class StagingLoggingSettings(BaseLoggingSettings):
    """Staging logging settings."""
    
    log_level: str = "INFO"

class ProductionLoggingSettings(BaseLoggingSettings):
    """Production logging settings."""
    
    log_level: str = "WARNING"

class BaseAPISettings(BaseSettings):
    """Base API configuration settings."""
    
    # API settings
    api_title: str = Field(
        default="Open WebUI Customizer API",
        description="API title for documentation"
    )
    
    api_description: str = Field(
        default="API for customizing Open WebUI with custom branding and builds",
        description="API description"
    )
    
    api_version: str = Field(
        default="1.0.0",
        description="API version"
    )
    
    # Request limits
    max_request_size_mb: int = Field(
        default=100,
        description="Maximum request size in MB"
    )
    
    # Pagination defaults
    default_page_size: int = Field(
        default=50,
        description="Default pagination page size"
    )
    
    max_page_size: int = Field(
        default=1000,
        description="Maximum pagination page size"
    )

class DevAPISettings(BaseAPISettings):
    """Development API settings."""
    
    max_request_size_mb: int = 1000

class StagingAPISettings(BaseAPISettings):
    """Staging API settings."""

class ProductionAPISettings(BaseAPISettings):
    """Production API settings."""

class BaseSettings(BaseSettings):
    """Base application settings class with common defaults."""
    
    # Environment
    environment: str = Field(
        default="development",
        description="Application environment (development, staging, production)"
    )
    
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    
    # Host and port
    host: str = Field(
        default="0.0.0.0",
        description="Server host"
    )
    
    port: int = Field(
        default=8000,
        description="Server port"
    )
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"
        case_sensitive = False
        
        # Allow field values from environment variables
        # Example: DATABASE_URL=postgresql://user:pass@localhost/db
        # Example: SECURITY__SECRET_KEY=my-secret-key

class DevSettings(BaseSettings):
    """Development settings with relaxed restrictions."""
    
    debug: bool = True
    
    # Sub-settings
    database: DevDatabaseSettings = Field(default_factory=DevDatabaseSettings)
    security: DevSecuritySettings = Field(default_factory=DevSecuritySettings)
    git: DevGitSettings = Field(default_factory=DevGitSettings)
    pipeline: DevPipelineSettings = Field(default_factory=DevPipelineSettings)
    registry: DevRegistrySettings = Field(default_factory=DevRegistrySettings)
    logging: DevLoggingSettings = Field(default_factory=DevLoggingSettings)
    api: DevAPISettings = Field(default_factory=DevAPISettings)

class StagingSettings(BaseSettings):
    """Staging settings."""
    
    debug: bool = False
    
    # Sub-settings
    database: StagingDatabaseSettings = Field(default_factory=StagingDatabaseSettings)
    security: StagingSecuritySettings = Field(default_factory=StagingSecuritySettings)
    git: StagingGitSettings = Field(default_factory=StagingGitSettings)
    pipeline: StagingPipelineSettings = Field(default_factory=StagingPipelineSettings)
    registry: StagingRegistrySettings = Field(default_factory=StagingRegistrySettings)
    logging: StagingLoggingSettings = Field(default_factory=StagingLoggingSettings)
    api: StagingAPISettings = Field(default_factory=StagingAPISettings)

class ProductionSettings(BaseSettings):
    """Production settings with strict security."""
    
    debug: bool = False
    
    # Sub-settings
    database: ProductionDatabaseSettings = Field(default_factory=ProductionDatabaseSettings)
    security: ProductionSecuritySettings = Field(default_factory=ProductionSecuritySettings)
    git: ProductionGitSettings = Field(default_factory=ProductionGitSettings)
    pipeline: ProductionPipelineSettings = Field(default_factory=ProductionPipelineSettings)
    registry: ProductionRegistrySettings = Field(default_factory=ProductionRegistrySettings)
    logging: ProductionLoggingSettings = Field(default_factory=ProductionLoggingSettings)
    api: ProductionAPISettings = Field(default_factory=ProductionAPISettings)

def create_settings() -> BaseSettings:
    """Create appropriate settings instance based on environment."""
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "production":
        return ProductionSettings()
    elif environment == "staging":
        return StagingSettings()
    else:
        # Default to development for any unspecified environment
        return DevSettings()

# Global settings instance
settings = create_settings()

def get_settings() -> BaseSettings:
    """Get the global settings instance."""
    return settings

def reload_settings() -> BaseSettings:
    """Reload settings from environment variables."""
    global settings
    settings = create_settings()
    return settings