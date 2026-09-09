"""Load the shared disclaimer used by UI and later system prompts."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


def _disclaimer_path() -> Path:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[1] / "shared" / "disclaimer.json",  # Lambda bundle
        here.parents[2] / "shared" / "disclaimer.json",  # repo: backend/app/...
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError("shared/disclaimer.json not found")


@lru_cache(maxsize=1)
def load_disclaimer() -> dict[str, Any]:
    return json.loads(_disclaimer_path().read_text(encoding="utf-8"))
