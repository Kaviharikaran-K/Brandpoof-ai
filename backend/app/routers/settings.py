from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.audit import log_audit
from app.database import get_db
from app.deps import OrgContext, require_roles
from app.services.analysis.tone import llm_provider_configured

router = APIRouter(prefix="/api/settings", tags=["settings"])

AI_DISCLOSURE = (
    "BrandProof AI runs deterministic, rule-based checks by default. If an external LLM provider is "
    "configured by the server administrator AND an admin enables this consent toggle, submission "
    "text may be sent to that provider for advisory tone suggestions only. Uploaded documents are "
    "never executed, never used as system prompts, and are never sent to an LLM provider. No data "
    "leaves this server unless both conditions are met, and every suggestion is reviewed by a human."
)

AI_NOTE = (
    "Consent is per organisation and is recorded in the audit trail. Disable it at any time; nothing "
    "is sent while it is off, even if a provider key exists."
)


def _consent_payload(org: models.Organisation) -> schemas.AiConsentOut:
    return schemas.AiConsentOut(
        consent=org.llm_consent,
        provider_configured=llm_provider_configured(),
        disclosure=AI_DISCLOSURE,
        note=AI_NOTE,
        updated_at=org.updated_at,
    )


@router.get("/ai-consent", response_model=schemas.AiConsentOut)
async def get_ai_consent(
    ctx: OrgContext = Depends(require_roles(*models.MEMBER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> schemas.AiConsentOut:
    org = await db.get(models.Organisation, ctx.org_id)
    return _consent_payload(org)


@router.patch("/ai-consent", response_model=schemas.AiConsentOut)
async def update_ai_consent(
    payload: schemas.AiConsentIn,
    ctx: OrgContext = Depends(require_roles(models.ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> schemas.AiConsentOut:
    org = await db.get(models.Organisation, ctx.org_id)
    previous = org.llm_consent
    org.llm_consent = payload.consent
    await log_audit(
        db,
        org_id=ctx.org_id,
        user_id=ctx.user.id,
        action="settings.ai_consent_changed",
        entity_type="organisation",
        entity_id=str(ctx.org_id),
        details={"from": previous, "to": payload.consent},
    )
    await db.commit()
    await db.refresh(org)
    return _consent_payload(org)
