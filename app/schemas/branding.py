from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

# Branding Template Schemas
class BrandingTemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    brand_name: str
    replacement_rules: Optional[Dict[str, str]] = None

class BrandingTemplateCreate(BrandingTemplateBase):
    pass

class BrandingTemplateUpdate(BrandingTemplateBase):
    name: Optional[str] = None
    brand_name: Optional[str] = None

class BrandingTemplateInDBBase(BrandingTemplateBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class BrandingTemplate(BrandingTemplateInDBBase):
    pass

class BrandingTemplateWithAssets(BrandingTemplateInDBBase):
    assets: List['BrandingAsset'] = []

# Branding Asset Schemas
class BrandingAssetBase(BaseModel):
    file_name: str
    file_type: str
    file_path: str

class BrandingAssetCreate(BrandingAssetBase):
    template_id: int

class BrandingAssetUpdate(BrandingAssetBase):
    pass

class BrandingAssetInDBBase(BrandingAssetBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class BrandingAsset(BrandingAssetInDBBase):
    template_id: int

# Container Registry Schemas
class ContainerRegistryBase(BaseModel):
    name: str
    registry_type: str  # aws_ecr, docker_hub, quay_io
    base_image: str
    target_image: str
    aws_account_id: Optional[str] = None
    aws_region: Optional[str] = None
    repository_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

class ContainerRegistryCreate(ContainerRegistryBase):
    pass

class ContainerRegistryUpdate(ContainerRegistryBase):
    name: Optional[str] = None
    registry_type: Optional[str] = None
    base_image: Optional[str] = None
    target_image: Optional[str] = None

class ContainerRegistryInDBBase(ContainerRegistryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ContainerRegistry(ContainerRegistryInDBBase):
    pass

# Configuration Schemas
class ConfigurationBase(BaseModel):
    key: str
    value: str

class ConfigurationCreate(ConfigurationBase):
    pass

class ConfigurationUpdate(ConfigurationBase):
    key: Optional[str] = None
    value: Optional[str] = None

class ConfigurationInDBBase(ConfigurationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class Configuration(ConfigurationInDBBase):
    pass

# Pipeline Run Schemas
class PipelineRunBase(BaseModel):
    status: str  # pending, running, completed, failed
    steps_to_execute: List[str]
    logs: Optional[str] = None

class PipelineRunCreate(PipelineRunBase):
    pass

class PipelineRunUpdate(PipelineRunBase):
    status: Optional[str] = None
    steps_to_execute: Optional[List[str]] = None
    logs: Optional[str] = None

class PipelineRunInDBBase(PipelineRunBase):
    id: int
    started_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PipelineRun(PipelineRunInDBBase):
    pass