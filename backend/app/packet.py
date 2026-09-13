"""Map profile + interview to I-129 / H-style fields. No essays. No I-539."""

from __future__ import annotations

from typing import Any

PACKET_KEYS = (
    "petitionerLegalName",
    "petitionerUsAddress",
    "petitionerFein",
    "petitionerOrgType",
    "beneficiaryGiven",
    "beneficiaryFamily",
    "beneficiaryDateOfBirth",
    "beneficiaryCountryOfBirth",
    "beneficiaryCitizenship",
    "beneficiaryPassportNumber",
    "beneficiaryPassportExpiry",
    "beneficiaryAlienNumber",
    "intent",
    "entryPath",
    "capExemptClaim",
    "jobTitle",
    "socCode",
    "wageAmount",
    "wageUnit",
    "hoursPerWeek",
    "worksiteAddress",
    "lcaEtaNumber",
    "requestedStart",
    "requestedEnd",
    "offsiteItinerary",
    "evidencePassport",
    "evidenceOfferLetter",
    "evidenceLca",
)

BOOL_KEYS = frozenset(
    {"capExemptClaim", "offsiteItinerary", "evidencePassport", "evidenceOfferLetter", "evidenceLca"}
)


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()[:200]


def _name(profile: dict[str, Any]) -> dict[str, str]:
    name = profile.get("legalName") if isinstance(profile.get("legalName"), dict) else {}
    return {"given": _text(name.get("given")), "family": _text(name.get("family"))}


def build_packet(profile: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    """Derive a review packet. Saved formFields override these values later."""
    name = _name(profile)
    fein = _text(profile.get("employerFein"))
    wage = profile.get("wageAmount")
    lca = _text(case.get("lcaEtaNumber"))
    passport = _text(profile.get("passportNumber"))
    employer = _text(profile.get("employerLegalName"))
    title = _text(profile.get("jobTitle"))
    return {
        "petitionerLegalName": employer,
        "petitionerUsAddress": "",
        "petitionerFein": fein,
        "petitionerOrgType": "",
        "beneficiaryGiven": name["given"],
        "beneficiaryFamily": name["family"],
        "beneficiaryDateOfBirth": _text(profile.get("dateOfBirth")),
        "beneficiaryCountryOfBirth": _text(profile.get("countryOfBirth")),
        "beneficiaryCitizenship": _text(profile.get("countryOfCitizenship")),
        "beneficiaryPassportNumber": passport,
        "beneficiaryPassportExpiry": _text(profile.get("passportExpiry")),
        "beneficiaryAlienNumber": _text(profile.get("alienNumber")),
        "intent": _text(case.get("intent")),
        "entryPath": _text(case.get("entryPath")),
        "capExemptClaim": bool(case.get("capExemptClaim")),
        "jobTitle": title,
        "socCode": _text(profile.get("socCode")),
        "wageAmount": _text(wage),
        "wageUnit": _text(profile.get("wageUnit")),
        "hoursPerWeek": "",
        "worksiteAddress": _text(profile.get("worksiteAddress")),
        "lcaEtaNumber": lca,
        "requestedStart": _text(case.get("requestedStart")),
        "requestedEnd": _text(case.get("requestedEnd")),
        "offsiteItinerary": False,
        "evidencePassport": bool(passport or profile.get("confirmedPrefillAt")),
        "evidenceOfferLetter": bool(employer or title),
        "evidenceLca": bool(lca),
    }


def sanitize_form_fields(raw: dict[str, Any] | None) -> dict[str, Any]:
    data = raw or {}
    out: dict[str, Any] = {}
    for key in PACKET_KEYS:
        if key not in data:
            continue
        value = data[key]
        if key in BOOL_KEYS:
            out[key] = bool(value)
        else:
            cleaned = _text(value)
            if cleaned:
                out[key] = cleaned
    return out


def merge_packet(profile: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    derived = build_packet(profile, case)
    saved = sanitize_form_fields(case.get("formFields"))
    merged = dict(derived)
    for key, value in saved.items():
        merged[key] = value
    return merged


def case_with_packet(item: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    from app.store import public_case

    out = public_case(item)
    out["packet"] = merge_packet(profile, item)
    return out
