from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

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

# Pipeline Step Enum
from enum import Enum

class PipelineStep(str, Enum):
    SOURCE = "source"
    BUILD = "build"
    PUBLISH = "publish"
    CLEAN = "clean"