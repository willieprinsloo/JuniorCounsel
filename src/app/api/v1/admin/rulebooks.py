"""
Admin endpoints for rulebook management.

All endpoints require ADMIN role.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.dependencies import require_admin, get_current_user
from app.middleware.database import get_db
from app.persistence.models import User, RulebookStatusEnum
from app.persistence.repositories import RulebookRepository
from app.schemas.admin import RulebookUpload, RulebookUpdate
from app.schemas.rulebook import RulebookResponse, RulebookListResponse
from app.services.rulebook import RulebookService, RulebookValidationError

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
    rulebook_service = RulebookService(db)

    # Validate YAML syntax and structure before storing
    try:
        rules_json = rulebook_service.parse_yaml(rulebook_data.source_yaml)
    except RulebookValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid rulebook YAML",
                "details": str(e)
            }
        )

    # Compute content hash for change detection
    content_hash = rulebook_service.compute_content_hash(rulebook_data.source_yaml)

    rulebook = rulebook_repo.create(
        document_type=rulebook_data.document_type,
        jurisdiction=rulebook_data.jurisdiction,
        version=rulebook_data.version,
        source_yaml=rulebook_data.source_yaml,
        rules_json=rules_json,  # Store validated JSON immediately
        content_hash=content_hash,
        created_by_id=current_user.id,
        label=rulebook_data.label,
    )

    db.commit()

    return RulebookResponse(
        id=rulebook.id,
        document_type=rulebook.document_type,
        jurisdiction=rulebook.jurisdiction,
        version=rulebook.version,
        source_yaml=rulebook.source_yaml,
        rules_json=rulebook.rules_json,
        label=rulebook.label,
        status=rulebook.status,
        created_by_id=rulebook.created_by_id,
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
    rulebook_service = RulebookService(db)

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
        # Validate YAML syntax and structure before storing
        try:
            rules_json = rulebook_service.parse_yaml(rulebook_data.source_yaml)
        except RulebookValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Invalid rulebook YAML",
                    "details": str(e)
                }
            )

        # Update both YAML and JSON
        rulebook.source_yaml = rulebook_data.source_yaml
        rulebook.rules_json = rules_json
        rulebook.content_hash = rulebook_service.compute_content_hash(rulebook_data.source_yaml)

    from datetime import datetime
    rulebook.updated_at = datetime.utcnow()

    db.commit()

    return RulebookResponse(
        id=rulebook.id,
        document_type=rulebook.document_type,
        jurisdiction=rulebook.jurisdiction,
        version=rulebook.version,
        source_yaml=rulebook.source_yaml,
        rules_json=rulebook.rules_json,
        label=rulebook.label,
        status=rulebook.status,
        created_by_id=rulebook.created_by_id,
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
    rulebook_service = RulebookService(db)

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

    # Validate rulebook structure before publishing
    try:
        rulebook_service.validate_rules(rulebook.rules_json)
    except RulebookValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Cannot publish invalid rulebook",
                "details": str(e)
            }
        )

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
        source_yaml=updated_rulebook.source_yaml,
        rules_json=updated_rulebook.rules_json,
        label=updated_rulebook.label,
        status=updated_rulebook.status,
        created_by_id=updated_rulebook.created_by_id,
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
        source_yaml=updated_rulebook.source_yaml,
        rules_json=updated_rulebook.rules_json,
        label=updated_rulebook.label,
        status=updated_rulebook.status,
        created_by_id=updated_rulebook.created_by_id,
        created_at=updated_rulebook.created_at,
        updated_at=updated_rulebook.updated_at,
    )


@router.get("/", response_model=RulebookListResponse)
def list_rulebooks(
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction"),
    status: Optional[RulebookStatusEnum] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    sort: str = Query("created_at", description="Field to sort by"),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    List all rulebooks with pagination and filtering (admin only).

    Admins can see all rulebooks regardless of status.
    """
    rulebook_repo = RulebookRepository(db)
    rulebooks, total = rulebook_repo.list(
        document_type=document_type,
        jurisdiction=jurisdiction,
        status=status,
        page=page,
        per_page=per_page,
        sort=sort,
        order=order,
    )

    # Calculate next page
    next_page = page + 1 if (page * per_page) < total else None

    return RulebookListResponse(
        data=rulebooks,
        page=page,
        per_page=per_page,
        total=total,
        next_page=next_page,
    )


@router.get("/{rulebook_id}", response_model=RulebookResponse)
def get_rulebook(
    rulebook_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get a rulebook by ID (admin only).

    Returns full rulebook details including source_yaml for editing.
    """
    rulebook_repo = RulebookRepository(db)

    rulebook = rulebook_repo.get_by_id(rulebook_id)
    if not rulebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rulebook not found",
        )

    return RulebookResponse(
        id=rulebook.id,
        document_type=rulebook.document_type,
        jurisdiction=rulebook.jurisdiction,
        version=rulebook.version,
        source_yaml=rulebook.source_yaml,
        rules_json=rulebook.rules_json,
        label=rulebook.label,
        status=rulebook.status,
        created_by_id=rulebook.created_by_id,
        created_at=rulebook.created_at,
        updated_at=rulebook.updated_at,
    )


@router.post("/{rulebook_id}/duplicate", response_model=RulebookResponse, status_code=status.HTTP_201_CREATED)
def duplicate_rulebook(
    rulebook_id: int,
    new_version: str = Query(..., description="Version number for the duplicated rulebook"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Duplicate a rulebook as a new version (admin only).

    Creates a copy of an existing rulebook with a new version number.
    The duplicated rulebook starts in DRAFT status.
    Useful for creating new versions or cloning rulebooks for different jurisdictions.
    """
    rulebook_repo = RulebookRepository(db)

    # Get source rulebook
    source_rulebook = rulebook_repo.get_by_id(rulebook_id)
    if not source_rulebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source rulebook not found",
        )

    # Create duplicate with new version
    duplicate = rulebook_repo.create(
        document_type=source_rulebook.document_type,
        jurisdiction=source_rulebook.jurisdiction,
        version=new_version,
        source_yaml=source_rulebook.source_yaml,
        created_by_id=current_user.id,
        label=f"{source_rulebook.label} (v{new_version})" if source_rulebook.label else None,
    )

    db.commit()

    return RulebookResponse(
        id=duplicate.id,
        document_type=duplicate.document_type,
        jurisdiction=duplicate.jurisdiction,
        version=duplicate.version,
        source_yaml=duplicate.source_yaml,
        rules_json=duplicate.rules_json,
        label=duplicate.label,
        status=duplicate.status,
        created_by_id=duplicate.created_by_id,
        created_at=duplicate.created_at,
        updated_at=duplicate.updated_at,
    )
