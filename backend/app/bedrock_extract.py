"""Bedrock Converse extract. Never log model text or image bytes."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from app.disclaimer import load_disclaimer

logger = logging.getLogger("turboimmi.extract")

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def vision_model_id() -> str:
    return (os.environ.get("BEDROCK_VISION_MODEL_ID") or "").strip()


def _client() -> Any:
    import boto3
    from botocore.config import Config

    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-2"
    return boto3.client(
        "bedrock-runtime",
        region_name=region,
        config=Config(retries={"max_attempts": 2, "mode": "standard"}),
    )


def _prompt(doc_type: str) -> str:
    if doc_type == "offer_letter":
        return (
            "Extract employment fields from this offer letter. Return JSON only with keys: "
            "employerLegalName, employerFein, jobTitle, socCode, wageAmount, wageUnit, worksiteAddress. "
            "Use empty string if unknown. Do not add other keys. Do not guess visa approval."
        )
    return (
        "Extract passport biographic fields. Return JSON only with keys: "
        "legalName (object with given and family), dateOfBirth (ISO date), countryOfBirth, "
        "countryOfCitizenship, passportNumber, passportExpiry (ISO date). "
        "Use empty string if unknown. Do not add other keys. Do not guess visa approval."
    )


def extract_structured(
    *,
    doc_type: str,
    payload: bytes,
    content_type: str,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    model = vision_model_id()
    meta = {"modelId": model, "inputTokens": 0, "outputTokens": 0}
    if not model or not payload:
        return None, meta

    blocks: list[dict[str, Any]] = []
    if content_type in ("image/jpeg", "image/jpg"):
        blocks.append({"image": {"format": "jpeg", "source": {"bytes": payload}}})
    elif content_type == "image/png":
        blocks.append({"image": {"format": "png", "source": {"bytes": payload}}})
    elif content_type == "application/pdf":
        blocks.append(
            {"document": {"format": "pdf", "name": "upload", "source": {"bytes": payload}}}
        )
    else:
        return None, meta
    blocks.append({"text": _prompt(doc_type)})

    system = load_disclaimer().get("systemPromptBlock") or ""
    try:
        response = _client().converse(
            modelId=model,
            system=[{"text": str(system)}],
            messages=[{"role": "user", "content": blocks}],
            inferenceConfig={"maxTokens": 400, "temperature": 0},
        )
    except Exception:
        logger.warning("extract converse failed job_type=%s", doc_type)
        return None, meta

    usage = response.get("usage") or {}
    meta["inputTokens"] = int(usage.get("inputTokens") or 0)
    meta["outputTokens"] = int(usage.get("outputTokens") or 0)
    parts = response.get("output", {}).get("message", {}).get("content") or []
    text = ""
    for part in parts:
        if isinstance(part, dict) and part.get("text"):
            text = str(part["text"])
            break
    match = _JSON_RE.search(text)
    if not match:
        return None, meta
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None, meta
    if not isinstance(parsed, dict):
        return None, meta
    return parsed, meta
