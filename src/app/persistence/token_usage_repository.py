"""
Token usage repository for tracking API consumption and costs.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.persistence.models import TokenUsage, TokenUsageTypeEnum


class TokenUsageRepository:
    """Repository for recording and querying API token usage."""

    def __init__(self, session: Session):
        self.session = session

    def record_usage(
        self,
        usage_type: TokenUsageTypeEnum,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        organisation_id: Optional[int] = None,
        user_id: Optional[int] = None,
        case_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> TokenUsage:
        """
        Record API token usage.

        Args:
            usage_type: Type of operation (embedding, llm_generation, etc.)
            provider: AI provider (openai, anthropic)
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count (0 for embeddings)
            organisation_id: Organisation ID (for cost attribution)
            user_id: User ID (for cost attribution)
            case_id: Case ID (for cost attribution)
            resource_type: Type of resource (draft_session, document, etc.)
            resource_id: ID of related resource

        Returns:
            Created TokenUsage record
        """
        total_tokens = input_tokens + output_tokens

        # Calculate estimated cost
        estimated_cost_usd = self._calculate_cost(
            provider, model, input_tokens, output_tokens
        )

        usage = TokenUsage(
            organisation_id=organisation_id,
            user_id=user_id,
            case_id=case_id,
            usage_type=usage_type,
            resource_type=resource_type,
            resource_id=resource_id,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost_usd,
        )

        self.session.add(usage)
        self.session.flush()
        return usage

    def _calculate_cost(
        self, provider: str, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """
        Calculate estimated cost in USD based on current API pricing.

        Pricing as of 2024 (per 1M tokens):
        - OpenAI gpt-4-turbo: $10 input, $30 output
        - OpenAI gpt-4: $30 input, $60 output
        - OpenAI gpt-3.5-turbo: $0.50 input, $1.50 output
        - OpenAI text-embedding-3-small: $0.02 input
        - Anthropic claude-3-opus: $15 input, $75 output
        - Anthropic claude-3-sonnet: $3 input, $15 output
        - Anthropic claude-3-haiku: $0.25 input, $1.25 output

        Args:
            provider: Provider name
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count

        Returns:
            Estimated cost in USD
        """
        pricing = {
            "openai": {
                "gpt-4-turbo": {"input": 10.00, "output": 30.00},
                "gpt-4-turbo-preview": {"input": 10.00, "output": 30.00},
                "gpt-4": {"input": 30.00, "output": 60.00},
                "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
                "text-embedding-3-small": {"input": 0.02, "output": 0.0},
                "text-embedding-3-large": {"input": 0.13, "output": 0.0},
                "text-embedding-ada-002": {"input": 0.10, "output": 0.0},
            },
            "anthropic": {
                "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
                "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00},
                "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
                # Aliases without version suffixes
                "claude-3-opus": {"input": 15.00, "output": 75.00},
                "claude-3-sonnet": {"input": 3.00, "output": 15.00},
                "claude-3-haiku": {"input": 0.25, "output": 1.25},
            },
        }

        rates = pricing.get(provider, {}).get(model, {"input": 0, "output": 0})
        cost_input = (input_tokens / 1_000_000) * rates["input"]
        cost_output = (output_tokens / 1_000_000) * rates["output"]

        return round(cost_input + cost_output, 6)  # 6 decimal places

    def get_usage_summary(
        self,
        organisation_id: Optional[int] = None,
        user_id: Optional[int] = None,
        case_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        usage_type: Optional[TokenUsageTypeEnum] = None,
    ) -> Dict[str, Any]:
        """
        Get aggregated usage summary.

        Args:
            organisation_id: Filter by organisation
            user_id: Filter by user
            case_id: Filter by case
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            usage_type: Filter by usage type

        Returns:
            Dict with aggregated metrics
        """
        query = select(
            func.sum(TokenUsage.input_tokens).label("total_input_tokens"),
            func.sum(TokenUsage.output_tokens).label("total_output_tokens"),
            func.sum(TokenUsage.total_tokens).label("total_tokens"),
            func.sum(TokenUsage.estimated_cost_usd).label("total_cost_usd"),
            func.count(TokenUsage.id).label("request_count"),
        )

        if organisation_id is not None:
            query = query.where(TokenUsage.organisation_id == organisation_id)
        if user_id is not None:
            query = query.where(TokenUsage.user_id == user_id)
        if case_id is not None:
            query = query.where(TokenUsage.case_id == case_id)
        if start_date is not None:
            query = query.where(TokenUsage.created_at >= start_date)
        if end_date is not None:
            query = query.where(TokenUsage.created_at <= end_date)
        if usage_type is not None:
            query = query.where(TokenUsage.usage_type == usage_type)

        result = self.session.execute(query).first()

        return {
            "total_input_tokens": result.total_input_tokens or 0,
            "total_output_tokens": result.total_output_tokens or 0,
            "total_tokens": result.total_tokens or 0,
            "total_cost_usd": float(result.total_cost_usd or 0),
            "request_count": result.request_count or 0,
        }

    def get_usage_by_type(
        self,
        organisation_id: Optional[int] = None,
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[Dict[str, Any]]:
        """
        Get usage breakdown by usage type.

        Returns:
            List of dicts with usage_type and metrics
        """
        query = select(
            TokenUsage.usage_type,
            func.sum(TokenUsage.total_tokens).label("total_tokens"),
            func.sum(TokenUsage.estimated_cost_usd).label("total_cost_usd"),
            func.count(TokenUsage.id).label("request_count"),
        ).group_by(TokenUsage.usage_type)

        if organisation_id is not None:
            query = query.where(TokenUsage.organisation_id == organisation_id)
        if user_id is not None:
            query = query.where(TokenUsage.user_id == user_id)
        if start_date is not None:
            query = query.where(TokenUsage.created_at >= start_date)
        if end_date is not None:
            query = query.where(TokenUsage.created_at <= end_date)

        results = self.session.execute(query).all()

        return [
            {
                "usage_type": row.usage_type.value,
                "total_tokens": row.total_tokens or 0,
                "total_cost_usd": float(row.total_cost_usd or 0),
                "request_count": row.request_count or 0,
            }
            for row in results
        ]

    def get_top_cases_by_cost(
        self,
        organisation_id: Optional[int] = None,
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10,
    ) -> list[Dict[str, Any]]:
        """
        Get top cases by total cost.

        Returns:
            List of dicts with case_id and total_cost_usd
        """
        query = (
            select(
                TokenUsage.case_id,
                func.sum(TokenUsage.estimated_cost_usd).label("total_cost_usd"),
                func.sum(TokenUsage.total_tokens).label("total_tokens"),
            )
            .where(TokenUsage.case_id.isnot(None))
            .group_by(TokenUsage.case_id)
            .order_by(func.sum(TokenUsage.estimated_cost_usd).desc())
            .limit(limit)
        )

        if organisation_id is not None:
            query = query.where(TokenUsage.organisation_id == organisation_id)
        if user_id is not None:
            query = query.where(TokenUsage.user_id == user_id)
        if start_date is not None:
            query = query.where(TokenUsage.created_at >= start_date)
        if end_date is not None:
            query = query.where(TokenUsage.created_at <= end_date)

        results = self.session.execute(query).all()

        return [
            {
                "case_id": str(row.case_id),
                "total_cost_usd": float(row.total_cost_usd or 0),
                "total_tokens": row.total_tokens or 0,
            }
            for row in results
        ]
