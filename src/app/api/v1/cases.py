"""
Case endpoints for CRUD operations with pagination.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.middleware.database import get_db
from app.persistence.models import User, CaseStatusEnum
from app.persistence.repositories import CaseRepository
from app.schemas.case import CaseCreate, CaseUpdate, CaseResponse, CaseListResponse

router = APIRouter()


@router.post("/", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(
    case_data: CaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new case.

    Requires authentication.

    Args:
        case_data: Case creation data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created case object
    """
    case_repo = CaseRepository(db)
    case = case_repo.create(
        organisation_id=case_data.organisation_id,
        title=case_data.title,
        owner_id=case_data.owner_id or current_user.id,
        description=case_data.description,
        case_type=case_data.case_type,
        jurisdiction=case_data.jurisdiction
    )
    return case


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a case by ID.

    Requires authentication.

    Args:
        case_id: Case ID (UUID)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Case object

    Raises:
        HTTPException: If case not found (404)
    """
    case_repo = CaseRepository(db)
    case = case_repo.get_by_id(case_id)

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    return case


@router.get("/", response_model=CaseListResponse)
def list_cases(
    organisation_id: int = Query(..., description="Organisation ID to filter cases"),
    status: Optional[CaseStatusEnum] = Query(None, description="Filter by case status"),
    case_type: Optional[str] = Query(None, description="Filter by case type"),
    q: Optional[str] = Query(None, description="Search query (title, description)"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    sort: str = Query("created_at", description="Field to sort by"),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List cases with pagination and filtering.

    Requires authentication.

    Args:
        organisation_id: Organisation ID (required)
        status: Filter by case status
        case_type: Filter by case type
        q: Search query
        page: Page number
        per_page: Items per page
        sort: Sort field
        order: Sort order (asc/desc)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Paginated list of cases
    """
    case_repo = CaseRepository(db)
    cases, total = case_repo.list(
        organisation_id=organisation_id,
        status=status,
        case_type=case_type,
        q=q,
        page=page,
        per_page=per_page,
        sort=sort,
        order=order
    )

    # Calculate next page
    next_page = page + 1 if (page * per_page) < total else None

    return {
        "data": cases,
        "page": page,
        "per_page": per_page,
        "total": total,
        "next_page": next_page
    }


@router.patch("/{case_id}", response_model=CaseResponse)
def update_case(
    case_id: str,
    case_data: CaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a case.

    Requires authentication. Only updates provided fields.

    Args:
        case_id: Case ID (UUID)
        case_data: Case update data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated case object

    Raises:
        HTTPException: If case not found (404)
    """
    case_repo = CaseRepository(db)
    case = case_repo.get_by_id(case_id)

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    # Update only provided fields
    if case_data.title is not None:
        case.title = case_data.title
    if case_data.description is not None:
        case.description = case_data.description
    if case_data.case_type is not None:
        case.case_type = case_data.case_type
    if case_data.jurisdiction is not None:
        case.jurisdiction = case_data.jurisdiction
    if case_data.status is not None:
        case.status = case_data.status

    db.flush()
    return case


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a case.

    Requires authentication.

    Args:
        case_id: Case ID (UUID)
        db: Database session
        current_user: Current authenticated user

    Raises:
        HTTPException: If case not found (404)
    """
    case_repo = CaseRepository(db)
    deleted = case_repo.delete(case_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
