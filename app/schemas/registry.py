from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

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

class ContainerRegistryInDBBase(ContainerRegistryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ContainerRegistry(ContainerRegistryInDBBase):
    pass