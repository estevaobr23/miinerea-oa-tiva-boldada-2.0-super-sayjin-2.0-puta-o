from __future__ import annotations

import re

from .models import ClaimMatch, NormalizedResult

CLAIM_TYPES = {
    "cura": ("medical_cure", "high"),
    "curar": ("medical_cure", "high"),
    "reverter": ("medical_reversal", "high"),
    "reversao": ("medical_reversal", "high"),
    "reversão": ("medical_reversal", "high"),
    "harvard": ("authority_reference", "high"),
    "nobel": ("authority_reference", "high"),
    "remove celulas": ("biological_mechanism", "high"),
    "remove células": ("biological_mechanism", "high"),
    "remover celulas": ("biological_mechanism", "high"),
    "remover células": ("biological_mechanism", "high"),
    "hormonio": ("biological_mechanism", "medium"),
    "hormônio": ("biological_mechanism", "medium"),
    "proteina": ("biological_mechanism", "medium"),
    "proteína": ("biological_mechanism", "medium"),
    "sem dieta": ("effortless_result", "medium"),
    "sem exercicio": ("effortless_result", "medium"),
    "sem exercício": ("effortless_result", "medium"),
    "sem academia": ("effortless_result", "medium"),
}


def _context(text: str, start: int, end: int, radius: int = 90) -> str:
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    return re.sub(r"\s+", " ", text[left:right]).strip()


def detect_claims(records: list[NormalizedResult], configured_terms: list[str] | None = None) -> list[ClaimMatch]:
    terms = dict(CLAIM_TYPES)
    for term in configured_terms or []:
        terms.setdefault(term.lower(), ("configured_claim", "medium"))
    found: list[ClaimMatch] = []
    seen: set[tuple[str, str, str]] = set()
    for result in records:
        text = " | ".join(filter(None, [result.title, result.text, result.description]))
        lowered = text.lower()
        matches: list[tuple[str, int, int, str, str]] = []
        for term, (claim_type, severity) in terms.items():
            for match in re.finditer(re.escape(term.lower()), lowered):
                matches.append((term, match.start(), match.end(), claim_type, severity))
        for match in re.finditer(r"\b(?:em\s+)?\d{1,3}\s+dias?\b", lowered):
            matches.append((match.group(0), match.start(), match.end(), "time_bound_result", "medium"))
        for term, start, end, claim_type, severity in matches:
            identity = (result.dedup_key or "", claim_type, term.lower())
            if identity in seen:
                continue
            seen.add(identity)
            found.append(ClaimMatch(
                result_key=result.dedup_key or "",
                claim_type=claim_type,
                matched_term=term,
                context=_context(text, start, end),
                severity=severity,
                status="VALIDAR_TECNICAMENTE" if severity in {"medium", "high"} else "CLAIM_ENCONTRADO",
            ))
    return found

