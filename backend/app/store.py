"""Users + Cases persistence. DynamoDB in AWS; in-memory for pytest."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import uuid4

ALLOWED_ROLES = ("Applicant", "Attorney")
JOURNEY_STAGES = (
    "f1",
    "cpt",
    "opt",
    "stem_opt",
    "h1b",
    "h4",
    "h4_ead",
    "perm",
    "i140",
    "aos",
)
CASE_STATUSES = ("draft", "in_progress")
INTENTS = ("cap", "transfer", "extension")
ENTRY_PATHS = ("change_of_status", "consular")
PREFILL_STATUSES = ("uploaded", "extracted", "confirmed", "deleted")
DOC_TYPES = ("passport", "offer_letter")
ACTIVE_UPLOAD_STATUSES = ("uploaded", "extracted")
MAX_ACTIVE_UPLOADS = 2
MAX_EXTRACTS_PER_UTC_DAY = 3
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
ALLOWED_CONTENT_TYPES = ("image/jpeg", "image/png", "application/pdf")

_store: "Store | None" = None


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_job_id() -> str:
    return uuid4().hex


def new_case_id() -> str:
    return uuid4().hex


def utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def ttl_unix(days: int) -> int:
    from time import time

    return int(time()) + days * 86400


def user_pk(sub: str) -> str:
    return f"USER#{sub}"


def empty_profile(email: str | None) -> dict[str, Any]:
    profile: dict[str, Any] = {
        "legalName": {"given": "", "family": ""},
        "journeyStage": "h1b",
    }
    if email:
        profile["email"] = email
    return profile


def seed_user_item(sub: str, email: str | None) -> dict[str, Any]:
    now = utc_now()
    return {
        "pk": user_pk(sub),
        "sk": "PROFILE",
        "roleChosen": False,
        "profile": empty_profile(email),
        "createdAt": now,
        "updatedAt": now,
    }


def seed_case_item(sub: str, case_id: str | None = None) -> dict[str, Any]:
    cid = case_id or new_case_id()
    now = utc_now()
    return {
        "pk": user_pk(sub),
        "sk": f"CASE#{cid}",
        "caseId": cid,
        "visaClass": "H-1B",
        "status": "draft",
        "capExemptClaim": False,
        "formFields": {},
        "createdAt": now,
        "updatedAt": now,
    }


def public_user(item: dict[str, Any], *, sub: str, groups: list[str], email: str | None) -> dict[str, Any]:
    role = item.get("role")
    role_chosen = bool(item.get("roleChosen")) or role in ALLOWED_ROLES
    return {
        "sub": sub,
        "email": email or (item.get("profile") or {}).get("email"),
        "groups": groups,
        "roleChosen": role_chosen,
        "role": role if role in ALLOWED_ROLES else None,
    }


def public_profile(item: dict[str, Any]) -> dict[str, Any]:
    role = item.get("role")
    return {
        "roleChosen": bool(item.get("roleChosen")) or role in ALLOWED_ROLES,
        "role": role if role in ALLOWED_ROLES else None,
        "profile": dict(item.get("profile") or {}),
        "updatedAt": item.get("updatedAt"),
    }


def public_case(item: dict[str, Any]) -> dict[str, Any]:
    case_id = item.get("caseId")
    if not case_id:
        sk = str(item.get("sk") or "")
        case_id = sk.split("CASE#", 1)[-1] if sk.startswith("CASE#") else sk
    out: dict[str, Any] = {
        "caseId": case_id,
        "visaClass": item.get("visaClass") or "H-1B",
        "status": item.get("status") or "draft",
        "capExemptClaim": bool(item.get("capExemptClaim")),
        "formFields": dict(item.get("formFields") or {}),
        "createdAt": item.get("createdAt"),
        "updatedAt": item.get("updatedAt"),
    }
    for key in ("intent", "entryPath", "requestedStart", "requestedEnd", "lcaEtaNumber", "score", "attestationAcceptedAt"):
        if key in item and item[key] is not None:
            out[key] = item[key]
    return out


def public_job(item: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "jobId": item.get("jobId"),
        "docType": item.get("docType"),
        "status": item.get("status"),
        "source": item.get("source"),
        "createdAt": item.get("createdAt"),
        "updatedAt": item.get("updatedAt"),
    }
    if item.get("suggestions"):
        out["suggestions"] = dict(item["suggestions"])
    return out


def drop_none(item: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in item.items() if value is not None}


class Store(Protocol):
    def get_user(self, sub: str) -> dict[str, Any] | None: ...

    def put_user(self, item: dict[str, Any]) -> None: ...

    def list_cases(self, sub: str) -> list[dict[str, Any]]: ...

    def get_case(self, sub: str, case_id: str) -> dict[str, Any] | None: ...

    def put_case(self, item: dict[str, Any]) -> None: ...

    def list_jobs(self, sub: str) -> list[dict[str, Any]]: ...

    def get_job(self, sub: str, job_id: str) -> dict[str, Any] | None: ...

    def put_job(self, item: dict[str, Any]) -> None: ...

    def put_audit(self, item: dict[str, Any]) -> None: ...


class MemoryStore:
    def __init__(self) -> None:
        self._users: dict[str, dict[str, Any]] = {}
        self._cases: dict[tuple[str, str], dict[str, Any]] = {}
        self._jobs: dict[tuple[str, str], dict[str, Any]] = {}
        self._audits: list[dict[str, Any]] = []

    def get_user(self, sub: str) -> dict[str, Any] | None:
        item = self._users.get(sub)
        return dict(item) if item else None

    def put_user(self, item: dict[str, Any]) -> None:
        sub = str(item["pk"]).removeprefix("USER#")
        self._users[sub] = dict(item)

    def list_cases(self, sub: str) -> list[dict[str, Any]]:
        rows = [dict(item) for (owner, _), item in self._cases.items() if owner == sub]
        rows.sort(key=lambda row: str(row.get("createdAt") or ""), reverse=True)
        return rows

    def get_case(self, sub: str, case_id: str) -> dict[str, Any] | None:
        item = self._cases.get((sub, case_id))
        return dict(item) if item else None

    def put_case(self, item: dict[str, Any]) -> None:
        sub = str(item["pk"]).removeprefix("USER#")
        case_id = str(item.get("caseId") or "")
        self._cases[(sub, case_id)] = dict(item)

    def list_jobs(self, sub: str) -> list[dict[str, Any]]:
        rows = [dict(item) for (owner, _), item in self._jobs.items() if owner == sub]
        rows.sort(key=lambda row: str(row.get("createdAt") or ""), reverse=True)
        return rows

    def get_job(self, sub: str, job_id: str) -> dict[str, Any] | None:
        item = self._jobs.get((sub, job_id))
        return dict(item) if item else None

    def put_job(self, item: dict[str, Any]) -> None:
        sub = str(item["pk"]).removeprefix("USER#")
        job_id = str(item.get("jobId") or "")
        self._jobs[(sub, job_id)] = dict(item)

    def put_audit(self, item: dict[str, Any]) -> None:
        self._audits.append(dict(item))


class DynamoStore:
    def __init__(self) -> None:
        import boto3

        region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-2"
        ddb = boto3.resource("dynamodb", region_name=region)
        self._users = ddb.Table(os.environ["USERS_TABLE"])
        self._cases = ddb.Table(os.environ["CASES_TABLE"])
        prefill = os.environ.get("PREFILL_TABLE") or "turboimmi-dev-prefill-jobs"
        audit = os.environ.get("AUDIT_TABLE") or "turboimmi-dev-ai-audit"
        self._jobs = ddb.Table(prefill)
        self._audit = ddb.Table(audit)

    def get_user(self, sub: str) -> dict[str, Any] | None:
        resp = self._users.get_item(Key={"pk": user_pk(sub), "sk": "PROFILE"})
        item = resp.get("Item")
        return dict(item) if item else None

    def put_user(self, item: dict[str, Any]) -> None:
        self._users.put_item(Item=drop_none(item))

    def list_cases(self, sub: str) -> list[dict[str, Any]]:
        from boto3.dynamodb.conditions import Key

        resp = self._cases.query(
            KeyConditionExpression=Key("pk").eq(user_pk(sub)) & Key("sk").begins_with("CASE#")
        )
        rows = [dict(item) for item in resp.get("Items") or []]
        rows.sort(key=lambda row: str(row.get("createdAt") or ""), reverse=True)
        return rows

    def get_case(self, sub: str, case_id: str) -> dict[str, Any] | None:
        resp = self._cases.get_item(Key={"pk": user_pk(sub), "sk": f"CASE#{case_id}"})
        item = resp.get("Item")
        return dict(item) if item else None

    def put_case(self, item: dict[str, Any]) -> None:
        self._cases.put_item(Item=drop_none(item))

    def list_jobs(self, sub: str) -> list[dict[str, Any]]:
        from boto3.dynamodb.conditions import Key

        resp = self._jobs.query(
            KeyConditionExpression=Key("pk").eq(user_pk(sub)) & Key("sk").begins_with("JOB#")
        )
        rows = [dict(item) for item in resp.get("Items") or []]
        rows.sort(key=lambda row: str(row.get("createdAt") or ""), reverse=True)
        return rows

    def get_job(self, sub: str, job_id: str) -> dict[str, Any] | None:
        resp = self._jobs.get_item(Key={"pk": user_pk(sub), "sk": f"JOB#{job_id}"})
        item = resp.get("Item")
        return dict(item) if item else None

    def put_job(self, item: dict[str, Any]) -> None:
        self._jobs.put_item(Item=drop_none(item))

    def put_audit(self, item: dict[str, Any]) -> None:
        self._audit.put_item(Item=drop_none(item))


def get_store() -> Store:
    global _store
    if _store is None:
        use_memory = os.environ.get("TURBOIMMI_STORE", "").lower() == "memory"
        if not use_memory and os.environ.get("USERS_TABLE") and os.environ.get("CASES_TABLE"):
            _store = DynamoStore()
        else:
            _store = MemoryStore()
    return _store


def reset_store() -> None:
    global _store
    _store = None
