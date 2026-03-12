"""
Integration tests for rulebook-driven drafting workflow.

Tests the complete flow from rulebook parsing through research query generation
and draft generation, using real rulebook YAML files.

Phase 4.2 - FR-38 to FR-43 integration testing.
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import List, Dict, Any

from app.persistence.models import (
    Case, DraftSession, Rulebook, Document, DocumentChunk,
    DraftSessionStatusEnum, RulebookStatusEnum
)
from app.services.rulebook import RulebookService
from app.workers.draft_generation import (
    extract_search_queries,
    build_drafting_prompt,
    get_system_message_for_document_type,
    format_document_structure,
    draft_research_job,
    draft_generation_job
)


@pytest.fixture
def affidavit_rulebook_yaml():
    """Load founding affidavit rulebook YAML."""
    yaml_path = "tests/fixtures/rulebooks/affidavit_founding.yaml"
    with open(yaml_path, "r") as f:
        return f.read()


@pytest.fixture
def pleading_rulebook_yaml():
    """Load particulars of claim rulebook YAML."""
    yaml_path = "tests/fixtures/rulebooks/pleading_particulars_of_claim.yaml"
    with open(yaml_path, "r") as f:
        return f.read()


@pytest.fixture
def test_user(user_factory):
    """Create a test user for rulebook operations."""
    return user_factory()


@pytest.fixture
def test_org(organisation_factory):
    """Create a test organisation."""
    return organisation_factory()


@pytest.fixture
def affidavit_rulebook(db_session, affidavit_rulebook_yaml, test_user):
    """Create and publish affidavit rulebook in database."""
    rulebook_service = RulebookService(db_session)

    rulebook = rulebook_service.create_from_yaml(
        source_yaml=affidavit_rulebook_yaml,
        created_by_id=test_user.id,
        auto_publish=True
    )
    db_session.commit()
    return rulebook


@pytest.fixture
def pleading_rulebook(db_session, pleading_rulebook_yaml, test_user):
    """Create and publish pleading rulebook in database."""
    rulebook_service = RulebookService(db_session)

    rulebook = rulebook_service.create_from_yaml(
        source_yaml=pleading_rulebook_yaml,
        created_by_id=test_user.id,
        auto_publish=True
    )
    db_session.commit()
    return rulebook


@pytest.fixture
def affidavit_intake_responses():
    """Sample intake responses for founding affidavit."""
    return {
        "deponent_name": "John Smith",
        "deponent_capacity": "Applicant in person",
        "court_division": "Gauteng Division, Johannesburg",
        "matter_type": "Urgent application",
        "relief_sought": "Interdict preventing the Respondent from selling the property at 123 Main Street",
        "factual_basis": "I am the lawful owner of the property. The Respondent has unlawfully taken possession and threatens to sell it.",
        "urgency_reason": "The property sale is scheduled for 2024-03-15, and I will suffer irreparable harm if the sale proceeds.",
        "respondent_name": "ABC Properties (Pty) Ltd"
    }


@pytest.fixture
def pleading_intake_responses():
    """Sample intake responses for particulars of claim."""
    return {
        "plaintiff_name": "Jane Doe",
        "defendant_name": "XYZ Corporation",
        "claim_type": "Breach of contract",
        "cause_of_action": "The Defendant failed to deliver goods as per written contract dated 2024-01-10, resulting in financial loss.",
        "amount_claimed": "R 250,000.00",
        "interest_claimed": True,
        "interest_rate": "Mora interest at legal rate",
        "costs_claimed": True
    }


class TestRulebookQueryExtraction:
    """Test extraction of research queries from rulebooks."""

    def test_extract_queries_from_affidavit_rulebook(
        self, db_session, affidavit_rulebook, affidavit_intake_responses
    ):
        """Test query extraction with template substitution for affidavit."""
        rulebook_service = RulebookService(db_session)

        queries = extract_search_queries(
            intake_responses=affidavit_intake_responses,
            rulebook=affidavit_rulebook,
            rulebook_service=rulebook_service
        )

        # Should have queries from rulebook templates
        assert len(queries) > 0

        # Check template substitution occurred
        relief_sought = affidavit_intake_responses["relief_sought"]
        assert any(relief_sought[:50] in query for query in queries), \
            "Template substitution should include intake response content"

        # Check default queries present
        assert any("material facts" in query.lower() for query in queries), \
            "Should include material facts query template"

    def test_extract_queries_from_pleading_rulebook(
        self, db_session, pleading_rulebook, pleading_intake_responses
    ):
        """Test query extraction for pleading with defendant name substitution."""
        rulebook_service = RulebookService(db_session)

        queries = extract_search_queries(
            intake_responses=pleading_intake_responses,
            rulebook=pleading_rulebook,
            rulebook_service=rulebook_service
        )

        # Should have queries from rulebook
        assert len(queries) > 0

        # Check defendant name was substituted
        defendant_name = pleading_intake_responses["defendant_name"]
        assert any(defendant_name in query for query in queries), \
            "Defendant name should be substituted in query templates"

        # Check breach evidence query present
        assert any("breach" in query.lower() for query in queries), \
            "Should include breach evidence query template"

    def test_extract_queries_includes_intake_text(
        self, db_session, affidavit_rulebook, affidavit_intake_responses
    ):
        """Test that long intake text responses are included as queries."""
        rulebook_service = RulebookService(db_session)

        queries = extract_search_queries(
            intake_responses=affidavit_intake_responses,
            rulebook=affidavit_rulebook,
            rulebook_service=rulebook_service
        )

        # Factual basis is long text - should be included
        factual_basis = affidavit_intake_responses["factual_basis"]
        assert any(factual_basis[:50] in query for query in queries), \
            "Long intake text should be included as search query"

    def test_extract_queries_limits_to_10(
        self, db_session, affidavit_rulebook
    ):
        """Test that query extraction limits to 10 queries max."""
        rulebook_service = RulebookService(db_session)

        # Create intake with many long text fields
        many_responses = {
            f"field_{i}": f"This is a long text response number {i} " * 10
            for i in range(20)
        }

        queries = extract_search_queries(
            intake_responses=many_responses,
            rulebook=affidavit_rulebook,
            rulebook_service=rulebook_service
        )

        # Should be limited to 10
        assert len(queries) <= 10, "Should limit to 10 queries max"


class TestRulebookDraftingPrompt:
    """Test building drafting prompts from rulebooks."""

    def test_build_prompt_includes_document_structure(
        self, db_session, affidavit_rulebook, affidavit_intake_responses
    ):
        """Test that prompt includes rulebook document structure."""
        research_summary = {
            "profile": {"case_type": "urgent_application"},
            "excerpts": []
        }

        prompt = build_drafting_prompt(
            rulebook=affidavit_rulebook,
            intake_responses=affidavit_intake_responses,
            research_summary=research_summary,
            document_type="affidavit"
        )

        # Check structure sections are present
        assert "INTRODUCTION" in prompt, "Should include INTRODUCTION section"
        assert "BACKGROUND" in prompt, "Should include BACKGROUND section"
        assert "MATERIAL FACTS" in prompt, "Should include MATERIAL FACTS section"
        assert "LEGAL BASIS FOR THE RELIEF" in prompt, "Should include LEGAL BASIS section"
        assert "PRAYER FOR RELIEF" in prompt, "Should include PRAYER section"

    def test_build_prompt_includes_section_requirements(
        self, db_session, affidavit_rulebook, affidavit_intake_responses
    ):
        """Test that prompt includes section requirements (min paragraphs, etc)."""
        research_summary = {"profile": {}, "excerpts": []}

        prompt = build_drafting_prompt(
            rulebook=affidavit_rulebook,
            intake_responses=affidavit_intake_responses,
            research_summary=research_summary,
            document_type="affidavit"
        )

        # Check requirements are mentioned
        assert "at least" in prompt.lower() or "minimum" in prompt.lower(), \
            "Should include paragraph requirements"
        assert "REQUIRED" in prompt or "required" in prompt, \
            "Should mark required sections"

    def test_build_prompt_includes_style_guidance(
        self, db_session, affidavit_rulebook, affidavit_intake_responses
    ):
        """Test that prompt includes style guidance from rulebook."""
        research_summary = {"profile": {}, "excerpts": []}

        prompt = build_drafting_prompt(
            rulebook=affidavit_rulebook,
            intake_responses=affidavit_intake_responses,
            research_summary=research_summary,
            document_type="affidavit"
        )

        # Check style guidance present
        assert "STYLE AND FORMATTING" in prompt or "style" in prompt.lower(), \
            "Should include style guidance section"
        assert "formal" in prompt.lower() or "legal" in prompt.lower(), \
            "Should include legal writing guidance"

    def test_build_prompt_includes_intake_responses(
        self, db_session, pleading_rulebook, pleading_intake_responses
    ):
        """Test that prompt includes intake responses."""
        research_summary = {"profile": {}, "excerpts": []}

        prompt = build_drafting_prompt(
            rulebook=pleading_rulebook,
            intake_responses=pleading_intake_responses,
            research_summary=research_summary,
            document_type="pleading"
        )

        # Check intake data is present
        assert pleading_intake_responses["plaintiff_name"] in prompt, \
            "Should include plaintiff name from intake"
        assert pleading_intake_responses["defendant_name"] in prompt, \
            "Should include defendant name from intake"
        assert pleading_intake_responses["amount_claimed"] in prompt, \
            "Should include claimed amount from intake"

    def test_build_prompt_includes_research_excerpts(
        self, db_session, affidavit_rulebook, affidavit_intake_responses
    ):
        """Test that prompt includes research excerpts."""
        research_summary = {
            "queries_executed": ["test query"],
            "total_excerpts": 2,
            "key_excerpts": [
                {
                    "query": "What are the contract terms?",
                    "content": "The property sale agreement was signed on 2024-01-10.",
                    "document": "agreement.pdf",
                    "document_id": "123",
                    "page": 5,
                    "chunk_index": 0,
                    "similarity": 0.85
                },
                {
                    "query": "What evidence of breach?",
                    "content": "The Respondent took possession unlawfully on 2024-02-15.",
                    "document": "affidavit.pdf",
                    "document_id": "456",
                    "page": 3,
                    "chunk_index": 1,
                    "similarity": 0.82
                }
            ]
        }

        prompt = build_drafting_prompt(
            rulebook=affidavit_rulebook,
            intake_responses=affidavit_intake_responses,
            research_summary=research_summary,
            document_type="affidavit"
        )

        # Check excerpts are included
        assert "sale agreement" in prompt, "Should include first excerpt"
        assert "unlawfully" in prompt, "Should include second excerpt"
        assert "SUPPORTING EVIDENCE" in prompt or "evidence" in prompt.lower(), \
            "Should have evidence section"


class TestRulebookSystemMessage:
    """Test system message selection from rulebooks."""

    def test_get_system_message_from_affidavit_rulebook(
        self, db_session, affidavit_rulebook
    ):
        """Test that system message is extracted from affidavit rulebook."""
        system_message = get_system_message_for_document_type(
            document_type="affidavit",
            rulebook=affidavit_rulebook
        )

        # Check custom system message is used
        assert "South African" in system_message, \
            "Should include South African context"
        assert "litigation attorney" in system_message.lower() or \
               "affidavit" in system_message.lower(), \
            "Should mention affidavit expertise"

    def test_get_system_message_from_pleading_rulebook(
        self, db_session, pleading_rulebook
    ):
        """Test system message for pleading rulebook."""
        system_message = get_system_message_for_document_type(
            document_type="pleading",
            rulebook=pleading_rulebook
        )

        # Check pleading-specific content
        assert "South African" in system_message, \
            "Should include South African context"
        assert "litigator" in system_message.lower() or \
               "pleading" in system_message.lower(), \
            "Should mention pleading expertise"

    def test_get_system_message_fallback_without_rulebook(self):
        """Test that default message is used when no rulebook provided."""
        system_message = get_system_message_for_document_type(
            document_type="affidavit",
            rulebook=None
        )

        # Should return default message
        assert len(system_message) > 0, "Should return default message"
        assert "South African" in system_message, \
            "Default should include South African context"


class TestDocumentStructureFormatting:
    """Test formatting of document structure for LLM prompts."""

    def test_format_structure_includes_all_sections(
        self, db_session, affidavit_rulebook
    ):
        """Test that all sections from rulebook are formatted."""
        structure = affidavit_rulebook.rules_json["document_structure"]

        formatted = format_document_structure(structure)

        # Check all section titles present
        assert "INTRODUCTION" in formatted
        assert "BACKGROUND" in formatted
        assert "MATERIAL FACTS" in formatted
        assert "LEGAL BASIS" in formatted
        assert "PRAYER FOR RELIEF" in formatted

    def test_format_structure_includes_requirements(
        self, db_session, affidavit_rulebook
    ):
        """Test that section requirements are included."""
        structure = affidavit_rulebook.rules_json["document_structure"]

        formatted = format_document_structure(structure)

        # Check requirements mentioned
        assert "REQUIRED" in formatted or "OPTIONAL" in formatted, \
            "Should mark required/optional sections"
        assert "paragraphs" in formatted.lower(), \
            "Should mention paragraph requirements"

    def test_format_structure_includes_guidance(
        self, db_session, pleading_rulebook
    ):
        """Test that prompt guidance is included."""
        structure = pleading_rulebook.rules_json["document_structure"]

        formatted = format_document_structure(structure)

        # Check guidance present
        assert "Guidance:" in formatted or "guidance" in formatted.lower(), \
            "Should include prompt guidance"

    def test_format_structure_numbered(
        self, db_session, affidavit_rulebook
    ):
        """Test that sections are numbered."""
        structure = affidavit_rulebook.rules_json["document_structure"]

        formatted = format_document_structure(structure)

        # Check numbered format
        assert "1." in formatted, "Should have numbered sections"
        assert "2." in formatted, "Should have multiple numbered sections"


class TestEndToEndDraftingWorkflow:
    """Integration tests for complete drafting workflow with rulebooks."""

    @patch("app.workers.draft_generation.get_embedding_provider")
    @patch("app.workers.draft_generation.get_llm_provider")
    def test_draft_research_with_rulebook(
        self,
        mock_llm_provider,
        mock_embedding_provider,
        db_session,
        test_org,
        test_user,
        affidavit_rulebook,
        affidavit_intake_responses
    ):
        """Test draft research job using rulebook query templates."""
        # Create case and draft session
        test_case = Case(
            organisation_id=test_org.id,
            title="Test Urgent Application",
            owner_id=test_user.id
        )
        db_session.add(test_case)
        db_session.flush()

        draft = DraftSession(
            case_id=test_case.id,
            title="Test Founding Affidavit",
            document_type="affidavit",
            rulebook_id=affidavit_rulebook.id,
            intake_responses=affidavit_intake_responses,
            status=DraftSessionStatusEnum.INITIALIZING,
            user_id=test_user.id
        )
        db_session.add(draft)
        db_session.flush()

        # Create document and chunks
        doc = Document(
            case_id=test_case.id,
            organisation_id=test_org.id,
            filename="agreement.pdf",
            semantic_role="contract",
            uploaded_by_id=test_user.id
        )
        db_session.add(doc)
        db_session.flush()

        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=0,
            text="The sale agreement was executed on 2024-01-10 between the parties.",
            page_number=1,
            embedding=[0.1] * 1536  # Mock embedding
        )
        db_session.add(chunk)
        db_session.commit()

        # Mock embedding provider
        mock_embed = MagicMock()
        mock_embed.embed_query.return_value = [0.1] * 1536
        mock_embedding_provider.return_value = mock_embed

        # Mock LLM provider for case profiling
        mock_llm = MagicMock()
        mock_llm.generate.return_value = "Case Type: Urgent application for interdict"
        mock_llm_provider.return_value = mock_llm

        # Run research job
        draft_research_job(draft.id)

        # Verify draft updated
        db_session.refresh(draft)
        assert draft.research_summary is not None, "Research summary should be generated"
        # research_summary is now JSONB, use directly as dict
        assert "key_excerpts" in draft.research_summary, "Should have key_excerpts"
        assert draft.status == DraftSessionStatusEnum.DRAFTING, \
            "Status should be drafting after research completes"

    @patch("app.workers.draft_generation.get_llm_provider")
    def test_draft_generation_with_rulebook(
        self,
        mock_llm_provider,
        db_session,
        test_org,
        test_user,
        pleading_rulebook,
        pleading_intake_responses
    ):
        """Test draft generation job using rulebook templates and structure."""
        # Create case and draft session
        test_case = Case(
            organisation_id=test_org.id,
            title="Test Breach of Contract",
            owner_id=test_user.id
        )
        db_session.add(test_case)
        db_session.flush()

        research_summary = {
            "queries_executed": ["What are the contract terms?"],
            "total_excerpts": 1,
            "key_excerpts": [
                {
                    "query": "What are the contract terms?",
                    "content": "Contract clause 5.2 required delivery by 2024-02-01.",
                    "document": "contract.pdf",
                    "document_id": "123",
                    "page": 3,
                    "chunk_index": 0,
                    "similarity": 0.88
                }
            ]
        }

        draft = DraftSession(
            case_id=test_case.id,
            title="Test Particulars of Claim",
            document_type="pleading",
            rulebook_id=pleading_rulebook.id,
            intake_responses=pleading_intake_responses,
            research_summary=research_summary,  # Now JSONB, store as dict
            status=DraftSessionStatusEnum.DRAFTING,
            user_id=test_user.id
        )
        db_session.add(draft)
        db_session.commit()

        # Mock LLM provider
        mock_llm = MagicMock()
        mock_generated_content = """THE PARTIES

1. The Plaintiff is Jane Doe, an adult female...

MATERIAL ALLEGATIONS

2. On or about 10 January 2024, the Plaintiff and Defendant entered into a written agreement...
3. In terms of clause 5.2, the Defendant was required to deliver goods by 1 February 2024 [1].
4. The Defendant failed to deliver the goods...

PRAYER FOR RELIEF

WHEREFORE Plaintiff prays for judgment against Defendant for:
1. Payment of R 250,000.00
2. Interest at the legal rate
3. Costs of suit
"""
        mock_llm.generate.return_value = mock_generated_content
        mock_llm_provider.return_value = mock_llm

        # Run generation job
        draft_generation_job(draft.id)

        # Verify draft updated
        db_session.refresh(draft)
        # Draft doc should be generated and stored
        assert draft.draft_doc is not None, "Draft doc should be generated"
        assert draft.status == DraftSessionStatusEnum.REVIEW, \
            "Status should be review after generation completes"

        # Verify LLM was called with rulebook configuration
        mock_llm.generate.assert_called_once()
        call_kwargs = mock_llm.generate.call_args[1]

        # Check temperature from rulebook (0.4 for pleading)
        assert call_kwargs["temperature"] == 0.4, \
            "Should use temperature from rulebook"

        # Check max_tokens from rulebook (5000 for pleading)
        assert call_kwargs["max_tokens"] == 5000, \
            "Should use max_tokens from rulebook"

        # Check system message from rulebook
        assert "South African" in call_kwargs["system_message"], \
            "Should use system message from rulebook"

    def test_version_selection_workflow(
        self, db_session, affidavit_rulebook_yaml, test_user
    ):
        """Test that latest published rulebook is selected for new drafts."""
        rulebook_service = RulebookService(db_session)

        # Create version 1.0.0 and publish it
        rulebook_v1 = rulebook_service.create_from_yaml(
            source_yaml=affidavit_rulebook_yaml,
            created_by_id=test_user.id,
            auto_publish=True  # Publish v1.0.0
        )
        db_session.commit()

        # Create version 2.0.0 but keep as draft
        yaml_v2 = affidavit_rulebook_yaml.replace("1.0.0", "2.0.0")
        rulebook_v2 = rulebook_service.create_from_yaml(
            source_yaml=yaml_v2,
            created_by_id=test_user.id,
            auto_publish=False  # Keep as draft
        )
        db_session.commit()

        # Get latest published
        latest = rulebook_service.get_latest_published(
            document_type="affidavit",
            jurisdiction="south_africa_high_court"
        )

        # Should return 1.0.0 (published), not 2.0.0 (draft)
        assert latest is not None, "Should find published rulebook"
        assert latest.version == "1.0.0", \
            "Should return published version, not draft"

        # Now publish 2.0.0
        rulebook_service.publish_rulebook(rulebook_v2.id)
        db_session.commit()

        # Get latest published again
        latest = rulebook_service.get_latest_published(
            document_type="affidavit",
            jurisdiction="south_africa_high_court"
        )

        # Should now return 2.0.0
        assert latest.version == "2.0.0", \
            "Should return latest published version after publishing"
