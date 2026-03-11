"""
Pydantic schemas for organisation endpoints.
"""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, EmailStr


class OrganisationCreate(BaseModel):
    """Schema for creating a new organisation."""

    name: str
    contact_email: Optional[EmailStr] = None
    is_active: bool = True

    model_config = {"str_strip_whitespace": True}


class OrganisationUpdate(BaseModel):
    """Schema for updating an organisation."""

    name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    is_active: Optional[bool] = None

    model_config = {"str_strip_whitespace": True}


class OrganisationResponse(BaseModel):
    """Schema for organisation data in responses."""

    id: int
    name: str
    contact_email: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrganisationListResponse(BaseModel):
    """Schema for paginated organisation list response."""

    data: list[OrganisationResponse]
    page: int
    per_page: int
    total: int
