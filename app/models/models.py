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