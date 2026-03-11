"""
Rulebook endpoints for managing document type rules and templates.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.rulebook_validator import RulebookValidator, RulebookValidationError
from app.dependencies import get_current_user
from app.middleware.database import get_db
from app.persistence.models import User, RulebookStatusEnum
from app.persistence.repositories import RulebookRepository
from app.schemas.rulebook import (
    RulebookCreate,
    RulebookUpdate,
    RulebookResponse,
    RulebookListResponse,
)

router = APIRouter()


@router.post("/", response_model=RulebookResponse, status_code=status.HTTP_201_CREATED)
def create_rulebook(
    rulebook_data: RulebookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new rulebook.

    Requires authentication.

    Args:
        rulebook_data: Rulebook creation data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created rulebook object (status: draft)
    """
    rulebook_repo = RulebookRepository(db)
    rulebook = rulebook_repo.create(
        document_type=rulebook_data.document_type,
        jurisdiction=rulebook_data.jurisdiction,
        version=rulebook_data.version,
        source_yaml=rulebook_data.source_yaml,
        created_by_id=current_user.id,
        label=rulebook_data.label
    )
    return rulebook


@router.get("/{rulebook_id}", response_model=RulebookResponse)
def get_rulebook(
    rulebook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a rulebook by ID.

    Requires authentication.

    Args:
        rulebook_id: Rulebook ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Rulebook object

    Raises:
        HTTPException: If rulebook not found (404)
    """
    rulebook_repo = RulebookRepository(db)
    rulebook = rulebook_repo.get_by_id(rulebook_id)

    if not rulebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rulebook not found"
        )

    return rulebook


@router.get("/", response_model=RulebookListResponse)
def list_rulebooks(
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction"),
    status: Optional[RulebookStatusEnum] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    sort: str = Query("created_at", description="Field to sort by"),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List rulebooks with pagination and filtering.

    Requires authentication.

    Args:
        document_type: Filter by document type
        jurisdiction: Filter by jurisdiction
        status: Filter by rulebook status
        page: Page number
        per_page: Items per page
        sort: Sort field
        order: Sort order (asc/desc)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Paginated list of rulebooks
    """
    rulebook_repo = RulebookRepository(db)
    rulebooks, total = rulebook_repo.list(
        document_type=document_type,
        jurisdiction=jurisdiction,
        status=status,
        page=page,
        per_page=per_page,
        sort=sort,
        order=order
    )

    # Calculate next page
    next_page = page + 1 if (page * per_page) < total else None

    return {
        "data": rulebooks,
        "page": page,
        "per_page": per_page,
        "total": total,
        "next_page": next_page
    }


@router.get("/published/{document_type}/{jurisdiction}", response_model=RulebookResponse)
def get_published_rulebook(
    document_type: str,
    jurisdiction: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the latest published rulebook for a document type and jurisdiction.

    Requires authentication.

    Args:
        document_type: Document type (e.g., "affidavit", "pleading")
        jurisdiction: Jurisdiction (e.g., "Gauteng High Court")
        db: Database session
        current_user: Current authenticated user

    Returns:
        Latest published rulebook

    Raises:
        HTTPException: If no published rulebook found (404)
    """
    rulebook_repo = RulebookRepository(db)
    rulebook = rulebook_repo.get_published(
        document_type=document_type,
        jurisdiction=jurisdiction
    )

    if not rulebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No published rulebook found for {document_type} in {jurisdiction}"
        )

    return rulebook


@router.patch("/{rulebook_id}", response_model=RulebookResponse)
def update_rulebook(
    rulebook_id: int,
    rulebook_data: RulebookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a rulebook.

    Requires authentication. Only updates provided fields.

    Args:
        rulebook_id: Rulebook ID
        rulebook_data: Rulebook update data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated rulebook object

    Raises:
        HTTPException: If rulebook not found (404)
    """
    rulebook_repo = RulebookRepository(db)
    rulebook = rulebook_repo.get_by_id(rulebook_id)

    if not rulebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rulebook not found"
        )

    # Update only provided fields
    if rulebook_data.source_yaml is not None:
        rulebook.source_yaml = rulebook_data.source_yaml
    if rulebook_data.label is not None:
        rulebook.label = rulebook_data.label
    if rulebook_data.status is not None:
        rulebook.status = rulebook_data.status

    db.flush()
    return rulebook


@router.post("/validate")
def validate_rulebook_yaml(
    yaml_content: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Validate rulebook YAML without saving.

    Useful for admins to check YAML before creating/updating a rulebook.

    Args:
        yaml_content: YAML string to validate
        db: Database session
        current_user: Current authenticated user

    Returns:
        Validation result with errors and parsed JSON

    Example:
        ```json
        {
          "valid": true,
          "errors": [],
          "warnings": ["intake_questions[0] missing optional 'help_text'"],
          "parsed_json": {...}
        }
        ```
    """
    try:
        parsed = RulebookValidator.validate(yaml_content)
        return {
            "valid": True,
            "errors": [],
            "warnings": [],
            "parsed_json": parsed
        }
    except RulebookValidationError as e:
        return {
            "valid": False,
            "errors": [str(e)],
            "warnings": [],
            "parsed_json": None
        }


@router.delete("/{rulebook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rulebook(
    rulebook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a rulebook.

    Requires authentication.

    Args:
        rulebook_id: Rulebook ID
        db: Database session
        current_user: Current authenticated user

    Raises:
        HTTPException: If rulebook not found (404)
    """
    rulebook_repo = RulebookRepository(db)
    rulebook = rulebook_repo.get_by_id(rulebook_id)

    if not rulebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rulebook not found"
        )

    db.delete(rulebook)
    db.flush()
