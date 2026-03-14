"""
Pydantic schemas for document endpoints.
"""
from typing import Optional, Any
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, model_validator

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

    @model_validator(mode='before')
    @classmethod
    def convert_uuid_to_str(cls, data: Any) -> Any:
        """Convert UUID fields to strings before validation."""
        if isinstance(data, dict):
            # Convert all UUID fields
            for key in ['id', 'case_id', 'upload_session_id']:
                if key in data and isinstance(data[key], UUID):
                    data[key] = str(data[key])
            return data
        # Handle SQLAlchemy model objects
        if hasattr(data, '__dict__'):
            data_dict = {}
            for key, value in data.__dict__.items():
                if key.startswith('_'):
                    continue
                if isinstance(value, UUID):
                    data_dict[key] = str(value)
                else:
                    data_dict[key] = value
            return data_dict
        return data


class DocumentListResponse(BaseModel):
    """Schema for paginated document list response."""

    data: list[DocumentResponse]
    page: int
    per_page: int
    total: int
    next_page: Optional[int] = None
