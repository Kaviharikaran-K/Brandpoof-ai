import datetime as dt
import re
import uuid
from typing import Any

CATEGORY_FACTUAL_MISMATCH = "Factual mismatch"
CATEGORY_OUTDATED = "Outdated information"
CATEGORY_TERMINOLOGY = "Terminology violation"
CATEGORY_TONE = "Tone inconsistency"
CATEGORY_UNSUPPORTED = "Unsupported promotional claim"
CATEGORY_VISUAL = "Visual inconsistency"
CATEGORY_ACCESSIBILITY = "Accessibility issue"
CATEGORY_MISSING_CONFLICTING = "Missing or conflicting guideline"

SEVERITY_CRITICAL = "Critical"
SEVERITY_MAJOR = "Major"
SEVERITY_MINOR = "Minor"
SEVERITY_INFO = "Information"


def make_finding_id() -> str:
    return f"FND-{uuid.uuid4().hex[:8].upper()}"


def _norm_value(value: str) -> str:
    text = value.strip().lower()
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = text.replace(",", "")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*/\s*", "/", text)
    return text


def values_match(claim_value: str, approved_value: str) -> bool:
    a = _norm_value(claim_value)
    b = _norm_value(approved_value)
    if a == b:
        return True

    def strip_trailing(v: str) -> str:
        v = v.strip()
        if v.endswith("%"):
            v = v[:-1].strip()
        v = re.sub(r"\b(users?|uptime|hours?|support|percent)\b", "", v)
        return _norm_value(v)

    return strip_trailing(a) == strip_trailing(b)


def leading_number(value: str) -> float | None:
    match = re.search(r"[0-9][0-9,]*(?:\.[0-9]+)?", value)
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None


def is_overstatement(claim_value: str, approved_value: str, factor: float = 2.0) -> bool:
    claim_num = leading_number(claim_value)
    fact_num = leading_number(approved_value)
    if claim_num is None or fact_num is None or fact_num <= 0:
        return False
    return claim_num >= factor * fact_num


def is_fact_expired(fact: Any, today: dt.date | None = None) -> bool:
    if today is None:
        today = dt.date.today()
    expiry = getattr(fact, "expiry_date", None)
    return expiry is not None and expiry < today


def is_fact_effective(fact: Any, today: dt.date | None = None) -> bool:
    if today is None:
        today = dt.date.today()
    effective = getattr(fact, "effective_date", None)
    return effective is None or effective <= today


def fact_evidence(fact: Any) -> dict[str, Any]:
    return {
        "fact_id": getattr(fact, "fact_id", None),
        "name": getattr(fact, "name", None),
        "value": getattr(fact, "approved_value", None),
        "source_ref": getattr(fact, "source_ref", None),
        "version": getattr(fact, "version", None),
        "effective_date": str(getattr(fact, "effective_date", None) or ""),
        "expiry_date": str(getattr(fact, "expiry_date", None) or ""),
        "approval_status": getattr(fact, "approval_status", None),
    }
