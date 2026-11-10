from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.audit import log_audit
from app.database import get_db
from app.deps import OrgContext, require_roles
from app.services import files
from app.services.analysis.pipeline import analyse_text
from app.services.analysis.textprep import normalise
from app.services.visual import VisualInspection, inspect_image

router = APIRouter(prefix="/api/submissions", tags=["submissions"])

SUBMISSION_DIR = "submissions"

MAX_CONTENT_CHARS = 50000
MAX_ALT_TEXT_CHARS = 500


async def get_org_submission(
    db: AsyncSession, org_id: int, submission_id: int
) -> models.ContentSubmission:
    submission = await db.scalar(
        select(models.ContentSubmission).where(
            models.ContentSubmission.id == submission_id,
            models.ContentSubmission.org_id == org_id,
        )
    )
    if submission is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Submission not found")
    return submission


async def check_submission_access(ctx: OrgContext, submission: models.ContentSubmission) -> None:
    if ctx.role == models.ROLE_CREATOR and submission.created_by_id != ctx.user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Submission not found")


async def get_revisions(db: AsyncSession, submission_id: int) -> list[models.SubmissionRevision]:
    return list(
        (
            await db.execute(
                select(models.SubmissionRevision)
                .where(models.SubmissionRevision.submission_id == submission_id)
                .order_by(models.SubmissionRevision.revision_number)
            )
        )
        .scalars()
        .all()
    )


async def get_runs_with_findings(
    db: AsyncSession, submission_id: int
) -> list[tuple[models.AnalysisRun, list[models.Finding]]]:
    runs = list(
        (
            await db.execute(
                select(models.AnalysisRun)
                .where(models.AnalysisRun.submission_id == submission_id)
                .order_by(models.AnalysisRun.id.desc())
                .limit(10)
            )
        )
        .scalars()
        .all()
    )
    result: list[tuple[models.AnalysisRun, list[models.Finding]]] = []
    for run in runs:
        findings = list(
            (
                await db.execute(
                    select(models.Finding)
                    .where(models.Finding.analysis_run_id == run.id)
                    .order_by(models.Finding.start_offset, models.Finding.id)
                )
            )
            .scalars()
            .all()
        )
        result.append((run, findings))
    return result


async def get_comments(db: AsyncSession, submission_id: int) -> list[schemas.CommentOut]:
    rows = (
        await db.execute(
            select(models.ReviewComment, models.User)
            .join(models.User, models.User.id == models.ReviewComment.author_id)
            .where(models.ReviewComment.submission_id == submission_id)
            .order_by(models.ReviewComment.id)
        )
    ).all()
    return [
        schemas.CommentOut(
            id=comment.id,
            submission_id=submission_id,
            author_email=user.email,
            author_name=user.full_name,
            body=comment.body,
            created_at=comment.created_at,
        )
        for comment, user in rows
    ]


async def get_decisions(db: AsyncSession, submission_id: int) -> list[schemas.DecisionOut]:
    rows = (
        await db.execute(
            select(models.ApprovalDecision, models.User)
            .join(models.User, models.User.id == models.ApprovalDecision.decided_by_id)
            .where(models.ApprovalDecision.submission_id == submission_id)
            .order_by(models.ApprovalDecision.id)
        )
    ).all()
    return [
        schemas.DecisionOut(
            id=decision.id,
            submission_id=submission_id,
            decision=decision.decision,
            from_status=decision.from_status,
            to_status=decision.to_status,
            note=decision.note,
            decided_by_email=user.email,
            decided_at=decision.decided_at,
        )
        for decision, user in rows
    ]


async def creator_email(db: AsyncSession, user_id: int) -> str | None:
    user = await db.get(models.User, user_id)
    return user.email if user else None


async def build_detail(
    db: AsyncSession, submission: models.ContentSubmission
) -> schemas.SubmissionDetailOut:
    revisions = await get_revisions(db, submission.id)
    runs = await get_runs_with_findings(db, submission.id)
    comments = await get_comments(db, submission.id)
    decisions = await get_decisions(db, submission.id)
    return schemas.SubmissionDetailOut(
        id=submission.id,
        org_id=submission.org_id,
        title=submission.title,
        submission_type=submission.submission_type,
        status=submission.status,
        created_by_id=submission.created_by_id,
        created_by_email=await creator_email(db, submission.created_by_id),
        has_image=submission.image_stored is not None,
        image_name=submission.image_name,
        alt_text=submission.alt_text,
        created_at=submission.created_at,
        updated_at=submission.updated_at,
        decided_at=submission.decided_at,
        revisions=[
            schemas.RevisionOut(
                id=rev.id,
                submission_id=submission.id,
                revision_number=rev.revision_number,
                content=rev.content,
                created_by_id=rev.created_by_id,
                created_at=rev.created_at,
            )
            for rev in revisions
        ],
        runs=[
            schemas.AnalysisRunOut(
                id=run.id,
                submission_id=submission.id,
                revision_id=run.revision_id,
                engine=run.engine,
                finding_count=run.finding_count,
                created_at=run.created_at,
                visual_report=run.visual_report,
                findings=[schemas.FindingOut.model_validate(f) for f in findings],
            )
            for run, findings in runs
        ],
        comments=comments,
        decisions=decisions,
    )


async def build_summary(
    db: AsyncSession, submissions: list[models.ContentSubmission]
) -> list[schemas.SubmissionSummaryOut]:
    summaries: list[schemas.SubmissionSummaryOut] = []
    for submission in submissions:
        revision_count = await db.scalar(
            select(func.count()).select_from(models.SubmissionRevision).where(
                models.SubmissionRevision.submission_id == submission.id
            )
        )
        latest_revision = await db.scalar(
            select(models.SubmissionRevision)
            .where(models.SubmissionRevision.submission_id == submission.id)
            .order_by(models.SubmissionRevision.revision_number.desc())
            .limit(1)
        )
        latest_run = await db.scalar(
            select(models.AnalysisRun)
            .where(models.AnalysisRun.submission_id == submission.id)
            .order_by(models.AnalysisRun.id.desc())
            .limit(1)
        )
        finding_count = None
        clarification_count = None
        if latest_run is not None:
            finding_count = await db.scalar(
                select(func.count()).select_from(models.Finding).where(
                    models.Finding.analysis_run_id == latest_run.id
                )
            )
            clarification_count = await db.scalar(
                select(func.count()).select_from(models.Finding).where(
                    models.Finding.analysis_run_id == latest_run.id,
                    models.Finding.requires_clarification.is_(True),
                )
            )
        summaries.append(
            schemas.SubmissionSummaryOut(
                id=submission.id,
                title=submission.title,
                submission_type=submission.submission_type,
                status=submission.status,
                created_by_id=submission.created_by_id,
                created_by_email=await creator_email(db, submission.created_by_id),
                current_revision_number=latest_revision.revision_number if latest_revision else None,
                revision_count=revision_count or 0,
                latest_finding_count=finding_count,
                latest_clarification_count=clarification_count,
                created_at=submission.created_at,
                updated_at=submission.updated_at,
            )
        )
    return summaries


def validate_submission_payload(title: str, submission_type: str, content: str) -> None:
    title = title.strip()
    if not title or len(title) > 200:
        raise HTTPException(422, "Title must be between 1 and 200 characters")
    if submission_type not in models.SUBMISSION_TYPES:
        raise HTTPException(422, f"submission_type must be one of {', '.join(models.SUBMISSION_TYPES)}")
    content = content.strip()
    if not content:
        raise HTTPException(422, "Content cannot be empty")
    if len(content) > MAX_CONTENT_CHARS:
        raise HTTPException(422, f"Content exceeds the {MAX_CONTENT_CHARS} character limit")


def validate_alt_text(alt_text: str) -> str | None:
    cleaned = alt_text.strip()
    if len(cleaned) > MAX_ALT_TEXT_CHARS:
        raise HTTPException(422, f"Alt text exceeds the {MAX_ALT_TEXT_CHARS} character limit")
    return cleaned or None


@router.post("", response_model=schemas.SubmissionDetailOut, status_code=status.HTTP_201_CREATED)
async def create_submission(
    title: str = Form(...),
    submission_type: str = Form(...),
    content: str = Form(...),
    alt_text: str = Form(""),
    image: UploadFile | None = File(None),
    ctx: OrgContext = Depends(require_roles(models.ROLE_CREATOR, models.ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> schemas.SubmissionDetailOut:
    validate_submission_payload(title, submission_type, content)
    submission = models.ContentSubmission(
        org_id=ctx.org_id,
        title=title.strip(),
        submission_type=submission_type,
        status=models.SUBMISSION_DRAFT,
        created_by_id=ctx.user.id,
        alt_text=validate_alt_text(alt_text),
    )
    db.add(submission)
    await db.flush()
    revision = models.SubmissionRevision(
        submission_id=submission.id,
        revision_number=1,
        content=normalise(content),
        created_by_id=ctx.user.id,
    )
    db.add(revision)
    await db.flush()
    submission.current_revision_id = revision.id
    if image is not None and image.filename:
        stored, original, content_type, size = await files.save_upload(
            ctx.org_id, SUBMISSION_DIR, image, files.ALLOWED_IMAGE_TYPES
        )
        submission.image_stored = stored
        submission.image_name = original
        submission.image_content_type = content_type
        submission.image_size_bytes = size
    await log_audit(
        db,
        org_id=ctx.org_id,
        user_id=ctx.user.id,
        action="submission.created",
        entity_type="content_submission",
        entity_id=submission.id,
        details={"title": submission.title, "submission_type": submission.submission_type},
    )
    await db.commit()
    await db.refresh(submission)
    await db.refresh(revision)
    return await build_detail(db, submission)


@router.get("", response_model=list[schemas.SubmissionSummaryOut])
async def list_submissions(
    status_filter: str | None = None,
    ctx: OrgContext = Depends(require_roles(*models.MEMBER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> list[schemas.SubmissionSummaryOut]:
    stmt = select(models.ContentSubmission).where(models.ContentSubmission.org_id == ctx.org_id)
    if status_filter:
        stmt = stmt.where(models.ContentSubmission.status == status_filter)
    if ctx.role == models.ROLE_CREATOR:
        stmt = stmt.where(models.ContentSubmission.created_by_id == ctx.user.id)
    stmt = stmt.order_by(models.ContentSubmission.updated_at.desc()).limit(200)
    submissions = list((await db.execute(stmt)).scalars().all())
    return await build_summary(db, submissions)


@router.get("/{submission_id}", response_model=schemas.SubmissionDetailOut)
async def get_submission(
    submission_id: int,
    ctx: OrgContext = Depends(require_roles(*models.MEMBER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> schemas.SubmissionDetailOut:
    submission = await get_org_submission(db, ctx.org_id, submission_id)
    await check_submission_access(ctx, submission)
    return await build_detail(db, submission)


@router.get("/{submission_id}/image")
async def get_submission_image(
    submission_id: int,
    ctx: OrgContext = Depends(require_roles(*models.MEMBER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    submission = await get_org_submission(db, ctx.org_id, submission_id)
    await check_submission_access(ctx, submission)
    if not submission.image_stored:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No image attached")
    path = files.upload_path(ctx.org_id, SUBMISSION_DIR, submission.image_stored)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Stored file is missing")
    return FileResponse(
        path, filename=submission.image_name or "image", media_type=submission.image_content_type
    )


async def persist_analysis(
    db: AsyncSession,
    submission: models.ContentSubmission,
    revision: models.SubmissionRevision,
    result,
    visual_report: dict | None = None,
) -> models.AnalysisRun:
    run = models.AnalysisRun(
        submission_id=submission.id,
        revision_id=revision.id,
        engine=result.engine,
        finding_count=len(result.findings),
        visual_report=visual_report,
    )
    db.add(run)
    await db.flush()
    for finding in result.findings:
        row = models.Finding(
            submission_id=submission.id,
            analysis_run_id=run.id,
            finding_id=finding["finding_id"],
            category=finding["category"],
            severity=finding["severity"],
            detected_text=finding["detected_text"],
            start_offset=finding["start_offset"],
            end_offset=finding["end_offset"],
            evidence=finding.get("evidence"),
            explanation=finding["explanation"],
            suggested_correction=finding.get("suggested_correction"),
            confidence=finding.get("confidence"),
            review_status=finding.get("review_status", "open"),
            requires_clarification=finding.get("requires_clarification", False),
            needs_human_review=finding.get("needs_human_review", False),
        )
        db.add(row)
    return run


async def inspect_submission_visual(
    db: AsyncSession, org_id: int, submission: models.ContentSubmission
) -> VisualInspection:
    if not submission.image_stored:
        return VisualInspection(report={}, findings=[], ocr_text=None, analysed=False)
    assets = list(
        (
            await db.execute(
                select(models.ApprovedAsset).where(models.ApprovedAsset.org_id == org_id)
            )
        )
        .scalars()
        .all()
    )
    palette = [
        {"name": asset.name, "hex": asset.colour_value}
        for asset in assets
        if asset.asset_type == "colour" and asset.colour_value
    ]
    logo = next(
        (asset for asset in assets if asset.asset_type == "logo" and asset.file_stored), None
    )
    logo_path = (
        files.upload_path(org_id, files.LOGO_SUBDIR, logo.file_stored) if logo else None
    )
    image_path = files.upload_path(org_id, SUBMISSION_DIR, submission.image_stored)
    return inspect_image(
        image_path,
        content_type=submission.image_content_type,
        alt_text=submission.alt_text,
        palette=palette,
        logo_path=logo_path,
    )


def final_status_for(findings: list[dict]) -> str:
    if any(f.get("requires_clarification") for f in findings):
        return models.SUBMISSION_CLARIFICATION_REQUIRED
    return models.SUBMISSION_SUBMITTED


async def run_analysis_workflow(
    db: AsyncSession, ctx: OrgContext, submission: models.ContentSubmission
) -> models.AnalysisRun:
    revision = await db.get(models.SubmissionRevision, submission.current_revision_id)
    if revision is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Submission has no revision to analyse")
    previous = submission.status
    submission.status = models.SUBMISSION_UNDER_ANALYSIS
    await log_audit(
        db,
        org_id=ctx.org_id,
        user_id=ctx.user.id,
        action="submission.status_changed",
        entity_type="content_submission",
        entity_id=submission.id,
        details={"from": previous, "to": models.SUBMISSION_UNDER_ANALYSIS},
    )
    org = await db.get(models.Organisation, ctx.org_id)
    visual = await inspect_submission_visual(db, ctx.org_id, submission)
    result = await analyse_text(
        db,
        ctx.org_id,
        revision.content,
        llm_consent=bool(org and org.llm_consent),
        extra_text=visual.ocr_text,
    )
    if visual.report:
        result.findings.extend(visual.findings)
        if visual.analysed:
            result.engine = f"{result.engine} + Visual"
    run = await persist_analysis(
        db, submission, revision, result, visual.report if visual.report else None
    )
    final = final_status_for(result.findings)
    submission.status = final
    await log_audit(
        db,
        org_id=ctx.org_id,
        user_id=ctx.user.id,
        action="submission.analysed",
        entity_type="content_submission",
        entity_id=submission.id,
        details={
            "engine": run.engine,
            "finding_count": run.finding_count,
            "from": models.SUBMISSION_UNDER_ANALYSIS,
            "to": final,
            "revision": revision.revision_number,
        },
    )
    return run


@router.post("/{submission_id}/analyse", response_model=schemas.SubmissionDetailOut)
async def analyse_submission(
    submission_id: int,
    ctx: OrgContext = Depends(require_roles(models.ROLE_CREATOR, models.ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> schemas.SubmissionDetailOut:
    submission = await get_org_submission(db, ctx.org_id, submission_id)
    await check_submission_access(ctx, submission)
    if submission.status in models.TERMINAL_STATUSES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This submission is already closed")
    if submission.status == models.SUBMISSION_UNDER_ANALYSIS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Analysis is already in progress")
    await run_analysis_workflow(db, ctx, submission)
    await db.commit()
    await db.refresh(submission)
    return await build_detail(db, submission)


@router.post("/{submission_id}/revise", response_model=schemas.SubmissionDetailOut)
async def revise_submission(
    submission_id: int,
    content: str = Form(...),
    alt_text: str | None = Form(None),
    image: UploadFile | None = File(None),
    ctx: OrgContext = Depends(require_roles(models.ROLE_CREATOR, models.ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> schemas.SubmissionDetailOut:
    submission = await get_org_submission(db, ctx.org_id, submission_id)
    await check_submission_access(ctx, submission)
    if submission.status in models.TERMINAL_STATUSES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This submission is already closed")
    content = content.strip()
    if not content:
        raise HTTPException(422, "Revision content cannot be empty")
    if len(content) > MAX_CONTENT_CHARS:
        raise HTTPException(422, f"Content exceeds the {MAX_CONTENT_CHARS} character limit")
    if alt_text is not None:
        submission.alt_text = validate_alt_text(alt_text)
    next_number = (
        (
            await db.scalar(
                select(func.max(models.SubmissionRevision.revision_number)).where(
                    models.SubmissionRevision.submission_id == submission.id
                )
            )
        )
        or 0
    ) + 1
    revision = models.SubmissionRevision(
        submission_id=submission.id,
        revision_number=next_number,
        content=normalise(content),
        created_by_id=ctx.user.id,
    )
    db.add(revision)
    await db.flush()
    submission.current_revision_id = revision.id
    if image is not None and image.filename:
        stored, original, content_type, size = await files.save_upload(
            ctx.org_id, SUBMISSION_DIR, image, files.ALLOWED_IMAGE_TYPES
        )
        submission.image_stored = stored
        submission.image_name = original
        submission.image_content_type = content_type
        submission.image_size_bytes = size
    previous = submission.status
    submission.status = models.SUBMISSION_RESUBMITTED
    await log_audit(
        db,
        org_id=ctx.org_id,
        user_id=ctx.user.id,
        action="submission.revised",
        entity_type="content_submission",
        entity_id=submission.id,
        details={"from": previous, "to": models.SUBMISSION_RESUBMITTED, "revision": next_number},
    )
    await run_analysis_workflow(db, ctx, submission)
    await db.commit()
    await db.refresh(submission)
    return await build_detail(db, submission)
