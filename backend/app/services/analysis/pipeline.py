from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.services.analysis.claims import extract_claims
from app.services.analysis.common import CATEGORY_MISSING_CONFLICTING
from app.services.analysis.terminology import check_terminology
from app.services.analysis.textprep import normalise
from app.services.analysis.tone import check_tone
from app.services.analysis.verification import verify_claims


class AnalysisResult:
    def __init__(
        self,
        engine: str,
        findings: list[dict],
        normalised_text: str,
        disclosure: str | None = None,
    ):
        self.engine = engine
        self.findings = findings
        self.normalised_text = normalised_text
        self.disclosure = disclosure


def _mark_ocr_findings(findings: list[dict]) -> list[dict]:
    marked: list[dict] = []
    for finding in findings:
        if finding["category"] == CATEGORY_MISSING_CONFLICTING:
            continue
        finding["start_offset"] = 0
        finding["end_offset"] = 0
        finding["needs_human_review"] = True
        finding["explanation"] = (
            "[Text extracted from the attached image] " + finding["explanation"]
        )
        evidence = dict(finding.get("evidence") or {})
        evidence["source"] = "image_ocr"
        finding["evidence"] = evidence
        marked.append(finding)
    return marked


async def analyse_text(
    db: AsyncSession,
    org_id: int,
    text: str,
    *,
    llm_consent: bool = False,
    extra_text: str | None = None,
) -> AnalysisResult:
    normalised = normalise(text)
    facts = list(
        (
            await db.execute(
                select(models.ApprovedFact)
                .where(models.ApprovedFact.org_id == org_id)
                .order_by(models.ApprovedFact.id)
            )
        )
        .scalars()
        .all()
    )
    terms = list(
        (
            await db.execute(
                select(models.ApprovedTerm)
                .where(models.ApprovedTerm.org_id == org_id)
                .order_by(models.ApprovedTerm.id)
            )
        )
        .scalars()
        .all()
    )

    findings: list[dict] = []
    findings.extend(check_terminology(normalised, terms))
    tone_findings, engine, disclosure = check_tone(normalised, llm_consent)
    findings.extend(tone_findings)
    claims = extract_claims(normalised)
    findings.extend(verify_claims(claims, facts))

    if extra_text:
        normalised_extra = normalise(extra_text)
        extra_findings: list[dict] = []
        extra_findings.extend(check_terminology(normalised_extra, terms))
        extra_findings.extend(check_tone(normalised_extra, llm_consent)[0])
        extra_findings.extend(verify_claims(extract_claims(normalised_extra), facts))
        findings.extend(_mark_ocr_findings(extra_findings))

    return AnalysisResult(
        engine=engine,
        findings=findings,
        normalised_text=normalised,
        disclosure=disclosure,
    )
