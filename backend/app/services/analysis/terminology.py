import re
from typing import Any

from app.services.analysis.common import (
    CATEGORY_MISSING_CONFLICTING,
    CATEGORY_TERMINOLOGY,
    SEVERITY_MAJOR,
    SEVERITY_MINOR,
    make_finding_id,
)


def _term_pattern(term: str) -> re.Pattern:
    return re.compile(rf"\b{re.escape(term)}s?\b", re.IGNORECASE)


def check_terminology(text: str, terms: list[Any]) -> list[dict]:
    findings: list[dict] = []
    required_terms = [t.term for t in terms if t.rule_type == "required"]
    for term in terms:
        if term.rule_type != "prohibited":
            continue
        word = (term.term or "").strip()
        if not word:
            continue
        for match in _term_pattern(word).finditer(text):
            detected = match.group(0)
            if required_terms:
                correction = f'Replace "{detected}" with the approved term "{required_terms[0]}".'
            else:
                correction = "Replace with an approved alternative term."
            findings.append(
                {
                    "finding_id": make_finding_id(),
                    "category": CATEGORY_TERMINOLOGY,
                    "severity": SEVERITY_MAJOR,
                    "detected_text": detected,
                    "start_offset": match.start(),
                    "end_offset": match.end(),
                    "evidence": {
                        "rule_type": "prohibited",
                        "term": term.term,
                        "description": term.description,
                        "rule_id": term.id,
                    },
                    "explanation": (
                        f'The term "{detected}" is prohibited by the organisation\'s terminology rules. '
                        f'{term.description or f"Prohibited term: {term.term}."}'
                    ),
                    "suggested_correction": correction,
                    "confidence": "high",
                    "review_status": "open",
                    "requires_clarification": False,
                }
            )
    for term in terms:
        if term.rule_type != "required":
            continue
        word = (term.term or "").strip()
        if not word:
            continue
        if not _term_pattern(word).search(text):
            findings.append(
                {
                    "finding_id": make_finding_id(),
                    "category": CATEGORY_MISSING_CONFLICTING,
                    "severity": SEVERITY_MINOR,
                    "detected_text": word,
                    "start_offset": 0,
                    "end_offset": 0,
                    "evidence": {
                        "rule_type": "required",
                        "term": term.term,
                        "description": term.description,
                        "rule_id": term.id,
                    },
                    "explanation": (
                        f'The required term "{term.term}" does not appear in the submission. '
                        "Required terms must be present in governed copy."
                    ),
                    "suggested_correction": f'Include the approved term "{term.term}" where appropriate.',
                    "confidence": "high",
                    "review_status": "open",
                    "requires_clarification": False,
                }
            )
    return findings
