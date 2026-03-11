"""
Vector search endpoints for semantic document retrieval.
"""
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.core.ai_providers import get_embedding_provider
from app.dependencies import get_current_user
from app.middleware.database import get_db
from app.persistence.models import User, DocumentChunk, Document, DocumentStatusEnum
from app.schemas.search import SearchRequest, SearchResponse, SearchResult

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=SearchResponse)
def search_documents(
    case_id: str = Query(..., description="Case ID to search within"),
    query: str = Query(..., min_length=3, description="Search query"),
    limit: int = Query(10, ge=1, le=100, description="Number of results"),
    similarity_threshold: float = Query(0.7, ge=0, le=1, description="Minimum similarity score"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Semantic search within case documents.

    Uses vector similarity (cosine distance) with pgvector.

    Args:
        case_id: Case ID to search within
        query: Natural language search query
        limit: Maximum number of results (1-100)
        similarity_threshold: Minimum similarity score (0-1)
        document_type: Optional filter by document type
        db: Database session
        current_user: Current authenticated user

    Returns:
        Search results with relevant document chunks and citations
    """
    logger.info(f"Search query: '{query}' in case {case_id} by user {current_user.id}")

    try:
        # Generate query embedding
        embedding_provider = get_embedding_provider()
        query_embedding = embedding_provider.embed_text(query)

        logger.debug(f"Generated query embedding: {len(query_embedding)} dimensions")

    except Exception as e:
        logger.error(f"Failed to generate query embedding: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate query embedding: {str(e)}"
        )

    try:
        # Build vector search query using pgvector cosine distance
        # Lower distance = higher similarity
        stmt = select(
            DocumentChunk,
            Document,
            func.cosine_distance(DocumentChunk.embedding, query_embedding).label('distance')
        ).join(
            Document, DocumentChunk.document_id == Document.id
        ).where(
            Document.case_id == case_id,
            Document.overall_status == DocumentStatusEnum.COMPLETED
        )

        # Apply document type filter if provided
        if document_type:
            stmt = stmt.where(Document.document_type == document_type)

        # Order by similarity (lower distance = higher similarity)
        stmt = stmt.order_by('distance').limit(limit)

        # Execute query
        results = db.execute(stmt).all()

        logger.debug(f"Found {len(results)} results before filtering")

    except Exception as e:
        logger.error(f"Search query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search query failed: {str(e)}"
        )

    # Format results and apply similarity threshold
    search_results = []
    for chunk, document, distance in results:
        # Convert distance to similarity (1 - distance for cosine)
        similarity = 1 - distance

        if similarity >= similarity_threshold:
            search_results.append(SearchResult(
                chunk_id=str(chunk.id),
                document_id=str(document.id),
                document_filename=document.filename,
                content=chunk.content,
                page_number=chunk.page_number,
                similarity=round(similarity, 4),
                citation={
                    "document": document.filename,
                    "page": chunk.page_number,
                    "chunk_index": chunk.chunk_index
                }
            ))

    logger.info(f"Returning {len(search_results)} results above threshold {similarity_threshold}")

    return SearchResponse(
        query=query,
        results=search_results,
        total=len(search_results)
    )


@router.post("/", response_model=SearchResponse)
def search_documents_post(
    search_request: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Semantic search within case documents (POST version).

    Allows for more complex search requests via JSON body.

    Args:
        search_request: Search request with query and filters
        db: Database session
        current_user: Current authenticated user

    Returns:
        Search results with relevant document chunks and citations
    """
    return search_documents(
        case_id=search_request.case_id,
        query=search_request.query,
        limit=search_request.limit,
        similarity_threshold=search_request.similarity_threshold,
        document_type=search_request.document_type,
        db=db,
        current_user=current_user
    )
