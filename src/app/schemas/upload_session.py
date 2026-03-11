"""
Pydantic schemas for upload session endpoints.
"""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel


class UploadSessionCreate(BaseModel):
    """Schema for creating a new upload session."""

    case_id: str
    total_documents: int = 0

    model_config = {"str_strip_whitespace": True}


class UploadSessionResponse(BaseModel):
    """Schema for upload session data in responses."""

    id: str
    case_id: str
    uploaded_by_id: int
    total_documents: int
    completed_documents: int
    failed_documents: int
    created_at: datetime

    model_config = {"from_attributes": True}


class UploadSessionListResponse(BaseModel):
    """Schema for paginated upload session list response."""

    data: list[UploadSessionResponse]
    page: int
    per_page: int
    total: int
    next_page: Optional[int] = None
