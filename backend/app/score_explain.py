"""Bedrock explanation of rule hits only. Never invent approval odds. Never send passport numbers."""

from __future__ import annotations

import logging
import os
from typing import Any

from app.disclaimer import load_disclaimer

logger = logging.getLogger("turboimmi.score")


def chat_model_id() -> str:
    return (os.environ.get("BEDROCK_CHAT_MODEL_ID") or "").strip()


def explain_hits(deductions: list[dict[str, str]]) -> tuple[str | None, dict[str, Any]]:
    model = chat_model_id()
    meta = {"modelId": model, "inputTokens": 0, "outputTokens": 0}
    if not model or not deductions:
        return None, meta
    lines = [f"{item.get('id')}: {item.get('message')}" for item in deductions]
    prompt = (
        "Explain these completeness/consistency rule hits in plain language. "
        "Do not predict visa approval. Do not add rules that are not listed. "
        "Remind the reader this is educational and an attorney must review before filing.\n"
        + "\n".join(lines)
    )
    try:
        import boto3
        from botocore.config import Config

        region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-2"
        client = boto3.client(
            "bedrock-runtime",
            region_name=region,
            config=Config(retries={"max_attempts": 2, "mode": "standard"}),
        )
        system = load_disclaimer().get("systemPromptBlock") or ""
        response = client.converse(
            modelId=model,
            system=[{"text": str(system)}],
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 250, "temperature": 0},
        )
    except Exception:
        logger.warning("score explain converse failed")
        return None, meta
    usage = response.get("usage") or {}
    meta["inputTokens"] = int(usage.get("inputTokens") or 0)
    meta["outputTokens"] = int(usage.get("outputTokens") or 0)
    parts = response.get("output", {}).get("message", {}).get("content") or []
    text = ""
    for part in parts:
        if isinstance(part, dict) and part.get("text"):
            text = str(part["text"]).strip()
            break
    return (text or None), meta
