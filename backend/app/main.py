"""Local FastAPI app. Same handler runs on API Gateway + Lambda."""

from __future__ import annotations

import os
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from app.auth import Principal, get_principal
from app.cognito_admin import add_user_to_group, list_groups
from app.disclaimer import load_disclaimer
from app.envload import load_repo_env
from app.models import CreateCaseBody, PatchCaseBody, ProfileBody, RoleBody
from app.store import (
    ALLOWED_ROLES,
    CASE_STATUSES,
    INTENTS,
    JOURNEY_STAGES,
    get_store,
    new_case_id,
    public_case,
    public_profile,
    public_user,
    seed_case_item,
    seed_user_item,
    utc_now,
)

load_repo_env()

app = FastAPI(
    title="TurboImmi API",
    version="0.1.0",
    description="Educational immigration tooling. Not a law firm. Not legal advice.",
)

_cors = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors or ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

AuthUser = Annotated[Principal, Depends(get_principal)]


def _http(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def _ensure_user(principal: Principal) -> dict[str, Any]:
    store = get_store()
    item = store.get_user(principal.sub)
    if item is None:
        item = seed_user_item(principal.sub, principal.email)
        store.put_user(item)
        return item
    profile = dict(item.get("profile") or {})
    if principal.email and not profile.get("email"):
        profile["email"] = principal.email
        item["profile"] = profile
        item["updatedAt"] = utc_now()
        store.put_user(item)
    return item


def _chosen_role(principal: Principal, item: dict[str, Any]) -> str | None:
    groups = set(principal.groups)
    stored = item.get("role")
    if not groups.intersection(ALLOWED_ROLES) and os.environ.get("USER_POOL_ID"):
        groups.update(list_groups(principal.username))
    if "Applicant" in groups or stored == "Applicant":
        return "Applicant"
    if "Attorney" in groups or stored == "Attorney":
        return "Attorney"
    if item.get("roleChosen") and stored in ALLOWED_ROLES:
        return stored
    return None


def require_applicant(principal: AuthUser) -> Principal:
    item = _ensure_user(principal)
    if _chosen_role(principal, item) != "Applicant":
        raise _http(403, "FORBIDDEN", "Applicant role required")
    return principal


ApplicantUser = Annotated[Principal, Depends(require_applicant)]


def _merge_profile(existing: dict[str, Any], body: ProfileBody) -> dict[str, Any]:
    merged = dict(existing)
    data = body.model_dump(exclude_unset=True)
    if "legalName" in data and data["legalName"] is not None:
        current = dict(merged.get("legalName") or {})
        name = data.pop("legalName") or {}
        for key in ("given", "family"):
            if key in name and name[key] is not None:
                current[key] = name[key]
        merged["legalName"] = current
    if "journeyStage" in data and data["journeyStage"] is not None:
        stage = data["journeyStage"]
        if stage not in JOURNEY_STAGES:
            raise _http(400, "VALIDATION", "Unknown journeyStage")
    if "confirmedPrefillAt" in data:
        data.pop("confirmedPrefillAt")
    for key, value in data.items():
        if value is None:
            continue
        merged[key] = value
    return merged


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/disclaimer")
def disclaimer() -> dict:
    return load_disclaimer()


@app.get("/health/auth")
def health_auth(principal: AuthUser) -> dict[str, str]:
    return {"status": "ok", "sub": principal.sub}


@app.get("/me")
def get_me(principal: AuthUser) -> dict[str, Any]:
    store = get_store()
    item = _ensure_user(principal)
    role = _chosen_role(principal, item)
    if role and (not item.get("roleChosen") or item.get("role") != role):
        item["roleChosen"] = True
        item["role"] = role
        item["updatedAt"] = utc_now()
        store.put_user(item)
    groups = list(principal.groups)
    if role and role not in groups:
        groups = [*groups, role]
    return public_user(item, sub=principal.sub, groups=groups, email=principal.email)


@app.post("/me/role")
def post_me_role(principal: AuthUser, body: RoleBody) -> dict[str, Any]:
    store = get_store()
    item = _ensure_user(principal)
    existing = _chosen_role(principal, item)
    if existing:
        raise _http(409, "ROLE_LOCKED", "Role already chosen")
    add_user_to_group(principal.username, body.role)
    now = utc_now()
    item["roleChosen"] = True
    item["role"] = body.role
    item["updatedAt"] = now
    store.put_user(item)
    if body.role == "Applicant" and not store.list_cases(principal.sub):
        store.put_case(seed_case_item(principal.sub))
    return {
        "role": body.role,
        "roleChosen": True,
        "refreshRequired": True,
    }


@app.get("/me/profile")
def get_profile(principal: AuthUser) -> dict[str, Any]:
    return public_profile(_ensure_user(principal))


@app.put("/me/profile")
def put_profile(principal: AuthUser, body: ProfileBody) -> dict[str, Any]:
    store = get_store()
    item = _ensure_user(principal)
    item["profile"] = _merge_profile(dict(item.get("profile") or {}), body)
    item["updatedAt"] = utc_now()
    store.put_user(item)
    return public_profile(item)


@app.get("/cases")
def list_cases(principal: ApplicantUser) -> dict[str, Any]:
    return {"cases": [public_case(item) for item in get_store().list_cases(principal.sub)]}


@app.post("/cases")
def create_case(principal: ApplicantUser, body: CreateCaseBody | None = None) -> dict[str, Any]:
    store = get_store()
    payload = body or CreateCaseBody()
    item = seed_case_item(principal.sub, new_case_id())
    if payload.intent:
        item["intent"] = payload.intent
    if payload.entryPath:
        item["entryPath"] = payload.entryPath
    store.put_case(item)
    return public_case(item)


@app.get("/cases/{case_id}")
def get_case(principal: ApplicantUser, case_id: str) -> dict[str, Any]:
    item = get_store().get_case(principal.sub, case_id)
    if item is None:
        raise _http(404, "NOT_FOUND", "Case not found")
    return public_case(item)


@app.patch("/cases/{case_id}")
def patch_case(principal: ApplicantUser, case_id: str, body: PatchCaseBody) -> dict[str, Any]:
    store = get_store()
    item = store.get_case(principal.sub, case_id)
    if item is None:
        raise _http(404, "NOT_FOUND", "Case not found")
    data = body.model_dump(exclude_unset=True)
    if data.get("intent") is not None and data["intent"] not in INTENTS:
        raise _http(400, "VALIDATION", "Unknown intent")
    if data.get("status") is not None and data["status"] not in CASE_STATUSES:
        raise _http(400, "VALIDATION", "Unknown status")
    if "formFields" in data and data["formFields"] is not None:
        fields = dict(item.get("formFields") or {})
        fields.update(data.pop("formFields"))
        item["formFields"] = fields
    for key, value in data.items():
        if value is None:
            continue
        item[key] = value
    item["updatedAt"] = utc_now()
    store.put_case(item)
    return public_case(item)


handler = Mangum(app)
