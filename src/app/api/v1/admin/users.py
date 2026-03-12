"""
Admin endpoints for user management.

All endpoints require ADMIN role.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.dependencies import require_admin, get_current_user
from app.middleware.database import get_db
from app.persistence.models import User, OrganisationRoleEnum
from app.persistence.repositories import (
    UserRepository,
    OrganisationRepository,
    OrganisationUserRepository,
)
from app.schemas.admin import (
    AdminUserCreate,
    AdminUserUpdate,
    AdminUserResponse,
    AdminUserListResponse,
    OrganisationMembershipResponse,
)

router = APIRouter()


@router.get("/", response_model=AdminUserListResponse)
def list_users(
    q: str = Query(None, description="Search query (email or full name)"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    sort: str = Query("created_at", description="Field to sort by"),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    List all users with pagination and search (admin only).

    - **q**: Search users by email or full name
    - **page**: Page number (1-indexed)
    - **per_page**: Number of users per page (max 100)
    - **sort**: Field to sort by (default: created_at)
    - **order**: Sort order (asc/desc, default: desc)
    """
    user_repo = UserRepository(db)

    users, total = user_repo.list(
        q=q,
        page=page,
        per_page=per_page,
        sort=sort,
        order=order,
    )

    # For each user, load their organisation memberships
    org_user_repo = OrganisationUserRepository(db)
    user_responses = []

    for user in users:
        # Get user's organisation memberships
        stmt = db.query(
            org_user_repo.session.query(
                org_user_repo.session.get_bind().execute(
                    f"""
                    SELECT ou.organisation_id, o.name, ou.role, ou.created_at
                    FROM organisation_users ou
                    JOIN organisations o ON ou.organisation_id = o.id
                    WHERE ou.user_id = {user.id}
                    ORDER BY ou.created_at DESC
                    """
                )
            )
        )

        # Simple approach: use existing relationships
        memberships = []
        user_with_orgs = user_repo.get_with_organisations(user.id)
        if user_with_orgs and user_with_orgs.organisations:
            for org_user in user_with_orgs.organisations:
                memberships.append(
                    OrganisationMembershipResponse(
                        organisation_id=org_user.organisation.id,
                        organisation_name=org_user.organisation.name,
                        role=org_user.role,
                        joined_at=org_user.created_at,
                    )
                )

        user_responses.append(
            AdminUserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                created_at=user.created_at,
                updated_at=user.updated_at,
                organisations=memberships,
            )
        )

    # Calculate next page
    next_page = page + 1 if page * per_page < total else None

    return AdminUserListResponse(
        data=user_responses,
        page=page,
        per_page=per_page,
        total=total,
        next_page=next_page,
    )


@router.get("/{user_id}", response_model=AdminUserResponse)
def get_user(
    user_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get a specific user by ID with their organisation memberships (admin only).
    """
    user_repo = UserRepository(db)
    user = user_repo.get_with_organisations(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Load organisation memberships
    memberships = []
    if user.organisations:
        for org_user in user.organisations:
            memberships.append(
                OrganisationMembershipResponse(
                    organisation_id=org_user.organisation.id,
                    organisation_name=org_user.organisation.name,
                    role=org_user.role,
                    joined_at=org_user.created_at,
                )
            )

    return AdminUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        created_at=user.created_at,
        updated_at=user.updated_at,
        organisations=memberships,
    )


@router.post("/", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: AdminUserCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Create a new user (admin only).

    Creates a user account with the specified email, password, and full name.
    Password will be hashed before storage.
    """
    user_repo = UserRepository(db)

    # Check if email already exists
    existing_user = user_repo.get_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Hash password
    password_hash = hash_password(user_data.password)

    # Create user
    user = user_repo.create(
        email=user_data.email,
        password_hash=password_hash,
        full_name=user_data.full_name,
    )

    db.commit()

    return AdminUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        created_at=user.created_at,
        updated_at=user.updated_at,
        organisations=[],
    )


@router.patch("/{user_id}", response_model=AdminUserResponse)
def update_user(
    user_id: int,
    user_data: AdminUserUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Update a user's information (admin only).

    Can update email, full name, and password (will be hashed).
    Only provided fields will be updated.
    """
    user_repo = UserRepository(db)

    # Check user exists
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Check email uniqueness if being updated
    if user_data.email and user_data.email != user.email:
        existing_user = user_repo.get_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already in use",
            )

    # Hash password if provided
    password_hash = None
    if user_data.password:
        password_hash = hash_password(user_data.password)

    # Update user
    updated_user = user_repo.update(
        user_id=user_id,
        email=user_data.email,
        password_hash=password_hash,
        full_name=user_data.full_name,
    )

    db.commit()

    # Load memberships for response
    user_with_orgs = user_repo.get_with_organisations(user_id)
    memberships = []
    if user_with_orgs and user_with_orgs.organisations:
        for org_user in user_with_orgs.organisations:
            memberships.append(
                OrganisationMembershipResponse(
                    organisation_id=org_user.organisation.id,
                    organisation_name=org_user.organisation.name,
                    role=org_user.role,
                    joined_at=org_user.created_at,
                )
            )

    return AdminUserResponse(
        id=updated_user.id,
        email=updated_user.email,
        full_name=updated_user.full_name,
        created_at=updated_user.created_at,
        updated_at=updated_user.updated_at,
        organisations=memberships,
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Delete a user (admin only).

    WARNING: This will cascade delete all related data:
    - Organisation memberships
    - Cases owned by the user
    - Documents uploaded by the user
    - Draft sessions created by the user

    Users cannot delete themselves.
    """
    user_repo = UserRepository(db)

    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own user account",
        )

    # Check user exists
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Delete user
    user_repo.delete(user_id)
    db.commit()

    return None
