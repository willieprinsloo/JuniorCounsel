"""
Pydantic schemas for search endpoints.
"""
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Search request schema."""
    case_id: str = Field(..., description="Case ID to search within")
    query: str = Field(..., min_length=3, description="Search query")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")
    similarity_threshold: float = Field(0.7, ge=0, le=1, description="Minimum similarity score")
    document_type: Optional[str] = Field(None, description="Filter by document type")


class SearchResult(BaseModel):
    """Individual search result."""
    chunk_id: str = Field(..., description="Chunk ID")
    document_id: str = Field(..., description="Document ID")
    document_filename: str = Field(..., description="Document filename")
    content: str = Field(..., description="Chunk content")
    page_number: int = Field(..., description="Page number")
    similarity: float = Field(..., description="Similarity score (0-1)")
    citation: Dict[str, any] = Field(..., description="Citation metadata")

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    """Search response schema."""
    query: str = Field(..., description="Original search query")
    results: List[SearchResult] = Field(..., description="Search results")
    total: int = Field(..., description="Total number of results")
