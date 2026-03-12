"""
Pydantic schemas for case endpoints.
"""
from typing import Optional, Any
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_serializer

from app.persistence.models import CaseStatusEnum


class CaseCreate(BaseModel):
    """Schema for creating a new case."""

    organisation_id: int
    title: str
    owner_id: Optional[int] = None
    description: Optional[str] = None
    case_type: Optional[str] = None
    jurisdiction: Optional[str] = None

    model_config = {"str_strip_whitespace": True}


class CaseUpdate(BaseModel):
    """Schema for updating a case."""

    title: Optional[str] = None
    description: Optional[str] = None
    case_type: Optional[str] = None
    jurisdiction: Optional[str] = None
    status: Optional[CaseStatusEnum] = None

    model_config = {"str_strip_whitespace": True}


class CaseResponse(BaseModel):
    """Schema for case data in responses."""

    id: str  # UUID converted to string via field_serializer
    organisation_id: int
    owner_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    case_type: Optional[str] = None
    jurisdiction: Optional[str] = None
    status: CaseStatusEnum
    case_metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    @field_serializer('id')
    def serialize_id(self, value: UUID | str, _info) -> str:
        """Convert UUID to string for JSON serialization."""
        return str(value)

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }


class CaseListResponse(BaseModel):
    """Schema for paginated case list response."""

    data: list[CaseResponse]
    page: int
    per_page: int
    total: int
    next_page: Optional[int] = None
