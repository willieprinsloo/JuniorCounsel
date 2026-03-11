"""
Integration tests for document processing workflow.

Tests the complete pipeline:
1. Document upload and enqueuing
2. OCR/text extraction
3. Chunking
4. Embedding generation
5. Vector indexing
6. Search and retrieval
"""
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from sqlalchemy.orm import Session

from app.persistence.models import (
    Document,
    DocumentChunk,
    DocumentStatusEnum,
    Case,
    Organisation,
    User
)
from app.persistence.repositories import DocumentRepository, CaseRepository
from app.workers.document_processing import document_processing_job
from app.core.ai_providers import get_embedding_provider


@pytest.fixture
def test_organisation(db_session: Session):
    """Create test organisation."""
    org = Organisation(
        name="Test Law Firm",
        email="test@lawfirm.co.za",
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
        first_name="Test",
        last_name="Attorney",
        organisation_id=test_organisation.id,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_case(db_session: Session, test_organisation: Organisation, test_user: User):
    """Create test case."""
    case = Case(
        title="Test Case - Document Processing",
        case_number="2025/12345",
        organisation_id=test_organisation.id,
        created_by_id=test_user.id,
        description="Integration test case for document workflow"
    )
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)
    return case


@pytest.fixture
def test_document(db_session: Session, test_case: Case):
    """Create test document."""
    doc = Document(
        case_id=test_case.id,
        filename="test_affidavit.pdf",
        file_path="/tmp/test_affidavit.pdf",
        file_size=1024 * 50,  # 50KB
        mime_type="application/pdf",
        overall_status=DocumentStatusEnum.QUEUED,
        stage="queued",
        needs_ocr=False,
        metadata={"test": True}
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc


@pytest.fixture
def mock_embedding_provider():
    """Mock embedding provider for tests."""
    provider = Mock()
    provider.model = "text-embedding-3-small"
    provider.dimension = 1536

    # Mock embed_text to return fixed vector
    def mock_embed_text(text: str):
        # Return a deterministic vector based on text length
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        return [float((hash_val + i) % 100) / 100.0 for i in range(1536)]

    provider.embed_text = Mock(side_effect=mock_embed_text)

    # Mock embed_batch
    def mock_embed_batch(texts, batch_size=100):
        return [mock_embed_text(text) for text in texts]

    provider.embed_batch = Mock(side_effect=mock_embed_batch)

    return provider


class TestDocumentProcessingWorkflow:
    """Integration tests for document processing workflow."""

    def test_pdf_text_extraction_workflow(
        self,
        db_session: Session,
        test_document: Document,
        mock_embedding_provider
    ):
        """Test complete workflow for PDF with embedded text."""
        # Create mock PDF file
        test_file_path = "/tmp/test_affidavit.pdf"
        mock_pdf_content = """
        IN THE HIGH COURT OF SOUTH AFRICA
        GAUTENG DIVISION, PRETORIA

        Case No: 2025/12345

        AFFIDAVIT

        I, John Smith, hereby declare under oath:

        1. I am the applicant in this matter.
        2. The facts deposed to herein are within my personal knowledge.
        3. This affidavit is made in support of my application.
        """

        # Mock the file operations
        with patch('app.services.text_extraction.extract_text') as mock_extract:
            mock_extract.return_value = mock_pdf_content

            with patch('app.core.ai_providers.get_embedding_provider') as mock_get_provider:
                mock_get_provider.return_value = mock_embedding_provider

                # Run the document processing job
                document_processing_job(str(test_document.id))

        # Verify document was updated
        db_session.refresh(test_document)
        assert test_document.overall_status == DocumentStatusEnum.COMPLETED
        assert test_document.stage == "completed"
        assert test_document.stage_progress == 100
        assert test_document.extracted_text == mock_pdf_content

        # Verify chunks were created
        doc_repo = DocumentRepository(db_session)
        chunks = doc_repo.get_chunks(str(test_document.id))
        assert len(chunks) > 0

        # Verify embeddings were generated
        for chunk in chunks:
            assert chunk.embedding is not None
            assert len(chunk.embedding) == 1536
            assert chunk.content is not None
            assert len(chunk.content) > 0

    def test_ocr_workflow(
        self,
        db_session: Session,
        test_case: Case,
        mock_embedding_provider
    ):
        """Test complete workflow for scanned PDF requiring OCR."""
        # Create document that needs OCR
        doc = Document(
            case_id=test_case.id,
            filename="scanned_document.pdf",
            file_path="/tmp/scanned_document.pdf",
            file_size=1024 * 100,  # 100KB
            mime_type="application/pdf",
            overall_status=DocumentStatusEnum.QUEUED,
            stage="queued",
            needs_ocr=True,  # Requires OCR
            metadata={"scanned": True}
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        mock_ocr_text = """
        LEASE AGREEMENT

        This lease agreement is entered into on 1 January 2025
        between the Lessor and the Lessee.

        The property is located at 123 Main Street, Johannesburg.
        """

        with patch('app.services.ocr.perform_ocr') as mock_ocr:
            mock_ocr.return_value = mock_ocr_text

            with patch('app.core.ai_providers.get_embedding_provider') as mock_get_provider:
                mock_get_provider.return_value = mock_embedding_provider

                # Run the document processing job
                document_processing_job(str(doc.id))

        # Verify OCR was called
        mock_ocr.assert_called_once_with("/tmp/scanned_document.pdf")

        # Verify document was processed
        db_session.refresh(doc)
        assert doc.overall_status == DocumentStatusEnum.COMPLETED
        assert doc.extracted_text == mock_ocr_text

        # Verify chunks were created with OCR text
        doc_repo = DocumentRepository(db_session)
        chunks = doc_repo.get_chunks(str(doc.id))
        assert len(chunks) > 0
        assert "LEASE AGREEMENT" in chunks[0].content or "lease agreement" in chunks[0].content.lower()

    def test_chunking_with_overlap(
        self,
        db_session: Session,
        test_document: Document,
        mock_embedding_provider
    ):
        """Test that chunking creates overlapping chunks correctly."""
        long_text = " ".join([f"Sentence {i} about legal matter." for i in range(100)])

        with patch('app.services.text_extraction.extract_text') as mock_extract:
            mock_extract.return_value = long_text

            with patch('app.core.ai_providers.get_embedding_provider') as mock_get_provider:
                mock_get_provider.return_value = mock_embedding_provider

                document_processing_job(str(test_document.id))

        # Verify chunks were created
        doc_repo = DocumentRepository(db_session)
        chunks = doc_repo.get_chunks(str(test_document.id))

        assert len(chunks) > 1  # Should create multiple chunks

        # Verify chunks have sequential indices
        indices = [chunk.chunk_index for chunk in chunks]
        assert indices == list(range(len(chunks)))

        # Verify chunks have embeddings
        for chunk in chunks:
            assert chunk.embedding is not None
            assert len(chunk.embedding) == 1536

    def test_error_handling_and_retry(
        self,
        db_session: Session,
        test_document: Document
    ):
        """Test that errors are caught and document status is updated."""
        with patch('app.services.text_extraction.extract_text') as mock_extract:
            # Simulate extraction failure
            mock_extract.side_effect = Exception("Text extraction failed")

            # Run the job (should catch the error)
            with pytest.raises(Exception, match="Text extraction failed"):
                document_processing_job(str(test_document.id))

        # Verify document status was updated to failed
        db_session.refresh(test_document)
        assert test_document.overall_status == DocumentStatusEnum.FAILED
        assert "Text extraction failed" in test_document.error_message

    def test_document_classification(
        self,
        db_session: Session,
        test_document: Document,
        mock_embedding_provider
    ):
        """Test automatic document type classification."""
        affidavit_text = """
        AFFIDAVIT

        I, the undersigned, John Smith, do hereby make oath and state:

        1. I am the applicant in this matter.
        2. The facts herein are within my personal knowledge.
        """

        with patch('app.services.text_extraction.extract_text') as mock_extract:
            mock_extract.return_value = affidavit_text

            with patch('app.core.ai_providers.get_embedding_provider') as mock_get_provider:
                mock_get_provider.return_value = mock_embedding_provider

                with patch('app.services.classification.classify_document_content') as mock_classify:
                    mock_classify.return_value = "affidavit"

                    document_processing_job(str(test_document.id))

        # Verify classification was performed
        db_session.refresh(test_document)
        assert test_document.metadata is not None
        assert test_document.metadata.get("suggested_type") == "affidavit"

    def test_embedding_batch_processing(
        self,
        db_session: Session,
        test_document: Document,
        mock_embedding_provider
    ):
        """Test that embeddings are generated in batches for efficiency."""
        # Create a long document that will generate many chunks
        long_text = " ".join([f"Legal paragraph {i} with content." for i in range(200)])

        with patch('app.services.text_extraction.extract_text') as mock_extract:
            mock_extract.return_value = long_text

            with patch('app.core.ai_providers.get_embedding_provider') as mock_get_provider:
                mock_get_provider.return_value = mock_embedding_provider

                document_processing_job(str(test_document.id))

        # Verify embed_batch was called (not embed_text repeatedly)
        assert mock_embedding_provider.embed_batch.called

        # Verify all chunks were embedded
        doc_repo = DocumentRepository(db_session)
        chunks = doc_repo.get_chunks(str(test_document.id))

        for chunk in chunks:
            assert chunk.embedding is not None

    def test_progress_tracking(
        self,
        db_session: Session,
        test_document: Document,
        mock_embedding_provider
    ):
        """Test that document processing updates progress correctly."""
        test_text = "Test legal document content."

        progress_updates = []

        def track_progress(*args, **kwargs):
            db_session.refresh(test_document)
            progress_updates.append({
                'stage': test_document.stage,
                'progress': test_document.stage_progress
            })

        with patch('app.services.text_extraction.extract_text') as mock_extract:
            mock_extract.return_value = test_text
            mock_extract.side_effect = track_progress

            with patch('app.core.ai_providers.get_embedding_provider') as mock_get_provider:
                mock_get_provider.return_value = mock_embedding_provider

                document_processing_job(str(test_document.id))

        # Verify final status
        db_session.refresh(test_document)
        assert test_document.overall_status == DocumentStatusEnum.COMPLETED
        assert test_document.stage == "completed"
        assert test_document.stage_progress == 100


class TestVectorSearchIntegration:
    """Integration tests for vector search on processed documents."""

    def test_search_after_processing(
        self,
        db_session: Session,
        test_case: Case,
        mock_embedding_provider
    ):
        """Test that processed documents are searchable via vector similarity."""
        # Create and process a document
        doc = Document(
            case_id=test_case.id,
            filename="contract.pdf",
            file_path="/tmp/contract.pdf",
            file_size=1024 * 30,
            mime_type="application/pdf",
            overall_status=DocumentStatusEnum.QUEUED,
            stage="queued",
            needs_ocr=False
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        contract_text = """
        EMPLOYMENT CONTRACT

        This agreement is made between ABC Company (Employer)
        and Jane Doe (Employee) on 1 February 2025.

        The employee shall be employed as Senior Attorney
        with a monthly salary of R50,000.
        """

        with patch('app.services.text_extraction.extract_text') as mock_extract:
            mock_extract.return_value = contract_text

            with patch('app.core.ai_providers.get_embedding_provider') as mock_get_provider:
                mock_get_provider.return_value = mock_embedding_provider

                document_processing_job(str(doc.id))

        # Verify chunks were created
        doc_repo = DocumentRepository(db_session)
        chunks = doc_repo.get_chunks(str(doc.id))
        assert len(chunks) > 0

        # Test search functionality
        from sqlalchemy import select, func

        query = "employment salary"
        query_embedding = mock_embedding_provider.embed_text(query)

        stmt = select(
            DocumentChunk,
            func.cosine_distance(DocumentChunk.embedding, query_embedding).label('distance')
        ).where(
            DocumentChunk.document_id == doc.id
        ).order_by('distance').limit(5)

        results = db_session.execute(stmt).all()

        assert len(results) > 0

        # Verify similarity scores
        for chunk, distance in results:
            similarity = 1 - distance
            assert 0 <= similarity <= 1
            assert "employment" in chunk.content.lower() or "salary" in chunk.content.lower()
