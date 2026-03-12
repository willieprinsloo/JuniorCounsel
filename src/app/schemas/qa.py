"""
Pydantic schemas for Q&A endpoints.
"""
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class QARequest(BaseModel):
    """Q&A request schema."""
    case_id: str = Field(..., description="Case ID")
    question: str = Field(..., min_length=5, description="Question to answer")
    max_context_chunks: int = Field(5, ge=1, le=20, description="Maximum context chunks to use")


class SearchResult(BaseModel):
    """Search result matching frontend SearchResult type."""
    chunk_id: str = Field(..., description="Chunk ID")
    document_id: str = Field(..., description="Document ID")
    document_filename: str = Field(..., description="Document filename")
    content: str = Field(..., description="Chunk content")
    page_number: int = Field(..., description="Page number")
    similarity: float = Field(..., description="Similarity score")
    citation: Dict[str, Any] = Field(default_factory=dict, description="Citation metadata")


class QAResponse(BaseModel):
    """Q&A response schema."""
    question: str = Field(..., description="Original question")
    answer: str = Field(..., description="Generated answer with citations")
    sources: List[SearchResult] = Field(..., description="Source search results")
    confidence: float = Field(..., description="Confidence score (0-1)")
