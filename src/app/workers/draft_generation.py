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

        # Extract search queries from intake responses
        queries = extract_search_queries(draft.intake_responses, rulebook.rules_json)
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

        # Generate draft with LLM
        llm_provider = get_llm_provider()
        generated_content = llm_provider.generate(
            prompt=prompt,
            system_message=get_system_message_for_document_type(draft.document_type),
            temperature=0.5,  # Moderate creativity
            max_tokens=4000
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


def extract_search_queries(intake_responses: Dict[str, Any], rulebook_rules: Dict[str, Any]) -> List[str]:
    """
    Generate search queries from intake responses.

    Args:
        intake_responses: User's answers to intake questions
        rulebook_rules: Rulebook configuration

    Returns:
        List of search queries
    """
    queries = []

    # Extract key facts/issues from intake
    for key, value in intake_responses.items():
        if isinstance(value, str) and len(value) > 20:
            # Use meaningful text as search query
            queries.append(value[:500])  # Limit to 500 chars
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and len(item) > 20:
                    queries.append(item[:500])

    # Add rulebook-specific queries if defined
    if rulebook_rules and "research_queries" in rulebook_rules:
        queries.extend(rulebook_rules["research_queries"][:5])

    # Limit to 10 queries max
    return queries[:10]


def build_drafting_prompt(
    rulebook: Any,
    intake_responses: Dict[str, Any],
    research_summary: Dict[str, Any],
    document_type: str
) -> str:
    """
    Build LLM prompt for draft generation.

    Args:
        rulebook: Rulebook with document structure
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

    # Format intake responses
    intake_text = "\n".join([f"- {k}: {v}" for k, v in intake_responses.items()])

    # Format research excerpts with citations
    excerpts = research_summary.get("key_excerpts", [])[:10]
    excerpts_text = ""
    for i, excerpt in enumerate(excerpts):
        excerpts_text += f"[{i+1}] {excerpt['content'][:500]}\n(Source: {excerpt['document']}, Page {excerpt['page']})\n\n"

    prompt = f"""You are drafting a {document_type} for South African litigation.

**Document Structure (from rulebook):**
{structure_text}

**Facts and Information (from intake):**
{intake_text}

**Supporting Evidence (from case documents):**
{excerpts_text}

**Instructions:**
1. Follow the document structure exactly
2. Use formal legal language appropriate for South African courts
3. Cite evidence using [1], [2], etc. format
4. Include all required sections from the structure
5. Ensure factual accuracy (cite sources for all factual claims)
6. Make it court-ready and professional
7. Use South African legal terminology

Generate the {document_type}:"""

    return prompt


def get_system_message_for_document_type(document_type: str) -> str:
    """Get system message based on document type."""
    messages = {
        "affidavit": """You are an expert South African litigation attorney specializing in affidavits.
You draft clear, precise affidavits that comply with High Court rules.
You cite evidence meticulously and use proper legal terminology.""",

        "pleading": """You are an expert South African litigation attorney specializing in pleadings.
You draft well-structured pleadings (particulars of claim, pleas, replications) following court rules.
You cite legal precedent and factual evidence accurately.""",

        "heads_of_argument": """You are an expert South African advocate specializing in heads of argument.
You draft persuasive, well-researched heads with proper legal citations.
You structure arguments logically with supporting case law and statutory references."""
    }

    return messages.get(document_type, "You are an expert legal drafting assistant for South African courts.")


def format_document_structure(structure: List[Dict[str, Any]]) -> str:
    """
    Format document structure from rulebook into readable text.

    Args:
        structure: List of section definitions

    Returns:
        Formatted structure text
    """
    if not structure:
        return "No specific structure provided - use standard format for document type"

    formatted = []
    for section in structure:
        if isinstance(section, dict):
            name = section.get("name", "Section")
            description = section.get("description", "")
            formatted.append(f"- {name}: {description}")
        elif isinstance(section, str):
            formatted.append(f"- {section}")

    return "\n".join(formatted)


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
