import re
from dataclasses import dataclass

PROMO_WORDS = ("guaranteed", "best", "unlimited", "perfect", "always", "never fails")

UNIT_WORDS = (
    "users?",
    "tenants?",
    "customers?",
    "seats?",
    "accounts?",
    "teams?",
    "projects?",
    "devices?",
)


@dataclass
class Claim:
    value: str
    unit: str
    topic: str
    text: str
    start: int
    end: int
    kind: str


def _find(pattern: str, text: str, unit: str, topic: str, kind: str = "factual") -> list[Claim]:
    claims: list[Claim] = []
    for match in re.finditer(pattern, text, re.IGNORECASE):
        claims.append(
            Claim(
                value=match.group(1).strip(),
                unit=unit,
                topic=topic,
                text=match.group(0),
                start=match.start(),
                end=match.end(),
                kind=kind,
            )
        )
    return claims


def _drop_overlapping(claims: list[Claim]) -> list[Claim]:
    specific = [c for c in claims if c.topic not in {"generic", "promise"}]
    generic = [c for c in claims if c.topic in {"generic", "promise"}]
    kept: list[Claim] = []
    for claim in generic:
        overlaps_specific = any(
            claim.start < s.end and s.start < claim.end for s in specific
        )
        if not overlaps_specific:
            kept.append(claim)
    return specific + kept


def _dedupe(claims: list[Claim]) -> list[Claim]:
    seen: set[tuple[int, int, str]] = set()
    unique: list[Claim] = []
    for claim in claims:
        key = (claim.start, claim.end, claim.topic)
        if key in seen:
            continue
        seen.add(key)
        unique.append(claim)
    return unique


def extract_claims(text: str) -> list[Claim]:
    claims: list[Claim] = []
    units = "|".join(UNIT_WORDS)
    claims.extend(_find(rf"\b([0-9][0-9,\.]*)\s*(?:{units})\b", text, "users", "capacity"))
    claims.extend(
        _find(
            rf"\b(?:supports?|supporting|up to|handles?)\s+(?>[0-9][0-9,\.]*)(?!\s*(?:{units})\b)",
            text,
            "count",
            "capacity",
        )
    )
    claims.extend(
        _find(r"\b([0-9]+(?:\.[0-9]+)?%)\s*(?:availability|uptime)\b", text, "percent", "availability")
    )
    claims.extend(
        _find(
            r"\b(?:availability|uptime)\s*(?:of|is|at)?\s*([0-9]+(?:\.[0-9]+)?%)",
            text,
            "percent",
            "availability",
        )
    )
    claims.extend(_find(r"\b(24\s*/\s*7|24x7|24\s*-\s*7)\b", text, "hours", "support"))
    claims.extend(_find(r"\b([0-9]+(?:\.[0-9]+)?%)", text, "percent", "generic", kind="numeric"))
    for word in PROMO_WORDS:
        for match in re.finditer(rf"\b{re.escape(word)}\b", text, re.IGNORECASE):
            claims.append(
                Claim(word, "word", "promise", match.group(0), match.start(), match.end(), "promotional")
            )
    return _dedupe(_drop_overlapping(claims))
