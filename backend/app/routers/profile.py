from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.audit import log_audit
from app.database import get_db
from app.deps import OrgContext, require_roles

router = APIRouter(prefix="/api/brand/profile", tags=["brand-profile"])


@router.get("", response_model=schemas.ProfileOut | None)
async def get_profile(
    ctx: OrgContext = Depends(require_roles(*models.MEMBER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> schemas.ProfileOut | None:
    profile = await db.scalar(
        select(models.BrandProfile).where(models.BrandProfile.org_id == ctx.org_id)
    )
    if profile is None:
        return None
    return schemas.ProfileOut.model_validate(profile)


@router.put("", response_model=schemas.ProfileOut)
async def upsert_profile(
    payload: schemas.ProfileIn,
    ctx: OrgContext = Depends(require_roles(models.ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> schemas.ProfileOut:
    profile = await db.scalar(
        select(models.BrandProfile).where(models.BrandProfile.org_id == ctx.org_id)
    )
    if profile is None:
        profile = models.BrandProfile(org_id=ctx.org_id)
        db.add(profile)
        action = "brand_profile.created"
    else:
        action = "brand_profile.updated"
    profile.name = payload.name.strip()
    profile.product_name = payload.product_name.strip()
    profile.tagline = payload.tagline.strip()
    profile.tone = payload.tone.strip()
    profile.description = payload.description.strip()
    await log_audit(
        db,
        org_id=ctx.org_id,
        user_id=ctx.user.id,
        action=action,
        entity_type="brand_profile",
        entity_id=ctx.org_id,
        details={"name": profile.name, "product_name": profile.product_name},
    )
    await db.commit()
    await db.refresh(profile)
    return schemas.ProfileOut.model_validate(profile)
