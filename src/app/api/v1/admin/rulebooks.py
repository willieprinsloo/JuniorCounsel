"""
Admin endpoints for rulebook management.

All endpoints require ADMIN role.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.dependencies import require_admin, get_current_user
from app.middleware.database import get_db
from app.persistence.models import User, RulebookStatusEnum
from app.persistence.repositories import RulebookRepository
from app.schemas.admin import RulebookUpload, RulebookUpdate
from app.schemas.rulebook import RulebookResponse, RulebookListResponse

router = APIRouter()


@router.post("/", response_model=RulebookResponse, status_code=status.HTTP_201_CREATED)
def upload_rulebook(
    rulebook_data: RulebookUpload,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Upload a new rulebook (admin only).

    Creates a new rulebook with the provided YAML content.
    Rulebook starts in DRAFT status by default.
    """
    rulebook_repo = RulebookRepository(db)

    # TODO: Validate YAML syntax and structure
    # For now, just store the raw YAML

    rulebook = rulebook_repo.create(
        document_type=rulebook_data.document_type,
        jurisdiction=rulebook_data.jurisdiction,
        version=rulebook_data.version,
        source_yaml=rulebook_data.source_yaml,
        created_by_id=current_user.id,
        label=rulebook_data.label,
    )

    db.commit()

    return RulebookResponse(
        id=rulebook.id,
        document_type=rulebook.document_type,
        jurisdiction=rulebook.jurisdiction,
        version=rulebook.version,
        label=rulebook.label,
        status=rulebook.status,
        created_at=rulebook.created_at,
        updated_at=rulebook.updated_at,
    )


@router.patch("/{rulebook_id}", response_model=RulebookResponse)
def update_rulebook(
    rulebook_id: int,
    rulebook_data: RulebookUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Update a rulebook's label or YAML content (admin only).

    Can only update rulebooks in DRAFT status.
    To update a PUBLISHED rulebook, create a new version instead.
    """
    rulebook_repo = RulebookRepository(db)

    rulebook = rulebook_repo.get_by_id(rulebook_id)
    if not rulebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rulebook not found",
        )

    # Only allow updating DRAFT rulebooks
    if rulebook.status != RulebookStatusEnum.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update {rulebook.status.value} rulebook. Create a new version instead.",
        )

    # Update fields
    if rulebook_data.label is not None:
        rulebook.label = rulebook_data.label

    if rulebook_data.source_yaml is not None:
        # TODO: Validate YAML syntax
        rulebook.source_yaml = rulebook_data.source_yaml

    from datetime import datetime
    rulebook.updated_at = datetime.utcnow()

    db.commit()

    return RulebookResponse(
        id=rulebook.id,
        document_type=rulebook.document_type,
        jurisdiction=rulebook.jurisdiction,
        version=rulebook.version,
        label=rulebook.label,
        status=rulebook.status,
        created_at=rulebook.created_at,
        updated_at=rulebook.updated_at,
    )


@router.post("/{rulebook_id}/publish", response_model=RulebookResponse)
def publish_rulebook(
    rulebook_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Publish a rulebook (admin only).

    Changes status from DRAFT to PUBLISHED.
    Once published, the rulebook becomes available for use in draft sessions.
    """
    rulebook_repo = RulebookRepository(db)

    rulebook = rulebook_repo.get_by_id(rulebook_id)
    if not rulebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rulebook not found",
        )

    if rulebook.status != RulebookStatusEnum.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot publish {rulebook.status.value} rulebook",
        )

    # TODO: Validate rulebook structure before publishing
    # Ensure it has all required fields, valid YAML, etc.

    updated_rulebook = rulebook_repo.update_status(
        rulebook_id=rulebook_id,
        status=RulebookStatusEnum.PUBLISHED,
    )

    db.commit()

    return RulebookResponse(
        id=updated_rulebook.id,
        document_type=updated_rulebook.document_type,
        jurisdiction=updated_rulebook.jurisdiction,
        version=updated_rulebook.version,
        label=updated_rulebook.label,
        status=updated_rulebook.status,
        created_at=updated_rulebook.created_at,
        updated_at=updated_rulebook.updated_at,
    )


@router.post("/{rulebook_id}/deprecate", response_model=RulebookResponse)
def deprecate_rulebook(
    rulebook_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Deprecate a rulebook (admin only).

    Changes status to DEPRECATED.
    Deprecated rulebooks are no longer available for new draft sessions
    but existing draft sessions can still reference them.
    """
    rulebook_repo = RulebookRepository(db)

    rulebook = rulebook_repo.get_by_id(rulebook_id)
    if not rulebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rulebook not found",
        )

    if rulebook.status == RulebookStatusEnum.DEPRECATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rulebook is already deprecated",
        )

    updated_rulebook = rulebook_repo.update_status(
        rulebook_id=rulebook_id,
        status=RulebookStatusEnum.DEPRECATED,
    )

    db.commit()

    return RulebookResponse(
        id=updated_rulebook.id,
        document_type=updated_rulebook.document_type,
        jurisdiction=updated_rulebook.jurisdiction,
        version=updated_rulebook.version,
        label=updated_rulebook.label,
        status=updated_rulebook.status,
        created_at=updated_rulebook.created_at,
        updated_at=updated_rulebook.updated_at,
    )
