"""
Upload session endpoints for batch upload tracking.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.middleware.database import get_db
from app.persistence.models import User
from app.persistence.repositories import UploadSessionRepository
from app.schemas.upload_session import (
    UploadSessionCreate,
    UploadSessionResponse,
    UploadSessionListResponse,
)

router = APIRouter()


@router.post("/", response_model=UploadSessionResponse, status_code=status.HTTP_201_CREATED)
def create_upload_session(
    session_data: UploadSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new upload session for batch uploads.

    Requires authentication.

    Args:
        session_data: Upload session creation data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created upload session object
    """
    session_repo = UploadSessionRepository(db)
    upload_session = session_repo.create(
        case_id=session_data.case_id,
        uploaded_by_id=current_user.id,
        total_documents=session_data.total_documents
    )
    return upload_session


@router.get("/{upload_session_id}", response_model=UploadSessionResponse)
def get_upload_session(
    upload_session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get an upload session by ID.

    Requires authentication.

    Args:
        upload_session_id: Upload session ID (UUID)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Upload session object

    Raises:
        HTTPException: If upload session not found (404)
    """
    session_repo = UploadSessionRepository(db)
    upload_session = session_repo.get_by_id(upload_session_id)

    if not upload_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload session not found"
        )

    return upload_session


@router.get("/", response_model=UploadSessionListResponse)
def list_upload_sessions(
    case_id: str = Query(..., description="Case ID to filter upload sessions"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    sort: str = Query("created_at", description="Field to sort by"),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List upload sessions with pagination.

    Requires authentication.

    Args:
        case_id: Case ID (required)
        page: Page number
        per_page: Items per page
        sort: Sort field
        order: Sort order (asc/desc)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Paginated list of upload sessions
    """
    session_repo = UploadSessionRepository(db)
    sessions, total = session_repo.list(
        case_id=case_id,
        page=page,
        per_page=per_page,
        sort=sort,
        order=order
    )

    # Calculate next page
    next_page = page + 1 if (page * per_page) < total else None

    return {
        "data": sessions,
        "page": page,
        "per_page": per_page,
        "total": total,
        "next_page": next_page
    }
