"""
Token usage schemas for API requests and responses.
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class UsageSummaryResponse(BaseModel):
    """Aggregated usage summary response."""
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_cost_usd: float
    request_count: int

    class Config:
        from_attributes = True


class UsageByTypeItem(BaseModel):
    """Usage breakdown by type."""
    usage_type: str
    total_tokens: int
    total_cost_usd: float
    request_count: int

    class Config:
        from_attributes = True


class UsageByTypeResponse(BaseModel):
    """List of usage by type."""
    usage_by_type: List[UsageByTypeItem]


class TopCaseItem(BaseModel):
    """Top case by cost."""
    case_id: str
    total_cost_usd: float
    total_tokens: int

    class Config:
        from_attributes = True


class TopCasesResponse(BaseModel):
    """List of top cases by cost."""
    top_cases: List[TopCaseItem]


class UsageDashboardResponse(BaseModel):
    """Complete usage dashboard response."""
    summary: UsageSummaryResponse
    by_type: List[UsageByTypeItem]
    top_cases: List[TopCaseItem]
    organisation_id: Optional[int] = None
    user_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    class Config:
        from_attributes = True
