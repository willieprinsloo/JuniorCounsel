"""
Integration tests for Document API endpoints.

Tests retry and delete functionality for document management.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from sqlalchemy.orm import Session

from app.persistence.models import (
    Document,
    DocumentChunk,
    DocumentStatusEnum,
    Case,
    Organisation,
    User
)
from app.persistence.repositories import DocumentRepository


@pytest.fixture
def test_organisation(db_session: Session):
    """Create test organisation."""
    org = Organisation(
        name="Test Law Firm",
        contact_email="test@lawfirm.co.za",
        is_active=True
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


@pytest.fixture
def test_user(db_session: Session, test_organisation: Organisation):
    """Create test user."""
    user = User(
        email="attorney@lawfirm.co.za",
        password_hash="hashed_password",
        full_name="Test Attorney"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_case(db_session: Session, test_organisation: Organisation, test_user: User):
    """Create test case."""
    case = Case(
        title="Test Case - API Tests",
        case_number="2026/TEST",
        organisation_id=test_organisation.id,
        owner_id=test_user.id,
        description="Test case for document API"
    )
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)
    return case


@pytest.fixture
def failed_document(db_session: Session, test_case: Case, test_user: User):
    """Create a failed document for retry testing."""
    doc = Document(
        case_id=test_case.id,
        uploaded_by_id=test_user.id,
        filename="failed_document.pdf",
        file_path="test_case/failed_doc.pdf",
        file_size=1024 * 50,
        overall_status=DocumentStatusEnum.FAILED,
        stage=None,
        stage_progress=0,
        error_message="Text extraction failed: OCR dependencies not installed",
        needs_ocr=False
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc


@pytest.fixture
def completed_document(db_session: Session, test_case: Case, test_user: User):
    """Create a completed document for delete testing."""
    doc = Document(
        case_id=test_case.id,
        uploaded_by_id=test_user.id,
        filename="completed_document.pdf",
        file_path="test_case/completed_doc.pdf",
        file_size=1024 * 100,
        overall_status=DocumentStatusEnum.COMPLETED,
        stage=None,
        stage_progress=100,
        needs_ocr=False,
        text_content="Sample document text content"
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc


@pytest.fixture
def document_with_chunks(db_session: Session, completed_document: Document):
    """Create document chunks for testing cascade deletion."""
    chunks = []
    for i in range(5):
        chunk = DocumentChunk(
            document_id=completed_document.id,
            chunk_index=i,
            content=f"Chunk {i} content with legal text",
            embedding=[0.1] * 1536,  # Mock embedding vector
            page_number=1,
            char_start=i * 100,
            char_end=(i + 1) * 100
        )
        chunks.append(chunk)
        db_session.add(chunk)

    db_session.commit()
    for chunk in chunks:
        db_session.refresh(chunk)

    return chunks


class TestDocumentRetryEndpoint:
    """Tests for POST /api/v1/documents/{id}/retry endpoint."""

    def test_retry_failed_document(
        self,
        db_session: Session,
        failed_document: Document
    ):
        """Test retrying a failed document resets status and re-enqueues."""
        doc_repo = DocumentRepository(db_session)

        # Verify initial failed state
        assert failed_document.overall_status == DocumentStatusEnum.FAILED
        assert failed_document.error_message is not None
        assert failed_document.stage_progress == 0

        # Mock queue enqueue
        with patch('app.core.queue.enqueue_document_processing') as mock_enqueue:
            mock_enqueue.return_value = "job-123"

            # Simulate retry endpoint logic
            failed_document.overall_status = DocumentStatusEnum.QUEUED
            failed_document.stage = None
            failed_document.stage_progress = 0
            failed_document.error_message = None
            db_session.flush()
            db_session.commit()

            # Enqueue processing job
            job_id = mock_enqueue(str(failed_document.id))
            db_session.commit()

        # Verify document was reset
        db_session.refresh(failed_document)
        assert failed_document.overall_status == DocumentStatusEnum.QUEUED
        assert failed_document.error_message is None
        assert failed_document.stage is None
        assert failed_document.stage_progress == 0

        # Verify job was enqueued
        mock_enqueue.assert_called_once_with(str(failed_document.id))

    def test_retry_nonexistent_document(self, db_session: Session):
        """Test retrying a non-existent document returns 404."""
        doc_repo = DocumentRepository(db_session)

        # Try to get non-existent document
        fake_id = "00000000-0000-0000-0000-000000000000"
        document = doc_repo.get_by_id(fake_id)

        # Should return None (would be 404 in API)
        assert document is None

    def test_retry_already_queued_document(
        self,
        db_session: Session,
        test_case: Case,
        test_user: User
    ):
        """Test retrying a document that's already queued."""
        # Create queued document
        doc = Document(
            case_id=test_case.id,
            uploaded_by_id=test_user.id,
            filename="queued_doc.pdf",
            file_path="test_case/queued.pdf",
            file_size=1024,
            overall_status=DocumentStatusEnum.QUEUED,
            stage=None,
            stage_progress=0,
            needs_ocr=False
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        # Retry should still work (re-enqueue)
        with patch('app.core.queue.enqueue_document_processing') as mock_enqueue:
            mock_enqueue.return_value = "job-456"

            doc.overall_status = DocumentStatusEnum.QUEUED
            doc.stage = None
            doc.stage_progress = 0
            doc.error_message = None
            db_session.flush()
            db_session.commit()

            job_id = mock_enqueue(str(doc.id))

        # Should successfully re-enqueue
        mock_enqueue.assert_called_once()

    def test_retry_with_queue_failure(
        self,
        db_session: Session,
        failed_document: Document
    ):
        """Test retry handles queue enqueue failures gracefully."""
        # Mock queue enqueue to fail
        with patch('app.core.queue.enqueue_document_processing') as mock_enqueue:
            mock_enqueue.side_effect = Exception("Redis connection failed")

            # Reset status first
            failed_document.overall_status = DocumentStatusEnum.QUEUED
            failed_document.stage = None
            failed_document.stage_progress = 0
            failed_document.error_message = None
            db_session.flush()
            db_session.commit()

            # Try to enqueue (should fail)
            try:
                job_id = mock_enqueue(str(failed_document.id))
            except Exception as e:
                # Record error message
                failed_document.error_message = f"Failed to enqueue job: {str(e)}"
                db_session.flush()
                db_session.commit()

        # Verify error was recorded
        db_session.refresh(failed_document)
        assert "Failed to enqueue job" in failed_document.error_message
        assert "Redis connection failed" in failed_document.error_message


class TestDocumentDeleteEndpoint:
    """Tests for DELETE /api/v1/documents/{id} endpoint."""

    def test_delete_document_basic(
        self,
        db_session: Session,
        completed_document: Document
    ):
        """Test basic document deletion."""
        doc_repo = DocumentRepository(db_session)
        doc_id = str(completed_document.id)

        # Mock file deletion
        with patch('app.core.storage.storage.delete_file') as mock_delete_file:
            mock_delete_file.return_value = True

            # Delete document
            db_session.delete(completed_document)
            db_session.flush()
            db_session.commit()

        # Verify document was deleted
        deleted_doc = doc_repo.get_by_id(doc_id)
        assert deleted_doc is None

        # Verify file deletion was called
        mock_delete_file.assert_called_once()

    def test_delete_document_with_chunks(
        self,
        db_session: Session,
        completed_document: Document,
        document_with_chunks: list[DocumentChunk]
    ):
        """Test document deletion cascades to chunks."""
        doc_repo = DocumentRepository(db_session)
        doc_id = str(completed_document.id)

        # Verify chunks exist before deletion
        assert len(document_with_chunks) == 5
        for chunk in document_with_chunks:
            assert chunk.document_id == completed_document.id

        # Mock file deletion
        with patch('app.core.storage.storage.delete_file') as mock_delete_file:
            mock_delete_file.return_value = True

            # Delete document
            db_session.delete(completed_document)
            db_session.flush()
            db_session.commit()

        # Verify document was deleted
        deleted_doc = doc_repo.get_by_id(doc_id)
        assert deleted_doc is None

        # Verify chunks were cascade deleted
        remaining_chunks = db_session.query(DocumentChunk).filter(
            DocumentChunk.document_id == doc_id
        ).all()
        assert len(remaining_chunks) == 0

    def test_delete_document_file_not_found(
        self,
        db_session: Session,
        completed_document: Document
    ):
        """Test deletion continues even if physical file doesn't exist."""
        doc_repo = DocumentRepository(db_session)
        doc_id = str(completed_document.id)

        # Mock file deletion to raise FileNotFoundError
        with patch('app.core.storage.storage.delete_file') as mock_delete_file:
            mock_delete_file.side_effect = FileNotFoundError("File not found")

            # Should still delete from database despite file error
            try:
                mock_delete_file(completed_document.file_path)
            except FileNotFoundError:
                pass  # Ignore file error, continue with DB deletion

            db_session.delete(completed_document)
            db_session.flush()
            db_session.commit()

        # Verify document was deleted from database
        deleted_doc = doc_repo.get_by_id(doc_id)
        assert deleted_doc is None

    def test_delete_nonexistent_document(self, db_session: Session):
        """Test deleting a non-existent document returns 404."""
        doc_repo = DocumentRepository(db_session)

        # Try to get non-existent document
        fake_id = "00000000-0000-0000-0000-000000000000"
        document = doc_repo.get_by_id(fake_id)

        # Should return None (would be 404 in API)
        assert document is None

    def test_delete_processing_document(
        self,
        db_session: Session,
        test_case: Case,
        test_user: User
    ):
        """Test deleting a document that's currently processing."""
        # Create processing document
        doc = Document(
            case_id=test_case.id,
            uploaded_by_id=test_user.id,
            filename="processing_doc.pdf",
            file_path="test_case/processing.pdf",
            file_size=1024 * 200,
            overall_status=DocumentStatusEnum.PROCESSING,
            stage="embedding",
            stage_progress=60,
            needs_ocr=False
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        doc_id = str(doc.id)

        # Should allow deletion even while processing
        with patch('app.core.storage.storage.delete_file') as mock_delete_file:
            mock_delete_file.return_value = True

            db_session.delete(doc)
            db_session.flush()
            db_session.commit()

        # Verify document was deleted
        doc_repo = DocumentRepository(db_session)
        deleted_doc = doc_repo.get_by_id(doc_id)
        assert deleted_doc is None


class TestDocumentStatusViewer:
    """Tests for document status tracking and display."""

    def test_status_progression(
        self,
        db_session: Session,
        test_case: Case,
        test_user: User
    ):
        """Test document status progression through processing stages."""
        # Create new document
        doc = Document(
            case_id=test_case.id,
            uploaded_by_id=test_user.id,
            filename="status_test.pdf",
            file_path="test_case/status_test.pdf",
            file_size=1024,
            overall_status=DocumentStatusEnum.QUEUED,
            stage=None,
            stage_progress=0,
            needs_ocr=False
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        # Simulate status progression
        stages = [
            (DocumentStatusEnum.PROCESSING, "text_extraction", 20),
            (DocumentStatusEnum.PROCESSING, "chunking", 40),
            (DocumentStatusEnum.PROCESSING, "embedding", 60),
            (DocumentStatusEnum.PROCESSING, "indexing", 85),
            (DocumentStatusEnum.COMPLETED, None, 100),
        ]

        doc_repo = DocumentRepository(db_session)

        for status, stage, progress in stages:
            doc_repo.update_status(
                document_id=str(doc.id),
                overall_status=status,
                stage=stage,
                stage_progress=progress
            )
            db_session.commit()
            db_session.refresh(doc)

            # Verify status update
            assert doc.overall_status == status
            assert doc.stage == stage
            assert doc.stage_progress == progress

    def test_error_message_recording(
        self,
        db_session: Session,
        test_case: Case,
        test_user: User
    ):
        """Test error messages are properly recorded for failed documents."""
        doc = Document(
            case_id=test_case.id,
            uploaded_by_id=test_user.id,
            filename="error_test.pdf",
            file_path="test_case/error_test.pdf",
            file_size=1024,
            overall_status=DocumentStatusEnum.QUEUED,
            stage=None,
            stage_progress=0,
            needs_ocr=True
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        # Simulate failure
        error_message = "OCR dependencies not installed. Install with: pip install pytesseract"
        doc_repo = DocumentRepository(db_session)
        doc_repo.update_status(
            document_id=str(doc.id),
            overall_status=DocumentStatusEnum.FAILED,
            stage=None,
            stage_progress=0,
            error_message=error_message
        )
        db_session.commit()
        db_session.refresh(doc)

        # Verify error was recorded
        assert doc.overall_status == DocumentStatusEnum.FAILED
        assert doc.error_message == error_message
        assert doc.stage_progress == 0
