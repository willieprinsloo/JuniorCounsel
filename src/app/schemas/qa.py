"""
Pydantic schemas for Q&A endpoints.
"""
from typing import List
from pydantic import BaseModel, Field


class QARequest(BaseModel):
    """Q&A request schema."""
    case_id: str = Field(..., description="Case ID")
    question: str = Field(..., min_length=5, description="Question to answer")
    max_context_chunks: int = Field(5, ge=1, le=20, description="Maximum context chunks to use")


class Citation(BaseModel):
    """Citation schema."""
    id: str = Field(..., description="Citation marker (e.g., [1])")
    document: str = Field(..., description="Document filename")
    page: int = Field(..., description="Page number")
    similarity: float = Field(..., description="Similarity score")


class QAResponse(BaseModel):
    """Q&A response schema."""
    question: str = Field(..., description="Original question")
    answer: str = Field(..., description="Generated answer with citations")
    citations: List[Citation] = Field(..., description="Source citations")
    context_used: int = Field(..., description="Number of context chunks used")
