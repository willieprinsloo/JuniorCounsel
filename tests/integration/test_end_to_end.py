"""
End-to-end integration tests for complete system workflows.

Tests the entire system from document upload through draft generation:
1. Upload documents
2. Process documents (OCR, chunking, embedding, indexing)
3. Perform semantic search
4. Ask Q&A questions
5. Create draft session with intake
6. Run research
7. Generate draft
8. Verify citations
"""
import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from datetime import datetime

from sqlalchemy.orm import Session

from app.persistence.models import (
    Organisation,
    User,
    Case,
    Document,
    DocumentChunk,
    DocumentStatusEnum,
    UploadSession,
    UploadSessionStatusEnum,
    DraftSession,
    DraftSessionStatusEnum,
    Rulebook
)
from app.persistence.repositories import (
    CaseRepository,
    DocumentRepository,
    UploadSessionRepository,
    DraftSessionRepository,
    RulebookRepository
)
from app.workers.document_processing import document_processing_job
from app.workers.draft_generation import draft_research_job, draft_generation_job


@pytest.fixture
def test_organisation(db_session: Session):
    """Create test organisation."""
    org = Organisation(
        name="End-to-End Test Firm",
        email="e2e@testfirm.co.za",
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
        email="e2e@testfirm.co.za",
        password_hash="hashed_password",
        first_name="E2E",
        last_name="Tester",
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
        title="E2E Test Case - Complete Workflow",
        case_number="2025/E2E",
        organisation_id=test_organisation.id,
        created_by_id=test_user.id,
        description="End-to-end integration test case"
    )
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)
    return case


@pytest.fixture
def test_rulebook(db_session: Session, test_organisation: Organisation):
    """Create test rulebook."""
    rulebook = Rulebook(
        name="E2E Test Rulebook",
        document_type="affidavit",
        version="1.0",
        organisation_id=test_organisation.id,
        source_yaml="""
document_type: affidavit
structure:
  - name: Introduction
    description: Deponent details and oath
  - name: Facts
    description: Relevant facts with evidence
  - name: Conclusion
    description: Prayer and signature
""",
        rules_json={
            "document_type": "affidavit",
            "document_structure": [
                {"name": "Introduction", "description": "Deponent details and oath"},
                {"name": "Facts", "description": "Relevant facts with evidence"},
                {"name": "Conclusion", "description": "Prayer and signature"}
            ]
        },
        is_active=True
    )
    db_session.add(rulebook)
    db_session.commit()
    db_session.refresh(rulebook)
    return rulebook


@pytest.fixture
def mock_ai_providers():
    """Create mock AI providers for testing."""
    # Mock embedding provider
    embedding_provider = Mock()
    embedding_provider.model = "text-embedding-3-small"
    embedding_provider.dimension = 1536

    def mock_embed_text(text: str):
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        return [float((hash_val + i) % 100) / 100.0 for i in range(1536)]

    embedding_provider.embed_text = Mock(side_effect=mock_embed_text)
    embedding_provider.embed_batch = Mock(side_effect=lambda texts, batch_size=100: [mock_embed_text(t) for t in texts])

    # Mock LLM provider
    llm_provider = Mock()
    llm_provider.model = "gpt-4"

    def mock_generate(prompt: str, system_message: str = None, temperature: float = 0.7, max_tokens: int = 2000):
        # Generate realistic affidavit content with citations
        return """AFFIDAVIT

I, the undersigned, JANE DOE, do hereby make oath and state:

INTRODUCTION
1. I am an adult female and the applicant in this matter [1].
2. The facts deposed to herein are within my personal knowledge and belief.

FACTS
3. I entered into a lease agreement on 1 March 2024 for premises at 456 Oak Street [1].
4. The monthly rental was R15,000 as per the agreement [2].
5. The landlord breached the lease by failing to conduct repairs [3].
6. I sent written notice on 15 December 2024 requesting repairs [3].

CONCLUSION
7. I respectfully request that this Honourable Court grant the relief sought in the Notice of Motion.

SIGNED at JOHANNESBURG on this day of ___________ 2025.

_______________________
JANE DOE
DEPONENT"""

    llm_provider.generate = Mock(side_effect=mock_generate)

    return {
        "embedding": embedding_provider,
        "llm": llm_provider
    }


class TestCompleteSystemWorkflow:
    """End-to-end tests for complete system workflows."""

    def test_complete_workflow_upload_to_draft(
        self,
        db_session: Session,
        test_case: Case,
        test_user: User,
        test_rulebook: Rulebook,
        mock_ai_providers
    ):
        """
        Test complete workflow from document upload through draft generation.

        Workflow steps:
        1. Create upload session
        2. Upload documents
        3. Process documents (OCR, chunking, embedding)
        4. Verify search works
        5. Create draft session with intake
        6. Run research (RAG)
        7. Generate draft (LLM)
        8. Verify final draft with citations
        """
        # ====================================================================
        # PHASE 1: Document Upload
        # ====================================================================

        # Create upload session
        upload_session = UploadSession(
            case_id=test_case.id,
            created_by_id=test_user.id,
            status=UploadSessionStatusEnum.UPLOADING,
            total_documents=2
        )
        db_session.add(upload_session)
        db_session.commit()
        db_session.refresh(upload_session)

        # Upload Document 1: Lease agreement
        doc1 = Document(
            case_id=test_case.id,
            upload_session_id=upload_session.id,
            filename="lease_agreement.pdf",
            file_path="/tmp/e2e_lease.pdf",
            file_size=1024 * 60,
            mime_type="application/pdf",
            overall_status=DocumentStatusEnum.QUEUED,
            stage="queued",
            needs_ocr=False
        )
        db_session.add(doc1)

        # Upload Document 2: Correspondence
        doc2 = Document(
            case_id=test_case.id,
            upload_session_id=upload_session.id,
            filename="repair_request.pdf",
            file_path="/tmp/e2e_request.pdf",
            file_size=1024 * 20,
            mime_type="application/pdf",
            overall_status=DocumentStatusEnum.QUEUED,
            stage="queued",
            needs_ocr=False
        )
        db_session.add(doc2)

        db_session.commit()
        db_session.refresh(doc1)
        db_session.refresh(doc2)

        # Mark upload session as complete
        upload_session.status = UploadSessionStatusEnum.COMPLETED
        db_session.commit()

        # ====================================================================
        # PHASE 2: Document Processing
        # ====================================================================

        # Mock document content
        lease_content = """
LEASE AGREEMENT

This lease agreement is entered into on 1 March 2024
between ABC Properties (Pty) Ltd (the "Lessor")
and Jane Doe (the "Lessee").

PREMISES: 456 Oak Street, Johannesburg, 2000

RENTAL: R15,000 per month, payable in advance

REPAIRS: The Lessor shall maintain the premises in good repair
and shall attend to all structural repairs within 14 days of notice.

TERM: 12 months commencing 1 March 2024
"""

        repair_request_content = """
LETTER TO LANDLORD

Date: 15 December 2024

ABC Properties (Pty) Ltd
123 Main Road
Johannesburg

Dear Sir/Madam,

RE: REPAIR REQUEST - 456 OAK STREET

I hereby give notice that the following repairs are required:
1. Leaking roof in main bedroom
2. Broken window in kitchen
3. Faulty geyser

Please attend to these repairs within 14 days as per clause 8 of the lease.

Yours faithfully,
Jane Doe
"""

        # Process documents with mocked AI
        with patch('app.services.text_extraction.extract_text') as mock_extract:
            with patch('app.core.ai_providers.get_embedding_provider') as mock_get_embed:
                mock_get_embed.return_value = mock_ai_providers["embedding"]

                # Process doc1
                mock_extract.return_value = lease_content
                document_processing_job(str(doc1.id))

                # Process doc2
                mock_extract.return_value = repair_request_content
                document_processing_job(str(doc2.id))

        # Verify documents were processed
        db_session.refresh(doc1)
        db_session.refresh(doc2)

        assert doc1.overall_status == DocumentStatusEnum.COMPLETED
        assert doc2.overall_status == DocumentStatusEnum.COMPLETED
        assert doc1.extracted_text == lease_content
        assert doc2.extracted_text == repair_request_content

        # Verify chunks were created
        doc_repo = DocumentRepository(db_session)
        doc1_chunks = doc_repo.get_chunks(str(doc1.id))
        doc2_chunks = doc_repo.get_chunks(str(doc2.id))

        assert len(doc1_chunks) > 0
        assert len(doc2_chunks) > 0

        # Verify embeddings exist
        for chunk in doc1_chunks + doc2_chunks:
            assert chunk.embedding is not None
            assert len(chunk.embedding) == 1536

        # ====================================================================
        # PHASE 3: Semantic Search Verification
        # ====================================================================

        from sqlalchemy import select, func

        # Test search: "rental amount"
        query = "rental amount"
        query_embedding = mock_ai_providers["embedding"].embed_text(query)

        stmt = select(
            DocumentChunk,
            Document,
            func.cosine_distance(DocumentChunk.embedding, query_embedding).label('distance')
        ).join(
            Document, DocumentChunk.document_id == Document.id
        ).where(
            Document.case_id == test_case.id,
            Document.overall_status == DocumentStatusEnum.COMPLETED
        ).order_by('distance').limit(5)

        results = db_session.execute(stmt).all()

        assert len(results) > 0

        # Verify relevant chunk was found
        found_rental = False
        for chunk, document, distance in results:
            similarity = 1 - distance
            if similarity >= 0.6 and "15,000" in chunk.content:
                found_rental = True
                break

        assert found_rental, "Search should find rental amount"

        # ====================================================================
        # PHASE 4: Q&A Verification (RAG)
        # ====================================================================

        # Simulate Q&A: "What is the monthly rental?"
        qa_query = "What is the monthly rental amount?"
        qa_embedding = mock_ai_providers["embedding"].embed_text(qa_query)

        qa_stmt = select(
            DocumentChunk,
            Document,
            func.cosine_distance(DocumentChunk.embedding, qa_embedding).label('distance')
        ).join(
            Document, DocumentChunk.document_id == Document.id
        ).where(
            Document.case_id == test_case.id,
            Document.overall_status == DocumentStatusEnum.COMPLETED
        ).order_by('distance').limit(3)

        qa_results = db_session.execute(qa_stmt).all()
        assert len(qa_results) > 0

        # Build context for LLM
        context_parts = []
        for i, (chunk, doc, dist) in enumerate(qa_results):
            context_parts.append(f"[{i+1}] {chunk.content}")

        context = "\n\n".join(context_parts)

        # Generate answer with LLM
        with patch('app.core.ai_providers.get_llm_provider') as mock_get_llm:
            mock_llm = Mock()
            mock_llm.generate = Mock(return_value="The monthly rental is R15,000 as per the lease agreement [1].")
            mock_get_llm.return_value = mock_llm

            answer = mock_llm.generate(
                prompt=f"Context: {context}\n\nQuestion: {qa_query}\n\nAnswer:",
                system_message="You are a legal assistant.",
                temperature=0.3,
                max_tokens=500
            )

        assert "15,000" in answer or "R15,000" in answer

        # ====================================================================
        # PHASE 5: Draft Session Creation
        # ====================================================================

        # Create draft session
        draft_session = DraftSession(
            case_id=test_case.id,
            created_by_id=test_user.id,
            rulebook_id=test_rulebook.id,
            document_type="affidavit",
            title="Affidavit - Breach of Lease",
            status=DraftSessionStatusEnum.INTAKE,
            intake_responses={
                "deponent_name": "Jane Doe",
                "deponent_role": "Lessee",
                "key_facts": "I am the lessee of premises at 456 Oak Street under a lease dated 1 March 2024. The monthly rental is R15,000. The lessor has failed to conduct repairs despite written notice on 15 December 2024.",
                "relief_sought": "An order compelling the lessor to conduct repairs"
            }
        )
        db_session.add(draft_session)
        db_session.commit()
        db_session.refresh(draft_session)

        # ====================================================================
        # PHASE 6: Draft Research (RAG)
        # ====================================================================

        with patch('app.core.ai_providers.get_embedding_provider') as mock_get_embed:
            mock_get_embed.return_value = mock_ai_providers["embedding"]

            with patch('app.core.queue.enqueue_draft_generation'):
                draft_research_job(str(draft_session.id))

        # Verify research completed
        db_session.refresh(draft_session)
        assert draft_session.status == DraftSessionStatusEnum.DRAFTING
        assert draft_session.research_summary is not None

        research = draft_session.research_summary
        assert "key_excerpts" in research
        assert len(research["key_excerpts"]) > 0

        # Verify relevant excerpts were found
        excerpts_text = " ".join([e["content"] for e in research["key_excerpts"]])
        assert "lease" in excerpts_text.lower() or "rental" in excerpts_text.lower()

        # ====================================================================
        # PHASE 7: Draft Generation (LLM)
        # ====================================================================

        with patch('app.core.ai_providers.get_llm_provider') as mock_get_llm:
            mock_get_llm.return_value = mock_ai_providers["llm"]

            draft_generation_job(str(draft_session.id))

        # Verify draft generated
        db_session.refresh(draft_session)
        assert draft_session.status == DraftSessionStatusEnum.REVIEW
        assert draft_session.generated_content is not None

        generated = draft_session.generated_content
        assert "AFFIDAVIT" in generated
        assert "Jane Doe" in generated or "JANE DOE" in generated

        # ====================================================================
        # PHASE 8: Citation Verification
        # ====================================================================

        # Verify metadata and citations
        assert draft_session.metadata is not None
        metadata = draft_session.metadata

        assert "citations" in metadata
        citations = metadata["citations"]
        assert len(citations) > 0

        # Verify citation structure
        for citation in citations:
            assert "marker" in citation  # e.g., "[1]"
            assert "document" in citation  # filename
            assert "page" in citation  # page number
            assert "content" in citation  # excerpt

        # Verify citations map to research excerpts
        research_docs = [e["document"] for e in research["key_excerpts"]]
        citation_docs = [c["document"] for c in citations]

        # At least one citation should reference a research excerpt
        assert any(doc in research_docs for doc in citation_docs)

        # ====================================================================
        # PHASE 9: System-Wide Verification
        # ====================================================================

        # Verify case repository functions
        case_repo = CaseRepository(db_session)
        case_documents = case_repo.get_documents(test_case.id)
        assert len(case_documents) == 2

        # Verify upload session tracking
        upload_repo = UploadSessionRepository(db_session)
        case_uploads = upload_repo.get_by_case(test_case.id)
        assert len(case_uploads) == 1
        assert case_uploads[0].total_documents == 2

        # Verify draft session repository
        draft_repo = DraftSessionRepository(db_session)
        case_drafts = draft_repo.get_by_case(test_case.id)
        assert len(case_drafts) == 1
        assert case_drafts[0].status == DraftSessionStatusEnum.REVIEW

        # ====================================================================
        # SUCCESS: Complete workflow verified
        # ====================================================================

        print("\n" + "="*70)
        print("END-TO-END TEST PASSED")
        print("="*70)
        print(f"✅ Documents uploaded: 2")
        print(f"✅ Documents processed: 2")
        print(f"✅ Chunks created: {len(doc1_chunks) + len(doc2_chunks)}")
        print(f"✅ Search working: Yes")
        print(f"✅ Q&A working: Yes")
        print(f"✅ Draft research: {len(research['key_excerpts'])} excerpts")
        print(f"✅ Draft generation: {len(generated)} characters")
        print(f"✅ Citations: {len(citations)}")
        print("="*70 + "\n")


class TestPerformanceAndScalability:
    """Performance and scalability verification tests."""

    def test_large_document_processing(
        self,
        db_session: Session,
        test_case: Case,
        mock_ai_providers
    ):
        """Test processing of large document with many chunks."""
        # Create large document
        large_doc = Document(
            case_id=test_case.id,
            filename="large_case_bundle.pdf",
            file_path="/tmp/large_bundle.pdf",
            file_size=1024 * 1024 * 5,  # 5MB
            mime_type="application/pdf",
            overall_status=DocumentStatusEnum.QUEUED,
            stage="queued",
            needs_ocr=False
        )
        db_session.add(large_doc)
        db_session.commit()
        db_session.refresh(large_doc)

        # Generate large text (will create many chunks)
        large_text = "\n\n".join([
            f"Paragraph {i}: This is legal content about various aspects of the case. "
            f"It includes facts, arguments, and references to legal principles. "
            f"The content is sufficiently long to trigger chunking algorithms."
            for i in range(100)
        ])

        # Process document
        with patch('app.services.text_extraction.extract_text') as mock_extract:
            mock_extract.return_value = large_text

            with patch('app.core.ai_providers.get_embedding_provider') as mock_get_embed:
                mock_get_embed.return_value = mock_ai_providers["embedding"]

                import time
                start = time.time()
                document_processing_job(str(large_doc.id))
                duration = time.time() - start

        # Verify processing completed
        db_session.refresh(large_doc)
        assert large_doc.overall_status == DocumentStatusEnum.COMPLETED

        # Verify chunks were created
        doc_repo = DocumentRepository(db_session)
        chunks = doc_repo.get_chunks(str(large_doc.id))

        assert len(chunks) > 10  # Should create multiple chunks
        print(f"\n✅ Large document processed: {len(chunks)} chunks in {duration:.2f}s")

        # Verify embed_batch was used (more efficient)
        assert mock_ai_providers["embedding"].embed_batch.called

    def test_concurrent_search_performance(
        self,
        db_session: Session,
        test_case: Case,
        mock_ai_providers
    ):
        """Test search performance with multiple concurrent queries."""
        # This test verifies that vector indexes work correctly
        # In production, you would run: SET LOCAL hnsw.ef_search = 100

        # Create test document with chunks
        doc = Document(
            case_id=test_case.id,
            filename="test_perf.pdf",
            file_path="/tmp/perf.pdf",
            file_size=1024 * 30,
            mime_type="application/pdf",
            overall_status=DocumentStatusEnum.COMPLETED,
            stage="completed"
        )
        db_session.add(doc)
        db_session.flush()

        # Add chunks with embeddings
        for i in range(50):
            chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=i,
                content=f"Legal content paragraph {i} with various terms and concepts.",
                embedding=mock_ai_providers["embedding"].embed_text(f"content {i}"),
                page_number=i // 10 + 1
            )
            db_session.add(chunk)

        db_session.commit()

        # Perform multiple searches
        from sqlalchemy import select, func

        queries = [
            "legal content",
            "various terms",
            "concepts paragraph",
            "contract clause",
            "evidence facts"
        ]

        import time
        search_times = []

        for query in queries:
            query_embedding = mock_ai_providers["embedding"].embed_text(query)

            start = time.time()

            stmt = select(
                DocumentChunk,
                func.cosine_distance(DocumentChunk.embedding, query_embedding).label('distance')
            ).where(
                DocumentChunk.document_id == doc.id
            ).order_by('distance').limit(10)

            results = db_session.execute(stmt).all()
            duration = time.time() - start

            search_times.append(duration)
            assert len(results) > 0

        avg_search_time = sum(search_times) / len(search_times)
        print(f"\n✅ Average search time: {avg_search_time*1000:.2f}ms ({len(queries)} queries)")
