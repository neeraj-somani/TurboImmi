"""Load repo-root .env for local uvicorn. Lambda already has table names in the function env."""

from __future__ import annotations

import os
from pathlib import Path


def load_repo_env() -> None:
    if os.environ.get("TURBOIMMI_STORE", "").lower() == "memory":
        return
    root = Path(__file__).resolve().parents[2] / ".env"
    if not root.is_file():
        return
    for raw in root.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key or not value:
            continue
        os.environ.setdefault(key, value)
