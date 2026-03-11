"""
Persistence layer for Junior Counsel.

This module contains SQLAlchemy models and repository classes for data access.
"""
from .models import (
    Base,
    Organisation,
    User,
    OrganisationUser,
    OrganisationRoleEnum,
    Case,
    CaseStatusEnum,
    Document,
    DocumentTypeEnum,
    DocumentStatusEnum,
    DocumentStageEnum,
    UploadSession,
    DocumentChunk,
    DraftSession,
    DraftSessionStatusEnum,
    Rulebook,
    RulebookStatusEnum,
)
from .repositories import (
    OrganisationRepository,
    CaseRepository,
    DocumentRepository,
    UploadSessionRepository,
    DraftSessionRepository,
    RulebookRepository,
)

__all__ = [
    # Base
    "Base",
    # Models
    "Organisation",
    "User",
    "OrganisationUser",
    "OrganisationRoleEnum",
    "Case",
    "CaseStatusEnum",
    "Document",
    "DocumentTypeEnum",
    "DocumentStatusEnum",
    "DocumentStageEnum",
    "UploadSession",
    "DocumentChunk",
    "DraftSession",
    "DraftSessionStatusEnum",
    "Rulebook",
    "RulebookStatusEnum",
    # Repositories
    "OrganisationRepository",
    "CaseRepository",
    "DocumentRepository",
    "UploadSessionRepository",
    "DraftSessionRepository",
    "RulebookRepository",
]
