"""
Authentication endpoints for user registration and login.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.dependencies import get_current_user
from app.middleware.database import get_db
from app.persistence.models import User
from app.persistence.repositories import UserRepository, PasswordResetTokenRepository
from app.schemas.auth import (
    Token,
    UserRegister,
    UserResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    VerifyResetTokenRequest,
    VerifyResetTokenResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user.

    Args:
        user_data: User registration data (email, password, full_name)
        db: Database session

    Returns:
        Created user object

    Raises:
        HTTPException: If email already exists (409 Conflict)
    """
    user_repo = UserRepository(db)

    # Check if user already exists
    existing_user = user_repo.get_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # Hash password and create user
    hashed_password = hash_password(user_data.password)
    user = user_repo.create(
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name
    )

    return user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login and get access token.

    Args:
        form_data: OAuth2 password form (username=email, password)
        db: Database session

    Returns:
        JWT access token

    Raises:
        HTTPException: If credentials are invalid (401 Unauthorized)
    """
    user_repo = UserRepository(db)

    # Get user by email (username field in OAuth2 form)
    user = user_repo.get_by_email(form_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token = create_access_token(data={"sub": user.email})

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user.

    Args:
        current_user: Current user from JWT token

    Returns:
        User object
    """
    return current_user


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Request a password reset email.

    Generates a secure token and sends a password reset link to the user's email.
    Always returns success to prevent email enumeration attacks.

    Args:
        request: Request containing the user's email
        db: Database session

    Returns:
        Success message (always, even if email doesn't exist)
    """
    import secrets
    from datetime import datetime, timedelta
    from app.core.config import settings

    user_repo = UserRepository(db)
    token_repo = PasswordResetTokenRepository(db)

    # Always return success to prevent email enumeration
    response_message = "If that email exists in our system, you will receive a password reset link shortly."

    # Find user by email
    user = user_repo.get_by_email(request.email)
    if not user:
        # Don't reveal that the email doesn't exist
        return {"message": response_message}

    # Generate secure token (32 bytes = 64 hex characters)
    token = secrets.token_urlsafe(32)

    # Token expires in 1 hour
    expires_at = datetime.utcnow() + timedelta(hours=1)

    # Delete any existing tokens for this user
    token_repo.delete_by_user(user.id)

    # Create new token
    token_repo.create(
        user_id=user.id,
        token=token,
        expires_at=expires_at
    )

    db.commit()

    # TODO: Send email with reset link
    # For now, log the reset URL (will integrate email in next step)
    # In production, this would be: send_password_reset_email(user.email, token)
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    print(f"\n{'='*80}")
    print(f"PASSWORD RESET REQUESTED FOR: {user.email}")
    print(f"Reset URL: {reset_url}")
    print(f"Token expires at: {expires_at}")
    print(f"{'='*80}\n")

    return {"message": response_message}


@router.post("/verify-reset-token", response_model=VerifyResetTokenResponse)
def verify_reset_token(
    request: VerifyResetTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Verify if a password reset token is valid.

    Args:
        request: Request containing the token to verify
        db: Database session

    Returns:
        Validation result with message
    """
    token_repo = PasswordResetTokenRepository(db)

    is_valid = token_repo.is_valid(request.token)

    if is_valid:
        return {
            "valid": True,
            "message": "Token is valid"
        }
    else:
        return {
            "valid": False,
            "message": "Token is invalid or has expired"
        }


@router.post("/reset-password", response_model=ResetPasswordResponse)
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Reset user password using a valid token.

    Args:
        request: Request containing token and new password
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If token is invalid or expired (400 Bad Request)
    """
    from datetime import datetime

    user_repo = UserRepository(db)
    token_repo = PasswordResetTokenRepository(db)

    # Verify token is valid
    reset_token = token_repo.get_by_token(request.token)
    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    if reset_token.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has already been used"
        )

    if datetime.utcnow() > reset_token.expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired"
        )

    # Get user
    user = user_repo.get_by_id(reset_token.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )

    # Hash new password and update user
    new_password_hash = hash_password(request.new_password)
    user_repo.update(
        user_id=user.id,
        password_hash=new_password_hash
    )

    # Mark token as used
    token_repo.mark_as_used(request.token)

    db.commit()

    return {"message": "Password has been successfully reset"}
