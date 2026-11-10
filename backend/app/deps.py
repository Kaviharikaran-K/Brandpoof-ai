from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.database import get_db
from app.security import TokenError, decode_token

COOKIE_NAME = "bp_token"


async def get_current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> models.User:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        auth = request.headers.get("Authorization")
        if auth and auth.lower().startswith("bearer "):
            token = auth[7:].strip()
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        payload = decode_token(token)
    except TokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid session payload")
    user = await db.get(models.User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    return user


class OrgContext:
    def __init__(self, org: models.Organisation, membership: models.OrganisationMember, user: models.User):
        self.org = org
        self.membership = membership
        self.user = user

    @property
    def org_id(self) -> int:
        return self.org.id

    @property
    def role(self) -> str:
        return self.membership.role


async def get_org_context(
    request: Request,
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrgContext:
    raw = request.headers.get("X-Org-Id")
    if raw is None:
        result = await db.execute(
            select(models.OrganisationMember)
            .where(models.OrganisationMember.user_id == user.id)
            .order_by(models.OrganisationMember.id)
            .limit(1)
        )
        membership = result.scalar_one_or_none()
        if membership is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not a member of any organisation")
    else:
        try:
            org_id = int(raw)
        except ValueError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "X-Org-Id header must be an integer")
        result = await db.execute(
            select(models.OrganisationMember).where(
                models.OrganisationMember.user_id == user.id,
                models.OrganisationMember.org_id == org_id,
            )
        )
        membership = result.scalar_one_or_none()
        if membership is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not a member of this organisation")
    org = await db.get(models.Organisation, membership.org_id)
    if org is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Organisation not found")
    return OrgContext(org, membership, user)


def require_roles(*roles: str):
    async def checker(ctx: OrgContext = Depends(get_org_context)) -> OrgContext:
        if ctx.role not in roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, f"This action requires one of the roles: {', '.join(roles)}"
            )
        return ctx

    return checker
