from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    description: str | None = Field(default=None,max_length=1000)

class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=256)
    description: str | None = Field(default=None, max_length=1000)

    @field_validator("name")
    @classmethod
    def name_cant_be_null(cls, v: str | None) -> str:
        if v is None:
            raise ValueError("Name cant be null")
        return v

class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None 
    owner_id: UUID
    created_at: datetime
    updated_at: datetime
    project_size_limit_gb: int
    document_size_limit_mb: int
class InviteUserRequest(BaseModel):
    user_id: UUID