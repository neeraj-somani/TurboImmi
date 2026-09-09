"""Cognito JWT principal. API Gateway verifies the token; local/tests decode the payload."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from typing import Any

from fastapi import HTTPException, Request

_UNAUTH = HTTPException(
    status_code=401,
    detail={"code": "UNAUTHORIZED", "message": "Sign in required"},
)


@dataclass
class Principal:
    sub: str
    username: str
    email: str | None = None
    groups: list[str] = field(default_factory=list)
    claims: dict[str, Any] = field(default_factory=dict)


def _b64url_json(segment: str) -> dict[str, Any]:
    pad = "=" * (-len(segment) % 4)
    try:
        data = json.loads(base64.urlsafe_b64decode(segment + pad))
    except (ValueError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def decode_jwt_payload(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) < 2:
        return {}
    return _b64url_json(parts[1])


def parse_groups(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(item) for item in raw if str(item).strip()]
    if isinstance(raw, str):
        text = raw.strip()
        if text.startswith("["):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                return [str(item) for item in parsed if str(item).strip()]
        return [part.strip() for part in text.split(",") if part.strip()]
    return []


def claims_from_request(request: Request) -> dict[str, Any]:
    event = request.scope.get("aws.event") or {}
    claims = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("jwt", {})
        .get("claims")
        or {}
    )
    if isinstance(claims, dict) and claims.get("sub"):
        return claims
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        decoded = decode_jwt_payload(token)
        if decoded.get("sub"):
            return decoded
    return {}


def principal_from_claims(claims: dict[str, Any]) -> Principal | None:
    sub = claims.get("sub")
    if not isinstance(sub, str) or not sub.strip():
        return None
    username = claims.get("cognito:username") or claims.get("username") or sub
    email = claims.get("email")
    return Principal(
        sub=sub.strip(),
        username=str(username).strip() if username else sub.strip(),
        email=str(email).strip() if isinstance(email, str) and email.strip() else None,
        groups=parse_groups(claims.get("cognito:groups")),
        claims=claims,
    )


def get_principal(request: Request) -> Principal:
    principal = principal_from_claims(claims_from_request(request))
    if principal is None:
        raise _UNAUTH
    return principal
