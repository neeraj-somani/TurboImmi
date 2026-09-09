from __future__ import annotations

import base64
import json


def fake_jwt(**claims: object) -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none"}).encode()).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    return f"{header}.{payload}.sig"


def auth_header(sub: str = "user-1", **claims: object) -> dict[str, str]:
    token = fake_jwt(sub=sub, **claims)
    return {"Authorization": f"Bearer {token}"}
