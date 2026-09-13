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
    AdminAttorneyPatch,
    AdminProfileBody,
    AttorneyBody,
    AttestationBody,
    ConfirmPrefillBody,
    ConsultBody,
    CreateCaseBody,
    ExtractBody,
    ChatBody,
    PatchCaseBody,
    ProfileBody,
    RoleBody,
    ScoreBody,
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
    ENTRY_PATHS,
    INTENTS,
    JOURNEY_STAGES,
    MAX_ACTIVE_UPLOADS,
    MAX_CHAT_TURNS,
    MAX_EXTRACTS_PER_UTC_DAY,
    MAX_UPLOAD_BYTES,
    get_store,
    new_case_id,
    new_job_id,
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
from app.attorneys import (
    FLAG_VALUES,
    MAX_CONSULT_MESSAGE,
    MAX_OPEN_CONSULTS,
    SPECIALTIES,
    US_STATES,
    attorney_item,
    attorney_pk,
    normalize_specialties,
    normalize_state,
    public_attorney,
    public_attorney_admin,
    public_consult,
)
from app.packet import case_with_packet, sanitize_form_fields
from app.score import evaluate
from app.score_explain import explain_hits
from app.alerts import public_alert
from app.policy_chat import MAX_CHAT_MESSAGE, answer_question
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


def _allowlist_email() -> str:
    return (os.environ.get("ADMIN_ALLOWLIST_EMAIL") or "").strip().lower()


def _chosen_role(principal: Principal, item: dict[str, Any]) -> str | None:
    groups = set(principal.groups)
    stored = item.get("role")
    if not groups.intersection(ALLOWED_ROLES) and os.environ.get("USER_POOL_ID"):
        groups.update(list_groups(principal.username))
    if "Admin" in groups or stored == "Admin":
        return "Admin"
    if "Applicant" in groups or stored == "Applicant":
        return "Applicant"
    if "Attorney" in groups or stored == "Attorney":
        return "Attorney"
    if item.get("roleChosen") and stored in ALLOWED_ROLES:
        return stored
    return None


def _maybe_promote_admin(principal: Principal, item: dict[str, Any]) -> dict[str, Any]:
    allow = _allowlist_email()
    email = (principal.email or "").strip().lower()
    if not allow or not email or email != allow:
        return item
    existing = _chosen_role(principal, item)
    if existing in {"Applicant", "Attorney"}:
        return item
    if existing == "Admin" and item.get("roleChosen") and item.get("admin"):
        return item
    add_user_to_group(principal.username, "Admin")
    now = utc_now()
    admin = dict(item.get("admin") or {})
    if not admin.get("displayName"):
        admin["displayName"] = email.split("@", 1)[0][:80]
    item["admin"] = admin
    item["role"] = "Admin"
    item["roleChosen"] = True
    item["updatedAt"] = now
    get_store().put_user(item)
    return item


def require_applicant(principal: AuthUser) -> Principal:
    item = _ensure_user(principal)
    if _chosen_role(principal, item) != "Applicant":
        raise _http(403, "FORBIDDEN", "Applicant role required")
    return principal


ApplicantUser = Annotated[Principal, Depends(require_applicant)]


def require_attorney(principal: AuthUser) -> Principal:
    item = _ensure_user(principal)
    if _chosen_role(principal, item) != "Attorney":
        raise _http(403, "FORBIDDEN", "Attorney role required")
    return principal


AttorneyUser = Annotated[Principal, Depends(require_attorney)]


def require_admin(principal: AuthUser) -> Principal:
    item = _maybe_promote_admin(principal, _ensure_user(principal))
    if _chosen_role(principal, item) != "Admin":
        raise _http(403, "FORBIDDEN", "Admin role required")
    return principal


AdminUser = Annotated[Principal, Depends(require_admin)]


def _public_admin(item: dict[str, Any]) -> dict[str, Any]:
    admin = dict(item.get("admin") or {})
    return {
        "displayName": admin.get("displayName") or "",
        "updatedAt": item.get("updatedAt"),
    }


def _ensure_attorney_card(principal: Principal) -> dict[str, Any]:
    store = get_store()
    store.ensure_seed_attorneys()
    existing = store.get_attorney_by_sub(principal.sub)
    if existing:
        return existing
    name = ""
    user = _ensure_user(principal)
    legal = (user.get("profile") or {}).get("legalName") or {}
    if isinstance(legal, dict):
        name = f"{legal.get('given') or ''} {legal.get('family') or ''}".strip()
    item = attorney_item(
        {
            "displayName": name or "Attorney",
            "firmName": "",
            "usState": "CA",
            "specialties": ["h1b"],
            "bio": "",
            "cognitoSub": principal.sub,
        }
    )
    store.put_attorney(item)
    return item


def _consult_view(item: dict[str, Any]) -> dict[str, Any]:
    store = get_store()
    extra: dict[str, Any] = {}
    attorney = store.get_attorney(str(item.get("attorneyId") or ""))
    if attorney:
        extra["attorneyDisplayName"] = attorney.get("displayName")
    applicant = store.get_user(str(item.get("applicantSub") or ""))
    if applicant:
        legal = (applicant.get("profile") or {}).get("legalName") or {}
        if isinstance(legal, dict):
            extra["applicantDisplayName"] = f"{legal.get('given') or ''} {legal.get('family') or ''}".strip()
    return public_consult(item, extra)


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
    item = _maybe_promote_admin(principal, _ensure_user(principal))
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
    if body.role == "Attorney":
        _ensure_attorney_card(principal)
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
    profile = dict(_ensure_user(principal).get("profile") or {})
    return {"cases": [case_with_packet(item, profile) for item in get_store().list_cases(principal.sub)]}


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
    profile = dict(_ensure_user(principal).get("profile") or {})
    return case_with_packet(item, profile)


@app.get("/cases/{case_id}")
def get_case(principal: ApplicantUser, case_id: str) -> dict[str, Any]:
    item = get_store().get_case(principal.sub, case_id)
    if item is None:
        raise _http(404, "NOT_FOUND", "Case not found")
    profile = dict(_ensure_user(principal).get("profile") or {})
    return case_with_packet(item, profile)


@app.patch("/cases/{case_id}")
def patch_case(principal: ApplicantUser, case_id: str, body: PatchCaseBody) -> dict[str, Any]:
    store = get_store()
    item = store.get_case(principal.sub, case_id)
    if item is None:
        raise _http(404, "NOT_FOUND", "Case not found")
    data = body.model_dump(exclude_unset=True)
    if data.get("intent") is not None and data["intent"] not in INTENTS:
        raise _http(400, "VALIDATION", "Unknown intent")
    if data.get("entryPath") is not None and data["entryPath"] not in ENTRY_PATHS:
        raise _http(400, "VALIDATION", "Unknown entryPath")
    if data.get("status") is not None and data["status"] not in CASE_STATUSES:
        raise _http(400, "VALIDATION", "Unknown status")
    start = data.get("requestedStart", item.get("requestedStart"))
    end = data.get("requestedEnd", item.get("requestedEnd"))
    if start and end and str(end) < str(start):
        raise _http(400, "VALIDATION", "Requested end must be on or after start")
    if "formFields" in data and data["formFields"] is not None:
        fields = dict(item.get("formFields") or {})
        fields.update(sanitize_form_fields(data.pop("formFields")))
        item["formFields"] = fields
    for key, value in data.items():
        if value is None:
            continue
        item[key] = value
    if item.get("intent") in INTENTS and item.get("entryPath") in ENTRY_PATHS and item.get("status") == "draft":
        item["status"] = "in_progress"
    item["updatedAt"] = utc_now()
    store.put_case(item)
    profile = dict(_ensure_user(principal).get("profile") or {})
    return case_with_packet(item, profile)


@app.post("/cases/{case_id}/score")
def score_case(principal: ApplicantUser, case_id: str, body: ScoreBody | None = None) -> dict[str, Any]:
    store = get_store()
    item = store.get_case(principal.sub, case_id)
    if item is None:
        raise _http(404, "NOT_FOUND", "Case not found")
    profile = dict(_ensure_user(principal).get("profile") or {})
    payload = body or ScoreBody()
    result = evaluate(profile, item)
    now = utc_now()
    result["scoredAt"] = now
    explanation = None
    if payload.explain:
        explanation, meta = explain_hits(result["deductions"])
        _write_audit(
            principal.sub,
            kind="explain_score",
            model_id=str(meta.get("modelId") or "none"),
            input_tokens=int(meta.get("inputTokens") or 0),
            output_tokens=int(meta.get("outputTokens") or 0),
        )
        if explanation:
            result["explanation"] = explanation
    item["score"] = result
    item["updatedAt"] = now
    store.put_case(item)
    out = case_with_packet(item, profile)
    out["score"] = result
    return out


@app.post("/chat")
def policy_chat(principal: AuthUser, body: ChatBody) -> dict[str, Any]:
    if len(body.message) > MAX_CHAT_MESSAGE:
        raise _http(400, "VALIDATION", "Message is too long")
    question = body.message.strip()
    if not question:
        raise _http(400, "VALIDATION", "Message is required")
    store = get_store()
    user = _ensure_user(principal)
    today = utc_day()
    count = 0 if user.get("chatDay") != today else int(user.get("chatCount") or 0)
    if count >= MAX_CHAT_TURNS:
        raise _http(429, "RATE_LIMIT", "Chat limit is 15 per day")
    result = answer_question(question, store)
    now = utc_now()
    user["chatDay"] = today
    user["chatCount"] = count + 1
    user["updatedAt"] = now
    store.put_user(user)
    urls = [
        str(item.get("source_url"))
        for item in result.get("citations") or []
        if item.get("source_url")
    ]
    _write_audit(
        principal.sub,
        kind="chat",
        model_id=str(result.get("modelId") or "none"),
        input_tokens=int(result.get("inputTokens") or 0),
        output_tokens=int(result.get("outputTokens") or 0),
        citation_urls=urls,
    )
    return {
        "answer": result["answer"],
        "refused": bool(result.get("refused")),
        "citations": result.get("citations") or [],
        "remaining": MAX_CHAT_TURNS - count - 1,
    }


@app.get("/alerts")
def list_alerts(principal: AuthUser) -> dict[str, Any]:
    del principal
    rows = [public_alert(item) for item in get_store().list_alerts()]
    return {"alerts": rows}


@app.post("/cases/{case_id}/attestation")
def attest_case(principal: ApplicantUser, case_id: str, body: AttestationBody) -> dict[str, Any]:
    expected = str(load_disclaimer().get("attestation") or "").strip()
    if not body.accepted or body.text.strip() != expected:
        raise _http(400, "VALIDATION", "Attestation checkbox text must be accepted")
    store = get_store()
    item = store.get_case(principal.sub, case_id)
    if item is None:
        raise _http(404, "NOT_FOUND", "Case not found")
    now = utc_now()
    item["attestationAcceptedAt"] = now
    item["status"] = "ready_to_file"
    item["updatedAt"] = now
    store.put_case(item)
    profile = dict(_ensure_user(principal).get("profile") or {})
    return case_with_packet(item, profile)


@app.get("/attorneys")
def list_attorneys(
    principal: AuthUser,
    state: str | None = None,
    specialty: str | None = None,
) -> dict[str, Any]:
    del principal
    if state and normalize_state(state) not in US_STATES:
        raise _http(400, "VALIDATION", "Unknown US state")
    if specialty and specialty.lower() not in SPECIALTIES:
        raise _http(400, "VALIDATION", "Unknown specialty")
    get_store().ensure_seed_attorneys()
    rows = get_store().list_attorneys(state=state, specialty=specialty)
    return {"attorneys": [public_attorney(item) for item in rows]}


@app.get("/attorneys/{attorney_id}")
def get_attorney(principal: AuthUser, attorney_id: str) -> dict[str, Any]:
    item = get_store().get_attorney(attorney_id)
    if item is None:
        raise _http(404, "NOT_FOUND", "Attorney not found")
    if not item.get("published") and item.get("cognitoSub") != principal.sub:
        raise _http(404, "NOT_FOUND", "Attorney not found")
    return public_attorney(item)


@app.put("/attorneys/me")
def put_attorney_me(principal: AttorneyUser, body: AttorneyBody) -> dict[str, Any]:
    us_state = normalize_state(body.usState)
    if us_state not in US_STATES:
        raise _http(400, "VALIDATION", "Unknown US state")
    specialties = normalize_specialties(body.specialties)
    if not specialties:
        raise _http(400, "VALIDATION", "Choose at least one specialty")
    if not body.displayName.strip():
        raise _http(400, "VALIDATION", "Display name is required")
    store = get_store()
    existing = store.get_attorney_by_sub(principal.sub)
    item = attorney_item(
        {
            "displayName": body.displayName,
            "firmName": body.firmName or "",
            "usState": us_state,
            "specialties": specialties,
            "bio": body.bio or "",
            "cognitoSub": principal.sub,
        },
        existing=existing,
    )
    store.put_attorney(item)
    return public_attorney(item)


@app.get("/admin/me")
def get_admin_me(principal: AdminUser) -> dict[str, Any]:
    return _public_admin(_ensure_user(principal))


@app.put("/admin/me")
def put_admin_me(principal: AdminUser, body: AdminProfileBody) -> dict[str, Any]:
    name = body.displayName.strip()
    if not name:
        raise _http(400, "VALIDATION", "Display name is required")
    store = get_store()
    item = _ensure_user(principal)
    admin = dict(item.get("admin") or {})
    admin["displayName"] = name[:80]
    item["admin"] = admin
    item["updatedAt"] = utc_now()
    store.put_user(item)
    return _public_admin(item)


@app.get("/admin/attorneys")
def admin_list_attorneys(
    principal: AdminUser,
    published: bool | None = None,
    verified: bool | None = None,
    flagged: bool | None = None,
) -> dict[str, Any]:
    del principal
    rows = get_store().list_all_attorneys()
    if published is not None:
        rows = [item for item in rows if bool(item.get("published")) is published]
    if verified is not None:
        rows = [item for item in rows if bool(item.get("verified")) is verified]
    if flagged is not None:
        rows = [item for item in rows if (str(item.get("flag") or "none") != "none") is flagged]
    return {"attorneys": [public_attorney_admin(item) for item in rows]}


@app.patch("/admin/attorneys/{attorney_id}")
def admin_patch_attorney(principal: AdminUser, attorney_id: str, body: AdminAttorneyPatch) -> dict[str, Any]:
    del principal
    store = get_store()
    item = store.get_attorney(attorney_id)
    if item is None:
        raise _http(404, "NOT_FOUND", "Attorney not found")
    if body.published is not None:
        item["published"] = body.published
    if body.verified is not None:
        item["verified"] = body.verified
    if body.flag is not None:
        flag = body.flag.strip().lower()
        if flag not in FLAG_VALUES:
            raise _http(400, "VALIDATION", "Unknown flag")
        item["flag"] = flag
        if flag == "none":
            item["flagNote"] = ""
    if body.flagNote is not None and (item.get("flag") or "none") != "none":
        item["flagNote"] = str(body.flagNote).strip()[:200]
    item["updatedAt"] = utc_now()
    store.put_attorney(item)
    return public_attorney_admin(item)


@app.post("/consults")
def create_consult(principal: ApplicantUser, body: ConsultBody) -> dict[str, Any]:
    message = body.message.strip()
    if not message or len(message) > MAX_CONSULT_MESSAGE:
        raise _http(400, "VALIDATION", f"Message must be 1–{MAX_CONSULT_MESSAGE} characters")
    store = get_store()
    store.ensure_seed_attorneys()
    attorney = store.get_attorney(body.attorneyId)
    if attorney is None or not attorney.get("published"):
        raise _http(404, "NOT_FOUND", "Attorney not found")
    if body.caseId:
        case = store.get_case(principal.sub, body.caseId)
        if case is None:
            raise _http(404, "NOT_FOUND", "Case not found")
    open_count = sum(1 for item in store.list_consults_for_applicant(principal.sub) if item.get("status") in {"requested", "seen"})
    if open_count >= MAX_OPEN_CONSULTS:
        raise _http(429, "RATE_LIMIT", "Too many open consult requests")
    now = utc_now()
    consult_id = new_job_id()
    item = {
        "pk": attorney_pk(body.attorneyId),
        "sk": f"CONSULT#{consult_id}",
        "consultId": consult_id,
        "attorneyId": body.attorneyId,
        "applicantSub": principal.sub,
        "caseId": body.caseId or "",
        "message": message,
        "status": "requested",
        "createdAt": now,
        "gsi1pk": user_pk(principal.sub),
        "gsi1sk": f"CONSULT#{consult_id}",
    }
    store.put_consult(item)
    return _consult_view(item)


@app.get("/consults")
def list_consults(principal: AuthUser) -> dict[str, Any]:
    store = get_store()
    role = _chosen_role(principal, _ensure_user(principal))
    if role == "Applicant":
        rows = store.list_consults_for_applicant(principal.sub)
        return {"consults": [_consult_view(item) for item in rows]}
    if role == "Attorney":
        card = _ensure_attorney_card(principal)
        rows = store.list_consults_for_attorney(str(card.get("attorneyId") or ""))
        updated = []
        for item in rows:
            if item.get("status") == "requested":
                item["status"] = "seen"
                store.put_consult(item)
            updated.append(item)
        return {
            "consults": [_consult_view(item) for item in updated],
            "attorney": public_attorney(card),
        }
    raise _http(403, "FORBIDDEN", "Choose a role first")


def _active_uploads(sub: str) -> list[dict[str, Any]]:
    return [job for job in get_store().list_jobs(sub) if job.get("status") in ACTIVE_UPLOAD_STATUSES]


def _extracts_today(sub: str) -> int:
    today = utc_day()
    return sum(1 for job in get_store().list_jobs(sub) if job.get("extractDay") == today)


def _write_audit(
    sub: str,
    *,
    kind: str,
    model_id: str,
    input_tokens: int,
    output_tokens: int,
    citation_urls: list[str] | None = None,
) -> None:
    now = utc_now()
    get_store().put_audit(
        {
            "pk": user_pk(sub),
            "sk": f"TS#{now}#{new_job_id()[:8]}",
            "kind": kind,
            "modelId": model_id,
            "inputTokens": input_tokens,
            "outputTokens": output_tokens,
            "citationUrls": citation_urls or [],
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
