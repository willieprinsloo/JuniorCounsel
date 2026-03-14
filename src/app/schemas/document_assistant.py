"""
Schemas for Document Assistant API endpoints.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Single chat message."""
    role: str = Field(..., description="Message role: user, assistant, system, tool")
    content: str = Field(..., description="Message content")


class DocumentChatRequest(BaseModel):
    """Request for document assistant chat."""
    message: str = Field(..., description="User message")
    conversation_history: List[ChatMessage] = Field(
        default_factory=list,
        description="Previous conversation messages"
    )


class SuggestedAction(BaseModel):
    """Suggested action for user."""
    action: str = Field(..., description="Action type: create_draft, etc.")
    label: str = Field(..., description="Display label for action")
    rulebook_id: Optional[int] = Field(None, description="Rulebook ID if applicable")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional action metadata")


class ToolResult(BaseModel):
    """Result from a tool execution."""
    tool: str = Field(..., description="Tool name")
    result: Any = Field(..., description="Tool result data")


class DocumentChatResponse(BaseModel):
    """Response from document assistant chat."""
    ai_response: str = Field(..., description="AI assistant response")
    tools_used: List[str] = Field(default_factory=list, description="List of tools called")
    tool_results: List[ToolResult] = Field(default_factory=list, description="Results from tool calls")
    suggested_actions: List[SuggestedAction] = Field(default_factory=list, description="Suggested next actions")
    draft_session_id: Optional[str] = Field(None, description="Created draft session ID if applicable")


class DocumentAnalysisRequest(BaseModel):
    """Request for bulk document analysis."""
    analysis_type: str = Field(
        default="full",
        description="Analysis type: full, summary, or key_facts"
    )


class KeyParty(BaseModel):
    """A party mentioned in documents."""
    name: str
    role: str
    mentioned_in: Optional[List[str]] = None


class ImportantDate(BaseModel):
    """An important date from documents."""
    date: str
    description: str
    source: Optional[str] = None
    page: Optional[int] = None


class KeyFact(BaseModel):
    """A key fact extracted from documents."""
    fact: str
    confidence: Optional[float] = None
    source: str
    page: Optional[int] = None


class Warning(BaseModel):
    """A warning about potential issues."""
    type: str
    message: str
    severity: str


class DocumentAnalysis(BaseModel):
    """Structured document analysis result."""
    key_parties: List[KeyParty] = Field(default_factory=list)
    important_dates: List[ImportantDate] = Field(default_factory=list)
    key_facts: List[KeyFact] = Field(default_factory=list)
    document_types: Dict[str, int] = Field(default_factory=dict)
    warnings: List[Warning] = Field(default_factory=list)


class DocumentAnalysisResponse(BaseModel):
    """Response from document analysis endpoint."""
    case_id: str
    total_documents: int
    completed_documents: int
    processing_documents: int
    analysis: DocumentAnalysis
    tokens_used: int = 0
    cost_usd: float = 0.0
    message: Optional[str] = None
