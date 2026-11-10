import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.audit import log_audit
from app.database import get_db
from app.deps import COOKIE_NAME, get_current_user
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return cleaned or "org"


def set_auth_cookie(response: Response, token: str) -> None:
    from app.config import get_settings

    settings = get_settings()
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure or settings.environment == "production",
        path="/",
    )


async def memberships_for(db: AsyncSession, user: models.User) -> list[schemas.MembershipOut]:
    result = await db.execute(
        select(models.OrganisationMember, models.Organisation)
        .join(models.Organisation, models.Organisation.id == models.OrganisationMember.org_id)
        .where(models.OrganisationMember.user_id == user.id)
        .order_by(models.OrganisationMember.id)
    )
    rows = result.all()
    return [
        schemas.MembershipOut(
            org_id=org.id, org_name=org.name, slug=org.slug, role=member.role
        )
        for member, org in rows
    ]


def me_payload(user: models.User, memberships: list[schemas.MembershipOut]) -> schemas.MeOut:
    return schemas.MeOut(
        user=schemas.UserOut(id=user.id, email=user.email, full_name=user.full_name),
        memberships=memberships,
    )


@router.post("/register", response_model=schemas.MeOut, status_code=status.HTTP_201_CREATED)
async def register(
    payload: schemas.RegisterIn, response: Response, db: AsyncSession = Depends(get_db)
) -> schemas.MeOut:
    email = payload.email.lower()
    existing = await db.scalar(select(models.User).where(models.User.email == email))
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    user = models.User(
        email=email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name.strip(),
    )
    db.add(user)
    await db.flush()
    first_name = payload.full_name.strip().split()[0] if payload.full_name.strip() else "New"
    org = models.Organisation(
        name=f"{first_name}'s Organisation",
        slug=f"{slugify(first_name)}-{uuid.uuid4().hex[:6]}",
    )
    db.add(org)
    await db.flush()
    membership = models.OrganisationMember(org_id=org.id, user_id=user.id, role=models.ROLE_ADMIN)
    db.add(membership)
    await log_audit(
        db,
        org_id=org.id,
        user_id=user.id,
        action="user.registered",
        entity_type="user",
        entity_id=user.id,
        details={"email": email},
    )
    await db.commit()
    await db.refresh(user)
    set_auth_cookie(response, create_access_token(user.id))
    return me_payload(user, await memberships_for(db, user))


@router.post("/login", response_model=schemas.MeOut)
async def login(
    payload: schemas.LoginIn, response: Response, db: AsyncSession = Depends(get_db)
) -> schemas.MeOut:
    email = payload.email.lower()
    user = await db.scalar(select(models.User).where(models.User.email == email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account is inactive")
    set_auth_cookie(response, create_access_token(user.id))
    return me_payload(user, await memberships_for(db, user))


@router.post("/logout", response_model=schemas.Message)
async def logout(response: Response) -> schemas.Message:
    response.delete_cookie(COOKIE_NAME, path="/")
    return schemas.Message(detail="Logged out")


@router.get("/me", response_model=schemas.MeOut)
async def me(
    user: models.User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> schemas.MeOut:
    return me_payload(user, await memberships_for(db, user))
