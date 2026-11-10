import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.audit import log_audit
from app.database import get_db
from app.deps import get_current_user

router = APIRouter(prefix="/api/organisations", tags=["organisations"])


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return cleaned or "org"


async def require_membership(db: AsyncSession, user: models.User, org_id: int) -> models.OrganisationMember:
    membership = await db.scalar(
        select(models.OrganisationMember).where(
            models.OrganisationMember.user_id == user.id,
            models.OrganisationMember.org_id == org_id,
        )
    )
    if membership is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not a member of this organisation")
    return membership


@router.post("", response_model=schemas.OrgOut, status_code=status.HTTP_201_CREATED)
async def create_organisation(
    payload: schemas.OrgCreate,
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.OrgOut:
    org = models.Organisation(name=payload.name.strip(), slug=f"{slugify(payload.name)}-{uuid.uuid4().hex[:6]}")
    db.add(org)
    await db.flush()
    db.add(models.OrganisationMember(org_id=org.id, user_id=user.id, role=models.ROLE_ADMIN))
    await log_audit(
        db,
        org_id=org.id,
        user_id=user.id,
        action="organisation.created",
        entity_type="organisation",
        entity_id=org.id,
        details={"name": org.name},
    )
    await db.commit()
    await db.refresh(org)
    return schemas.OrgOut(id=org.id, name=org.name, slug=org.slug, role=models.ROLE_ADMIN, created_at=org.created_at)


@router.get("", response_model=list[schemas.OrgOut])
async def list_organisations(
    user: models.User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[schemas.OrgOut]:
    result = await db.execute(
        select(models.OrganisationMember, models.Organisation)
        .join(models.Organisation, models.Organisation.id == models.OrganisationMember.org_id)
        .where(models.OrganisationMember.user_id == user.id)
        .order_by(models.OrganisationMember.id)
    )
    return [
        schemas.OrgOut(
            id=org.id,
            name=org.name,
            slug=org.slug,
            role=member.role,
            created_at=org.created_at,
        )
        for member, org in result.all()
    ]


@router.get("/{org_id}/members", response_model=list[schemas.MemberOut])
async def list_members(
    org_id: int,
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[schemas.MemberOut]:
    await require_membership(db, user, org_id)
    result = await db.execute(
        select(models.OrganisationMember, models.User)
        .join(models.User, models.User.id == models.OrganisationMember.user_id)
        .where(models.OrganisationMember.org_id == org_id)
        .order_by(models.OrganisationMember.id)
    )
    return [
        schemas.MemberOut(
            user_id=member.user_id,
            email=usr.email,
            full_name=usr.full_name,
            role=member.role,
            joined_at=member.created_at,
        )
        for member, usr in result.all()
    ]


@router.post("/{org_id}/members", response_model=schemas.MemberOut, status_code=status.HTTP_201_CREATED)
async def add_member(
    org_id: int,
    payload: schemas.MemberAddIn,
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.MemberOut:
    membership = await require_membership(db, user, org_id)
    if membership.role != models.ROLE_ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only admins can manage members")
    target = await db.scalar(select(models.User).where(models.User.email == payload.email.lower()))
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No user account exists with that email")
    existing = await db.scalar(
        select(models.OrganisationMember).where(
            models.OrganisationMember.org_id == org_id,
            models.OrganisationMember.user_id == target.id,
        )
    )
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This user is already a member")
    new_member = models.OrganisationMember(org_id=org_id, user_id=target.id, role=payload.role)
    db.add(new_member)
    await log_audit(
        db,
        org_id=org_id,
        user_id=user.id,
        action="member.added",
        entity_type="organisation_member",
        entity_id=target.id,
        details={"email": target.email, "role": payload.role},
    )
    await db.commit()
    await db.refresh(new_member)
    return schemas.MemberOut(
        user_id=target.id,
        email=target.email,
        full_name=target.full_name,
        role=new_member.role,
        joined_at=new_member.created_at,
    )


@router.patch("/{org_id}/members/{user_id}", response_model=schemas.MemberOut)
async def update_member_role(
    org_id: int,
    user_id: int,
    payload: schemas.MemberUpdateIn,
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.MemberOut:
    membership = await require_membership(db, user, org_id)
    if membership.role != models.ROLE_ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only admins can manage members")
    target_membership = await db.scalar(
        select(models.OrganisationMember).where(
            models.OrganisationMember.org_id == org_id,
            models.OrganisationMember.user_id == user_id,
        )
    )
    if target_membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    old_role = target_membership.role
    if old_role == models.ROLE_ADMIN and payload.role != models.ROLE_ADMIN:
        admin_count = await db.scalar(
            select(func.count()).select_from(models.OrganisationMember).where(
                models.OrganisationMember.org_id == org_id,
                models.OrganisationMember.role == models.ROLE_ADMIN,
            )
        )
        if admin_count <= 1:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "An organisation must keep at least one admin")
    target_membership.role = payload.role
    await log_audit(
        db,
        org_id=org_id,
        user_id=user.id,
        action="member.role_updated",
        entity_type="organisation_member",
        entity_id=user_id,
        details={"from": old_role, "to": payload.role},
    )
    await db.commit()
    await db.refresh(target_membership)
    target_user = await db.get(models.User, user_id)
    return schemas.MemberOut(
        user_id=user_id,
        email=target_user.email if target_user else "",
        full_name=target_user.full_name if target_user else "",
        role=target_membership.role,
        joined_at=target_membership.created_at,
    )


@router.delete("/{org_id}/members/{user_id}", response_model=schemas.Message)
async def remove_member(
    org_id: int,
    user_id: int,
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.Message:
    membership = await require_membership(db, user, org_id)
    if membership.role != models.ROLE_ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only admins can manage members")
    target_membership = await db.scalar(
        select(models.OrganisationMember).where(
            models.OrganisationMember.org_id == org_id,
            models.OrganisationMember.user_id == user_id,
        )
    )
    if target_membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    if target_membership.role == models.ROLE_ADMIN:
        admin_count = await db.scalar(
            select(func.count()).select_from(models.OrganisationMember).where(
                models.OrganisationMember.org_id == org_id,
                models.OrganisationMember.role == models.ROLE_ADMIN,
            )
        )
        if admin_count <= 1:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "An organisation must keep at least one admin")
    await db.delete(target_membership)
    await log_audit(
        db,
        org_id=org_id,
        user_id=user.id,
        action="member.removed",
        entity_type="organisation_member",
        entity_id=user_id,
        details={},
    )
    await db.commit()
    return schemas.Message(detail="Member removed")
