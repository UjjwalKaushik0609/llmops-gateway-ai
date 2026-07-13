"""
Analytics, cost tracking, and reporting endpoints.
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from backend.database.connection import get_db
from backend.models.db_models import User, Request as RequestModel
from backend.models.schemas import AnalyticsSummary, CostForecast
from backend.security.dependencies import get_current_user, require_admin
from backend.config import settings

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get analytics summary for the authenticated user."""
    since = datetime.utcnow() - timedelta(days=days)

    # Filter by user unless admin
    base_filter = [RequestModel.timestamp >= since]
    if current_user.role != "admin":
        base_filter.append(RequestModel.user_id == current_user.id)

    # Total requests
    total_req = await db.execute(
        select(func.count(RequestModel.id)).where(and_(*base_filter))
    )
    total_requests = total_req.scalar() or 0

    # Total tokens
    token_result = await db.execute(
        select(
            func.coalesce(func.sum(RequestModel.tokens_input), 0),
            func.coalesce(func.sum(RequestModel.tokens_output), 0),
        ).where(and_(*base_filter))
    )
    tokens_in, tokens_out = token_result.one()
    total_tokens = int(tokens_in + tokens_out)

    # Total cost
    cost_result = await db.execute(
        select(func.coalesce(func.sum(RequestModel.cost_usd), 0.0)).where(and_(*base_filter))
    )
    total_cost = float(cost_result.scalar() or 0.0)

    # Avg latency
    latency_result = await db.execute(
        select(func.coalesce(func.avg(RequestModel.latency_ms), 0)).where(and_(*base_filter))
    )
    avg_latency = float(latency_result.scalar() or 0.0)

    # By provider
    provider_result = await db.execute(
        select(
            RequestModel.provider,
            func.count(RequestModel.id),
            func.coalesce(func.sum(RequestModel.cost_usd), 0.0),
        ).where(and_(*base_filter)).group_by(RequestModel.provider)
    )
    provider_rows = provider_result.all()
    requests_by_provider = {row[0]: row[1] for row in provider_rows}
    cost_by_provider = {row[0]: round(float(row[2]), 4) for row in provider_rows}

    # Top models
    model_result = await db.execute(
        select(
            RequestModel.model,
            RequestModel.provider,
            func.count(RequestModel.id).label("count"),
            func.coalesce(func.sum(RequestModel.cost_usd), 0.0).label("cost"),
        ).where(and_(*base_filter))
        .group_by(RequestModel.model, RequestModel.provider)
        .order_by(func.count(RequestModel.id).desc())
        .limit(5)
    )
    top_models = [
        {"model": r[0], "provider": r[1], "requests": r[2], "cost_usd": round(float(r[3]), 4)}
        for r in model_result.all()
    ]

    # Error rate
    error_result = await db.execute(
        select(func.count(RequestModel.id)).where(
            and_(*base_filter, RequestModel.status == "error")
        )
    )
    error_count = error_result.scalar() or 0
    error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0.0

    # Daily costs (last 30 days)
    daily_result = await db.execute(
        select(
            func.date(RequestModel.timestamp).label("date"),
            func.coalesce(func.sum(RequestModel.cost_usd), 0.0).label("cost"),
            func.count(RequestModel.id).label("requests"),
        ).where(and_(*base_filter))
        .group_by(func.date(RequestModel.timestamp))
        .order_by(func.date(RequestModel.timestamp))
    )
    daily_costs = [
        {"date": str(r[0]), "cost_usd": round(float(r[1]), 4), "requests": r[2]}
        for r in daily_result.all()
    ]

    return AnalyticsSummary(
        total_requests=total_requests,
        total_tokens=total_tokens,
        total_cost_usd=round(total_cost, 4),
        avg_latency_ms=round(avg_latency, 1),
        requests_by_provider=requests_by_provider,
        cost_by_provider=cost_by_provider,
        error_rate=round(error_rate, 2),
        top_models=top_models,
        daily_costs=daily_costs,
    )


@router.get("/cost-forecast", response_model=CostForecast)
async def get_cost_forecast(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Forecast end-of-month spend based on current usage."""
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    days_elapsed = (now - month_start).days + 1
    days_in_month = 30  # approximate
    days_remaining = days_in_month - days_elapsed

    # Current month spend
    month_filter = [
        RequestModel.user_id == current_user.id,
        RequestModel.timestamp >= month_start,
    ]
    spend_result = await db.execute(
        select(func.coalesce(func.sum(RequestModel.cost_usd), 0.0)).where(and_(*month_filter))
    )
    current_spend = float(spend_result.scalar() or 0.0)

    daily_avg = current_spend / days_elapsed if days_elapsed > 0 else 0
    projected = current_spend + (daily_avg * days_remaining)
    budget = current_user.monthly_budget_usd
    budget_remaining = max(0, budget - current_spend)
    will_exceed = projected > budget

    recommendations = []
    if will_exceed:
        recommendations.append("Switch to cost-optimized routing strategy")
        recommendations.append(f"Reduce daily spend by ${(projected - budget) / days_remaining:.2f}")
        recommendations.append("Consider using smaller models for simple queries")
        recommendations.append("Enable response caching to reduce duplicate API calls")
    elif current_spend / budget > 0.7:
        recommendations.append("You've used 70% of your monthly budget - monitor closely")
        recommendations.append("Enable auto-routing for cost optimization")

    return CostForecast(
        current_month_spend=round(current_spend, 4),
        projected_month_spend=round(projected, 4),
        daily_average=round(daily_avg, 4),
        days_remaining=days_remaining,
        budget_remaining=round(budget_remaining, 4),
        will_exceed_budget=will_exceed,
        recommended_actions=recommendations,
    )


@router.get("/requests")
async def get_request_history(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    provider: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated request history."""
    filters = []
    if current_user.role != "admin":
        filters.append(RequestModel.user_id == current_user.id)
    if provider:
        filters.append(RequestModel.provider == provider)

    offset = (page - 1) * per_page

    result = await db.execute(
        select(RequestModel)
        .where(and_(*filters) if filters else True)
        .order_by(RequestModel.timestamp.desc())
        .offset(offset)
        .limit(per_page)
    )
    requests = result.scalars().all()

    count_result = await db.execute(
        select(func.count(RequestModel.id)).where(and_(*filters) if filters else True)
    )
    total = count_result.scalar() or 0

    return {
        "requests": [
            {
                "id": r.id,
                "provider": r.provider,
                "model": r.model,
                "tokens_input": r.tokens_input,
                "tokens_output": r.tokens_output,
                "cost_usd": r.cost_usd,
                "latency_ms": r.latency_ms,
                "status": r.status,
                "routing_strategy": r.routed_by,
                "timestamp": r.timestamp,
            }
            for r in requests
        ],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page,
        },
    }


@router.get("/admin/global-stats")
async def get_global_stats(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: global platform statistics."""
    user_count = await db.execute(select(func.count(User.id)))
    total_users = user_count.scalar() or 0

    req_count = await db.execute(select(func.count(RequestModel.id)))
    total_requests = req_count.scalar() or 0

    total_cost_result = await db.execute(
        select(func.coalesce(func.sum(RequestModel.cost_usd), 0.0))
    )
    total_cost = float(total_cost_result.scalar() or 0.0)

    return {
        "total_users": total_users,
        "total_requests": total_requests,
        "total_cost_usd": round(total_cost, 4),
        "platform": settings.app_name,
    }
