"""
Pydantic schemas for rulebook endpoints.
"""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel

from app.persistence.models import RulebookStatusEnum


class RulebookCreate(BaseModel):
    """Schema for creating a new rulebook."""

    document_type: str
    jurisdiction: str
    version: str
    source_yaml: str
    label: Optional[str] = None

    model_config = {"str_strip_whitespace": True}


class RulebookUpdate(BaseModel):
    """Schema for updating a rulebook."""

    source_yaml: Optional[str] = None
    label: Optional[str] = None
    status: Optional[RulebookStatusEnum] = None

    model_config = {"str_strip_whitespace": True}


class RulebookResponse(BaseModel):
    """Schema for rulebook data in responses."""

    id: int
    document_type: str
    jurisdiction: str
    version: str
    source_yaml: str
    rules_json: Optional[dict] = None
    label: Optional[str] = None
    status: RulebookStatusEnum
    created_by_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RulebookListResponse(BaseModel):
    """Schema for paginated rulebook list response."""

    data: list[RulebookResponse]
    page: int
    per_page: int
    total: int
    next_page: Optional[int] = None
