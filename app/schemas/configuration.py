from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Pipeline Configuration Schemas
class PipelineConfigurationBase(BaseModel):
    name: str
    base_image: str
    image_tag_suffix: str
    registry_id: int

class PipelineConfigurationCreate(PipelineConfigurationBase):
    pass

class PipelineConfigurationUpdate(PipelineConfigurationBase):
    name: Optional[str] = None
    base_image: Optional[str] = None
    image_tag_suffix: Optional[str] = None
    registry_id: Optional[int] = None

class PipelineConfigurationInDBBase(PipelineConfigurationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PipelineConfiguration(PipelineConfigurationInDBBase):
    pass