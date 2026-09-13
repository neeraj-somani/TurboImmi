"""Attorney directory helpers. Referral only. No bar check in P0."""

from __future__ import annotations

from typing import Any

from app.store import new_job_id, utc_now

SPECIALTIES = ("h1b", "f1_opt", "h4", "perm")
US_STATES = frozenset(
    {
        "AL",
        "AK",
        "AZ",
        "AR",
        "CA",
        "CO",
        "CT",
        "DC",
        "DE",
        "FL",
        "GA",
        "HI",
        "IA",
        "ID",
        "IL",
        "IN",
        "KS",
        "KY",
        "LA",
        "MA",
        "MD",
        "ME",
        "MI",
        "MN",
        "MO",
        "MS",
        "MT",
        "NC",
        "ND",
        "NE",
        "NH",
        "NJ",
        "NM",
        "NV",
        "NY",
        "OH",
        "OK",
        "OR",
        "PA",
        "RI",
        "SC",
        "SD",
        "TN",
        "TX",
        "UT",
        "VA",
        "VT",
        "WA",
        "WI",
        "WV",
        "WY",
    }
)
CONSULT_STATUSES = ("requested", "seen", "closed")
MAX_CONSULT_MESSAGE = 400
MAX_OPEN_CONSULTS = 8

SEED_ATTORNEYS = (
    {
        "attorneyId": "demo-chen",
        "displayName": "Jordan Chen",
        "firmName": "Chen Immigration Demo PLLC",
        "usState": "CA",
        "specialties": ["h1b", "f1_opt"],
        "bio": "Demo listing for H-1B and F-1/OPT educational referral. Not a real law firm.",
        "published": True,
        "verified": False,
        "cognitoSub": "",
    },
    {
        "attorneyId": "demo-okonkwo",
        "displayName": "Amara Okonkwo",
        "firmName": "Okonkwo Work Visa Demo LLC",
        "usState": "TX",
        "specialties": ["h1b", "perm"],
        "bio": "Demo listing for H-1B and PERM educational referral. Not a real law firm.",
        "published": True,
        "verified": False,
        "cognitoSub": "",
    },
)


def attorney_pk(attorney_id: str) -> str:
    return f"ATTORNEY#{attorney_id}"


def _text(value: Any, limit: int = 120) -> str:
    return str(value or "").strip()[:limit]


def normalize_state(value: Any) -> str:
    return _text(value, 2).upper()


def normalize_specialties(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        key = _text(item, 20).lower()
        if key in SPECIALTIES and key not in out:
            out.append(key)
    return out


def gsi_keys(us_state: str, specialties: list[str], attorney_id: str) -> dict[str, str]:
    spec = specialties[0] if specialties else "h1b"
    return {
        "gsi1pk": f"STATE#{us_state}",
        "gsi1sk": f"SPEC#{spec}#{attorney_id}",
    }


FLAG_VALUES = ("none", "incomplete", "mismatch", "other")


def basic_checks(item: dict[str, Any]) -> dict[str, Any]:
    missing: list[str] = []
    if not _text(item.get("displayName")):
        missing.append("displayName")
    if not normalize_state(item.get("usState")):
        missing.append("usState")
    if not normalize_specialties(item.get("specialties")):
        missing.append("specialties")
    if not _text(item.get("bio"), 400):
        missing.append("bio")
    return {"ok": not missing, "missing": missing}


def public_attorney(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "attorneyId": item.get("attorneyId"),
        "displayName": item.get("displayName") or "",
        "firmName": item.get("firmName") or "",
        "usState": item.get("usState") or "",
        "specialties": list(item.get("specialties") or []),
        "bio": item.get("bio") or "",
        "published": bool(item.get("published")),
        "verified": bool(item.get("verified")),
        "flag": item.get("flag") or "none",
        "flagNote": item.get("flagNote") or "",
        "createdAt": item.get("createdAt"),
        "updatedAt": item.get("updatedAt"),
    }


def public_attorney_admin(item: dict[str, Any]) -> dict[str, Any]:
    out = public_attorney(item)
    out["checks"] = basic_checks(item)
    return out


def public_consult(item: dict[str, Any], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    out = {
        "consultId": item.get("consultId"),
        "attorneyId": item.get("attorneyId"),
        "applicantSub": item.get("applicantSub"),
        "caseId": item.get("caseId") or None,
        "message": item.get("message") or "",
        "status": item.get("status") or "requested",
        "createdAt": item.get("createdAt"),
    }
    if extra:
        out.update(extra)
    return out


def attorney_item(payload: dict[str, Any], *, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    attorney_id = _text((existing or {}).get("attorneyId") or payload.get("attorneyId") or new_job_id(), 40)
    now = utc_now()
    us_state = normalize_state(payload.get("usState"))
    specialties = normalize_specialties(payload.get("specialties"))
    published = bool((existing or {}).get("published")) if existing else False
    sub = _text(payload.get("cognitoSub") or (existing or {}).get("cognitoSub"), 80)
    item = {
        "pk": attorney_pk(attorney_id),
        "sk": "PROFILE",
        "attorneyId": attorney_id,
        "cognitoSub": sub,
        "displayName": _text(payload.get("displayName"), 80),
        "firmName": _text(payload.get("firmName"), 80),
        "usState": us_state,
        "specialties": specialties,
        "bio": _text(payload.get("bio"), 400),
        "published": published,
        "verified": bool((existing or {}).get("verified")) if existing else False,
        "flag": (existing or {}).get("flag") or "none",
        "flagNote": (existing or {}).get("flagNote") or "",
        "createdAt": (existing or {}).get("createdAt") or now,
        "updatedAt": now,
        **gsi_keys(us_state, specialties, attorney_id),
    }
    return item


def seed_attorney_items() -> list[dict[str, Any]]:
    now = utc_now()
    rows: list[dict[str, Any]] = []
    for raw in SEED_ATTORNEYS:
        attorney_id = str(raw["attorneyId"])
        us_state = str(raw["usState"])
        specialties = list(raw["specialties"])
        rows.append(
            {
                "pk": attorney_pk(attorney_id),
                "sk": "PROFILE",
                "attorneyId": attorney_id,
                "cognitoSub": "",
                "displayName": raw["displayName"],
                "firmName": raw["firmName"],
                "usState": us_state,
                "specialties": specialties,
                "bio": raw["bio"],
                "published": True,
                "verified": False,
                "createdAt": now,
                "updatedAt": now,
                **gsi_keys(us_state, specialties, attorney_id),
            }
        )
    return rows


def matches_filters(item: dict[str, Any], state: str | None, specialty: str | None) -> bool:
    if state and normalize_state(item.get("usState")) != normalize_state(state):
        return False
    if specialty:
        wanted = _text(specialty, 20).lower()
        specs = [str(value).lower() for value in (item.get("specialties") or [])]
        if wanted not in specs:
            return False
    return True
