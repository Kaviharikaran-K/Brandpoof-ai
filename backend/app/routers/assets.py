from fastapi import APIRouter, Depends, File, Form, HTTPException, status, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.audit import log_audit
from app.database import get_db
from app.deps import OrgContext, require_roles
from app.services import files

router = APIRouter(prefix="/api/brand/assets", tags=["brand-assets"])

LOGO_SUBDIR = files.LOGO_SUBDIR


@router.get("", response_model=list[schemas.AssetOut])
async def list_assets(
    ctx: OrgContext = Depends(require_roles(*models.MEMBER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> list[schemas.AssetOut]:
    rows = (
        await db.execute(
            select(models.ApprovedAsset)
            .where(models.ApprovedAsset.org_id == ctx.org_id)
            .order_by(models.ApprovedAsset.id)
            .limit(500)
        )
    ).scalars().all()
    return [schemas.AssetOut.model_validate(a) for a in rows]


@router.post("/colours", response_model=schemas.AssetOut, status_code=status.HTTP_201_CREATED)
async def create_colour(
    payload: schemas.AssetColourIn,
    ctx: OrgContext = Depends(require_roles(models.ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> schemas.AssetOut:
    asset = models.ApprovedAsset(
        org_id=ctx.org_id,
        asset_type="colour",
        name=payload.name.strip(),
        colour_value=payload.colour_value.upper(),
        created_by_id=ctx.user.id,
    )
    db.add(asset)
    await db.flush()
    await log_audit(
        db,
        org_id=ctx.org_id,
        user_id=ctx.user.id,
        action="asset.created",
        entity_type="approved_asset",
        entity_id=asset.id,
        details={"asset_type": "colour", "name": asset.name, "colour_value": asset.colour_value},
    )
    await db.commit()
    await db.refresh(asset)
    return schemas.AssetOut.model_validate(asset)


@router.post("/logos", response_model=schemas.AssetOut, status_code=status.HTTP_201_CREATED)
async def upload_logo(
    name: str = Form(min_length=1, max_length=160),
    file: UploadFile = File(...),
    ctx: OrgContext = Depends(require_roles(models.ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> schemas.AssetOut:
    stored, original, content_type, size = await files.save_upload(
        ctx.org_id, LOGO_SUBDIR, file, files.ALLOWED_IMAGE_TYPES
    )
    asset = models.ApprovedAsset(
        org_id=ctx.org_id,
        asset_type="logo",
        name=name.strip(),
        file_stored=stored,
        file_name=original,
        content_type=content_type,
        size_bytes=size,
        created_by_id=ctx.user.id,
    )
    db.add(asset)
    await db.flush()
    await log_audit(
        db,
        org_id=ctx.org_id,
        user_id=ctx.user.id,
        action="asset.created",
        entity_type="approved_asset",
        entity_id=asset.id,
        details={"asset_type": "logo", "name": asset.name, "file_name": original},
    )
    await db.commit()
    await db.refresh(asset)
    return schemas.AssetOut.model_validate(asset)


async def get_org_asset(db: AsyncSession, org_id: int, asset_id: int) -> models.ApprovedAsset:
    asset = await db.scalar(
        select(models.ApprovedAsset).where(
            models.ApprovedAsset.id == asset_id,
            models.ApprovedAsset.org_id == org_id,
        )
    )
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Asset not found")
    return asset


@router.get("/logos/{asset_id}/file")
async def download_logo(
    asset_id: int,
    ctx: OrgContext = Depends(require_roles(*models.MEMBER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    asset = await get_org_asset(db, ctx.org_id, asset_id)
    if asset.asset_type != "logo" or not asset.file_stored:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Logo file not found")
    path = files.upload_path(ctx.org_id, LOGO_SUBDIR, asset.file_stored)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Stored file is missing")
    return FileResponse(path, filename=asset.file_name or "logo", media_type=asset.content_type)


@router.delete("/{asset_id}", response_model=schemas.Message)
async def delete_asset(
    asset_id: int,
    ctx: OrgContext = Depends(require_roles(models.ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> schemas.Message:
    asset = await get_org_asset(db, ctx.org_id, asset_id)
    await log_audit(
        db,
        org_id=ctx.org_id,
        user_id=ctx.user.id,
        action="asset.deleted",
        entity_type="approved_asset",
        entity_id=asset.id,
        details={"name": asset.name, "asset_type": asset.asset_type},
    )
    if asset.asset_type == "logo" and asset.file_stored:
        files.delete_upload(ctx.org_id, LOGO_SUBDIR, asset.file_stored)
    await db.delete(asset)
    await db.commit()
    return schemas.Message(detail="Asset deleted")
