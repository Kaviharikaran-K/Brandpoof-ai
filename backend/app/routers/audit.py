from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.database import get_db
from app.deps import OrgContext, require_roles

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=list[schemas.AuditOut])
async def list_audit(
    entity_type: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    ctx: OrgContext = Depends(require_roles(models.ROLE_ADMIN, models.ROLE_REVIEWER)),
    db: AsyncSession = Depends(get_db),
) -> list[schemas.AuditOut]:
    stmt = (
        select(models.AuditLog, models.User.email)
        .outerjoin(models.User, models.User.id == models.AuditLog.user_id)
        .where(models.AuditLog.org_id == ctx.org_id)
        .order_by(models.AuditLog.id.desc())
        .limit(limit)
    )
    if entity_type:
        stmt = stmt.where(models.AuditLog.entity_type == entity_type)
    rows = (await db.execute(stmt)).all()
    return [
        schemas.AuditOut(
            id=log.id,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            details=log.details,
            user_email=email,
            created_at=log.created_at,
        )
        for log, email in rows
    ]
