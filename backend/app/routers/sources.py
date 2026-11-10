from fastapi import APIRouter, Depends, File, Form, HTTPException, status, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.audit import log_audit
from app.database import get_db
from app.deps import OrgContext, require_roles
from app.services import files

router = APIRouter(prefix="/api/brand/sources", tags=["brand-sources"])

SUBDIR = "sources"


@router.get("", response_model=list[schemas.SourceOut])
async def list_sources(
    ctx: OrgContext = Depends(require_roles(*models.MEMBER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> list[schemas.SourceOut]:
    rows = (
        await db.execute(
            select(models.SourceDocument)
            .where(models.SourceDocument.org_id == ctx.org_id)
            .order_by(models.SourceDocument.id.desc())
            .limit(200)
        )
    ).scalars().all()
    return [schemas.SourceOut.model_validate(s) for s in rows]


@router.post("", response_model=schemas.SourceOut, status_code=status.HTTP_201_CREATED)
async def upload_source(
    title: str = Form(default="", max_length=160),
    file: UploadFile = File(...),
    ctx: OrgContext = Depends(require_roles(models.ROLE_ADMIN, models.ROLE_CREATOR)),
    db: AsyncSession = Depends(get_db),
) -> schemas.SourceOut:
    stored, original, content_type, size = await files.save_upload(
        ctx.org_id, SUBDIR, file, files.ALLOWED_DOC_TYPES
    )
    source = models.SourceDocument(
        org_id=ctx.org_id,
        title=title.strip() or original,
        file_stored=stored,
        file_name=original,
        content_type=content_type,
        size_bytes=size,
        uploaded_by_id=ctx.user.id,
    )
    db.add(source)
    await db.flush()
    await log_audit(
        db,
        org_id=ctx.org_id,
        user_id=ctx.user.id,
        action="source_document.uploaded",
        entity_type="source_document",
        entity_id=source.id,
        details={"title": source.title, "file_name": original, "size_bytes": size},
    )
    await db.commit()
    await db.refresh(source)
    return schemas.SourceOut.model_validate(source)


async def get_org_source(db: AsyncSession, org_id: int, source_id: int) -> models.SourceDocument:
    source = await db.scalar(
        select(models.SourceDocument).where(
            models.SourceDocument.id == source_id,
            models.SourceDocument.org_id == org_id,
        )
    )
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source document not found")
    return source


@router.get("/{source_id}/download")
async def download_source(
    source_id: int,
    ctx: OrgContext = Depends(require_roles(*models.MEMBER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    source = await get_org_source(db, ctx.org_id, source_id)
    path = files.upload_path(ctx.org_id, SUBDIR, source.file_stored)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Stored file is missing")
    return FileResponse(path, filename=source.file_name, media_type=source.content_type)


@router.delete("/{source_id}", response_model=schemas.Message)
async def delete_source(
    source_id: int,
    ctx: OrgContext = Depends(require_roles(models.ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> schemas.Message:
    source = await get_org_source(db, ctx.org_id, source_id)
    await log_audit(
        db,
        org_id=ctx.org_id,
        user_id=ctx.user.id,
        action="source_document.deleted",
        entity_type="source_document",
        entity_id=source.id,
        details={"title": source.title},
    )
    files.delete_upload(ctx.org_id, SUBDIR, source.file_stored)
    await db.delete(source)
    await db.commit()
    return schemas.Message(detail="Source document deleted")
