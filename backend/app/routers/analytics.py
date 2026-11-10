import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.database import get_db
from app.deps import OrgContext, require_roles
from app.services import analytics

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _validate_range(date_from: dt.date | None, date_to: dt.date | None) -> None:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, "date_from must be on or before date_to")


@router.get("/overview", response_model=schemas.AnalyticsOverviewOut)
async def analytics_overview(
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    ctx: OrgContext = Depends(require_roles(*models.MEMBER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> schemas.AnalyticsOverviewOut:
    _validate_range(date_from, date_to)
    data = await analytics.overview(
        db,
        org_id=ctx.org_id,
        role=ctx.role,
        user_id=ctx.user.id,
        date_from=date_from,
        date_to=date_to,
    )
    return schemas.AnalyticsOverviewOut.model_validate(data)


@router.get("/issues", response_model=schemas.AnalyticsIssuesOut)
async def analytics_issues(
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    category: str | None = None,
    ctx: OrgContext = Depends(require_roles(*models.MEMBER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> schemas.AnalyticsIssuesOut:
    _validate_range(date_from, date_to)
    data = await analytics.issues(
        db,
        org_id=ctx.org_id,
        role=ctx.role,
        user_id=ctx.user.id,
        date_from=date_from,
        date_to=date_to,
        category=category,
    )
    return schemas.AnalyticsIssuesOut.model_validate(data)


@router.get("/trends", response_model=schemas.AnalyticsTrendsOut)
async def analytics_trends(
    days: int = Query(default=30, ge=1, le=365),
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    category: str | None = None,
    ctx: OrgContext = Depends(require_roles(*models.MEMBER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> schemas.AnalyticsTrendsOut:
    _validate_range(date_from, date_to)
    data = await analytics.trends(
        db,
        org_id=ctx.org_id,
        role=ctx.role,
        user_id=ctx.user.id,
        days=days,
        date_from=date_from,
        date_to=date_to,
        category=category,
    )
    return schemas.AnalyticsTrendsOut.model_validate(data)
