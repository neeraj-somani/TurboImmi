"""Citation-or-silence policy chat. Educational only. No approval odds."""

from __future__ import annotations

import logging
import os
from typing import Any

from app.disclaimer import load_disclaimer
from app.retrieve import retrieve
from app.score_explain import chat_model_id

logger = logging.getLogger("turboimmi.chat")

REFUSE_TOKEN = "REFUSE"
MAX_CHAT_MESSAGE = 400
MAX_CHAT_TURNS = 15
MAX_CHAT_TOKENS = 280

SILENCE = (
    "I can only answer from the short USCIS excerpts we store, and I do not have a cited "
    "source for that. Verify on USCIS.gov. A licensed attorney must review before filing."
)


def public_citation(item: dict[str, Any]) -> dict[str, str]:
    return {
        "title": str(item.get("title") or ""),
        "source_url": str(item.get("source_url") or ""),
        "retrieved_at": str(item.get("retrieved_at") or ""),
    }


def fixture_answer(chunks: list[dict[str, Any]]) -> str:
    first = chunks[0]
    cite = public_citation(first)
    return (
        f"{first.get('text')} Source: {cite['title']} — as of {cite['retrieved_at']} — "
        f"Verify on USCIS.gov. A licensed attorney must review before filing. "
        "This is educational, not legal advice."
    )


def _context_block(chunks: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for item in chunks:
        parts.append(
            f"TITLE: {item.get('title')}\nURL: {item.get('source_url')}\n"
            f"AS_OF: {item.get('retrieved_at')}\nTEXT: {item.get('text')}"
        )
    return "\n\n".join(parts)


def _converse(question: str, chunks: list[dict[str, Any]]) -> tuple[str | None, dict[str, Any]]:
    model = chat_model_id()
    meta = {"modelId": model or "fixture", "inputTokens": 0, "outputTokens": 0}
    if not model:
        return fixture_answer(chunks), meta
    system = (
        f"{load_disclaimer().get('systemPromptBlock') or ''} "
        "Use only the USCIS excerpts in the user message. Quote or paraphrase them and include "
        "the source URL and as-of date. If they do not answer the question, reply with exactly "
        f"{REFUSE_TOKEN} and nothing else. Do not invent citations."
    )
    prompt = (
        f"EXCERPTS:\n{_context_block(chunks)}\n\nQUESTION:\n{question}\n\n"
        f"Answer from the excerpts only, or {REFUSE_TOKEN}."
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
        response = client.converse(
            modelId=model,
            system=[{"text": system}],
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": MAX_CHAT_TOKENS, "temperature": 0},
        )
    except Exception:
        logger.warning("policy chat converse failed")
        return fixture_answer(chunks), meta
    usage = response.get("usage") or {}
    meta["inputTokens"] = int(usage.get("inputTokens") or 0)
    meta["outputTokens"] = int(usage.get("outputTokens") or 0)
    parts = response.get("output", {}).get("message", {}).get("content") or []
    text = ""
    for part in parts:
        if isinstance(part, dict) and part.get("text"):
            text = str(part["text"]).strip()
            break
    if not text or text.upper().startswith(REFUSE_TOKEN):
        return None, meta
    return text, meta


def answer_question(question: str, store: Any) -> dict[str, Any]:
    chunks = retrieve(question, store)
    citations = [public_citation(item) for item in chunks]
    if not chunks:
        return {
            "answer": SILENCE,
            "refused": True,
            "citations": [],
            "modelId": "none",
            "inputTokens": 0,
            "outputTokens": 0,
        }
    text, meta = _converse(question, chunks)
    if not text:
        return {
            "answer": SILENCE,
            "refused": True,
            "citations": citations,
            "modelId": meta.get("modelId"),
            "inputTokens": meta.get("inputTokens") or 0,
            "outputTokens": meta.get("outputTokens") or 0,
        }
    return {
        "answer": text,
        "refused": False,
        "citations": citations,
        "modelId": meta.get("modelId"),
        "inputTokens": meta.get("inputTokens") or 0,
        "outputTokens": meta.get("outputTokens") or 0,
    }
