# app/schemas/pagination.py
from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="Page number")
    size: int = Field(default=10, ge=1, le=100, description="Page size (max 100)")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size