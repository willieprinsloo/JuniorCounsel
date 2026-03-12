"""
Draft session endpoints for document drafting workflow.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.middleware.database import get_db
from app.persistence.models import User, DraftSessionStatusEnum
from app.persistence.repositories import DraftSessionRepository, CitationRepository
from app.schemas.draft_session import (
    DraftSessionCreate,
    DraftSessionUpdate,
    DraftSessionResponse,
    DraftSessionListResponse,
    IntakeResponsesSubmit,
    CitationResponse,
    CitationsListResponse,
)

router = APIRouter()


@router.post("/", response_model=DraftSessionResponse, status_code=status.HTTP_201_CREATED)
def create_draft_session(
    draft_data: DraftSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new draft session.

    Requires authentication.

    Args:
        draft_data: Draft session creation data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created draft session object (status: intake)
    """
    draft_repo = DraftSessionRepository(db)
    draft_session = draft_repo.create(
        case_id=draft_data.case_id,
        user_id=current_user.id,
        rulebook_id=draft_data.rulebook_id,
        title=draft_data.title,
        document_type=draft_data.document_type
    )
    return draft_session


@router.get("/{draft_session_id}", response_model=DraftSessionResponse)
def get_draft_session(
    draft_session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a draft session by ID.

    Requires authentication.

    Args:
        draft_session_id: Draft session ID (UUID)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Draft session object

    Raises:
        HTTPException: If draft session not found (404)
    """
    draft_repo = DraftSessionRepository(db)
    draft_session = draft_repo.get_by_id(draft_session_id)

    if not draft_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft session not found"
        )

    return draft_session


@router.get("/", response_model=DraftSessionListResponse)
def list_draft_sessions(
    case_id: str = Query(..., description="Case ID to filter draft sessions"),
    status: Optional[DraftSessionStatusEnum] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    sort: str = Query("created_at", description="Field to sort by"),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List draft sessions with pagination and filtering.

    Requires authentication.

    Args:
        case_id: Case ID (required)
        status: Filter by draft status
        page: Page number
        per_page: Items per page
        sort: Sort field
        order: Sort order (asc/desc)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Paginated list of draft sessions
    """
    draft_repo = DraftSessionRepository(db)
    drafts, total = draft_repo.list(
        case_id=case_id,
        status=status,
        page=page,
        per_page=per_page,
        sort=sort,
        order=order
    )

    # Calculate next page
    next_page = page + 1 if (page * per_page) < total else None

    return {
        "data": drafts,
        "page": page,
        "per_page": per_page,
        "total": total,
        "next_page": next_page
    }


@router.patch("/{draft_session_id}", response_model=DraftSessionResponse)
def update_draft_session(
    draft_session_id: str,
    draft_data: DraftSessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a draft session.

    Requires authentication. Only updates provided fields.

    Args:
        draft_session_id: Draft session ID (UUID)
        draft_data: Draft session update data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated draft session object

    Raises:
        HTTPException: If draft session not found (404)
    """
    draft_repo = DraftSessionRepository(db)
    draft_session = draft_repo.get_by_id(draft_session_id)

    if not draft_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft session not found"
        )

    # Update only provided fields
    if draft_data.title is not None:
        draft_session.title = draft_data.title
    if draft_data.intake_responses is not None:
        draft_session.intake_responses = draft_data.intake_responses
    if draft_data.status is not None:
        draft_session.status = draft_data.status

    db.flush()
    return draft_session


@router.delete("/{draft_session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_draft_session(
    draft_session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a draft session.

    Requires authentication.

    Args:
        draft_session_id: Draft session ID (UUID)
        db: Database session
        current_user: Current authenticated user

    Raises:
        HTTPException: If draft session not found (404)
    """
    draft_repo = DraftSessionRepository(db)
    draft_session = draft_repo.get_by_id(draft_session_id)

    if not draft_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft session not found"
        )

    db.delete(draft_session)
    db.flush()


@router.post("/{draft_session_id}/answers", response_model=DraftSessionResponse)
def submit_intake_responses(
    draft_session_id: str,
    intake_data: IntakeResponsesSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit intake responses for a draft session.

    Updates the draft session with user's answers to intake questions
    and transitions status to AWAITING_INTAKE → ready for generation.

    Requires authentication.

    Args:
        draft_session_id: Draft session ID (UUID)
        intake_data: Intake responses (dict of field_id → value)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated draft session object with intake_responses populated

    Raises:
        HTTPException: If draft session not found (404)
        HTTPException: If draft session not in valid state for intake (400)
    """
    draft_repo = DraftSessionRepository(db)
    draft_session = draft_repo.get_by_id(draft_session_id)

    if not draft_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft session not found"
        )

    # Validate status (should be INITIALIZING or AWAITING_INTAKE)
    if draft_session.status not in [
        DraftSessionStatusEnum.INITIALIZING,
        DraftSessionStatusEnum.AWAITING_INTAKE
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit intake for draft in {draft_session.status} status"
        )

    # Update intake responses
    draft_session.intake_responses = intake_data.intake_responses
    draft_session.status = DraftSessionStatusEnum.AWAITING_INTAKE

    db.flush()
    return draft_session


@router.post("/{draft_session_id}/start-generation", response_model=DraftSessionResponse)
def start_draft_generation(
    draft_session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start draft generation for a draft session.

    Enqueues background jobs for research and draft generation.
    Transitions status to RESEARCH → background workers process.

    Requires authentication.

    Args:
        draft_session_id: Draft session ID (UUID)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Draft session object with updated status (RESEARCH)

    Raises:
        HTTPException: If draft session not found (404)
        HTTPException: If draft session not ready for generation (400)
        HTTPException: If intake responses missing (400)
    """
    draft_repo = DraftSessionRepository(db)
    draft_session = draft_repo.get_by_id(draft_session_id)

    if not draft_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft session not found"
        )

    # Validate status (should be AWAITING_INTAKE)
    if draft_session.status != DraftSessionStatusEnum.AWAITING_INTAKE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start generation for draft in {draft_session.status} status. "
                   f"Expected {DraftSessionStatusEnum.AWAITING_INTAKE}"
        )

    # Validate intake responses provided
    if not draft_session.intake_responses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Intake responses required before starting generation. "
                   "Submit answers first via POST /draft-sessions/{id}/answers"
        )

    # Enqueue draft research job (will auto-trigger generation after research)
    from app.core.queue import enqueue_draft_research

    try:
        job_id = enqueue_draft_research(draft_session_id)
        draft_session.status = DraftSessionStatusEnum.RESEARCH
        db.flush()

        return draft_session

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enqueue draft generation: {str(e)}"
        )


@router.get("/{draft_session_id}/citations", response_model=CitationsListResponse)
def get_draft_citations(
    draft_session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get citations for a draft session (Audit mode).

    Returns all citations with source excerpts for verification.
    Used in Audit mode to show side-by-side source documents.

    Requires authentication.

    Args:
        draft_session_id: Draft session ID (UUID)
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of citations with source document excerpts

    Raises:
        HTTPException: If draft session not found (404)
        HTTPException: If draft not yet generated (400)
    """
    draft_repo = DraftSessionRepository(db)
    draft_session = draft_repo.get_by_id(draft_session_id)

    if not draft_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft session not found"
        )

    # Validate draft has been generated
    if draft_session.status not in [
        DraftSessionStatusEnum.REVIEW,
        DraftSessionStatusEnum.READY
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Citations not available for draft in {draft_session.status} status. "
                   f"Draft must be generated first."
        )

    # Query citations from Citation model
    citation_repo = CitationRepository(db)
    citations_with_doc_info = citation_repo.get_with_document_info(draft_session_id)

    # Convert to CitationResponse objects
    citations_data = []
    for citation_dict in citations_with_doc_info:
        citations_data.append(CitationResponse(
            marker=citation_dict["marker"],
            content=citation_dict["citation_text"],
            document_name=citation_dict["document_filename"] or "Unknown",
            document_id=citation_dict["document_id"] or "",
            page=citation_dict["page_number"],
            similarity=citation_dict["similarity_score"]
        ))

    return CitationsListResponse(
        draft_session_id=draft_session_id,
        citations=citations_data,
        total_citations=len(citations_data)
    )
