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

    # Research phase outputs
    case_profile: Optional[dict] = None
    research_summary: Optional[dict] = None
    outline: Optional[dict] = None

    # Intake responses
    intake_responses: Optional[dict] = None

    # Generated DraftDoc
    draft_doc: Optional[dict] = None

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


class IntakeResponsesSubmit(BaseModel):
    """Schema for submitting intake responses."""

    intake_responses: dict

    model_config = {"str_strip_whitespace": True}


class CitationResponse(BaseModel):
    """Schema for a single citation."""

    marker: str  # e.g., "[1]", "[2]"
    content: str  # Excerpt from source document
    document_name: str
    document_id: str
    page: Optional[int] = None
    similarity: Optional[float] = None

    model_config = {"from_attributes": True}


class CitationsListResponse(BaseModel):
    """Schema for list of citations in audit mode."""

    draft_session_id: str
    citations: list[CitationResponse]
    total_citations: int
