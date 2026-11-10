import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.audit import log_audit
from app.database import get_db
from app.deps import OrgContext, require_roles
from app.routers.submissions import (
    build_detail,
    build_summary,
    get_org_submission,
)

router = APIRouter(prefix="/api/reviews", tags=["reviews"])

DECISION_APPROVE = "approve"
DECISION_REJECT = "reject"
DECISION_REQUEST_CHANGES = "request_changes"
DECISION_REQUEST_CLARIFICATION = "request_clarification"

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    models.SUBMISSION_SUBMITTED: {
        DECISION_APPROVE,
        DECISION_REJECT,
        DECISION_REQUEST_CHANGES,
        DECISION_REQUEST_CLARIFICATION,
    },
    models.SUBMISSION_RESUBMITTED: {
        DECISION_APPROVE,
        DECISION_REJECT,
        DECISION_REQUEST_CHANGES,
        DECISION_REQUEST_CLARIFICATION,
    },
    models.SUBMISSION_CLARIFICATION_REQUIRED: {
        DECISION_APPROVE,
        DECISION_REJECT,
        DECISION_REQUEST_CHANGES,
        DECISION_REQUEST_CLARIFICATION,
    },
    models.SUBMISSION_UNDER_ANALYSIS: set(),
    models.SUBMISSION_DRAFT: set(),
    models.SUBMISSION_CHANGES_REQUESTED: {DECISION_REQUEST_CLARIFICATION},
    models.SUBMISSION_APPROVED: set(),
    models.SUBMISSION_REJECTED: set(),
}

DECISION_TARGET_STATUS = {
    DECISION_APPROVE: models.SUBMISSION_APPROVED,
    DECISION_REJECT: models.SUBMISSION_REJECTED,
    DECISION_REQUEST_CHANGES: models.SUBMISSION_CHANGES_REQUESTED,
    DECISION_REQUEST_CLARIFICATION: models.SUBMISSION_CLARIFICATION_REQUIRED,
}


@router.get("/queue", response_model=list[schemas.SubmissionSummaryOut])
async def review_queue(
    ctx: OrgContext = Depends(require_roles(models.ROLE_REVIEWER, models.ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> list[schemas.SubmissionSummaryOut]:
    stmt = (
        select(models.ContentSubmission)
        .where(
            models.ContentSubmission.org_id == ctx.org_id,
            models.ContentSubmission.status.in_(models.QUEUE_STATUSES),
        )
        .order_by(models.ContentSubmission.updated_at.desc())
        .limit(200)
    )
    submissions = list((await db.execute(stmt)).scalars().all())
    return await build_summary(db, submissions)


@router.get("/decided", response_model=list[schemas.SubmissionSummaryOut])
async def decided_submissions(
    ctx: OrgContext = Depends(require_roles(models.ROLE_REVIEWER, models.ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> list[schemas.SubmissionSummaryOut]:
    stmt = (
        select(models.ContentSubmission)
        .where(
            models.ContentSubmission.org_id == ctx.org_id,
            models.ContentSubmission.status.in_(models.TERMINAL_STATUSES),
        )
        .order_by(models.ContentSubmission.updated_at.desc())
        .limit(200)
    )
    submissions = list((await db.execute(stmt)).scalars().all())
    return await build_summary(db, submissions)


@router.get("/{submission_id}", response_model=schemas.SubmissionDetailOut)
async def get_review(
    submission_id: int,
    ctx: OrgContext = Depends(require_roles(models.ROLE_REVIEWER, models.ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> schemas.SubmissionDetailOut:
    submission = await get_org_submission(db, ctx.org_id, submission_id)
    return await build_detail(db, submission)


@router.post("/{submission_id}/comment", response_model=schemas.SubmissionDetailOut)
async def add_comment(
    submission_id: int,
    payload: schemas.CommentIn,
    ctx: OrgContext = Depends(require_roles(*models.MEMBER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> schemas.SubmissionDetailOut:
    submission = await get_org_submission(db, ctx.org_id, submission_id)
    if ctx.role == models.ROLE_CREATOR and submission.created_by_id != ctx.user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Submission not found")
    if submission.status in models.TERMINAL_STATUSES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This submission is already closed")
    comment = models.ReviewComment(
        submission_id=submission.id,
        author_id=ctx.user.id,
        body=payload.body.strip(),
    )
    db.add(comment)
    await log_audit(
        db,
        org_id=ctx.org_id,
        user_id=ctx.user.id,
        action="submission.comment_added",
        entity_type="content_submission",
        entity_id=submission.id,
        details={"role": ctx.role},
    )
    await db.commit()
    await db.refresh(submission)
    return await build_detail(db, submission)


async def apply_decision(
    db: AsyncSession,
    ctx: OrgContext,
    submission: models.ContentSubmission,
    decision: str,
    note: str,
) -> models.ContentSubmission:
    allowed = ALLOWED_TRANSITIONS.get(submission.status, set())
    if decision not in allowed:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Decision {decision} is not allowed while the submission is '{submission.status}'",
        )
    target = DECISION_TARGET_STATUS[decision]
    previous = submission.status
    submission.status = target
    submission.decided_by_id = ctx.user.id
    now = dt.datetime.now(dt.timezone.utc)
    submission.decided_at = now
    record = models.ApprovalDecision(
        submission_id=submission.id,
        decision=decision,
        from_status=previous,
        to_status=target,
        note=note.strip(),
        decided_by_id=ctx.user.id,
        decided_at=now,
    )
    db.add(record)
    await db.flush()
    await log_audit(
        db,
        org_id=ctx.org_id,
        user_id=ctx.user.id,
        action=f"submission.{decision}",
        entity_type="content_submission",
        entity_id=submission.id,
        details={"from": previous, "to": target},
    )
    return submission


@router.post("/{submission_id}/approve", response_model=schemas.SubmissionDetailOut)
async def approve_submission(
    submission_id: int,
    payload: schemas.DecisionIn | None = None,
    ctx: OrgContext = Depends(require_roles(models.ROLE_REVIEWER, models.ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> schemas.SubmissionDetailOut:
    submission = await get_org_submission(db, ctx.org_id, submission_id)
    await apply_decision(db, ctx, submission, DECISION_APPROVE, (payload or schemas.DecisionIn()).note)
    await db.commit()
    await db.refresh(submission)
    return await build_detail(db, submission)


@router.post("/{submission_id}/reject", response_model=schemas.SubmissionDetailOut)
async def reject_submission(
    submission_id: int,
    payload: schemas.DecisionIn | None = None,
    ctx: OrgContext = Depends(require_roles(models.ROLE_REVIEWER, models.ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> schemas.SubmissionDetailOut:
    submission = await get_org_submission(db, ctx.org_id, submission_id)
    note = (payload or schemas.DecisionIn()).note
    if not note.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "A rejection requires a note")
    await apply_decision(db, ctx, submission, DECISION_REJECT, note)
    await db.commit()
    await db.refresh(submission)
    return await build_detail(db, submission)


@router.post("/{submission_id}/request-changes", response_model=schemas.SubmissionDetailOut)
async def request_changes(
    submission_id: int,
    payload: schemas.DecisionIn | None = None,
    ctx: OrgContext = Depends(require_roles(models.ROLE_REVIEWER, models.ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> schemas.SubmissionDetailOut:
    submission = await get_org_submission(db, ctx.org_id, submission_id)
    note = (payload or schemas.DecisionIn()).note
    if not note.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Requesting changes requires a note")
    await apply_decision(db, ctx, submission, DECISION_REQUEST_CHANGES, note)
    await db.commit()
    await db.refresh(submission)
    return await build_detail(db, submission)


@router.post("/{submission_id}/request-clarification", response_model=schemas.SubmissionDetailOut)
async def request_clarification(
    submission_id: int,
    payload: schemas.DecisionIn | None = None,
    ctx: OrgContext = Depends(require_roles(models.ROLE_REVIEWER, models.ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> schemas.SubmissionDetailOut:
    submission = await get_org_submission(db, ctx.org_id, submission_id)
    note = (payload or schemas.DecisionIn()).note
    if not note.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Requesting clarification requires a note")
    await apply_decision(db, ctx, submission, DECISION_REQUEST_CLARIFICATION, note)
    await db.commit()
    await db.refresh(submission)
    return await build_detail(db, submission)
