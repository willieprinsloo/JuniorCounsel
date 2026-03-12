"""
FastAPI dependencies for authentication and authorization.
"""
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.middleware.database import get_db
from app.persistence.models import User, OrganisationUser, OrganisationRoleEnum
from app.persistence.repositories import UserRepository
from app.schemas.auth import TokenData

# OAuth2 scheme for JWT tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the currently authenticated user from JWT token.

    Args:
        token: JWT access token from Authorization header
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode token
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    email: Optional[str] = payload.get("sub")
    if email is None:
        raise credentials_exception

    # Fetch user from database
    user_repo = UserRepository(db)
    user = user_repo.get_by_email(email)
    if user is None:
        raise credentials_exception

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to get the currently authenticated and active user.

    Args:
        current_user: User from get_current_user dependency

    Returns:
        User object if active

    Raises:
        HTTPException: If user is inactive
    """
    # Note: User model doesn't have is_active field yet
    # This is a placeholder for future implementation
    # if not current_user.is_active:
    #     raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_user_role_in_org(
    db: Session,
    user_id: int,
    organisation_id: int
) -> Optional[OrganisationRoleEnum]:
    """
    Helper function to get a user's role in a specific organisation.

    Args:
        db: Database session
        user_id: User ID
        organisation_id: Organisation ID

    Returns:
        OrganisationRoleEnum if user is a member, None otherwise
    """
    stmt = select(OrganisationUser).where(
        OrganisationUser.user_id == user_id,
        OrganisationUser.organisation_id == organisation_id
    )
    org_user = db.execute(stmt).scalar_one_or_none()
    return org_user.role if org_user else None


def has_role_in_any_org(
    db: Session,
    user_id: int,
    required_role: OrganisationRoleEnum
) -> bool:
    """
    Check if a user has a specific role in any organisation.

    Args:
        db: Database session
        user_id: User ID
        required_role: Required role

    Returns:
        True if user has the role in at least one organisation
    """
    stmt = select(OrganisationUser).where(
        OrganisationUser.user_id == user_id,
        OrganisationUser.role == required_role
    )
    org_user = db.execute(stmt).first()
    return org_user is not None


def require_admin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to require the current user to be an ADMIN in at least one organisation.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        User object if user is an admin

    Raises:
        HTTPException: 403 Forbidden if user is not an admin
    """
    if not has_role_in_any_org(db, current_user.id, OrganisationRoleEnum.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def require_admin_for_org(organisation_id: int):
    """
    Dependency factory to require admin access for a specific organisation.

    Usage:
        @router.post("/organisations/{org_id}/...")
        def endpoint(
            org_id: int,
            current_user: User = Depends(require_admin_for_org(org_id))
        ):
            ...

    Args:
        organisation_id: Organisation ID to check admin access for

    Returns:
        Dependency function
    """
    def _require_admin_for_org(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        """Check if user is admin for the specified organisation."""
        role = get_user_role_in_org(db, current_user.id, organisation_id)

        if role != OrganisationRoleEnum.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Admin access required for organisation {organisation_id}"
            )

        return current_user

    return _require_admin_for_org
