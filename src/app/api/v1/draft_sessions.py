"""
Draft session endpoints for document drafting workflow.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.middleware.database import get_db
from app.persistence.models import User, DraftSessionStatusEnum
from app.persistence.repositories import DraftSessionRepository
from app.schemas.draft_session import (
    DraftSessionCreate,
    DraftSessionUpdate,
    DraftSessionResponse,
    DraftSessionListResponse,
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
