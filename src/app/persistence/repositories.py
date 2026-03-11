"""
Repository classes for data access.

All repositories implement pagination on list methods and enforce organisation scoping.
"""
from typing import Optional, Tuple
from sqlalchemy import select, func, or_, desc, asc
from sqlalchemy.orm import Session

from .models import (
    Organisation,
    User,
    OrganisationUser,
    OrganisationRoleEnum,
    Case,
    CaseStatusEnum,
    Document,
    DocumentStatusEnum,
    UploadSession,
    DraftSession,
    DraftSessionStatusEnum,
    Rulebook,
    RulebookStatusEnum,
)


class OrganisationRepository:
    """Repository for Organisation entities."""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        name: str,
        contact_email: Optional[str] = None,
        is_active: bool = True,
    ) -> Organisation:
        """Create a new organisation."""
        org = Organisation(
            name=name,
            contact_email=contact_email,
            is_active=is_active,
        )
        self.session.add(org)
        self.session.flush()
        return org

    def get_by_id(self, organisation_id: int) -> Optional[Organisation]:
        """Get organisation by ID."""
        return self.session.get(Organisation, organisation_id)

    def list_active(self) -> list[Organisation]:
        """List all active organisations."""
        stmt = select(Organisation).where(Organisation.is_active == True).order_by(Organisation.name)
        return list(self.session.execute(stmt).scalars().all())

    def add_user(
        self,
        organisation_id: int,
        user_id: int,
        role: OrganisationRoleEnum,
    ) -> OrganisationUser:
        """Add a user to an organisation with a role."""
        org_user = OrganisationUser(
            organisation_id=organisation_id,
            user_id=user_id,
            role=role,
        )
        self.session.add(org_user)
        self.session.flush()
        return org_user

    def remove_user(self, organisation_id: int, user_id: int) -> bool:
        """Remove a user from an organisation."""
        stmt = select(OrganisationUser).where(
            OrganisationUser.organisation_id == organisation_id,
            OrganisationUser.user_id == user_id,
        )
        org_user = self.session.execute(stmt).scalar_one_or_none()

        if org_user:
            self.session.delete(org_user)
            self.session.flush()
            return True
        return False


class CaseRepository:
    """Repository for Case entities with pagination."""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        organisation_id: int,
        title: str,
        owner_id: Optional[int] = None,
        description: Optional[str] = None,
        case_type: Optional[str] = None,
        jurisdiction: Optional[str] = None,
    ) -> Case:
        """Create a new case."""
        case = Case(
            organisation_id=organisation_id,
            owner_id=owner_id,
            title=title,
            description=description,
            case_type=case_type,
            jurisdiction=jurisdiction,
        )
        self.session.add(case)
        self.session.flush()
        return case

    def get_by_id(self, case_id: str) -> Optional[Case]:
        """Get case by ID."""
        return self.session.get(Case, case_id)

    def list(
        self,
        organisation_id: int,
        status: Optional[CaseStatusEnum] = None,
        case_type: Optional[str] = None,
        q: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        sort: str = "created_at",
        order: str = "desc",
    ) -> Tuple[list[Case], int]:
        """
        List cases with pagination and filtering.

        Args:
            organisation_id: Filter by organisation
            status: Filter by status
            case_type: Filter by case type
            q: Search query (case-insensitive, searches title and description)
            page: Page number (1-indexed)
            per_page: Items per page (max 100)
            sort: Field to sort by
            order: Sort order ('asc' or 'desc')

        Returns:
            Tuple of (cases, total_count)
        """
        # Cap per_page at 100
        per_page = min(per_page, 100)

        # Base query with organisation scoping
        stmt = select(Case).where(Case.organisation_id == organisation_id)

        # Apply filters
        if status:
            stmt = stmt.where(Case.status == status)

        if case_type:
            stmt = stmt.where(Case.case_type == case_type)

        if q:
            search_pattern = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    Case.title.ilike(search_pattern),
                    Case.description.ilike(search_pattern),
                )
            )

        # Count total before pagination
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.session.scalar(count_stmt) or 0

        # Apply sorting
        sort_column = getattr(Case, sort, Case.created_at)
        direction = desc if order.lower() == "desc" else asc
        stmt = stmt.order_by(direction(sort_column))

        # Apply pagination
        offset = (page - 1) * per_page
        stmt = stmt.limit(per_page).offset(offset)

        # Execute query
        cases = list(self.session.execute(stmt).scalars().all())

        return cases, total

    def update_status(self, case_id: str, status: CaseStatusEnum) -> Optional[Case]:
        """Update case status."""
        case = self.get_by_id(case_id)
        if case:
            case.status = status
            self.session.flush()
        return case

    def delete(self, case_id: str) -> bool:
        """Delete a case."""
        case = self.get_by_id(case_id)
        if case:
            self.session.delete(case)
            self.session.flush()
            return True
        return False


class DocumentRepository:
    """Repository for Document entities with pagination."""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        case_id: str,
        uploaded_by_id: int,
        filename: str,
        upload_session_id: Optional[str] = None,
        needs_ocr: bool = False,
    ) -> Document:
        """Create a new document."""
        doc = Document(
            case_id=case_id,
            uploaded_by_id=uploaded_by_id,
            filename=filename,
            upload_session_id=upload_session_id,
            needs_ocr=needs_ocr,
        )
        self.session.add(doc)
        self.session.flush()
        return doc

    def get_by_id(self, document_id: str) -> Optional[Document]:
        """Get document by ID."""
        return self.session.get(Document, document_id)

    def list(
        self,
        case_id: str,
        document_type: Optional[str] = None,
        status: Optional[DocumentStatusEnum] = None,
        q: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        sort: str = "created_at",
        order: str = "desc",
    ) -> Tuple[list[Document], int]:
        """
        List documents with pagination and filtering.

        Args:
            case_id: Filter by case
            document_type: Filter by document type
            status: Filter by overall_status
            q: Search query (filename)
            page: Page number (1-indexed)
            per_page: Items per page (max 100)
            sort: Field to sort by
            order: Sort order ('asc' or 'desc')

        Returns:
            Tuple of (documents, total_count)
        """
        per_page = min(per_page, 100)

        # Base query
        stmt = select(Document).where(Document.case_id == case_id)

        # Apply filters
        if document_type:
            stmt = stmt.where(Document.document_type == document_type)

        if status:
            stmt = stmt.where(Document.overall_status == status)

        if q:
            search_pattern = f"%{q.strip()}%"
            stmt = stmt.where(Document.filename.ilike(search_pattern))

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.session.scalar(count_stmt) or 0

        # Apply sorting
        sort_column = getattr(Document, sort, Document.created_at)
        direction = desc if order.lower() == "desc" else asc
        stmt = stmt.order_by(direction(sort_column))

        # Apply pagination
        offset = (page - 1) * per_page
        stmt = stmt.limit(per_page).offset(offset)

        # Execute
        documents = list(self.session.execute(stmt).scalars().all())

        return documents, total

    def update_status(
        self,
        document_id: str,
        overall_status: DocumentStatusEnum,
        stage: Optional[str] = None,
        stage_progress: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> Optional[Document]:
        """Update document processing status."""
        doc = self.get_by_id(document_id)
        if doc:
            doc.overall_status = overall_status
            if stage is not None:
                doc.stage = stage
            if stage_progress is not None:
                doc.stage_progress = stage_progress
            if error_message is not None:
                doc.error_message = error_message
            self.session.flush()
        return doc


class UploadSessionRepository:
    """Repository for UploadSession entities with pagination."""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        case_id: str,
        uploaded_by_id: int,
        total_documents: int = 0,
    ) -> UploadSession:
        """Create a new upload session."""
        session = UploadSession(
            case_id=case_id,
            uploaded_by_id=uploaded_by_id,
            total_documents=total_documents,
        )
        self.session.add(session)
        self.session.flush()
        return session

    def get_by_id(self, upload_session_id: str) -> Optional[UploadSession]:
        """Get upload session by ID."""
        return self.session.get(UploadSession, upload_session_id)

    def list(
        self,
        case_id: str,
        page: int = 1,
        per_page: int = 20,
        sort: str = "created_at",
        order: str = "desc",
    ) -> Tuple[list[UploadSession], int]:
        """List upload sessions with pagination."""
        per_page = min(per_page, 100)

        stmt = select(UploadSession).where(UploadSession.case_id == case_id)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.session.scalar(count_stmt) or 0

        # Apply sorting
        sort_column = getattr(UploadSession, sort, UploadSession.created_at)
        direction = desc if order.lower() == "desc" else asc
        stmt = stmt.order_by(direction(sort_column))

        # Apply pagination
        offset = (page - 1) * per_page
        stmt = stmt.limit(per_page).offset(offset)

        sessions = list(self.session.execute(stmt).scalars().all())

        return sessions, total

    def update_counts(
        self,
        upload_session_id: str,
        completed_increment: int = 0,
        failed_increment: int = 0,
    ) -> Optional[UploadSession]:
        """Update document counts for an upload session."""
        session = self.get_by_id(upload_session_id)
        if session:
            session.completed_documents += completed_increment
            session.failed_documents += failed_increment
            self.session.flush()
        return session


class DraftSessionRepository:
    """Repository for DraftSession entities with pagination."""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        case_id: str,
        user_id: int,
        rulebook_id: int,
        title: str,
        document_type: str,
    ) -> DraftSession:
        """Create a new draft session."""
        draft = DraftSession(
            case_id=case_id,
            user_id=user_id,
            rulebook_id=rulebook_id,
            title=title,
            document_type=document_type,
        )
        self.session.add(draft)
        self.session.flush()
        return draft

    def get_by_id(self, draft_session_id: str) -> Optional[DraftSession]:
        """Get draft session by ID."""
        return self.session.get(DraftSession, draft_session_id)

    def list(
        self,
        case_id: str,
        status: Optional[DraftSessionStatusEnum] = None,
        page: int = 1,
        per_page: int = 20,
        sort: str = "created_at",
        order: str = "desc",
    ) -> Tuple[list[DraftSession], int]:
        """List draft sessions with pagination."""
        per_page = min(per_page, 100)

        stmt = select(DraftSession).where(DraftSession.case_id == case_id)

        if status:
            stmt = stmt.where(DraftSession.status == status)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.session.scalar(count_stmt) or 0

        # Apply sorting
        sort_column = getattr(DraftSession, sort, DraftSession.created_at)
        direction = desc if order.lower() == "desc" else asc
        stmt = stmt.order_by(direction(sort_column))

        # Apply pagination
        offset = (page - 1) * per_page
        stmt = stmt.limit(per_page).offset(offset)

        drafts = list(self.session.execute(stmt).scalars().all())

        return drafts, total

    def update_status(
        self,
        draft_session_id: str,
        status: DraftSessionStatusEnum,
        error_message: Optional[str] = None,
    ) -> Optional[DraftSession]:
        """Update draft session status."""
        draft = self.get_by_id(draft_session_id)
        if draft:
            draft.status = status
            if error_message is not None:
                draft.error_message = error_message
            self.session.flush()
        return draft


class RulebookRepository:
    """Repository for Rulebook entities with pagination."""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        document_type: str,
        jurisdiction: str,
        version: str,
        source_yaml: str,
        created_by_id: int,
        label: Optional[str] = None,
    ) -> Rulebook:
        """Create a new rulebook."""
        rulebook = Rulebook(
            document_type=document_type,
            jurisdiction=jurisdiction,
            version=version,
            source_yaml=source_yaml,
            created_by_id=created_by_id,
            label=label,
        )
        self.session.add(rulebook)
        self.session.flush()
        return rulebook

    def get_by_id(self, rulebook_id: int) -> Optional[Rulebook]:
        """Get rulebook by ID."""
        return self.session.get(Rulebook, rulebook_id)

    def list(
        self,
        document_type: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        status: Optional[RulebookStatusEnum] = None,
        page: int = 1,
        per_page: int = 20,
        sort: str = "created_at",
        order: str = "desc",
    ) -> Tuple[list[Rulebook], int]:
        """List rulebooks with pagination and filtering."""
        per_page = min(per_page, 100)

        stmt = select(Rulebook)

        # Apply filters
        if document_type:
            stmt = stmt.where(Rulebook.document_type == document_type)

        if jurisdiction:
            stmt = stmt.where(Rulebook.jurisdiction == jurisdiction)

        if status:
            stmt = stmt.where(Rulebook.status == status)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.session.scalar(count_stmt) or 0

        # Apply sorting
        sort_column = getattr(Rulebook, sort, Rulebook.created_at)
        direction = desc if order.lower() == "desc" else asc
        stmt = stmt.order_by(direction(sort_column))

        # Apply pagination
        offset = (page - 1) * per_page
        stmt = stmt.limit(per_page).offset(offset)

        rulebooks = list(self.session.execute(stmt).scalars().all())

        return rulebooks, total

    def get_published(
        self,
        document_type: str,
        jurisdiction: str,
    ) -> Optional[Rulebook]:
        """Get the latest published rulebook for a document type and jurisdiction."""
        stmt = (
            select(Rulebook)
            .where(
                Rulebook.document_type == document_type,
                Rulebook.jurisdiction == jurisdiction,
                Rulebook.status == RulebookStatusEnum.PUBLISHED,
            )
            .order_by(desc(Rulebook.created_at))
            .limit(1)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def update_status(
        self,
        rulebook_id: int,
        status: RulebookStatusEnum,
    ) -> Optional[Rulebook]:
        """Update rulebook status (e.g., publish or deprecate)."""
        rulebook = self.get_by_id(rulebook_id)
        if rulebook:
            rulebook.status = status
            self.session.flush()
        return rulebook
