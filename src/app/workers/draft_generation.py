"""
Draft generation worker.

Handles the drafting workflow:
1. RAG research (semantic search for relevant case content)
2. LLM-based draft generation with citations
3. Citation extraction and validation
"""
import logging
import re
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.core.db import SessionLocal
from app.core.ai_providers import get_embedding_provider, get_llm_provider
from app.persistence.models import (
    DraftSessionStatusEnum,
    DocumentChunk,
    Document,
    DocumentStatusEnum
)
from app.persistence.repositories import DraftSessionRepository, RulebookRepository
from app.services.rulebook import RulebookService

logger = logging.getLogger(__name__)


def draft_research_job(draft_session_id: str):
    """
    Perform RAG research for a draft session.

    Searches case documents for relevant excerpts based on:
    - Intake responses (facts, issues, parties)
    - Document type requirements from rulebook
    - Semantic similarity

    Args:
        draft_session_id: DraftSession ID (UUID)

    Raises:
        Exception: If research fails (will be retried by RQ)
    """
    db: Optional[Session] = None
    try:
        db = SessionLocal()
        draft_repo = DraftSessionRepository(db)
        rulebook_repo = RulebookRepository(db)

        # Get draft session
        draft = draft_repo.get_by_id(draft_session_id)
        if not draft:
            raise ValueError(f"DraftSession {draft_session_id} not found")

        logger.info(f"Starting research for draft {draft_session_id}: {draft.title}")

        # Get rulebook for research guidance
        rulebook = rulebook_repo.get_by_id(draft.rulebook_id)
        if not rulebook:
            raise ValueError(f"Rulebook {draft.rulebook_id} not found")

        # Update status
        draft.status = DraftSessionStatusEnum.RESEARCH
        db.flush()
        db.commit()

        # Extract search queries using RulebookService
        rulebook_service = RulebookService(db)
        queries = extract_search_queries(
            draft.intake_responses,
            rulebook,
            rulebook_service
        )
        logger.info(f"[{draft_session_id}] Extracted {len(queries)} search queries")

        # Perform RAG searches
        all_excerpts = []
        embedding_provider = get_embedding_provider()

        for query in queries:
            try:
                # Generate query embedding
                query_embedding = embedding_provider.embed_text(query)

                # Search document chunks using pgvector
                stmt = select(
                    DocumentChunk,
                    Document,
                    func.cosine_distance(DocumentChunk.embedding, query_embedding).label('distance')
                ).join(
                    Document, DocumentChunk.document_id == Document.id
                ).where(
                    Document.case_id == draft.case_id,
                    Document.overall_status == DocumentStatusEnum.COMPLETED
                ).order_by('distance').limit(10)

                results = db.execute(stmt).all()

                for chunk, document, distance in results:
                    similarity = 1 - distance
                    if similarity >= 0.7:  # Similarity threshold
                        all_excerpts.append({
                            "query": query,
                            "content": chunk.content,
                            "document": document.filename,
                            "document_id": str(document.id),
                            "page": chunk.page_number,
                            "chunk_index": chunk.chunk_index,
                            "similarity": round(similarity, 4)
                        })

            except Exception as e:
                logger.warning(f"[{draft_session_id}] Query '{query}' failed: {e}")
                continue

        # Sort by similarity and deduplicate
        all_excerpts.sort(key=lambda x: x["similarity"], reverse=True)
        unique_excerpts = []
        seen_chunks = set()

        for excerpt in all_excerpts:
            chunk_key = (excerpt["document_id"], excerpt["chunk_index"])
            if chunk_key not in seen_chunks:
                unique_excerpts.append(excerpt)
                seen_chunks.add(chunk_key)
                if len(unique_excerpts) >= 20:  # Limit to top 20
                    break

        # Build research summary
        research_summary = {
            "queries_executed": queries,
            "total_excerpts": len(unique_excerpts),
            "relevant_documents": list(set([e["document"] for e in unique_excerpts])),
            "key_excerpts": unique_excerpts,
            "generated_at": datetime.utcnow().isoformat()
        }

        draft.research_summary = research_summary
        draft.status = DraftSessionStatusEnum.DRAFTING
        db.flush()
        db.commit()

        logger.info(f"[{draft_session_id}] Research completed: {len(unique_excerpts)} excerpts found")

        # Auto-trigger draft generation
        from app.core.queue import enqueue_draft_generation
        try:
            enqueue_draft_generation(draft_session_id)
            logger.info(f"[{draft_session_id}] Enqueued draft generation job")
        except Exception as e:
            logger.warning(f"[{draft_session_id}] Failed to enqueue generation: {e}")

    except Exception as e:
        logger.error(f"[{draft_session_id}] Research failed: {e}", exc_info=True)

        if db:
            try:
                draft_repo = DraftSessionRepository(db)
                draft_repo.update_status(
                    draft_session_id=draft_session_id,
                    status=DraftSessionStatusEnum.FAILED,
                    error_message=f"Research failed: {str(e)}"
                )
                db.commit()
            except Exception as update_error:
                logger.error(f"Failed to update error status: {update_error}")

        raise

    finally:
        if db:
            db.close()


def draft_generation_job(draft_session_id: str):
    """
    Generate a draft document using LLM.

    Uses:
    - Rulebook template and structure
    - Research summary (relevant excerpts)
    - Intake responses (facts, parties, etc.)
    - Document type conventions

    Args:
        draft_session_id: DraftSession ID (UUID)

    Raises:
        Exception: If generation fails (will be retried by RQ)
    """
    db: Optional[Session] = None
    try:
        db = SessionLocal()
        draft_repo = DraftSessionRepository(db)
        rulebook_repo = RulebookRepository(db)

        # Get draft session
        draft = draft_repo.get_by_id(draft_session_id)
        if not draft:
            raise ValueError(f"DraftSession {draft_session_id} not found")

        logger.info(f"Starting generation for draft {draft_session_id}: {draft.title}")

        # Get rulebook
        rulebook = rulebook_repo.get_by_id(draft.rulebook_id)
        if not rulebook:
            raise ValueError(f"Rulebook {draft.rulebook_id} not found")

        # Ensure we're in drafting status
        if draft.status != DraftSessionStatusEnum.DRAFTING:
            raise ValueError(f"Draft {draft_session_id} not in drafting status (current: {draft.status})")

        # Build drafting prompt
        prompt = build_drafting_prompt(
            rulebook=rulebook,
            intake_responses=draft.intake_responses,
            research_summary=draft.research_summary,
            document_type=draft.document_type
        )

        # Get LLM configuration from rulebook
        drafting_config = rulebook.rules_json.get("drafting_prompt", {})
        temperature = drafting_config.get("temperature", 0.5)
        max_tokens = drafting_config.get("max_tokens", 4000)

        # Generate draft with LLM
        llm_provider = get_llm_provider()
        generated_content = llm_provider.generate(
            prompt=prompt,
            system_message=get_system_message_for_document_type(draft.document_type, rulebook),
            temperature=temperature,
            max_tokens=max_tokens
        )

        logger.info(f"[{draft_session_id}] Generated {len(generated_content)} chars")

        # Extract citations from generated content
        citations = extract_citations_from_content(generated_content, draft.research_summary)

        # Save draft
        draft.generated_content = generated_content
        draft.metadata = {
            "citations": citations,
            "model_used": llm_provider.model,
            "generated_at": datetime.utcnow().isoformat(),
            "excerpt_count": len(draft.research_summary.get("key_excerpts", []))
        }
        draft.status = DraftSessionStatusEnum.REVIEW
        db.flush()
        db.commit()

        logger.info(f"[{draft_session_id}] Generation completed: {len(citations)} citations")

        # TODO: Emit event for notification
        # emit_event('draft.ready', draft_session_id=draft_session_id)

    except Exception as e:
        logger.error(f"[{draft_session_id}] Generation failed: {e}", exc_info=True)

        if db:
            try:
                draft_repo = DraftSessionRepository(db)
                draft_repo.update_status(
                    draft_session_id=draft_session_id,
                    status=DraftSessionStatusEnum.FAILED,
                    error_message=f"Generation failed: {str(e)}"
                )
                db.commit()
            except Exception as update_error:
                logger.error(f"Failed to update error status: {update_error}")

        raise

    finally:
        if db:
            db.close()


def extract_search_queries(
    intake_responses: Dict[str, Any],
    rulebook: Any,
    rulebook_service: RulebookService
) -> List[str]:
    """
    Generate search queries from intake responses and rulebook templates.

    Uses RulebookService to:
    1. Get research query templates from rulebook
    2. Substitute {placeholders} with intake answers
    3. Add meaningful text from intake responses

    Args:
        intake_responses: User's answers to intake questions
        rulebook: Rulebook model with rules_json
        rulebook_service: RulebookService instance for template substitution

    Returns:
        List of search queries
    """
    queries = []

    # Get research queries from rulebook with template substitution
    rulebook_queries = rulebook_service.get_research_queries(
        rulebook.id,
        intake_responses
    )
    queries.extend(rulebook_queries)

    # Extract key facts/issues from intake as additional queries
    for key, value in intake_responses.items():
        if isinstance(value, str) and len(value) > 20:
            # Use meaningful text as search query
            queries.append(value[:500])  # Limit to 500 chars
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and len(item) > 20:
                    queries.append(item[:500])

    # Limit to 10 queries max
    return queries[:10]


def build_drafting_prompt(
    rulebook: Any,
    intake_responses: Dict[str, Any],
    research_summary: Dict[str, Any],
    document_type: str
) -> str:
    """
    Build LLM prompt for draft generation using rulebook templates.

    Uses rulebook's:
    - document_structure: Section titles, descriptions, prompt_guidance
    - drafting_prompt.style_guidance: Style instructions
    - Custom fields and templates

    Args:
        rulebook: Rulebook with rules_json containing templates
        intake_responses: User's intake answers
        research_summary: RAG research results
        document_type: Type of document to generate

    Returns:
        Complete prompt for LLM
    """
    rules = rulebook.rules_json or {}

    # Extract document structure from rulebook
    structure = rules.get("document_structure", [])
    structure_text = format_document_structure(structure)

    # Extract style guidance from drafting_prompt
    drafting_config = rules.get("drafting_prompt", {})
    style_guidance = drafting_config.get("style_guidance", "")

    # Format intake responses in readable format
    intake_lines = []
    for k, v in intake_responses.items():
        if isinstance(v, (list, dict)):
            intake_lines.append(f"- {k}: {str(v)[:200]}")
        else:
            intake_lines.append(f"- {k}: {v}")
    intake_text = "\n".join(intake_lines)

    # Format research excerpts with citations
    excerpts = research_summary.get("key_excerpts", [])[:20]  # Use up to 20 excerpts
    excerpts_text = ""
    for i, excerpt in enumerate(excerpts):
        content = excerpt['content'][:500]  # Limit excerpt length
        doc_name = excerpt['document']
        page = excerpt.get('page', 'N/A')
        excerpts_text += f"[{i+1}] {content}\n    (Source: {doc_name}, Page {page})\n\n"

    # Build comprehensive prompt
    prompt = f"""You are drafting a {document_type} for South African High Court proceedings.

**DOCUMENT STRUCTURE (Required Sections):**
{structure_text}

**CASE INFORMATION (From intake questions):**
{intake_text}

**SUPPORTING EVIDENCE (From case documents - cite using [N] format):**
{excerpts_text}

**STYLE AND FORMATTING REQUIREMENTS:**
{style_guidance}

**INSTRUCTIONS:**
1. Follow the document structure exactly - include all required sections in order
2. Each section should have:
   - A heading in CAPITALS
   - Numbered paragraphs (1., 2., 3., etc.)
   - Content that fulfills the section's purpose
3. Use formal legal register appropriate for South African High Court
4. Cite supporting evidence using [1], [2], etc. format wherever you make factual claims
5. Reference intake information to personalize the draft (parties, dates, case details)
6. Ensure the document is court-ready and professional
7. Use South African legal terminology consistently (e.g., "the Applicant", "the Respondent", "I aver that...")

Generate the complete {document_type} now:"""

    return prompt


def get_system_message_for_document_type(document_type: str, rulebook: Optional[Any] = None) -> str:
    """
    Get system message based on document type and rulebook.

    If rulebook has custom system_message in drafting_prompt, use that.
    Otherwise, use default system message for document type.

    Args:
        document_type: Type of document (affidavit, pleading, heads_of_argument)
        rulebook: Optional Rulebook with rules_json containing drafting_prompt.system_message

    Returns:
        System message for LLM
    """
    # Try to get system message from rulebook first
    if rulebook and rulebook.rules_json:
        drafting_config = rulebook.rules_json.get("drafting_prompt", {})
        custom_system_message = drafting_config.get("system_message")
        if custom_system_message:
            return custom_system_message

    # Fallback to default system messages
    default_messages = {
        "affidavit": """You are an expert South African litigation attorney specializing in affidavits.
You draft clear, precise affidavits that comply with High Court rules and Uniform Rules of Court.
You cite evidence meticulously using [N] format and use proper South African legal terminology.
You structure affidavits with numbered paragraphs and clear section headings in CAPITALS.""",

        "pleading": """You are an expert South African litigation attorney specializing in pleadings.
You draft well-structured pleadings (particulars of claim, pleas, replications) following High Court practice.
You cite legal precedent and factual evidence accurately using [N] format.
You plead material facts clearly and precisely with numbered paragraphs.""",

        "heads_of_argument": """You are an expert South African advocate specializing in heads of argument.
You draft persuasive, well-researched heads with proper legal citations and case law references.
You structure arguments logically with supporting precedents and statutory references.
You use formal legal language appropriate for appellate advocacy."""
    }

    return default_messages.get(
        document_type,
        "You are an expert legal drafting assistant for South African High Court proceedings."
    )


def format_document_structure(structure: List[Dict[str, Any]]) -> str:
    """
    Format document structure from rulebook into readable LLM prompt.

    Includes:
    - Section titles
    - Content templates (if provided)
    - Prompt guidance for each section
    - Required vs optional sections

    Args:
        structure: List of section definitions from rulebook

    Returns:
        Formatted structure text for LLM prompt
    """
    if not structure:
        return "No specific structure provided - use standard format for document type"

    formatted = []
    for i, section in enumerate(structure, 1):
        if not isinstance(section, dict):
            continue

        section_id = section.get("section_id", f"section_{i}")
        title = section.get("title", "UNTITLED SECTION")
        required = section.get("required", True)
        content_template = section.get("content_template", "")
        prompt_guidance = section.get("prompt_guidance", "")
        min_paragraphs = section.get("minimum_paragraphs")
        max_paragraphs = section.get("maximum_paragraphs")

        # Build section description
        section_text = f"{i}. {title} {'(REQUIRED)' if required else '(OPTIONAL)'}"

        # Add paragraph requirements
        if min_paragraphs or max_paragraphs:
            requirements = []
            if min_paragraphs:
                requirements.append(f"at least {min_paragraphs} paragraphs")
            if max_paragraphs:
                requirements.append(f"at most {max_paragraphs} paragraphs")
            section_text += f"\n   Requirements: {', '.join(requirements)}"

        # Add content guidance
        if prompt_guidance:
            section_text += f"\n   Guidance: {prompt_guidance[:300]}"
        elif content_template:
            section_text += f"\n   Purpose: {content_template[:300]}"

        formatted.append(section_text)

        # Handle nested subsections
        subsections = section.get("subsections", [])
        if subsections:
            for j, subsection in enumerate(subsections, 1):
                if isinstance(subsection, dict):
                    subtitle = subsection.get("title", "Subsection")
                    formatted.append(f"   {i}.{j}. {subtitle}")

    return "\n\n".join(formatted)


def extract_citations_from_content(content: str, research_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract citation markers [1], [2], etc. from generated content.

    Args:
        content: Generated draft content
        research_summary: Research summary with excerpts

    Returns:
        List of citations with metadata
    """
    # Find all [N] patterns
    citation_markers = re.findall(r'\[(\d+)\]', content)

    # Map to research excerpts
    citations = []
    excerpts = research_summary.get("key_excerpts", [])

    for marker in set(citation_markers):
        idx = int(marker) - 1
        if 0 <= idx < len(excerpts):
            excerpt = excerpts[idx]
            citations.append({
                "marker": f"[{marker}]",
                "document": excerpt["document"],
                "page": excerpt["page"],
                "content": excerpt["content"][:200] + "...",
                "similarity": excerpt["similarity"]
            })

    return citations
