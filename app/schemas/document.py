from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class DocumentCreate(BaseModel):
    project_id: UUID
    name: str

class DocumentUpdate(BaseModel):
    name: str

class DocumentResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    s3_key: str
    size_bytes: int
    content_type: str
    uploaded_by: UUID
    created_at: datetime
    updated_at: datetime
