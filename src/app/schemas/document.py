"""
Pydantic schemas for document endpoints.
"""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel

from app.persistence.models import DocumentStatusEnum


class DocumentCreate(BaseModel):
    """Schema for creating a new document."""

    case_id: str
    filename: str
    upload_session_id: Optional[str] = None
    needs_ocr: bool = False

    model_config = {"str_strip_whitespace": True}


class DocumentUpdate(BaseModel):
    """Schema for updating document metadata."""

    document_type: Optional[str] = None
    semantic_role: Optional[str] = None
    tags: Optional[list[str]] = None

    model_config = {"str_strip_whitespace": True}


class DocumentStatusUpdate(BaseModel):
    """Schema for updating document processing status."""

    overall_status: DocumentStatusEnum
    stage: Optional[str] = None
    stage_progress: Optional[int] = None
    error_message: Optional[str] = None


class DocumentResponse(BaseModel):
    """Schema for document data in responses."""

    id: str
    case_id: str
    uploaded_by_id: int
    upload_session_id: Optional[str] = None
    filename: str
    document_type: Optional[str] = None
    semantic_role: Optional[str] = None
    needs_ocr: bool
    overall_status: DocumentStatusEnum
    stage: Optional[str] = None
    stage_progress: int
    error_message: Optional[str] = None
    tags: Optional[list[str]] = None
    metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """Schema for paginated document list response."""

    data: list[DocumentResponse]
    page: int
    per_page: int
    total: int
    next_page: Optional[int] = None
