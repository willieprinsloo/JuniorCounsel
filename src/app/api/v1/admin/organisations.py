"""
Admin endpoints for organisation management.

All endpoints require ADMIN role.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.dependencies import require_admin
from app.middleware.database import get_db
from app.persistence.models import User, OrganisationRoleEnum
from app.persistence.repositories import (
    OrganisationRepository,
    OrganisationUserRepository,
    UserRepository,
)
from app.schemas.admin import (
    OrganisationMemberAdd,
    OrganisationMemberUpdate,
    OrganisationMemberResponse,
    OrganisationMembersListResponse,
)
from app.schemas.organisation import (
    OrganisationCreate,
    OrganisationUpdate,
    OrganisationResponse,
    OrganisationListResponse,
)

router = APIRouter()


@router.get("/", response_model=OrganisationListResponse)
def list_organisations(
    is_active: bool = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    sort: str = Query("name", description="Field to sort by"),
    order: str = Query("asc", regex="^(asc|desc)$", description="Sort order"),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    List all organisations with pagination (admin only).

    - **is_active**: Filter by active status (true/false)
    - **page**: Page number (1-indexed)
    - **per_page**: Number of organisations per page (max 100)
    - **sort**: Field to sort by (default: name)
    - **order**: Sort order (asc/desc, default: asc)
    """
    org_repo = OrganisationRepository(db)

    organisations, total = org_repo.list(
        is_active=is_active,
        page=page,
        per_page=per_page,
        sort=sort,
        order=order,
    )

    # Calculate next page
    next_page = page + 1 if page * per_page < total else None

    org_responses = [
        OrganisationResponse(
            id=org.id,
            name=org.name,
            contact_email=org.contact_email,
            is_active=org.is_active,
            created_at=org.created_at,
            updated_at=org.updated_at,
        )
        for org in organisations
    ]

    return OrganisationListResponse(
        data=org_responses,
        page=page,
        per_page=per_page,
        total=total,
    )


@router.get("/{organisation_id}", response_model=OrganisationResponse)
def get_organisation(
    organisation_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get a specific organisation by ID (admin only).
    """
    org_repo = OrganisationRepository(db)
    organisation = org_repo.get_by_id(organisation_id)

    if not organisation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation not found",
        )

    return OrganisationResponse(
        id=organisation.id,
        name=organisation.name,
        contact_email=organisation.contact_email,
        is_active=organisation.is_active,
        created_at=organisation.created_at,
        updated_at=organisation.updated_at,
    )


@router.post("/", response_model=OrganisationResponse, status_code=status.HTTP_201_CREATED)
def create_organisation(
    org_data: OrganisationCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Create a new organisation (admin only).
    """
    org_repo = OrganisationRepository(db)

    organisation = org_repo.create(
        name=org_data.name,
        contact_email=org_data.contact_email,
        is_active=org_data.is_active,
    )

    db.commit()

    return OrganisationResponse(
        id=organisation.id,
        name=organisation.name,
        contact_email=organisation.contact_email,
        is_active=organisation.is_active,
        created_at=organisation.created_at,
        updated_at=organisation.updated_at,
    )


@router.patch("/{organisation_id}", response_model=OrganisationResponse)
def update_organisation(
    organisation_id: int,
    org_data: OrganisationUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Update an organisation (admin only).

    Can update name, contact email, and active status.
    Only provided fields will be updated.
    """
    org_repo = OrganisationRepository(db)

    # Check organisation exists
    organisation = org_repo.get_by_id(organisation_id)
    if not organisation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation not found",
        )

    # Update organisation
    updated_org = org_repo.update(
        organisation_id=organisation_id,
        name=org_data.name,
        contact_email=org_data.contact_email,
        is_active=org_data.is_active,
    )

    db.commit()

    return OrganisationResponse(
        id=updated_org.id,
        name=updated_org.name,
        contact_email=updated_org.contact_email,
        is_active=updated_org.is_active,
        created_at=updated_org.created_at,
        updated_at=updated_org.updated_at,
    )


# Organisation Member Management Endpoints


@router.get("/{organisation_id}/members", response_model=OrganisationMembersListResponse)
def list_organisation_members(
    organisation_id: int,
    role: OrganisationRoleEnum = Query(None, description="Filter by role"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    List members of an organisation with pagination (admin only).

    - **role**: Filter by role (admin/practitioner/staff)
    - **page**: Page number (1-indexed)
    - **per_page**: Number of members per page (max 100)
    """
    # Verify organisation exists
    org_repo = OrganisationRepository(db)
    organisation = org_repo.get_by_id(organisation_id)
    if not organisation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation not found",
        )

    # Get members
    org_user_repo = OrganisationUserRepository(db)
    memberships, total = org_user_repo.list_by_organisation(
        organisation_id=organisation_id,
        role=role,
        page=page,
        per_page=per_page,
    )

    # Build response
    member_responses = []
    for membership in memberships:
        member_responses.append(
            OrganisationMemberResponse(
                id=membership.id,
                user_id=membership.user.id,
                email=membership.user.email,
                full_name=membership.user.full_name,
                role=membership.role,
                joined_at=None,  # OrganisationUser doesn't have timestamps
            )
        )

    # Calculate next page
    next_page = page + 1 if page * per_page < total else None

    return OrganisationMembersListResponse(
        data=member_responses,
        page=page,
        per_page=per_page,
        total=total,
        next_page=next_page,
    )


@router.post("/{organisation_id}/members", response_model=OrganisationMemberResponse, status_code=status.HTTP_201_CREATED)
def add_organisation_member(
    organisation_id: int,
    member_data: OrganisationMemberAdd,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Add a member to an organisation with a specific role (admin only).
    """
    org_repo = OrganisationRepository(db)
    user_repo = UserRepository(db)
    org_user_repo = OrganisationUserRepository(db)

    # Verify organisation exists
    organisation = org_repo.get_by_id(organisation_id)
    if not organisation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation not found",
        )

    # Verify user exists
    user = user_repo.get_by_id(member_data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Check if already a member
    existing_membership = org_user_repo.get_by_org_and_user(
        organisation_id, member_data.user_id
    )
    if existing_membership:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this organisation",
        )

    # Add member
    membership = org_repo.add_user(
        organisation_id=organisation_id,
        user_id=member_data.user_id,
        role=member_data.role,
    )

    db.commit()

    return OrganisationMemberResponse(
        id=membership.id,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=membership.role,
        joined_at=None,  # OrganisationUser doesn't have timestamps
    )


@router.patch("/{organisation_id}/members/{user_id}", response_model=OrganisationMemberResponse)
def update_member_role(
    organisation_id: int,
    user_id: int,
    member_data: OrganisationMemberUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Update a member's role in an organisation (admin only).
    """
    org_user_repo = OrganisationUserRepository(db)
    user_repo = UserRepository(db)

    # Check membership exists
    membership = org_user_repo.get_by_org_and_user(organisation_id, user_id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found",
        )

    # Update role
    updated_membership = org_user_repo.update_role(
        organisation_id=organisation_id,
        user_id=user_id,
        role=member_data.role,
    )

    db.commit()

    # Get user details
    user = user_repo.get_by_id(user_id)

    return OrganisationMemberResponse(
        id=updated_membership.id,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=updated_membership.role,
        joined_at=None,  # OrganisationUser doesn't have timestamps
    )


@router.delete("/{organisation_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_organisation_member(
    organisation_id: int,
    user_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Remove a member from an organisation (admin only).
    """
    org_repo = OrganisationRepository(db)

    # Check membership exists
    org_user_repo = OrganisationUserRepository(db)
    membership = org_user_repo.get_by_org_and_user(organisation_id, user_id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found",
        )

    # Remove member
    org_repo.remove_user(organisation_id, user_id)
    db.commit()

    return None
