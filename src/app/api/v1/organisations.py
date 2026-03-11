"""
Organisation endpoints for CRUD operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.middleware.database import get_db
from app.persistence.models import User
from app.persistence.repositories import OrganisationRepository
from app.schemas.organisation import (
    OrganisationCreate,
    OrganisationUpdate,
    OrganisationResponse,
)

router = APIRouter()


@router.post("/", response_model=OrganisationResponse, status_code=status.HTTP_201_CREATED)
def create_organisation(
    org_data: OrganisationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new organisation.

    Requires authentication.

    Args:
        org_data: Organisation creation data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created organisation object
    """
    org_repo = OrganisationRepository(db)
    organisation = org_repo.create(
        name=org_data.name,
        contact_email=org_data.contact_email,
        is_active=org_data.is_active
    )
    return organisation


@router.get("/{organisation_id}", response_model=OrganisationResponse)
def get_organisation(
    organisation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get an organisation by ID.

    Requires authentication.

    Args:
        organisation_id: Organisation ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Organisation object

    Raises:
        HTTPException: If organisation not found (404)
    """
    org_repo = OrganisationRepository(db)
    organisation = org_repo.get_by_id(organisation_id)

    if not organisation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation not found"
        )

    return organisation


@router.get("/", response_model=list[OrganisationResponse])
def list_organisations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all active organisations.

    Requires authentication.

    Args:
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of active organisations
    """
    org_repo = OrganisationRepository(db)
    organisations = org_repo.list_active()
    return organisations


@router.patch("/{organisation_id}", response_model=OrganisationResponse)
def update_organisation(
    organisation_id: int,
    org_data: OrganisationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an organisation.

    Requires authentication. Only updates provided fields.

    Args:
        organisation_id: Organisation ID
        org_data: Organisation update data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated organisation object

    Raises:
        HTTPException: If organisation not found (404)
    """
    org_repo = OrganisationRepository(db)
    organisation = org_repo.get_by_id(organisation_id)

    if not organisation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation not found"
        )

    # Update only provided fields
    if org_data.name is not None:
        organisation.name = org_data.name
    if org_data.contact_email is not None:
        organisation.contact_email = org_data.contact_email
    if org_data.is_active is not None:
        organisation.is_active = org_data.is_active

    db.flush()
    return organisation


@router.delete("/{organisation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organisation(
    organisation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an organisation (soft delete by setting is_active=False).

    Requires authentication.

    Args:
        organisation_id: Organisation ID
        db: Database session
        current_user: Current authenticated user

    Raises:
        HTTPException: If organisation not found (404)
    """
    org_repo = OrganisationRepository(db)
    organisation = org_repo.get_by_id(organisation_id)

    if not organisation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation not found"
        )

    # Soft delete
    organisation.is_active = False
    db.flush()
