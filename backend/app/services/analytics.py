import datetime as dt
from collections import Counter, defaultdict
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models

TERMINAL = set(models.TERMINAL_STATUSES)
PENDING = set(models.SUBMISSION_STATUSES) - TERMINAL - {models.SUBMISSION_DRAFT}
TERMINOLOGY_CATEGORY = "Terminology violation"
MISMATCH_CATEGORY = "Factual mismatch"
MAX_ROWS = 20000


def _date_bounds(
    date_from: dt.date | None, date_to: dt.date | None
) -> tuple[dt.datetime | None, dt.datetime | None]:
    start = dt.datetime.combine(date_from, dt.time.min) if date_from else None
    end = dt.datetime.combine(date_to + dt.timedelta(days=1), dt.time.min) if date_to else None
    return start, end


def _latest_runs_subquery():
    return (
        select(
            models.AnalysisRun.submission_id.label("submission_id"),
            func.max(models.AnalysisRun.id).label("run_id"),
        )
        .group_by(models.AnalysisRun.submission_id)
        .subquery()
    )


def _findings_select(
    *,
    org_id: int,
    role: str,
    user_id: int,
    start: dt.datetime | None,
    end: dt.datetime | None,
    latest_only: bool,
    category: str | None = None,
    clarification_only: bool = False,
    human_review_only: bool = False,
):
    stmt = select(
        models.Finding.category.label("category"),
        models.Finding.severity.label("severity"),
        models.Finding.detected_text.label("detected_text"),
        models.Finding.requires_clarification.label("requires_clarification"),
        models.Finding.needs_human_review.label("needs_human_review"),
        models.Finding.created_at.label("created_at"),
    ).join(
        models.ContentSubmission, models.ContentSubmission.id == models.Finding.submission_id
    )
    if latest_only:
        latest = _latest_runs_subquery()
        stmt = stmt.join(latest, latest.c.run_id == models.Finding.analysis_run_id)
    stmt = stmt.where(models.ContentSubmission.org_id == org_id)
    if role == models.ROLE_CREATOR:
        stmt = stmt.where(models.ContentSubmission.created_by_id == user_id)
    if start is not None:
        stmt = stmt.where(models.Finding.created_at >= start)
    if end is not None:
        stmt = stmt.where(models.Finding.created_at < end)
    if category:
        stmt = stmt.where(models.Finding.category == category)
    if clarification_only:
        stmt = stmt.where(models.Finding.requires_clarification.is_(True))
    if human_review_only:
        stmt = stmt.where(models.Finding.needs_human_review.is_(True))
    return stmt


async def _count(db: AsyncSession, stmt) -> int:
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    return int(total or 0)


async def _grouped(db: AsyncSession, stmt, column: str, limit: int | None = None):
    sub = stmt.subquery()
    col = sub.c[column]
    query = (
        select(col.label("label"), func.count().label("count"))
        .select_from(sub)
        .group_by(col)
        .order_by(func.count().desc())
    )
    if limit:
        query = query.limit(limit)
    return (await db.execute(query)).all()


async def _top_texts(db: AsyncSession, stmt, limit: int = 8) -> list[dict[str, Any]]:
    sub = stmt.subquery()
    lowered = func.lower(sub.c.detected_text)
    query = (
        select(
            sub.c.category.label("category"),
            lowered.label("text"),
            func.count().label("count"),
        )
        .select_from(sub)
        .group_by(sub.c.category, lowered)
        .order_by(func.count().desc())
        .limit(limit)
    )
    return [
        {"category": str(category), "detected_text": str(text), "count": int(count)}
        for category, text, count in (await db.execute(query)).all()
    ]


async def overview(
    db: AsyncSession,
    *,
    org_id: int,
    role: str,
    user_id: int,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
) -> dict[str, Any]:
    start, end = _date_bounds(date_from, date_to)

    status_stmt = select(models.ContentSubmission.status, func.count()).where(
        models.ContentSubmission.org_id == org_id
    )
    if role == models.ROLE_CREATOR:
        status_stmt = status_stmt.where(models.ContentSubmission.created_by_id == user_id)
    if start is not None:
        status_stmt = status_stmt.where(models.ContentSubmission.created_at >= start)
    if end is not None:
        status_stmt = status_stmt.where(models.ContentSubmission.created_at < end)
    status_stmt = status_stmt.group_by(models.ContentSubmission.status)
    status_counts = [
        {"status": status, "count": int(count)}
        for status, count in (await db.execute(status_stmt)).all()
    ]
    status_map = {row["status"]: row["count"] for row in status_counts}

    subs_stmt = select(
        models.ContentSubmission.id,
        models.ContentSubmission.created_at,
        models.ContentSubmission.decided_at,
        models.ContentSubmission.status,
    ).where(models.ContentSubmission.org_id == org_id)
    if role == models.ROLE_CREATOR:
        subs_stmt = subs_stmt.where(models.ContentSubmission.created_by_id == user_id)
    if start is not None:
        subs_stmt = subs_stmt.where(models.ContentSubmission.created_at >= start)
    if end is not None:
        subs_stmt = subs_stmt.where(models.ContentSubmission.created_at < end)
    submissions = (await db.execute(subs_stmt.limit(MAX_ROWS))).all()
    decided = [
        row for row in submissions if row.decided_at is not None and row.status in TERMINAL
    ]
    review_hours = [
        (row.decided_at - row.created_at).total_seconds() / 3600.0 for row in decided
    ]
    avg_review_hours = round(sum(review_hours) / len(review_hours), 1) if review_hours else None

    submission_ids = [row.id for row in submissions]
    avg_revision_cycles = None
    if submission_ids:
        revision_rows = (
            await db.execute(
                select(
                    models.SubmissionRevision.submission_id,
                    func.count().label("count"),
                )
                .where(models.SubmissionRevision.submission_id.in_(submission_ids))
                .group_by(models.SubmissionRevision.submission_id)
            )
        ).all()
        revision_counts = [int(count) for _, count in revision_rows]
        avg_revision_cycles = round(sum(revision_counts) / len(submission_ids), 2)

    latest_stmt = _findings_select(
        org_id=org_id, role=role, user_id=user_id, start=start, end=end, latest_only=True
    )
    all_stmt = _findings_select(
        org_id=org_id, role=role, user_id=user_id, start=start, end=end, latest_only=False
    )
    categories = [
        {"category": str(label), "count": int(count)}
        for label, count in await _grouped(db, latest_stmt, "category", 8)
    ]
    severities = [
        {"severity": str(label), "count": int(count)}
        for label, count in await _grouped(db, latest_stmt, "severity")
    ]
    top_issues = await _top_texts(db, all_stmt, 8)

    totals = {
        "submissions_total": sum(status_map.values()),
        "submissions_approved": status_map.get(models.SUBMISSION_APPROVED, 0),
        "submissions_rejected": status_map.get(models.SUBMISSION_REJECTED, 0),
        "submissions_pending": sum(status_map.get(status, 0) for status in PENDING),
        "submissions_draft": status_map.get(models.SUBMISSION_DRAFT, 0),
        "findings_total": await _count(db, all_stmt),
        "findings_latest": await _count(db, latest_stmt),
        "clarification_findings": await _count(
            db,
            _findings_select(
                org_id=org_id,
                role=role,
                user_id=user_id,
                start=start,
                end=end,
                latest_only=True,
                clarification_only=True,
            ),
        ),
        "needs_human_review": await _count(
            db,
            _findings_select(
                org_id=org_id,
                role=role,
                user_id=user_id,
                start=start,
                end=end,
                latest_only=True,
                human_review_only=True,
            ),
        ),
        "decided_total": len(decided),
        "avg_review_hours": avg_review_hours,
        "avg_revision_cycles": avg_revision_cycles,
    }
    return {
        "totals": totals,
        "status_counts": status_counts,
        "categories": categories,
        "severities": severities,
        "top_issues": top_issues,
        "date_from": date_from,
        "date_to": date_to,
    }


async def issues(
    db: AsyncSession,
    *,
    org_id: int,
    role: str,
    user_id: int,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    start, end = _date_bounds(date_from, date_to)
    base = dict(org_id=org_id, role=role, user_id=user_id, start=start, end=end)
    latest_stmt = _findings_select(**base, latest_only=True, category=category)
    terminology_stmt = _findings_select(
        **base, latest_only=False, category=TERMINOLOGY_CATEGORY
    )
    mismatch_stmt = _findings_select(**base, latest_only=False, category=MISMATCH_CATEGORY)
    clarification_stmt = _findings_select(
        **base, latest_only=False, clarification_only=True
    )
    return {
        "categories": [
            {"category": str(label), "count": int(count)}
            for label, count in await _grouped(db, latest_stmt, "category", 10)
        ],
        "severities": [
            {"severity": str(label), "count": int(count)}
            for label, count in await _grouped(db, latest_stmt, "severity")
        ],
        "repeated_terminology": await _top_texts(db, terminology_stmt),
        "top_factual_mismatches": await _top_texts(db, mismatch_stmt),
        "top_clarification_claims": await _top_texts(db, clarification_stmt),
        "needs_human_review": await _count(
            db, _findings_select(**base, latest_only=True, human_review_only=True)
        ),
        "date_from": date_from,
        "date_to": date_to,
    }


async def trends(
    db: AsyncSession,
    *,
    org_id: int,
    role: str,
    user_id: int,
    days: int = 30,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    today = dt.date.today()
    end_date = date_to or today
    start_date = date_from or (
        end_date - dt.timedelta(days=max(min(days, 365), 1) - 1)
    )
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    if (end_date - start_date).days > 366:
        start_date = end_date - dt.timedelta(days=366)
    start, end = _date_bounds(start_date, end_date)

    submission_dates = Counter()
    subs_stmt = select(models.ContentSubmission.created_at).where(
        models.ContentSubmission.org_id == org_id,
        models.ContentSubmission.created_at >= start,
        models.ContentSubmission.created_at < end,
    )
    if role == models.ROLE_CREATOR:
        subs_stmt = subs_stmt.where(models.ContentSubmission.created_by_id == user_id)
    for (created_at,) in (await db.execute(subs_stmt.limit(MAX_ROWS))).all():
        submission_dates[created_at.date()] += 1

    decision_dates = Counter()
    decision_stmt = (
        select(models.ApprovalDecision.decided_at)
        .join(
            models.ContentSubmission,
            models.ContentSubmission.id == models.ApprovalDecision.submission_id,
        )
        .where(
            models.ContentSubmission.org_id == org_id,
            models.ApprovalDecision.decided_at >= start,
            models.ApprovalDecision.decided_at < end,
        )
    )
    if role == models.ROLE_CREATOR:
        decision_stmt = decision_stmt.where(models.ContentSubmission.created_by_id == user_id)
    for (decided_at,) in (await db.execute(decision_stmt.limit(MAX_ROWS))).all():
        decision_dates[decided_at.date()] += 1

    finding_dates = Counter()
    category_dates: dict[str, Counter] = defaultdict(Counter)
    findings_stmt = _findings_select(
        org_id=org_id,
        role=role,
        user_id=user_id,
        start=start,
        end=end,
        latest_only=False,
        category=category,
    ).with_only_columns(models.Finding.category, models.Finding.created_at)
    for row_category, created_at in (await db.execute(findings_stmt.limit(MAX_ROWS))).all():
        finding_dates[created_at.date()] += 1
        category_dates[str(row_category)][created_at.date()] += 1

    series = []
    cursor = start_date
    while cursor <= end_date:
        series.append(
            {
                "date": cursor,
                "submissions": submission_dates.get(cursor, 0),
                "findings": finding_dates.get(cursor, 0),
                "decisions": decision_dates.get(cursor, 0),
            }
        )
        cursor += dt.timedelta(days=1)

    by_category = []
    for category_name, counter in category_dates.items():
        for day, count in sorted(counter.items()):
            by_category.append({"date": day, "category": category_name, "count": count})

    return {
        "series": series,
        "by_category": by_category,
        "date_from": start_date,
        "date_to": end_date,
    }
