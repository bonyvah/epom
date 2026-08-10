from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
class DocumentUpdate(BaseModel):
    name: str

class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    project_id: UUID
    name: str
    s3_key: str
    size_bytes: int
    content_type: str
    uploaded_by: UUID
    created_at: datetime
    updated_at: datetime
