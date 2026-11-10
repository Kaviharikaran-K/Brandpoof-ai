import os
import re
from typing import Protocol

from app.services.analysis.common import CATEGORY_TONE, SEVERITY_MINOR, make_finding_id

BANNED_PHRASES = [
    "synergy",
    "disruptive",
    "game-changing",
    "world-class",
    "revolutionary",
    "cutting-edge",
]


class ToneProvider(Protocol):
    def suggest(self, text: str) -> list[dict]:
        ...


class DeterministicToneProvider:
    name = "Rule-based"

    def suggest(self, text: str) -> list[dict]:
        findings: list[dict] = []
        for phrase in BANNED_PHRASES:
            for match in re.finditer(rf"\b{re.escape(phrase)}\b", text, re.IGNORECASE):
                findings.append(
                    {
                        "finding_id": make_finding_id(),
                        "category": CATEGORY_TONE,
                        "severity": SEVERITY_MINOR,
                        "detected_text": match.group(0),
                        "start_offset": match.start(),
                        "end_offset": match.end(),
                        "evidence": {"rule": "banned_phrase", "phrase": phrase, "engine": self.name},
                        "explanation": (
                            f'The phrase "{match.group(0)}" is on the banned-phrases list for governed copy. '
                            "Prefer specific, verifiable language over promotional jargon."
                        ),
                        "suggested_correction": "Replace with a specific, factual description.",
                        "confidence": "high",
                        "review_status": "open",
                        "requires_clarification": False,
                    }
                )
        exclamation_count = text.count("!")
        if exclamation_count > 2:
            first = text.find("!")
            findings.append(
                {
                    "finding_id": make_finding_id(),
                    "category": CATEGORY_TONE,
                    "severity": SEVERITY_MINOR,
                    "detected_text": "!" * min(exclamation_count, 5),
                    "start_offset": first,
                    "end_offset": first + 1,
                    "evidence": {"rule": "exclamation_limit", "count": exclamation_count, "engine": self.name},
                    "explanation": (
                        f"The text contains {exclamation_count} exclamation marks. Governed copy should "
                        "stay measured; use two or fewer."
                    ),
                    "suggested_correction": "Remove excess exclamation marks.",
                    "confidence": "high",
                    "review_status": "open",
                    "requires_clarification": False,
                }
            )
        for match in re.finditer(r"\b[A-Z]{5,}\b", text):
            findings.append(
                {
                    "finding_id": make_finding_id(),
                    "category": CATEGORY_TONE,
                    "severity": SEVERITY_MINOR,
                    "detected_text": match.group(0),
                    "start_offset": match.start(),
                    "end_offset": match.end(),
                    "evidence": {"rule": "all_caps", "engine": self.name},
                    "explanation": (
                        f'"{match.group(0)}" is written in all capitals. Avoid ALL-CAPS for emphasis '
                        "in governed copy unless it is a recognised acronym."
                    ),
                    "suggested_correction": "Use sentence case unless it is an acronym.",
                    "confidence": "medium",
                    "review_status": "open",
                    "requires_clarification": False,
                }
            )
        for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
            if len(sentence.split()) > 35:
                start = text.find(sentence)
                findings.append(
                    {
                        "finding_id": make_finding_id(),
                        "category": CATEGORY_TONE,
                        "severity": SEVERITY_MINOR,
                        "detected_text": sentence[:80],
                        "start_offset": max(start, 0),
                        "end_offset": max(start, 0) + len(sentence),
                        "evidence": {
                            "rule": "long_sentence",
                            "words": len(sentence.split()),
                            "engine": self.name,
                        },
                        "explanation": (
                            f"This sentence is {len(sentence.split())} words long. Long sentences dilute "
                            "clarity; consider splitting it."
                        ),
                        "suggested_correction": "Split into shorter sentences.",
                        "confidence": "medium",
                        "review_status": "open",
                        "requires_clarification": False,
                    }
                )
        return findings


class OptionalLLMToneProvider:
    name = "LLM-assisted (experimental)"
    disclosure = (
        "Optional LLM suggestions are enabled. Suggestions are advisory only, are reviewed by a human "
        "before use, and no submission content is executed."
    )

    def __init__(self) -> None:
        self.api_key = os.environ.get("BRANDPROOF_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")

    def enabled(self) -> bool:
        return bool(self.api_key)

    def suggest(self, text: str) -> list[dict]:
        return []


def llm_provider_configured() -> bool:
    return bool(os.environ.get("BRANDPROOF_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY"))


def get_tone_provider(consent: bool = False) -> tuple[ToneProvider, str, str | None]:
    if consent:
        llm = OptionalLLMToneProvider()
        if llm.enabled():
            return llm, llm.name, llm.disclosure
    rule = DeterministicToneProvider()
    return rule, rule.name, None


def check_tone(text: str, consent: bool = False) -> tuple[list[dict], str, str | None]:
    provider, name, disclosure = get_tone_provider(consent)
    return provider.suggest(text), name, disclosure
