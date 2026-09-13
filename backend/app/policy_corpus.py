"""Starter attributed H-1B excerpts for in-Lambda retrieval (hashed fixture or Titan)."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

REQUIRED = ("id", "source_url", "title", "retrieved_at", "content_hash", "text")


def _policy_path() -> Path:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[1] / "shared" / "policy" / "h1b_excerpts.json",
        here.parents[2] / "shared" / "policy" / "h1b_excerpts.json",
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError("shared/policy/h1b_excerpts.json not found")


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def load_policy_excerpts() -> list[dict[str, Any]]:
    raw = json.loads(_policy_path().read_text(encoding="utf-8"))
    chunks = list(raw.get("chunks") or [])
    if not chunks:
        raise ValueError("policy corpus is empty")
    out: list[dict[str, Any]] = []
    for chunk in chunks:
        item = dict(chunk)
        text = str(item.get("text") or "")
        if not text.strip():
            raise ValueError("policy excerpt text is empty")
        expected = hash_text(text)
        stored = str(item.get("content_hash") or "")
        if stored and stored != expected:
            raise ValueError(f"content_hash mismatch for {item.get('id')}")
        item["content_hash"] = expected
        missing = [key for key in REQUIRED if not item.get(key)]
        if missing:
            raise ValueError(f"policy excerpt missing {missing}")
        if "uscis.gov" not in str(item["source_url"]):
            raise ValueError("policy excerpt must deep-link to USCIS.gov")
        out.append(item)
    return out
