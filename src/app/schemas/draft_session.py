"""
Pydantic schemas for draft session endpoints.
"""
from typing import Optional, Any, Annotated
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, BeforeValidator

from app.persistence.models import DraftSessionStatusEnum


def uuid_to_str(v: Any) -> str:
    """Convert UUID to string."""
    if isinstance(v, UUID):
        return str(v)
    return str(v)


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

    id: Annotated[str, BeforeValidator(uuid_to_str)]  # UUID converted to string
    case_id: Annotated[str, BeforeValidator(uuid_to_str)]  # UUID converted to string
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

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }


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
    document_id: Annotated[str, BeforeValidator(uuid_to_str)]  # UUID converted to string
    page: Optional[int] = None
    similarity: Optional[float] = None

    model_config = {"from_attributes": True}


class CitationsListResponse(BaseModel):
    """Schema for list of citations in audit mode."""

    draft_session_id: Annotated[str, BeforeValidator(uuid_to_str)]  # UUID converted to string
    citations: list[CitationResponse]
    total_citations: int
