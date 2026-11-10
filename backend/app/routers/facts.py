import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.audit import log_audit
from app.database import get_db
from app.deps import OrgContext, require_roles

router = APIRouter(prefix="/api/brand/facts", tags=["brand-facts"])


async def get_org_fact(db: AsyncSession, org_id: int, fact_pk: int) -> models.ApprovedFact:
    fact = await db.scalar(
        select(models.ApprovedFact).where(
            models.ApprovedFact.id == fact_pk, models.ApprovedFact.org_id == org_id
        )
    )
    if fact is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fact not found")
    return fact


@router.get("", response_model=list[schemas.FactOut])
async def list_facts(
    status_filter: str | None = None,
    q: str | None = None,
    ctx: OrgContext = Depends(require_roles(*models.MEMBER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> list[schemas.FactOut]:
    stmt = select(models.ApprovedFact).where(models.ApprovedFact.org_id == ctx.org_id)
    if status_filter:
        stmt = stmt.where(models.ApprovedFact.approval_status == status_filter)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            (func.lower(models.ApprovedFact.name).like(like))
            | (func.lower(models.ApprovedFact.fact_id).like(like))
            | (func.lower(models.ApprovedFact.approved_value).like(like))
        )
    stmt = stmt.order_by(models.ApprovedFact.id.desc()).limit(500)
    facts = (await db.execute(stmt)).scalars().all()
    return [schemas.FactOut.model_validate(f) for f in facts]


@router.post("", response_model=schemas.FactOut, status_code=status.HTTP_201_CREATED)
async def create_fact(
    payload: schemas.FactIn,
    ctx: OrgContext = Depends(require_roles(models.ROLE_CREATOR, models.ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> schemas.FactOut:
    duplicate = await db.scalar(
        select(models.ApprovedFact).where(
            models.ApprovedFact.org_id == ctx.org_id,
            models.ApprovedFact.fact_id == payload.fact_id,
        )
    )
    if duplicate is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "A fact with this ID already exists in the organisation")
    fact = models.ApprovedFact(
        org_id=ctx.org_id,
        fact_id=payload.fact_id,
        name=payload.name.strip(),
        approved_value=payload.approved_value.strip(),
        description=payload.description.strip(),
        source_ref=payload.source_ref.strip(),
        version=payload.version,
        effective_date=payload.effective_date,
        expiry_date=payload.expiry_date,
        approval_status=models.FACT_PENDING,
        created_by_id=ctx.user.id,
    )
    db.add(fact)
    await db.flush()
    await log_audit(
        db,
        org_id=ctx.org_id,
        user_id=ctx.user.id,
        action="fact.created",
        entity_type="approved_fact",
        entity_id=fact.id,
        details={"fact_id": fact.fact_id, "name": fact.name, "status": fact.approval_status},
    )
    await db.commit()
    await db.refresh(fact)
    return schemas.FactOut.model_validate(fact)


@router.get("/{fact_pk}", response_model=schemas.FactOut)
async def get_fact(
    fact_pk: int,
    ctx: OrgContext = Depends(require_roles(*models.MEMBER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> schemas.FactOut:
    fact = await get_org_fact(db, ctx.org_id, fact_pk)
    return schemas.FactOut.model_validate(fact)


@router.put("/{fact_pk}", response_model=schemas.FactOut)
async def update_fact(
    fact_pk: int,
    payload: schemas.FactUpdateIn,
    ctx: OrgContext = Depends(require_roles(models.ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> schemas.FactOut:
    fact = await get_org_fact(db, ctx.org_id, fact_pk)
    if payload.fact_id is not None and payload.fact_id != fact.fact_id:
        duplicate = await db.scalar(
            select(models.ApprovedFact).where(
                models.ApprovedFact.org_id == ctx.org_id,
                models.ApprovedFact.fact_id == payload.fact_id,
            )
        )
        if duplicate is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "A fact with this ID already exists in the organisation")
        fact.fact_id = payload.fact_id
    if payload.name is not None:
        fact.name = payload.name.strip()
    if payload.approved_value is not None:
        fact.approved_value = payload.approved_value.strip()
    if payload.description is not None:
        fact.description = payload.description.strip()
    if payload.source_ref is not None:
        fact.source_ref = payload.source_ref.strip()
    if payload.version is not None:
        fact.version = payload.version
    else:
        fact.version = fact.version + 1
    if payload.effective_date is not None or payload.expiry_date is not None:
        fact.effective_date = payload.effective_date
        fact.expiry_date = payload.expiry_date
    fact.approval_status = models.FACT_PENDING
    fact.confirmed_by_id = None
    fact.confirmed_at = None
    await log_audit(
        db,
        org_id=ctx.org_id,
        user_id=ctx.user.id,
        action="fact.updated",
        entity_type="approved_fact",
        entity_id=fact.id,
        details={"fact_id": fact.fact_id, "version": fact.version, "status": fact.approval_status},
    )
    await db.commit()
    await db.refresh(fact)
    return schemas.FactOut.model_validate(fact)


@router.post("/{fact_pk}/confirm", response_model=schemas.FactOut)
async def confirm_fact(
    fact_pk: int,
    ctx: OrgContext = Depends(require_roles(models.ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> schemas.FactOut:
    fact = await get_org_fact(db, ctx.org_id, fact_pk)
    fact.approval_status = models.FACT_APPROVED
    fact.confirmed_by_id = ctx.user.id
    fact.confirmed_at = dt.datetime.now(dt.timezone.utc)
    await log_audit(
        db,
        org_id=ctx.org_id,
        user_id=ctx.user.id,
        action="fact.confirmed",
        entity_type="approved_fact",
        entity_id=fact.id,
        details={"fact_id": fact.fact_id, "version": fact.version},
    )
    await db.commit()
    await db.refresh(fact)
    return schemas.FactOut.model_validate(fact)


@router.delete("/{fact_pk}", response_model=schemas.Message)
async def delete_fact(
    fact_pk: int,
    ctx: OrgContext = Depends(require_roles(models.ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> schemas.Message:
    fact = await get_org_fact(db, ctx.org_id, fact_pk)
    await log_audit(
        db,
        org_id=ctx.org_id,
        user_id=ctx.user.id,
        action="fact.deleted",
        entity_type="approved_fact",
        entity_id=fact.id,
        details={"fact_id": fact.fact_id, "name": fact.name},
    )
    await db.delete(fact)
    await db.commit()
    return schemas.Message(detail="Fact deleted")
