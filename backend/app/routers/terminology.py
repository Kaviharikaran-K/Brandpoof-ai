from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.audit import log_audit
from app.database import get_db
from app.deps import OrgContext, require_roles

router = APIRouter(prefix="/api/brand/terminology", tags=["brand-terminology"])


async def get_org_term(db: AsyncSession, org_id: int, term_pk: int) -> models.ApprovedTerm:
    term = await db.scalar(
        select(models.ApprovedTerm).where(
            models.ApprovedTerm.id == term_pk, models.ApprovedTerm.org_id == org_id
        )
    )
    if term is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Terminology rule not found")
    return term


@router.get("", response_model=list[schemas.TermOut])
async def list_terms(
    ctx: OrgContext = Depends(require_roles(*models.MEMBER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> list[schemas.TermOut]:
    terms = (
        await db.execute(
            select(models.ApprovedTerm)
            .where(models.ApprovedTerm.org_id == ctx.org_id)
            .order_by(models.ApprovedTerm.id)
            .limit(500)
        )
    ).scalars().all()
    return [schemas.TermOut.model_validate(t) for t in terms]


@router.post("", response_model=schemas.TermOut, status_code=status.HTTP_201_CREATED)
async def create_term(
    payload: schemas.TermIn,
    ctx: OrgContext = Depends(require_roles(models.ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> schemas.TermOut:
    duplicate = await db.scalar(
        select(models.ApprovedTerm).where(
            models.ApprovedTerm.org_id == ctx.org_id,
            models.ApprovedTerm.rule_type == payload.rule_type,
            func.lower(models.ApprovedTerm.term) == payload.term.lower(),
        )
    )
    if duplicate is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This terminology rule already exists")
    term = models.ApprovedTerm(
        org_id=ctx.org_id,
        rule_type=payload.rule_type,
        term=payload.term,
        description=payload.description.strip(),
        created_by_id=ctx.user.id,
    )
    db.add(term)
    await db.flush()
    await log_audit(
        db,
        org_id=ctx.org_id,
        user_id=ctx.user.id,
        action="terminology.created",
        entity_type="approved_term",
        entity_id=term.id,
        details={"rule_type": term.rule_type, "term": term.term},
    )
    await db.commit()
    await db.refresh(term)
    return schemas.TermOut.model_validate(term)


@router.put("/{term_pk}", response_model=schemas.TermOut)
async def update_term(
    term_pk: int,
    payload: schemas.TermUpdateIn,
    ctx: OrgContext = Depends(require_roles(models.ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> schemas.TermOut:
    term = await get_org_term(db, ctx.org_id, term_pk)
    if payload.rule_type is not None:
        term.rule_type = payload.rule_type
    if payload.term is not None:
        term.term = payload.term
    if payload.description is not None:
        term.description = payload.description.strip()
    await log_audit(
        db,
        org_id=ctx.org_id,
        user_id=ctx.user.id,
        action="terminology.updated",
        entity_type="approved_term",
        entity_id=term.id,
        details={"term": term.term, "rule_type": term.rule_type},
    )
    await db.commit()
    await db.refresh(term)
    return schemas.TermOut.model_validate(term)


@router.delete("/{term_pk}", response_model=schemas.Message)
async def delete_term(
    term_pk: int,
    ctx: OrgContext = Depends(require_roles(models.ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> schemas.Message:
    term = await get_org_term(db, ctx.org_id, term_pk)
    await log_audit(
        db,
        org_id=ctx.org_id,
        user_id=ctx.user.id,
        action="terminology.deleted",
        entity_type="approved_term",
        entity_id=term.id,
        details={"term": term.term},
    )
    await db.delete(term)
    await db.commit()
    return schemas.Message(detail="Terminology rule deleted")
