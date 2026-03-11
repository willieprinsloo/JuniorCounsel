"""
Pydantic schemas for case endpoints.
"""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel

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

    id: str
    organisation_id: int
    owner_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    case_type: Optional[str] = None
    jurisdiction: Optional[str] = None
    status: CaseStatusEnum
    metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CaseListResponse(BaseModel):
    """Schema for paginated case list response."""

    data: list[CaseResponse]
    page: int
    per_page: int
    total: int
    next_page: Optional[int] = None
