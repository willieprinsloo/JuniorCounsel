"""
Unit tests for DocumentRepository.
"""
import pytest

from app.persistence import (
    DocumentRepository,
    DocumentStatusEnum,
    DocumentTypeEnum,
)


@pytest.mark.unit
class TestDocumentRepository:
    """Test DocumentRepository methods."""

    @pytest.fixture
    def document_repository(self, db_session):
        """Provide a DocumentRepository instance."""
        return DocumentRepository(db_session)

    def test_create_document(self, document_repository, case_factory, user_factory):
        """Test creating a new document."""
        case = case_factory(title="Test Case")
        user = user_factory(email="uploader@example.com")

        doc = document_repository.create(
            case_id=str(case.id),
            uploaded_by_id=user.id,
            filename="evidence.pdf",
            needs_ocr=True,
        )

        assert doc.id is not None
        assert doc.filename == "evidence.pdf"
        assert doc.case_id == case.id
        assert doc.uploaded_by_id == user.id
        assert doc.needs_ocr is True
        assert doc.overall_status == DocumentStatusEnum.QUEUED

    def test_get_by_id(self, document_repository, case_factory, user_factory, db_session):
        """Test retrieving a document by ID."""
        from app.persistence.models import Document

        case = case_factory()
        user = user_factory()

        doc = Document(
            case_id=case.id,
            uploaded_by_id=user.id,
            filename="test.pdf",
        )
        db_session.add(doc)
        db_session.flush()

        retrieved = document_repository.get_by_id(str(doc.id))

        assert retrieved is not None
        assert retrieved.id == doc.id
        assert retrieved.filename == "test.pdf"

    def test_list_documents_with_pagination(self, document_repository, case_factory, user_factory, db_session):
        """Test listing documents with pagination."""
        from app.persistence.models import Document

        case = case_factory()
        user = user_factory()

        # Create 25 documents
        for i in range(25):
            doc = Document(
                case_id=case.id,
                uploaded_by_id=user.id,
                filename=f"doc_{i}.pdf",
            )
            db_session.add(doc)
        db_session.flush()

        # Get first page
        page1, total = document_repository.list(
            case_id=str(case.id),
            page=1,
            per_page=10,
        )

        assert len(page1) == 10
        assert total == 25

        # Get second page
        page2, _ = document_repository.list(
            case_id=str(case.id),
            page=2,
            per_page=10,
        )

        assert len(page2) == 10

        # Ensure different documents on different pages
        page1_ids = {doc.id for doc in page1}
        page2_ids = {doc.id for doc in page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_list_with_document_type_filter(self, document_repository, case_factory, user_factory, db_session):
        """Test filtering documents by type."""
        from app.persistence.models import Document

        case = case_factory()
        user = user_factory()

        # Create documents of different types
        evidence_doc = Document(
            case_id=case.id,
            uploaded_by_id=user.id,
            filename="evidence.pdf",
            document_type=DocumentTypeEnum.EVIDENCE,
        )
        pleading_doc = Document(
            case_id=case.id,
            uploaded_by_id=user.id,
            filename="pleading.pdf",
            document_type=DocumentTypeEnum.PLEADING,
        )
        db_session.add_all([evidence_doc, pleading_doc])
        db_session.flush()

        # Filter by evidence type
        evidence_docs, total = document_repository.list(
            case_id=str(case.id),
            document_type=DocumentTypeEnum.EVIDENCE,
        )

        assert len(evidence_docs) == 1
        assert total == 1
        assert evidence_docs[0].document_type == DocumentTypeEnum.EVIDENCE

    def test_list_with_status_filter(self, document_repository, case_factory, user_factory, db_session):
        """Test filtering documents by status."""
        from app.persistence.models import Document

        case = case_factory()
        user = user_factory()

        # Create documents with different statuses
        queued_doc = Document(
            case_id=case.id,
            uploaded_by_id=user.id,
            filename="queued.pdf",
            overall_status=DocumentStatusEnum.QUEUED,
        )
        completed_doc = Document(
            case_id=case.id,
            uploaded_by_id=user.id,
            filename="completed.pdf",
            overall_status=DocumentStatusEnum.COMPLETED,
        )
        db_session.add_all([queued_doc, completed_doc])
        db_session.flush()

        # Filter by completed status
        completed_docs, total = document_repository.list(
            case_id=str(case.id),
            status=DocumentStatusEnum.COMPLETED,
        )

        assert len(completed_docs) == 1
        assert total == 1
        assert completed_docs[0].overall_status == DocumentStatusEnum.COMPLETED

    def test_search_by_filename(self, document_repository, case_factory, user_factory, db_session):
        """Test case-insensitive search by filename."""
        from app.persistence.models import Document

        case = case_factory()
        user = user_factory()

        doc1 = Document(case_id=case.id, uploaded_by_id=user.id, filename="Evidence_Report.pdf")
        doc2 = Document(case_id=case.id, uploaded_by_id=user.id, filename="Pleading_Final.pdf")
        doc3 = Document(case_id=case.id, uploaded_by_id=user.id, filename="Evidence_Summary.pdf")
        db_session.add_all([doc1, doc2, doc3])
        db_session.flush()

        # Search for "evidence" (case-insensitive)
        results, total = document_repository.list(
            case_id=str(case.id),
            q="evidence",
        )

        assert len(results) == 2
        assert total == 2
        assert all("evidence" in doc.filename.lower() for doc in results)

    def test_update_status(self, document_repository, case_factory, user_factory, db_session):
        """Test updating document status."""
        from app.persistence.models import Document, DocumentStageEnum

        case = case_factory()
        user = user_factory()

        doc = Document(
            case_id=case.id,
            uploaded_by_id=user.id,
            filename="test.pdf",
            overall_status=DocumentStatusEnum.QUEUED,
        )
        db_session.add(doc)
        db_session.flush()

        # Update status
        updated_doc = document_repository.update_status(
            document_id=str(doc.id),
            overall_status=DocumentStatusEnum.PROCESSING,
            stage=DocumentStageEnum.OCR,
            stage_progress=45,
        )

        assert updated_doc is not None
        assert updated_doc.overall_status == DocumentStatusEnum.PROCESSING
        assert updated_doc.stage == DocumentStageEnum.OCR
        assert updated_doc.stage_progress == 45

    def test_pagination_max_per_page(self, document_repository, case_factory, user_factory, db_session):
        """Test that per_page is capped at 100."""
        from app.persistence.models import Document

        case = case_factory()
        user = user_factory()

        # Create 150 documents
        for i in range(150):
            doc = Document(
                case_id=case.id,
                uploaded_by_id=user.id,
                filename=f"doc_{i}.pdf",
            )
            db_session.add(doc)
        db_session.flush()

        # Request 200 per page (should be capped at 100)
        results, total = document_repository.list(
            case_id=str(case.id),
            page=1,
            per_page=200,
        )

        assert len(results) == 100  # Capped at 100
        assert total == 150
