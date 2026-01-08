from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class BrandingTemplate(Base):
    __tablename__ = "branding_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(Text)
    brand_name = Column(String)
    replacement_rules = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to branding assets
    assets = relationship("BrandingAsset", back_populates="template")

class BrandingAsset(Base):
    __tablename__ = "branding_assets"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("branding_templates.id"))
    file_name = Column(String, index=True)
    file_type = Column(String)  # logo, favicon, theme, etc.
    file_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship back to template
    template = relationship("BrandingTemplate", back_populates="assets")

class ContainerRegistry(Base):
    __tablename__ = "container_registries"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    registry_type = Column(String)  # aws_ecr, docker_hub, quay_io
    base_image = Column(String)
    target_image = Column(String)
    aws_account_id = Column(String, nullable=True)
    aws_region = Column(String, nullable=True)
    repository_name = Column(String, nullable=True)
    username = Column(String, nullable=True)
    password = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Configuration(Base):
    __tablename__ = "configurations"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    status = Column(String)  # pending, running, completed, failed
    steps_to_execute = Column(JSON)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    logs = Column(Text)
    
    # New fields for custom fork support
    git_repository_id = Column(Integer, ForeignKey("git_repositories.id"), nullable=True)
    output_type = Column(String, default="docker_image", nullable=False)  # zip or docker_image
    registry_id = Column(Integer, ForeignKey("container_registries.id"), nullable=True)
    
    # Relationships
    git_repository = relationship("GitRepository", back_populates="pipeline_runs")
    build_outputs = relationship("BuildOutput", back_populates="pipeline_run")
    registry = relationship("ContainerRegistry")


class Credential(Base):
    """
    Stores encrypted credentials for various services.
    
    All sensitive data is encrypted at rest using AES-256-GCM.
    Credential data is never exposed in API responses.
    """
    __tablename__ = "credentials"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    credential_type = Column(String(50), nullable=False, index=True)
    encrypted_data = Column(Text, nullable=False)  # JSON string with encrypted payload
    encryption_key_id = Column(String(255), nullable=True)  # For key rotation tracking
    metadata = Column(JSON, default={})  # Non-sensitive metadata
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Optional expiration
    last_used_at = Column(DateTime, nullable=True)  # Track usage
    
    # Relationships
    git_repositories = relationship("GitRepository", back_populates="credential")


class GitRepository(Base):
    """
    Configured Git repositories for building custom forks.
    
    Supports both HTTPS and SSH protocols with optional credential binding.
    """
    __tablename__ = "git_repositories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    repository_url = Column(String(1024), nullable=False)
    repository_type = Column(String(20), nullable=False)  # 'https' or 'ssh'
    default_branch = Column(String(255), default="main", nullable=False)
    credential_id = Column(Integer, ForeignKey("credentials.id"), nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_status = Column(String(50), default="pending", nullable=False)
    verification_message = Column(Text, nullable=True)
    is_experimental = Column(Boolean, default=True, nullable=False)  # Custom forks are experimental
    metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    credential = relationship("Credential", back_populates="git_repositories")
    pipeline_runs = relationship("PipelineRun", back_populates="git_repository")


class BuildOutput(Base):
    """
    Tracks generated build artifacts (ZIP files and Docker images).
    
    Supports automatic cleanup of expired build outputs.
    """
    __tablename__ = "build_outputs"
    
    id = Column(Integer, primary_key=True, index=True)
    pipeline_run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=False)
    output_type = Column(String(50), nullable=False)  # 'zip' or 'docker_image'
    file_path = Column(String(1024), nullable=True)  # For ZIP files
    image_url = Column(String(1024), nullable=True)  # For Docker images (optional)
    file_size_bytes = Column(Integer, nullable=True)
    checksum_sha256 = Column(String(64), nullable=True)
    download_count = Column(Integer, default=0, nullable=False)
    expires_at = Column(DateTime, nullable=True)  # For automatic cleanup
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    pipeline_run = relationship("PipelineRun", back_populates="build_outputs")