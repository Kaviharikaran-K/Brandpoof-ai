from fastapi import APIRouter, Depends, File, Form, HTTPException, status, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.audit import log_audit
from app.database import get_db
from app.deps import OrgContext, require_roles
from app.services import files

router = APIRouter(prefix="/api/brand/guidelines", tags=["brand-guidelines"])

SUBDIR = "guidelines"


@router.get("", response_model=list[schemas.GuidelineOut])
async def list_guidelines(
    ctx: OrgContext = Depends(require_roles(*models.MEMBER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> list[schemas.GuidelineOut]:
    rows = (
        await db.execute(
            select(models.BrandGuideline)
            .where(models.BrandGuideline.org_id == ctx.org_id)
            .order_by(models.BrandGuideline.id.desc())
            .limit(200)
        )
    ).scalars().all()
    return [schemas.GuidelineOut.model_validate(g) for g in rows]


@router.post("", response_model=schemas.GuidelineOut, status_code=status.HTTP_201_CREATED)
async def upload_guideline(
    title: str = Form(min_length=1, max_length=160),
    file: UploadFile = File(...),
    ctx: OrgContext = Depends(require_roles(models.ROLE_ADMIN, models.ROLE_CREATOR)),
    db: AsyncSession = Depends(get_db),
) -> schemas.GuidelineOut:
    stored, original, content_type, size = await files.save_upload(
        ctx.org_id, SUBDIR, file, files.ALLOWED_DOC_TYPES
    )
    guideline = models.BrandGuideline(
        org_id=ctx.org_id,
        title=title.strip(),
        file_stored=stored,
        file_name=original,
        content_type=content_type,
        size_bytes=size,
        uploaded_by_id=ctx.user.id,
    )
    db.add(guideline)
    await db.flush()
    await log_audit(
        db,
        org_id=ctx.org_id,
        user_id=ctx.user.id,
        action="guideline.uploaded",
        entity_type="brand_guideline",
        entity_id=guideline.id,
        details={"title": guideline.title, "file_name": original, "size_bytes": size},
    )
    await db.commit()
    await db.refresh(guideline)
    return schemas.GuidelineOut.model_validate(guideline)


async def get_org_guideline(db: AsyncSession, org_id: int, guideline_id: int) -> models.BrandGuideline:
    guideline = await db.scalar(
        select(models.BrandGuideline).where(
            models.BrandGuideline.id == guideline_id,
            models.BrandGuideline.org_id == org_id,
        )
    )
    if guideline is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Guideline not found")
    return guideline


@router.get("/{guideline_id}/download")
async def download_guideline(
    guideline_id: int,
    ctx: OrgContext = Depends(require_roles(*models.MEMBER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    guideline = await get_org_guideline(db, ctx.org_id, guideline_id)
    path = files.upload_path(ctx.org_id, SUBDIR, guideline.file_stored)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Stored file is missing")
    return FileResponse(path, filename=guideline.file_name, media_type=guideline.content_type)


@router.delete("/{guideline_id}", response_model=schemas.Message)
async def delete_guideline(
    guideline_id: int,
    ctx: OrgContext = Depends(require_roles(models.ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> schemas.Message:
    guideline = await get_org_guideline(db, ctx.org_id, guideline_id)
    await log_audit(
        db,
        org_id=ctx.org_id,
        user_id=ctx.user.id,
        action="guideline.deleted",
        entity_type="brand_guideline",
        entity_id=guideline.id,
        details={"title": guideline.title},
    )
    files.delete_upload(ctx.org_id, SUBDIR, guideline.file_stored)
    await db.delete(guideline)
    await db.commit()
    return schemas.Message(detail="Guideline deleted")
