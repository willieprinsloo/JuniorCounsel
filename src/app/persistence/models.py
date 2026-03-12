from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def _uuid4() -> uuid.UUID:
    return uuid.uuid4()


class Organisation(Base):
    __tablename__ = "organisations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    users: Mapped[list["OrganisationUser"]] = relationship(back_populates="organisation")
    cases: Mapped[list["Case"]] = relationship(back_populates="organisation")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))  # Bcrypt hashed password
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organisations: Mapped[list["OrganisationUser"]] = relationship(back_populates="user")
    cases: Mapped[list["Case"]] = relationship(back_populates="owner")


class OrganisationRoleEnum(str, enum.Enum):
    ADMIN = "admin"
    PRACTITIONER = "practitioner"
    STAFF = "staff"


class OrganisationUser(Base):
    __tablename__ = "organisation_users"
    __table_args__ = (
        UniqueConstraint("organisation_id", "user_id", name="uq_organisation_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    organisation_id: Mapped[int] = mapped_column(ForeignKey("organisations.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[OrganisationRoleEnum] = mapped_column()

    organisation: Mapped[Organisation] = relationship(back_populates="users")
    user: Mapped[User] = relationship(back_populates="organisations")


class CaseStatusEnum(str, enum.Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    ARCHIVED = "archived"


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid4)
    organisation_id: Mapped[int] = mapped_column(ForeignKey("organisations.id", ondelete="RESTRICT"), index=True)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    case_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[CaseStatusEnum] = mapped_column(default=CaseStatusEnum.ACTIVE)
    jurisdiction: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    case_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organisation: Mapped[Organisation] = relationship(back_populates="cases")
    owner: Mapped[Optional[User]] = relationship(back_populates="cases")
    documents: Mapped[list["Document"]] = relationship(back_populates="case")


class DocumentTypeEnum(str, enum.Enum):
    PLEADING = "pleading"
    EVIDENCE = "evidence"
    CORRESPONDENCE = "correspondence"
    ORDER = "order"
    RESEARCH = "research"
    OTHER = "other"


class DocumentStatusEnum(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentStageEnum(str, enum.Enum):
    UPLOADING = "uploading"
    OCR = "ocr"
    TEXT_EXTRACTION = "text_extraction"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("case_id", "filename", name="uq_case_document"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    upload_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("upload_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    uploaded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))

    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # bytes
    mime_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    pages: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    document_type: Mapped[DocumentTypeEnum] = mapped_column(default=DocumentTypeEnum.OTHER, index=True)
    document_subtype: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    tags: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Processing state
    overall_status: Mapped[DocumentStatusEnum] = mapped_column(default=DocumentStatusEnum.QUEUED, index=True)
    stage: Mapped[Optional[DocumentStageEnum]] = mapped_column(nullable=True)
    stage_progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100

    # OCR metadata
    needs_ocr: Mapped[bool] = mapped_column(Boolean, default=False)
    ocr_confidence: Mapped[Optional[float]] = mapped_column(nullable=True)
    text_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    case: Mapped[Case] = relationship(back_populates="documents")
    uploaded_by: Mapped[User] = relationship()
    upload_session: Mapped[Optional["UploadSession"]] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document")


class UploadSession(Base):
    __tablename__ = "upload_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    uploaded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))

    total_documents: Mapped[int] = mapped_column(Integer, default=0)
    completed_documents: Mapped[int] = mapped_column(Integer, default=0)
    failed_documents: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    uploaded_by: Mapped[User] = relationship()
    documents: Mapped[list[Document]] = relationship(back_populates="upload_session")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)

    text_content: Mapped[str] = mapped_column(Text)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    paragraph_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    paragraph_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # pgvector embedding (will need pgvector extension enabled)
    # embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(1536), nullable=True)  # OpenAI ada-002 dimension

    # Metadata for search filtering
    chunk_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # heading, body, table, footnote
    semantic_role: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # facts, orders_sought, argument, etc.
    chunk_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    document: Mapped[Document] = relationship(back_populates="chunks")


class DraftSessionStatusEnum(str, enum.Enum):
    INITIALIZING = "initializing"
    AWAITING_INTAKE = "awaiting_intake"
    RESEARCH = "research"  # Performing RAG research
    DRAFTING = "drafting"  # LLM draft generation in progress
    REVIEW = "review"  # Draft ready for user review
    READY = "ready"  # Finalized and ready for export
    FAILED = "failed"


class DraftSession(Base):
    __tablename__ = "draft_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    rulebook_id: Mapped[int] = mapped_column(ForeignKey("rulebooks.id", ondelete="RESTRICT"))

    title: Mapped[str] = mapped_column(String(255))
    document_type: Mapped[str] = mapped_column(String(128))

    status: Mapped[DraftSessionStatusEnum] = mapped_column(default=DraftSessionStatusEnum.INITIALIZING)

    # Research phase outputs
    case_profile: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    research_summary: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Changed from Text to JSONB
    outline: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Intake responses (renamed from intake_answers for consistency with worker code)
    intake_responses: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Generated DraftDoc
    draft_doc: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped[User] = relationship()
    rulebook: Mapped["Rulebook"] = relationship()


class RulebookStatusEnum(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


class Rulebook(Base):
    __tablename__ = "rulebooks"
    __table_args__ = (
        UniqueConstraint("document_type", "jurisdiction", "version", name="uq_rulebook_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_type: Mapped[str] = mapped_column(String(128), index=True)
    jurisdiction: Mapped[str] = mapped_column(String(128), index=True)
    version: Mapped[str] = mapped_column(String(32))
    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    status: Mapped[RulebookStatusEnum] = mapped_column(default=RulebookStatusEnum.DRAFT)

    source_yaml: Mapped[str] = mapped_column(Text)
    rules_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by: Mapped[User] = relationship()


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid4)
    draft_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("draft_sessions.id", ondelete="CASCADE"), index=True
    )
    document_chunk_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="CASCADE"), index=True
    )

    # Citation metadata
    marker: Mapped[str] = mapped_column(String(16))  # e.g., "[1]", "[2]"
    citation_text: Mapped[str] = mapped_column(Text)  # Excerpt from source document
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    paragraph_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    similarity_score: Mapped[Optional[float]] = mapped_column(nullable=True)  # RAG similarity (0-1)

    # Position in generated document (for inline citations)
    position_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Character offset
    position_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    draft_session: Mapped[DraftSession] = relationship()
    document_chunk: Mapped[DocumentChunk] = relationship()


