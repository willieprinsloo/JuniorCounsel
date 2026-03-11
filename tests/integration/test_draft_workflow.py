"""
Integration tests for draft generation workflow.

Tests the complete drafting pipeline:
1. Draft session creation with intake
2. RAG research (multi-query vector search)
3. Draft generation with LLM
4. Citation extraction and validation
5. Status transitions
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from typing import List, Dict, Any

from sqlalchemy.orm import Session

from app.persistence.models import (
    DraftSession,
    DraftSessionStatusEnum,
    Document,
    DocumentChunk,
    DocumentStatusEnum,
    Rulebook,
    Case,
    Organisation,
    User
)
from app.persistence.repositories import (
    DraftSessionRepository,
    RulebookRepository,
    DocumentRepository
)
from app.workers.draft_generation import (
    draft_research_job,
    draft_generation_job,
    extract_search_queries,
    build_drafting_prompt,
    extract_citations_from_content,
    get_system_message_for_document_type
)


@pytest.fixture
def test_organisation(db_session: Session):
    """Create test organisation."""
    org = Organisation(
        name="Test Legal Practice",
        email="test@practice.co.za",
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
        email="advocate@practice.co.za",
        password_hash="hashed_password",
        first_name="Test",
        last_name="Advocate",
        organisation_id=test_organisation.id,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_case(db_session: Session, test_organisation: Organisation, test_user: User):
    """Create test case with processed documents."""
    case = Case(
        title="Smith v Jones - Breach of Contract",
        case_number="2025/54321",
        organisation_id=test_organisation.id,
        created_by_id=test_user.id,
        description="Contract dispute case"
    )
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)
    return case


@pytest.fixture
def test_documents(db_session: Session, test_case: Case, mock_embedding_provider):
    """Create test documents with chunks and embeddings."""
    documents = []

    # Document 1: Employment contract
    doc1 = Document(
        case_id=test_case.id,
        filename="employment_contract.pdf",
        file_path="/tmp/contract.pdf",
        file_size=1024 * 40,
        mime_type="application/pdf",
        overall_status=DocumentStatusEnum.COMPLETED,
        stage="completed",
        document_type="contract",
        extracted_text="Employment contract between ABC Ltd and John Smith. Salary: R50,000 per month. Termination clause applies."
    )
    db_session.add(doc1)
    db_session.flush()

    # Create chunks for doc1
    chunk1 = DocumentChunk(
        document_id=doc1.id,
        chunk_index=0,
        content="Employment contract between ABC Ltd and John Smith. Salary: R50,000 per month.",
        embedding=mock_embedding_provider.embed_text("Employment contract between ABC Ltd and John Smith"),
        page_number=1,
        char_start=0,
        char_end=100
    )
    db_session.add(chunk1)

    chunk2 = DocumentChunk(
        document_id=doc1.id,
        chunk_index=1,
        content="Termination clause: Either party may terminate with 30 days notice.",
        embedding=mock_embedding_provider.embed_text("Termination clause notice period"),
        page_number=2,
        char_start=100,
        char_end=180
    )
    db_session.add(chunk2)

    documents.append(doc1)

    # Document 2: Correspondence
    doc2 = Document(
        case_id=test_case.id,
        filename="letter_of_demand.pdf",
        file_path="/tmp/demand.pdf",
        file_size=1024 * 20,
        mime_type="application/pdf",
        overall_status=DocumentStatusEnum.COMPLETED,
        stage="completed",
        document_type="correspondence",
        extracted_text="Letter of demand sent on 15 January 2025 requesting payment of R50,000."
    )
    db_session.add(doc2)
    db_session.flush()

    chunk3 = DocumentChunk(
        document_id=doc2.id,
        chunk_index=0,
        content="Letter of demand sent on 15 January 2025 requesting payment of R50,000.",
        embedding=mock_embedding_provider.embed_text("Letter of demand payment"),
        page_number=1,
        char_start=0,
        char_end=75
    )
    db_session.add(chunk3)

    documents.append(doc2)

    db_session.commit()
    for doc in documents:
        db_session.refresh(doc)

    return documents


@pytest.fixture
def test_rulebook(db_session: Session, test_organisation: Organisation):
    """Create test rulebook for affidavits."""
    rulebook = Rulebook(
        name="High Court Affidavit Standard",
        document_type="affidavit",
        version="1.0",
        organisation_id=test_organisation.id,
        source_yaml="""
document_type: affidavit
structure:
  - name: Introduction
    description: Deponent identification and oath
  - name: Background
    description: Relevant facts and context
  - name: Facts in Support
    description: Numbered paragraphs with evidence
  - name: Conclusion
    description: Prayer for relief
""",
        rules_json={
            "document_type": "affidavit",
            "document_structure": [
                {"name": "Introduction", "description": "Deponent identification and oath"},
                {"name": "Background", "description": "Relevant facts and context"},
                {"name": "Facts in Support", "description": "Numbered paragraphs with evidence"},
                {"name": "Conclusion", "description": "Prayer for relief"}
            ],
            "research_queries": [
                "employment contract terms",
                "termination provisions"
            ]
        },
        is_active=True
    )
    db_session.add(rulebook)
    db_session.commit()
    db_session.refresh(rulebook)
    return rulebook


@pytest.fixture
def test_draft_session(
    db_session: Session,
    test_case: Case,
    test_user: User,
    test_rulebook: Rulebook
):
    """Create test draft session."""
    draft = DraftSession(
        case_id=test_case.id,
        created_by_id=test_user.id,
        rulebook_id=test_rulebook.id,
        document_type="affidavit",
        title="Affidavit in Support of Application",
        status=DraftSessionStatusEnum.INTAKE,
        intake_responses={
            "deponent_name": "John Smith",
            "deponent_role": "Applicant",
            "key_facts": "I entered into an employment contract with ABC Ltd on 1 January 2024. My salary was R50,000 per month. The company terminated my employment without notice.",
            "relief_sought": "Compensation for wrongful termination"
        }
    )
    db_session.add(draft)
    db_session.commit()
    db_session.refresh(draft)
    return draft


@pytest.fixture
def mock_embedding_provider():
    """Mock embedding provider."""
    provider = Mock()
    provider.model = "text-embedding-3-small"
    provider.dimension = 1536

    def mock_embed_text(text: str):
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        return [float((hash_val + i) % 100) / 100.0 for i in range(1536)]

    provider.embed_text = Mock(side_effect=mock_embed_text)

    def mock_embed_batch(texts, batch_size=100):
        return [mock_embed_text(text) for text in texts]

    provider.embed_batch = Mock(side_effect=mock_embed_batch)

    return provider


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider."""
    provider = Mock()
    provider.model = "gpt-4"

    def mock_generate(prompt: str, system_message: str = None, temperature: float = 0.7, max_tokens: int = 2000):
        return """AFFIDAVIT

I, the undersigned, JOHN SMITH, do hereby make oath and state:

INTRODUCTION
1. I am the applicant in this matter [1].
2. The facts deposed to herein are within my personal knowledge.

BACKGROUND
3. I was employed by ABC Ltd under an employment contract dated 1 January 2024 [1].
4. My monthly salary was R50,000 [1].

FACTS IN SUPPORT
5. The employment contract contained a termination clause requiring 30 days notice [2].
6. ABC Ltd terminated my employment without proper notice.
7. A letter of demand was sent on 15 January 2025 [3].

CONCLUSION
8. I respectfully request that this Honourable Court grant the relief sought."""

    provider.generate = Mock(side_effect=mock_generate)

    return provider


class TestDraftResearchWorkflow:
    """Integration tests for draft research job."""

    def test_research_job_complete_workflow(
        self,
        db_session: Session,
        test_draft_session: DraftSession,
        test_documents: List[Document],
        mock_embedding_provider
    ):
        """Test complete research workflow with RAG search."""
        with patch('app.core.ai_providers.get_embedding_provider') as mock_get_provider:
            mock_get_provider.return_value = mock_embedding_provider

            with patch('app.core.queue.enqueue_draft_generation') as mock_enqueue:
                # Run research job
                draft_research_job(str(test_draft_session.id))

        # Verify status updated
        db_session.refresh(test_draft_session)
        assert test_draft_session.status == DraftSessionStatusEnum.DRAFTING

        # Verify research summary was created
        assert test_draft_session.research_summary is not None
        summary = test_draft_session.research_summary

        assert "queries_executed" in summary
        assert "total_excerpts" in summary
        assert "key_excerpts" in summary
        assert "relevant_documents" in summary

        # Verify queries were executed
        assert len(summary["queries_executed"]) > 0

        # Verify excerpts were found
        assert summary["total_excerpts"] > 0
        assert len(summary["key_excerpts"]) > 0

        # Verify excerpt structure
        first_excerpt = summary["key_excerpts"][0]
        assert "query" in first_excerpt
        assert "content" in first_excerpt
        assert "document" in first_excerpt
        assert "page" in first_excerpt
        assert "similarity" in first_excerpt

        # Verify generation was auto-enqueued
        mock_enqueue.assert_called_once_with(str(test_draft_session.id))

    def test_extract_search_queries(self):
        """Test search query extraction from intake responses."""
        intake_responses = {
            "deponent_name": "John Smith",  # Short, won't be used
            "key_facts": "The contract was signed on 1 January 2024 and stipulated a monthly salary of R50,000.",
            "issues": ["Wrongful termination", "Breach of notice period"],
            "short_value": "Hi",  # Too short
            "non_string": 123  # Not a string
        }

        rulebook_rules = {
            "research_queries": ["employment law precedents", "termination clause enforcement"]
        }

        queries = extract_search_queries(intake_responses, rulebook_rules)

        # Verify meaningful queries were extracted
        assert len(queries) > 0
        assert len(queries) <= 10  # Max limit

        # Verify long text was included
        assert any("contract was signed" in q for q in queries)

        # Verify rulebook queries were added
        assert "employment law precedents" in queries or "termination clause enforcement" in queries

    def test_research_with_no_documents(
        self,
        db_session: Session,
        test_draft_session: DraftSession,
        mock_embedding_provider
    ):
        """Test research job when no documents are available."""
        # Delete all document chunks
        db_session.query(DocumentChunk).delete()
        db_session.commit()

        with patch('app.core.ai_providers.get_embedding_provider') as mock_get_provider:
            mock_get_provider.return_value = mock_embedding_provider

            with patch('app.core.queue.enqueue_draft_generation') as mock_enqueue:
                draft_research_job(str(test_draft_session.id))

        # Verify status still updated (empty research is valid)
        db_session.refresh(test_draft_session)
        assert test_draft_session.status == DraftSessionStatusEnum.DRAFTING

        # Verify research summary created but with no excerpts
        assert test_draft_session.research_summary is not None
        assert test_draft_session.research_summary["total_excerpts"] == 0

    def test_research_deduplication(
        self,
        db_session: Session,
        test_draft_session: DraftSession,
        test_documents: List[Document],
        mock_embedding_provider
    ):
        """Test that research deduplicates chunks correctly."""
        # Add duplicate query to intake to trigger multiple hits
        test_draft_session.intake_responses["duplicate_query"] = "employment contract"
        test_draft_session.intake_responses["duplicate_query_2"] = "employment contract"
        db_session.commit()

        with patch('app.core.ai_providers.get_embedding_provider') as mock_get_provider:
            mock_get_provider.return_value = mock_embedding_provider

            with patch('app.core.queue.enqueue_draft_generation'):
                draft_research_job(str(test_draft_session.id))

        db_session.refresh(test_draft_session)
        excerpts = test_draft_session.research_summary["key_excerpts"]

        # Verify no duplicate (document_id, chunk_index) pairs
        seen = set()
        for excerpt in excerpts:
            key = (excerpt["document_id"], excerpt["chunk_index"])
            assert key not in seen, "Duplicate chunk found"
            seen.add(key)


class TestDraftGenerationWorkflow:
    """Integration tests for draft generation job."""

    def test_generation_job_complete_workflow(
        self,
        db_session: Session,
        test_draft_session: DraftSession,
        test_documents: List[Document],
        test_rulebook: Rulebook,
        mock_llm_provider
    ):
        """Test complete generation workflow with LLM."""
        # Set up research summary (simulating completed research)
        test_draft_session.status = DraftSessionStatusEnum.DRAFTING
        test_draft_session.research_summary = {
            "queries_executed": ["employment contract", "termination"],
            "total_excerpts": 3,
            "key_excerpts": [
                {
                    "query": "employment contract",
                    "content": "Employment contract between ABC Ltd and John Smith. Salary: R50,000.",
                    "document": "employment_contract.pdf",
                    "document_id": str(test_documents[0].id),
                    "page": 1,
                    "chunk_index": 0,
                    "similarity": 0.92
                },
                {
                    "query": "termination",
                    "content": "Termination clause: 30 days notice required.",
                    "document": "employment_contract.pdf",
                    "document_id": str(test_documents[0].id),
                    "page": 2,
                    "chunk_index": 1,
                    "similarity": 0.88
                },
                {
                    "query": "payment demand",
                    "content": "Letter of demand sent on 15 January 2025.",
                    "document": "letter_of_demand.pdf",
                    "document_id": str(test_documents[1].id),
                    "page": 1,
                    "chunk_index": 0,
                    "similarity": 0.85
                }
            ]
        }
        db_session.commit()

        with patch('app.core.ai_providers.get_llm_provider') as mock_get_provider:
            mock_get_provider.return_value = mock_llm_provider

            # Run generation job
            draft_generation_job(str(test_draft_session.id))

        # Verify status updated to review
        db_session.refresh(test_draft_session)
        assert test_draft_session.status == DraftSessionStatusEnum.REVIEW

        # Verify content was generated
        assert test_draft_session.generated_content is not None
        assert len(test_draft_session.generated_content) > 0
        assert "AFFIDAVIT" in test_draft_session.generated_content

        # Verify metadata was saved
        assert test_draft_session.metadata is not None
        metadata = test_draft_session.metadata

        assert "citations" in metadata
        assert "model_used" in metadata
        assert "generated_at" in metadata

        # Verify citations were extracted
        citations = metadata["citations"]
        assert len(citations) > 0

        # Verify citation structure
        first_citation = citations[0]
        assert "marker" in first_citation
        assert "document" in first_citation
        assert "page" in first_citation
        assert "content" in first_citation

    def test_build_drafting_prompt(
        self,
        test_rulebook: Rulebook,
        test_draft_session: DraftSession
    ):
        """Test drafting prompt construction."""
        research_summary = {
            "key_excerpts": [
                {
                    "content": "Employment contract with R50,000 salary.",
                    "document": "contract.pdf",
                    "page": 1
                },
                {
                    "content": "Termination requires 30 days notice.",
                    "document": "contract.pdf",
                    "page": 2
                }
            ]
        }

        prompt = build_drafting_prompt(
            rulebook=test_rulebook,
            intake_responses=test_draft_session.intake_responses,
            research_summary=research_summary,
            document_type="affidavit"
        )

        # Verify prompt contains all required sections
        assert "affidavit" in prompt.lower()
        assert "Document Structure" in prompt
        assert "Facts and Information" in prompt
        assert "Supporting Evidence" in prompt
        assert "Instructions" in prompt

        # Verify intake data is included
        assert "John Smith" in prompt

        # Verify research excerpts are included with citations
        assert "[1]" in prompt
        assert "[2]" in prompt
        assert "Employment contract" in prompt or "employment contract" in prompt.lower()

        # Verify document structure is included
        assert "Introduction" in prompt or "Background" in prompt

    def test_system_message_selection(self):
        """Test document-type-specific system messages."""
        affidavit_msg = get_system_message_for_document_type("affidavit")
        assert "affidavit" in affidavit_msg.lower()
        assert "High Court" in affidavit_msg or "court" in affidavit_msg.lower()

        pleading_msg = get_system_message_for_document_type("pleading")
        assert "pleading" in pleading_msg.lower()

        heads_msg = get_system_message_for_document_type("heads_of_argument")
        assert "heads of argument" in heads_msg.lower() or "advocate" in heads_msg.lower()

        default_msg = get_system_message_for_document_type("unknown_type")
        assert "legal" in default_msg.lower()

    def test_citation_extraction(self):
        """Test citation marker extraction from generated content."""
        generated_content = """
        AFFIDAVIT

        1. I am employed by ABC Ltd [1].
        2. My salary is R50,000 per month [1].
        3. The contract requires 30 days notice [2].
        4. A demand letter was sent [3].
        5. I reference item [1] again here.
        """

        research_summary = {
            "key_excerpts": [
                {
                    "content": "Employment contract with ABC Ltd, salary R50,000.",
                    "document": "contract.pdf",
                    "page": 1,
                    "similarity": 0.92
                },
                {
                    "content": "Termination clause: 30 days notice.",
                    "document": "contract.pdf",
                    "page": 2,
                    "similarity": 0.88
                },
                {
                    "content": "Demand letter dated 15 January 2025.",
                    "document": "demand.pdf",
                    "page": 1,
                    "similarity": 0.85
                }
            ]
        }

        citations = extract_citations_from_content(generated_content, research_summary)

        # Verify citations were extracted
        assert len(citations) == 3  # [1], [2], [3]

        # Verify citation structure
        markers = [c["marker"] for c in citations]
        assert "[1]" in markers
        assert "[2]" in markers
        assert "[3]" in markers

        # Verify citation details
        citation_1 = next(c for c in citations if c["marker"] == "[1]")
        assert citation_1["document"] == "contract.pdf"
        assert citation_1["page"] == 1

    def test_generation_error_handling(
        self,
        db_session: Session,
        test_draft_session: DraftSession,
        test_rulebook: Rulebook
    ):
        """Test error handling during generation."""
        # Set up for generation
        test_draft_session.status = DraftSessionStatusEnum.DRAFTING
        test_draft_session.research_summary = {"key_excerpts": []}
        db_session.commit()

        with patch('app.core.ai_providers.get_llm_provider') as mock_get_provider:
            # Simulate LLM failure
            mock_provider = Mock()
            mock_provider.generate = Mock(side_effect=Exception("LLM API error"))
            mock_get_provider.return_value = mock_provider

            # Run generation job (should catch error)
            with pytest.raises(Exception, match="LLM API error"):
                draft_generation_job(str(test_draft_session.id))

        # Verify status updated to failed
        db_session.refresh(test_draft_session)
        assert test_draft_session.status == DraftSessionStatusEnum.FAILED
        assert "Generation failed" in test_draft_session.error_message


class TestEndToEndDraftWorkflow:
    """End-to-end integration tests for complete draft workflow."""

    def test_complete_workflow_research_to_generation(
        self,
        db_session: Session,
        test_draft_session: DraftSession,
        test_documents: List[Document],
        test_rulebook: Rulebook,
        mock_embedding_provider,
        mock_llm_provider
    ):
        """Test complete workflow from research through generation."""
        # Start with intake status
        assert test_draft_session.status == DraftSessionStatusEnum.INTAKE

        # Step 1: Run research
        with patch('app.core.ai_providers.get_embedding_provider') as mock_get_embed:
            mock_get_embed.return_value = mock_embedding_provider

            with patch('app.core.queue.enqueue_draft_generation'):
                draft_research_job(str(test_draft_session.id))

        db_session.refresh(test_draft_session)
        assert test_draft_session.status == DraftSessionStatusEnum.DRAFTING
        assert test_draft_session.research_summary is not None

        # Step 2: Run generation
        with patch('app.core.ai_providers.get_llm_provider') as mock_get_llm:
            mock_get_llm.return_value = mock_llm_provider

            draft_generation_job(str(test_draft_session.id))

        # Verify final state
        db_session.refresh(test_draft_session)
        assert test_draft_session.status == DraftSessionStatusEnum.REVIEW
        assert test_draft_session.generated_content is not None
        assert test_draft_session.metadata is not None
        assert len(test_draft_session.metadata["citations"]) > 0
