"""
Token usage API endpoints.

Provides endpoints for viewing token usage and costs:
- User own usage
- Organisation-wide usage (for admins)
- Usage breakdowns by type
- Top cases by cost
"""
import logging
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.middleware.database import get_db
from app.persistence.models import User, TokenUsageTypeEnum
from app.persistence.repositories import TokenUsageRepository
from app.schemas.token_usage import (
    UsageSummaryResponse,
    UsageByTypeResponse,
    UsageByTypeItem,
    TopCasesResponse,
    TopCaseItem,
    UsageDashboardResponse
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/summary", response_model=UsageSummaryResponse)
def get_usage_summary(
    organisation_id: Optional[int] = Query(None, description="Filter by organisation (admin only)"),
    user_id: Optional[int] = Query(None, description="Filter by user (admin only)"),
    case_id: Optional[str] = Query(None, description="Filter by case"),
    start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    usage_type: Optional[TokenUsageTypeEnum] = Query(None, description="Filter by usage type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get aggregated token usage summary.

    Users can view their own usage.
    Organisation admins can view organisation-wide usage.
    """
    token_repo = TokenUsageRepository(db)

    # Default to current user if no filters specified
    if not organisation_id and not user_id:
        user_id = current_user.id

    # TODO: Add authorization check - only admins can view org-wide or other users' usage
    # For now, allow all for development

    summary = token_repo.get_usage_summary(
        organisation_id=organisation_id,
        user_id=user_id,
        case_id=case_id,
        start_date=start_date,
        end_date=end_date,
        usage_type=usage_type
    )

    return UsageSummaryResponse(**summary)


@router.get("/by-type", response_model=UsageByTypeResponse)
def get_usage_by_type(
    organisation_id: Optional[int] = Query(None, description="Filter by organisation (admin only)"),
    user_id: Optional[int] = Query(None, description="Filter by user (admin only)"),
    start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get usage breakdown by usage type (embedding, LLM generation, Q&A, OCR).

    Users can view their own usage.
    Organisation admins can view organisation-wide usage.
    """
    token_repo = TokenUsageRepository(db)

    # Default to current user if no filters specified
    if not organisation_id and not user_id:
        user_id = current_user.id

    # TODO: Add authorization check

    usage_by_type = token_repo.get_usage_by_type(
        organisation_id=organisation_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date
    )

    items = [UsageByTypeItem(**item) for item in usage_by_type]
    return UsageByTypeResponse(usage_by_type=items)


@router.get("/top-cases", response_model=TopCasesResponse)
def get_top_cases_by_cost(
    organisation_id: Optional[int] = Query(None, description="Filter by organisation (admin only)"),
    user_id: Optional[int] = Query(None, description="Filter by user (admin only)"),
    start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    limit: int = Query(10, ge=1, le=100, description="Number of top cases to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get top cases by total cost.

    Users can view their own cases.
    Organisation admins can view organisation-wide cases.
    """
    token_repo = TokenUsageRepository(db)

    # Default to current user if no filters specified
    if not organisation_id and not user_id:
        user_id = current_user.id

    # TODO: Add authorization check

    top_cases = token_repo.get_top_cases_by_cost(
        organisation_id=organisation_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )

    items = [TopCaseItem(**item) for item in top_cases]
    return TopCasesResponse(top_cases=items)


@router.get("/dashboard", response_model=UsageDashboardResponse)
def get_usage_dashboard(
    organisation_id: Optional[int] = Query(None, description="Filter by organisation (admin only)"),
    user_id: Optional[int] = Query(None, description="Filter by user (admin only)"),
    start_date: Optional[datetime] = Query(None, description="Start date (defaults to 30 days ago)"),
    end_date: Optional[datetime] = Query(None, description="End date (defaults to now)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get complete usage dashboard with summary, breakdown, and top cases.

    Combines multiple endpoints into one for dashboard display.
    Defaults to last 30 days if no dates specified.
    """
    token_repo = TokenUsageRepository(db)

    # Default to current user if no filters specified
    if not organisation_id and not user_id:
        user_id = current_user.id

    # Default to last 30 days
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # TODO: Add authorization check

    # Get all data
    summary = token_repo.get_usage_summary(
        organisation_id=organisation_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date
    )

    usage_by_type = token_repo.get_usage_by_type(
        organisation_id=organisation_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date
    )

    top_cases = token_repo.get_top_cases_by_cost(
        organisation_id=organisation_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        limit=10
    )

    return UsageDashboardResponse(
        summary=UsageSummaryResponse(**summary),
        by_type=[UsageByTypeItem(**item) for item in usage_by_type],
        top_cases=[TopCaseItem(**item) for item in top_cases],
        organisation_id=organisation_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date
    )


@router.get("/document/{document_id}", response_model=UsageSummaryResponse)
def get_document_usage(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get token usage for a specific document.

    Returns aggregated tokens and costs for all processing stages
    (text extraction, embeddings, classification) of a document.
    """
    token_repo = TokenUsageRepository(db)

    # Get usage for this specific document
    summary = token_repo.get_usage_summary(
        resource_type="document",
        resource_id=document_id
    )

    return UsageSummaryResponse(**summary)
