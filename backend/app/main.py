"""Local FastAPI app. Same handler runs on API Gateway + Lambda."""

from __future__ import annotations

import os
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from app.auth import Principal, get_principal
from app.bedrock_extract import extract_structured
from app.cognito_admin import add_user_to_group, list_groups
from app.disclaimer import load_disclaimer
from app.envload import load_repo_env
from app.models import (
    ConfirmPrefillBody,
    CreateCaseBody,
    ExtractBody,
    PatchCaseBody,
    ProfileBody,
    RoleBody,
    UploadUrlBody,
)
from app.s3docs import (
    delete_object,
    docs_bucket,
    get_object_bytes,
    object_key,
    presign_put,
)
from app.store import (
    ACTIVE_UPLOAD_STATUSES,
    ALLOWED_CONTENT_TYPES,
    ALLOWED_ROLES,
    CASE_STATUSES,
    INTENTS,
    JOURNEY_STAGES,
    MAX_ACTIVE_UPLOADS,
    MAX_EXTRACTS_PER_UTC_DAY,
    MAX_UPLOAD_BYTES,
    get_store,
    new_case_id,
    new_job_id,
    public_case,
    public_job,
    public_profile,
    public_user,
    seed_case_item,
    seed_user_item,
    ttl_unix,
    user_pk,
    utc_day,
    utc_now,
)
from app.suggestions import fixture_suggestions, sanitize_suggestions

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


def _active_uploads(sub: str) -> list[dict[str, Any]]:
    return [job for job in get_store().list_jobs(sub) if job.get("status") in ACTIVE_UPLOAD_STATUSES]


def _extracts_today(sub: str) -> int:
    today = utc_day()
    return sum(1 for job in get_store().list_jobs(sub) if job.get("extractDay") == today)


def _write_audit(sub: str, *, kind: str, model_id: str, input_tokens: int, output_tokens: int) -> None:
    now = utc_now()
    get_store().put_audit(
        {
            "pk": user_pk(sub),
            "sk": f"TS#{now}#{new_job_id()[:8]}",
            "kind": kind,
            "modelId": model_id,
            "inputTokens": input_tokens,
            "outputTokens": output_tokens,
            "citationUrls": [],
            "expiresAt": ttl_unix(90),
        }
    )


@app.post("/prefill/upload-url")
def prefill_upload_url(principal: ApplicantUser, body: UploadUrlBody) -> dict[str, Any]:
    if body.contentType not in ALLOWED_CONTENT_TYPES:
        raise _http(400, "VALIDATION", "Only jpeg, png, or pdf")
    if body.contentLength <= 0 or body.contentLength > MAX_UPLOAD_BYTES:
        raise _http(400, "VALIDATION", "Each file must be 8 MB or smaller")
    store = get_store()
    if len(_active_uploads(principal.sub)) >= MAX_ACTIVE_UPLOADS:
        raise _http(400, "VALIDATION", "At most 2 files at a time. Delete uploads first.")
    job_id = new_job_id()
    bucket = docs_bucket()
    key = object_key(principal.sub, job_id) if bucket else ""
    now = utc_now()
    item = {
        "pk": user_pk(principal.sub),
        "sk": f"JOB#{job_id}",
        "jobId": job_id,
        "docType": body.docType,
        "status": "uploaded",
        "contentType": body.contentType,
        "contentLength": body.contentLength,
        "s3Key": key,
        "createdAt": now,
        "updatedAt": now,
        "expiresAt": ttl_unix(14),
    }
    store.put_job(item)
    upload_url = None
    if bucket and key:
        upload_url = presign_put(key, body.contentType)
    return {
        "jobId": job_id,
        "docType": body.docType,
        "uploadUrl": upload_url,
        "headers": {"Content-Type": body.contentType},
        "skipUpload": upload_url is None,
    }


@app.post("/prefill/extract")
def prefill_extract(principal: ApplicantUser, body: ExtractBody) -> dict[str, Any]:
    store = get_store()
    job = store.get_job(principal.sub, body.jobId)
    if job is None or job.get("status") == "deleted":
        raise _http(404, "NOT_FOUND", "Upload job not found")
    if _extracts_today(principal.sub) >= MAX_EXTRACTS_PER_UTC_DAY:
        raise _http(429, "RATE_LIMIT", "Extract limit is 3 per day")
    payload: bytes | None = None
    content_type = str(job.get("contentType") or "")
    key = str(job.get("s3Key") or "")
    if key and docs_bucket():
        fetched = get_object_bytes(key)
        if fetched:
            payload, content_type = fetched
            if len(payload) > MAX_UPLOAD_BYTES:
                raise _http(400, "VALIDATION", "Each file must be 8 MB or smaller")
    parsed = None
    meta = {"modelId": "", "inputTokens": 0, "outputTokens": 0}
    source = "fixture"
    if payload:
        parsed, meta = extract_structured(
            doc_type=str(job.get("docType")),
            payload=payload,
            content_type=content_type,
        )
        if parsed is not None:
            source = "bedrock"
    suggestions = sanitize_suggestions(str(job.get("docType")), parsed)
    if not suggestions:
        suggestions = fixture_suggestions(str(job.get("docType")))
        source = "fixture"
    now = utc_now()
    job["status"] = "extracted"
    job["suggestions"] = suggestions
    job["source"] = source
    job["extractedAt"] = now
    job["extractDay"] = utc_day()
    job["updatedAt"] = now
    store.put_job(job)
    _write_audit(
        principal.sub,
        kind="extract",
        model_id=str(meta.get("modelId") or source),
        input_tokens=int(meta.get("inputTokens") or 0),
        output_tokens=int(meta.get("outputTokens") or 0),
    )
    return public_job(job)


@app.post("/prefill/confirm")
def prefill_confirm(principal: ApplicantUser, body: ConfirmPrefillBody) -> dict[str, Any]:
    store = get_store()
    job = store.get_job(principal.sub, body.jobId)
    if job is None:
        raise _http(404, "NOT_FOUND", "Upload job not found")
    if job.get("status") != "extracted":
        raise _http(400, "CONFIRM_REQUIRED", "Extract and review suggestions before saving")
    user = _ensure_user(principal)
    confirmed = sanitize_suggestions(
        str(job.get("docType")),
        body.fields.model_dump(exclude_unset=True),
    )
    if not confirmed:
        raise _http(400, "VALIDATION", "Confirm at least one field")
    profile = _merge_profile(dict(user.get("profile") or {}), ProfileBody(**confirmed))
    now = utc_now()
    profile["confirmedPrefillAt"] = now
    user["profile"] = profile
    user["updatedAt"] = now
    store.put_user(user)
    key = str(job.get("s3Key") or "")
    delete_object(key)
    job["status"] = "confirmed"
    job["s3Key"] = ""
    job["suggestions"] = confirmed
    job["updatedAt"] = now
    store.put_job(job)
    return public_profile(user)


@app.delete("/prefill/uploads")
def prefill_delete_uploads(principal: ApplicantUser) -> dict[str, Any]:
    store = get_store()
    deleted = 0
    now = utc_now()
    for job in store.list_jobs(principal.sub):
        if job.get("status") == "deleted":
            continue
        delete_object(str(job.get("s3Key") or ""))
        job["status"] = "deleted"
        job["s3Key"] = ""
        job["suggestions"] = {}
        job["updatedAt"] = now
        store.put_job(job)
        deleted += 1
    return {"deleted": deleted}


handler = Mangum(app)
