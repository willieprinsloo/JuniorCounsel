"""
Q&A endpoints with retrieval-augmented generation.
"""
import logging
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.ai_providers import get_llm_provider
from app.dependencies import get_current_user
from app.middleware.database import get_db
from app.persistence.models import User, TokenUsageTypeEnum, Case
from app.persistence.repositories import TokenUsageRepository, CaseRepository
from app.persistence.chat_session_repository import ChatSessionRepository, ChatMessageRepository
from app.schemas.qa import QARequest, QAResponse, SearchResult
from app.api.v1.search import search_documents

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=QAResponse)
def ask_question(
    qa_request: QARequest,
    chat_session_id: Optional[str] = Query(None, description="Chat session ID to save message to"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Answer a question using case documents (RAG).

    Process:
    1. Search for relevant document chunks (vector similarity)
    2. Build context from top chunks
    3. Generate answer using LLM with citations
    4. Optionally save to chat session for persistence

    Args:
        qa_request: Question and case ID
        chat_session_id: Optional chat session ID to save message to
        db: Database session
        current_user: Current authenticated user

    Returns:
        Answer with citations
    """
    logger.info(f"Q&A question: '{qa_request.question}' in case {qa_request.case_id} by user {current_user.id}")

    # Step 1: Retrieve relevant chunks using vector search
    try:
        search_results = search_documents(
            case_id=qa_request.case_id,
            query=qa_request.question,
            limit=qa_request.max_context_chunks,
            similarity_threshold=0.6,  # Lower threshold for Q&A (more context)
            db=db,
            current_user=current_user
        )
    except Exception as e:
        logger.error(f"Failed to retrieve context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve context: {str(e)}"
        )

    if not search_results.results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No relevant information found in case documents"
        )

    # Step 2: Build context from search results
    context_parts = []
    sources = []

    for i, result in enumerate(search_results.results):
        citation_id = f"[{i+1}]"
        context_parts.append(f"{citation_id} {result.content}")

        # Convert search result to SearchResult schema
        sources.append(SearchResult(
            chunk_id=result.chunk_id,
            document_id=result.document_id,
            document_filename=result.document_filename,
            content=result.content,
            page_number=result.page_number,
            similarity=result.similarity,
            citation=result.citation
        ))

    context = "\n\n".join(context_parts)

    logger.debug(f"Built context from {len(sources)} chunks, {len(context)} chars")

    # Step 3: Generate answer with LLM
    try:
        llm_provider = get_llm_provider()

        system_message = """You are a legal assistant helping attorneys analyze case documents.

Rules:
1. Answer based ONLY on the provided context
2. Cite sources using [1], [2], etc. format
3. If the context doesn't contain the answer, say "I don't have enough information in the case documents to answer this question."
4. Be precise and professional
5. Include relevant legal citations from the documents
6. Use South African legal terminology where applicable"""

        prompt = f"""Context from case documents:

{context}

Question: {qa_request.question}

Answer (with citations):"""

        generation_result = llm_provider.generate(
            prompt=prompt,
            system_message=system_message,
            temperature=0.3,  # Low temperature for factual accuracy
            max_tokens=1000
        )

        # Record token usage
        case_repo = CaseRepository(db)
        case = case_repo.get_by_id(qa_request.case_id)

        if case:
            token_repo = TokenUsageRepository(db)
            token_repo.record_usage(
                usage_type=TokenUsageTypeEnum.LLM_QA,
                provider=llm_provider.provider,
                model=generation_result.model,
                input_tokens=generation_result.input_tokens,
                output_tokens=generation_result.output_tokens,
                organisation_id=case.organisation_id,
                user_id=current_user.id,
                case_id=qa_request.case_id,
                resource_type="qa_session",
                resource_id=None  # Could be chat_session_id if we have it
            )
            db.commit()

        logger.info(f"Generated answer: {len(generation_result.content)} chars, used {generation_result.input_tokens + generation_result.output_tokens} tokens")

    except Exception as e:
        logger.error(f"Failed to generate answer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate answer: {str(e)}"
        )

    # Calculate confidence based on average similarity of top sources
    avg_similarity = sum(s.similarity for s in sources) / len(sources) if sources else 0.0
    confidence = min(avg_similarity, 1.0)  # Ensure it's between 0 and 1

    # Save message to chat session if provided
    if chat_session_id:
        try:
            chat_session_repo = ChatSessionRepository(db)
            chat_session = chat_session_repo.get_by_id(UUID(chat_session_id))

            if chat_session and chat_session.user_id == current_user.id:
                # Save message to chat session
                message_repo = ChatMessageRepository(db)

                # Convert sources to dict for JSON storage
                sources_data = [
                    {
                        "chunk_id": str(s.chunk_id),
                        "document_id": str(s.document_id),
                        "document_filename": s.document_filename,
                        "content": s.content,
                        "page_number": s.page_number,
                        "similarity": s.similarity,
                        "citation": s.citation
                    }
                    for s in sources
                ]

                message_repo.create(
                    chat_session_id=UUID(chat_session_id),
                    question=qa_request.question,
                    answer=generation_result.content,
                    confidence=confidence,
                    sources=sources_data
                )
                logger.info(f"Saved Q&A message to chat session {chat_session_id}")
        except Exception as e:
            logger.error(f"Failed to save message to chat session: {e}")
            # Don't fail the request if saving to chat fails

    return QAResponse(
        question=qa_request.question,
        answer=generation_result.content,
        sources=sources,
        confidence=confidence
    )
