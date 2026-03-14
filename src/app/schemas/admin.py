"""
Pydantic schemas for admin endpoints.

Admin-specific schemas for managing users, organisations, and system configuration.
"""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.persistence.models import OrganisationRoleEnum


# User Management Schemas

class AdminUserCreate(BaseModel):
    """Schema for creating a new user (admin endpoint)."""

    email: EmailStr
    password: str
    full_name: str

    model_config = {"str_strip_whitespace": True}


class AdminUserUpdate(BaseModel):
    """Schema for updating a user (admin endpoint)."""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None  # If provided, will be hashed

    model_config = {"str_strip_whitespace": True}


class OrganisationMembershipResponse(BaseModel):
    """Schema for user's organisation membership with role."""

    organisation_id: int
    organisation_name: str
    role: OrganisationRoleEnum
    joined_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AdminUserResponse(BaseModel):
    """Extended user response for admin endpoints."""

    id: int
    email: str
    full_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    organisations: list[OrganisationMembershipResponse] = []

    model_config = {"from_attributes": True}


class AdminUserListResponse(BaseModel):
    """Schema for paginated user list response."""

    data: list[AdminUserResponse]
    page: int
    per_page: int
    total: int
    next_page: Optional[int] = None


# Organisation Member Management Schemas

class OrganisationMemberAdd(BaseModel):
    """Schema for adding a member to an organisation."""

    user_id: int
    role: OrganisationRoleEnum


class OrganisationMemberUpdate(BaseModel):
    """Schema for updating a member's role."""

    role: OrganisationRoleEnum


class OrganisationMemberResponse(BaseModel):
    """Schema for organisation member with user details."""

    id: int  # OrganisationUser.id
    user_id: int
    email: str
    full_name: Optional[str] = None
    role: OrganisationRoleEnum
    joined_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class OrganisationMembersListResponse(BaseModel):
    """Schema for paginated organisation members list."""

    data: list[OrganisationMemberResponse]
    page: int
    per_page: int
    total: int
    next_page: Optional[int] = None


# Rulebook Management Schemas (extensions)

class RulebookUpload(BaseModel):
    """Schema for uploading a new rulebook."""

    document_type: str
    jurisdiction: str
    version: str
    label: Optional[str] = None
    source_yaml: str  # The YAML content

    model_config = {"str_strip_whitespace": True}


class RulebookUpdate(BaseModel):
    """Schema for updating a rulebook."""

    label: Optional[str] = None
    source_yaml: Optional[str] = None

    model_config = {"str_strip_whitespace": True}
