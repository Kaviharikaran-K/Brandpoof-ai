import re
from typing import Any

from app.services.analysis.common import (
    CATEGORY_FACTUAL_MISMATCH,
    CATEGORY_MISSING_CONFLICTING,
    CATEGORY_OUTDATED,
    SEVERITY_CRITICAL,
    SEVERITY_MAJOR,
    fact_evidence,
    is_fact_effective,
    is_fact_expired,
    is_overstatement,
    make_finding_id,
    values_match,
)

from app.services.analysis.claims import Claim

TOPIC_KEYWORDS: dict[str, list[str]] = {
    "capacity": ["user", "users", "capacity", "tenant", "tenants", "seat", "seats", "maximum", "max", "account", "accounts"],
    "availability": ["availability", "uptime", "sla"],
    "support": ["support", "hours", "24/7", "24x7", "helpdesk"],
    "promise": ["guarantee", "guaranteed", "best", "promise", "unlimited"],
    "generic": [],
}


def _fact_matches_topic(fact: Any, topic: str) -> bool:
    keywords = TOPIC_KEYWORDS.get(topic, [])
    if not keywords:
        return False
    haystack = f"{fact.name} {fact.approved_value} {fact.description}".lower()
    return any(re.search(rf"\b{re.escape(kw)}\b", haystack) for kw in keywords)


def _evidence_map(facts: list[Any]) -> list[dict]:
    return [fact_evidence(f) for f in facts]


def _clarification_finding(claim: Claim, explanation: str, evidence: list[dict] | None = None) -> dict:
    return {
        "finding_id": make_finding_id(),
        "category": CATEGORY_MISSING_CONFLICTING,
        "severity": SEVERITY_MAJOR,
        "detected_text": claim.text,
        "start_offset": claim.start,
        "end_offset": claim.end,
        "evidence": {"related_facts": evidence or [], "claim": {"topic": claim.topic, "value": claim.value}},
        "explanation": explanation,
        "suggested_correction": None,
        "confidence": "high",
        "review_status": "open",
        "requires_clarification": True,
    }


def _outdated_finding(claim: Claim, facts: list[Any]) -> dict:
    return {
        "finding_id": make_finding_id(),
        "category": CATEGORY_OUTDATED,
        "severity": SEVERITY_MAJOR,
        "detected_text": claim.text,
        "start_offset": claim.start,
        "end_offset": claim.end,
        "evidence": {"related_facts": _evidence_map(facts)},
        "explanation": (
            f'The approved fact supporting "{claim.text}" has expired. '
            "Update the source and confirm a current fact before publishing."
        ),
        "suggested_correction": None,
        "confidence": "high",
        "review_status": "open",
        "requires_clarification": True,
    }


def verify_claim(claim: Claim, facts: list[Any], today=None) -> dict | None:
    if claim.kind == "promotional":
        related = [
            f
            for f in facts
            if f.approval_status == "approved" and _fact_matches_topic(f, claim.topic)
        ]
        if not related:
            return _clarification_finding(
                claim,
                "Clarification Required: No reliable approved evidence found. "
                f'The promotional claim "{claim.text}" cannot be verified against an approved fact.',
            )
        if any(is_fact_expired(f, today) for f in related):
            return _outdated_finding(claim, [f for f in related if is_fact_expired(f, today)])
        return None

    relevant = [f for f in facts if _fact_matches_topic(f, claim.topic)]
    approved = [f for f in relevant if f.approval_status == "approved" and is_fact_effective(f, today)]

    if not relevant:
        return _clarification_finding(
            claim,
            "Clarification Required: No reliable approved evidence found. "
            f'No approved fact exists for the claim "{claim.text}".',
        )

    if not approved:
        if any(f.approval_status == "pending" for f in relevant):
            return _clarification_finding(
                claim,
                "Clarification Required: No reliable approved evidence found. "
                f'A matching fact for "{claim.text}" exists but has not been confirmed by an admin.',
                _evidence_map(relevant),
            )
        return _clarification_finding(
            claim,
            "Clarification Required: No reliable approved evidence found. "
            f'No confirmed, effective fact supports the claim "{claim.text}".',
            _evidence_map(relevant),
        )

    expired = [f for f in approved if is_fact_expired(f, today)]
    active = [f for f in approved if not is_fact_expired(f, today)]
    if expired and not active:
        return _outdated_finding(claim, expired)

    grouped: dict[str, list[Any]] = {}
    for fact in active:
        grouped.setdefault(fact.approved_value.strip().lower(), []).append(fact)
    if len(grouped) > 1:
        return _clarification_finding(
            claim,
            "Clarification Required: No reliable approved evidence found. "
            f'Multiple approved facts conflict for "{claim.text}"; a reviewer must resolve the conflict.',
            _evidence_map(active),
        )

    canonical = active[0]
    if values_match(claim.value, canonical.approved_value):
        return None

    severity = SEVERITY_MAJOR
    if is_overstatement(claim.value, canonical.approved_value):
        severity = SEVERITY_CRITICAL

    return {
        "finding_id": make_finding_id(),
        "category": CATEGORY_FACTUAL_MISMATCH,
        "severity": severity,
        "detected_text": claim.text,
        "start_offset": claim.start,
        "end_offset": claim.end,
        "evidence": fact_evidence(canonical),
        "explanation": (
            f'The claim states "{claim.text}" but the approved fact {canonical.fact_id} '
            f'({canonical.name}) records the value as "{canonical.approved_value}" '
            f'(source: {canonical.source_ref or "unspecified"}, version {canonical.version}).'
        ),
        "suggested_correction": canonical.approved_value,
        "confidence": "high",
        "review_status": "open",
        "requires_clarification": False,
    }


def verify_claims(claims: list[Claim], facts: list[Any], today=None) -> list[dict]:
    findings: list[dict] = []
    seen: set[tuple[str, int, int]] = set()
    for claim in claims:
        key = (claim.topic, claim.start, claim.end)
        if key in seen:
            continue
        finding = verify_claim(claim, facts, today=today)
        if finding is not None:
            seen.add(key)
            findings.append(finding)
    return findings
