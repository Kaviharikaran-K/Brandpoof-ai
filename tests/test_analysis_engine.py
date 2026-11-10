import datetime as dt
from types import SimpleNamespace

from app.services.analysis.claims import extract_claims
from app.services.analysis.common import (
    CATEGORY_FACTUAL_MISMATCH,
    CATEGORY_MISSING_CONFLICTING,
    CATEGORY_OUTDATED,
    CATEGORY_TERMINOLOGY,
    CATEGORY_TONE,
    SEVERITY_CRITICAL,
    SEVERITY_MAJOR,
    SEVERITY_MINOR,
    values_match,
)
from app.services.analysis.terminology import check_terminology
from app.services.analysis.tone import check_tone
from app.services.analysis.verification import verify_claims


def fact(
    fact_id="NC-FR-001",
    name="Maximum supported users",
    approved_value="5,000",
    description="NovaCloud supports up to 5,000 users per tenant.",
    approval_status="approved",
    expiry_date=None,
):
    return SimpleNamespace(
        fact_id=fact_id,
        name=name,
        approved_value=approved_value,
        description=description,
        source_ref="Product Handbook v2.1",
        version=2,
        effective_date=dt.date(2025, 1, 1),
        expiry_date=expiry_date,
        approval_status=approval_status,
    )


def term(rule_type, word, description=""):
    return SimpleNamespace(id=1, rule_type=rule_type, term=word, description=description)


def test_claim_extraction_topics():
    claims = extract_claims(
        "NovaCloud now supports 50,000 users with 100% uptime and 24/7 support."
    )
    topics = {(c.topic, c.value) for c in claims}
    assert ("capacity", "50,000") in topics
    assert ("availability", "100%") in topics
    assert ("support", "24/7") in topics


def test_values_match_normalises_commas_and_units():
    assert values_match("5,000", "5000")
    assert values_match("99.5%", "99.5%")
    assert values_match("5,000 users", "5,000")
    assert not values_match("50,000", "5,000")


def test_case_a_matching_claim_produces_no_finding():
    findings = verify_claims(extract_claims("NovaCloud supports 5,000 users."), [fact()])
    assert findings == []


def test_case_b_mismatch_includes_evidence_and_correction():
    findings = verify_claims(extract_claims("NovaCloud supports 9,000 users."), [fact()])
    assert len(findings) == 1
    finding = findings[0]
    assert finding["category"] == CATEGORY_FACTUAL_MISMATCH
    assert finding["severity"] == SEVERITY_MAJOR
    assert finding["detected_text"] == "9,000 users"
    assert finding["suggested_correction"] == "5,000"
    assert finding["evidence"]["fact_id"] == "NC-FR-001"
    assert finding["evidence"]["source_ref"] == "Product Handbook v2.1"
    assert finding["requires_clarification"] is False


def test_case_b_overstatement_above_double_is_critical():
    findings = verify_claims(extract_claims("NovaCloud supports 50,000 users."), [fact()])
    assert len(findings) == 1
    assert findings[0]["severity"] == SEVERITY_CRITICAL


def test_case_c_no_fact_requires_clarification_without_correction():
    findings = verify_claims(extract_claims("NovaCloud supports 5,000 users."), [])
    assert len(findings) == 1
    finding = findings[0]
    assert finding["category"] == CATEGORY_MISSING_CONFLICTING
    assert finding["requires_clarification"] is True
    assert finding["suggested_correction"] is None
    assert finding["explanation"].startswith(
        "Clarification Required: No reliable approved evidence found."
    )


def test_case_d_conflicting_approved_facts_require_reviewer():
    facts = [
        fact(),
        fact(
            fact_id="NC-FR-009",
            name="User capacity (current)",
            approved_value="10,000",
            description="NovaCloud now supports 10,000 users per tenant.",
        ),
    ]
    findings = verify_claims(extract_claims("NovaCloud supports 5,000 users."), facts)
    assert len(findings) == 1
    assert findings[0]["category"] == CATEGORY_MISSING_CONFLICTING
    assert findings[0]["requires_clarification"] is True
    assert "conflict" in findings[0]["explanation"].lower()


def test_expired_fact_is_outdated_and_escalates():
    expired = fact(expiry_date=dt.date(2024, 1, 1))
    findings = verify_claims(extract_claims("NovaCloud supports 5,000 users."), [expired])
    assert len(findings) == 1
    assert findings[0]["category"] == CATEGORY_OUTDATED
    assert findings[0]["requires_clarification"] is True


def test_pending_fact_is_not_evidence():
    pending = fact(approval_status="pending")
    findings = verify_claims(extract_claims("NovaCloud supports 5,000 users."), [pending])
    assert len(findings) == 1
    assert findings[0]["requires_clarification"] is True
    assert "confirmed by an admin" in findings[0]["explanation"]


def test_terminology_prohibited_term_is_major_with_correction():
    findings = check_terminology(
        "Our consumer platform is ready.",
        [term("required", "Customer"), term("prohibited", "Consumer")],
    )
    prohibited = [f for f in findings if f["category"] == CATEGORY_TERMINOLOGY]
    assert len(prohibited) == 1
    assert prohibited[0]["severity"] == SEVERITY_MAJOR
    assert prohibited[0]["detected_text"].lower() == "consumer"
    assert "Customer" in prohibited[0]["suggested_correction"]


def test_terminology_is_case_insensitive_and_matches_plurals():
    findings = check_terminology(
        "CONSUMERS love it.",
        [term("prohibited", "Consumer")],
    )
    assert len(findings) == 1
    assert findings[0]["detected_text"].lower() == "consumers"


def test_required_term_missing_is_minor_guideline_gap():
    findings = check_terminology("Our buyers are happy.", [term("required", "Customer")])
    assert len(findings) == 1
    assert findings[0]["category"] == CATEGORY_MISSING_CONFLICTING
    assert findings[0]["severity"] == SEVERITY_MINOR
    assert findings[0]["requires_clarification"] is False


def test_required_term_present_passes():
    findings = check_terminology("Our customers are happy.", [term("required", "Customer")])
    assert findings == []


def test_tone_rules_and_engine_label():
    text = "Our AMAZING world-class platform is revolutionary!!!"
    findings, engine, disclosure = check_tone(text)
    rules = {f["evidence"]["rule"] for f in findings}
    assert "banned_phrase" in rules
    assert "exclamation_limit" in rules
    assert "all_caps" in rules
    assert all(f["category"] == CATEGORY_TONE for f in findings)
    assert all(f["severity"] == SEVERITY_MINOR for f in findings)
    assert engine == "Rule-based"
    assert disclosure is None


def test_tone_long_sentence_flagged():
    text = " ".join(["word"] * 40) + "."
    findings, _, _ = check_tone(text)
    assert any(f["evidence"]["rule"] == "long_sentence" for f in findings)


def test_clean_text_has_no_tone_findings():
    findings, _, _ = check_tone("NovaCloud supports 5,000 customers with reliable service.")
    assert findings == []
