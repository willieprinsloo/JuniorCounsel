"""
Pydantic schemas for draft session endpoints.
"""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel

from app.persistence.models import DraftSessionStatusEnum


class DraftSessionCreate(BaseModel):
    """Schema for creating a new draft session."""

    case_id: str
    rulebook_id: int
    title: str
    document_type: str

    model_config = {"str_strip_whitespace": True}


class DraftSessionUpdate(BaseModel):
    """Schema for updating a draft session."""

    title: Optional[str] = None
    intake_responses: Optional[dict] = None
    status: Optional[DraftSessionStatusEnum] = None

    model_config = {"str_strip_whitespace": True}


class DraftSessionResponse(BaseModel):
    """Schema for draft session data in responses."""

    id: str
    case_id: str
    user_id: int
    rulebook_id: int
    title: str
    document_type: str
    status: DraftSessionStatusEnum
    intake_responses: Optional[dict] = None
    research_summary: Optional[dict] = None
    generated_content: Optional[str] = None
    final_content: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DraftSessionListResponse(BaseModel):
    """Schema for paginated draft session list response."""

    data: list[DraftSessionResponse]
    page: int
    per_page: int
    total: int
    next_page: Optional[int] = None
