"""Structured prefill suggestions. Never store or log raw OCR text."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

PASSPORT_FIELDS = (
    "dateOfBirth",
    "countryOfBirth",
    "countryOfCitizenship",
    "passportNumber",
    "passportExpiry",
)
OFFER_FIELDS = (
    "employerLegalName",
    "employerFein",
    "jobTitle",
    "socCode",
    "wageAmount",
    "wageUnit",
    "worksiteAddress",
)

PASSPORT_FIXTURE: dict[str, Any] = {
    "legalName": {"given": "Ada", "family": "Lovelace"},
    "dateOfBirth": "1815-12-10",
    "countryOfBirth": "GB",
    "countryOfCitizenship": "GB",
    "passportNumber": "FIXTURE123",
    "passportExpiry": "2030-12-31",
}

OFFER_FIXTURE: dict[str, Any] = {
    "employerLegalName": "Example Robotics Inc",
    "jobTitle": "Software engineer",
    "wageAmount": "120000",
    "wageUnit": "year",
    "worksiteAddress": "Austin, TX",
}


def fixture_suggestions(doc_type: str) -> dict[str, Any]:
    if doc_type == "offer_letter":
        return deepcopy(OFFER_FIXTURE)
    return deepcopy(PASSPORT_FIXTURE)


def _clean_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"null", "none", "unknown", "n/a"}:
        return None
    return text[:200]


def sanitize_suggestions(doc_type: str, raw: dict[str, Any] | None) -> dict[str, Any]:
    data = raw or {}
    out: dict[str, Any] = {}
    if doc_type == "passport":
        name = data.get("legalName") if isinstance(data.get("legalName"), dict) else {}
        given = _clean_str(name.get("given"))
        family = _clean_str(name.get("family"))
        legal: dict[str, str] = {}
        if given:
            legal["given"] = given
        if family:
            legal["family"] = family
        if legal:
            out["legalName"] = legal
        for key in PASSPORT_FIELDS:
            cleaned = _clean_str(data.get(key))
            if cleaned:
                out[key] = cleaned
        return out
    for key in OFFER_FIELDS:
        cleaned = _clean_str(data.get(key))
        if cleaned:
            out[key] = cleaned
    return out
