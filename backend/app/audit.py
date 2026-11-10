from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app import models


async def log_audit(
    db: AsyncSession,
    *,
    org_id: int | None,
    user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    entry = models.AuditLog(
        org_id=org_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        details=details or {},
    )
    db.add(entry)
