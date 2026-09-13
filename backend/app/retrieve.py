"""In-Lambda retrieval over the starter H-1B excerpts. Cosine first; lexical fallback."""

from __future__ import annotations

import hashlib
import math
import os
import re
from typing import Any

from app.policy_corpus import load_policy_excerpts

EMBED_DIM = 256
MIN_COSINE = 0.22
TOP_K = 2
_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "about",
        "can",
        "do",
        "does",
        "for",
        "how",
        "i",
        "in",
        "is",
        "me",
        "my",
        "of",
        "on",
        "or",
        "please",
        "tell",
        "the",
        "to",
        "we",
        "what",
        "when",
        "where",
        "who",
        "why",
    }
)


def embed_model_id() -> str:
    return (os.environ.get("BEDROCK_EMBED_MODEL_ID") or "").strip()


def tokens(text: str) -> list[str]:
    folded = text.lower().replace("-", "")
    return _TOKEN.findall(folded)


def content_tokens(text: str) -> set[str]:
    return {token for token in tokens(text) if token not in _STOP and len(token) > 1}


def hashed_embedding(text: str, dim: int = EMBED_DIM) -> list[float]:
    vec = [0.0] * dim
    for token in tokens(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:2], "big") % dim
        vec[idx] += 1.0
    return normalize(vec)


def normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vec))
    if norm == 0:
        return list(vec)
    return [value / norm for value in vec]


def cosine(left: list[float], right: list[float]) -> float:
    size = min(len(left), len(right))
    if size == 0:
        return 0.0
    return sum(left[i] * right[i] for i in range(size))


def _as_floats(raw: Any) -> list[float]:
    if not isinstance(raw, list):
        return []
    out: list[float] = []
    for value in raw:
        try:
            out.append(float(value))
        except (TypeError, ValueError):
            return []
    return out


def _embed_texts(texts: list[str]) -> list[list[float]]:
    model = embed_model_id()
    if not model:
        return [hashed_embedding(text) for text in texts]
    try:
        from app.bedrock_embed import embed_texts

        vectors = embed_texts(texts, model_id=model)
        if len(vectors) == len(texts) and all(len(item) > 0 for item in vectors):
            return [normalize(item) for item in vectors]
    except Exception:
        pass
    return [hashed_embedding(text) for text in texts]


def _chunk_item(excerpt: dict[str, Any], embedding: list[float]) -> dict[str, Any]:
    return {
        "pk": f"CHUNK#{excerpt['id']}",
        "sk": "META",
        "chunkId": excerpt["id"],
        "source_url": excerpt["source_url"],
        "title": excerpt["title"],
        "retrieved_at": excerpt["retrieved_at"],
        "content_hash": excerpt["content_hash"],
        "text": excerpt["text"],
        "embedding": embedding,
        "embeddingDim": len(embedding),
    }


def ensure_embedded_chunks(store: Any) -> list[dict[str, Any]]:
    excerpts = load_policy_excerpts()
    existing = {item.get("chunkId"): item for item in store.list_policy_chunks()}
    ready: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for excerpt in excerpts:
        item = existing.get(excerpt["id"])
        embedding = _as_floats((item or {}).get("embedding"))
        if item and item.get("content_hash") == excerpt["content_hash"] and embedding:
            item = dict(item)
            item["embedding"] = embedding
            ready.append(item)
        else:
            missing.append(excerpt)
    if missing:
        vectors = _embed_texts([str(item["text"]) for item in missing])
        for excerpt, embedding in zip(missing, vectors, strict=True):
            item = _chunk_item(excerpt, embedding)
            store.put_policy_chunk(item)
            ready.append(item)
    return ready


def retrieve(query: str, store: Any, *, top_k: int = TOP_K) -> list[dict[str, Any]]:
    question = query.strip()
    if not question:
        return []
    chunks = ensure_embedded_chunks(store)
    query_vec = _embed_texts([question])[0]
    query_tokens = content_tokens(question)
    use_titan = bool(embed_model_id())
    ranked: list[tuple[int, float, dict[str, Any]]] = []
    for item in chunks:
        score = cosine(query_vec, _as_floats(item.get("embedding")))
        doc_tokens = content_tokens(f"{item.get('title')} {item.get('text')}")
        overlap = len(query_tokens & doc_tokens)
        if use_titan:
            if score < MIN_COSINE:
                continue
            ranked.append((overlap, score, item))
        elif overlap:
            ranked.append((overlap, score, item))
    ranked.sort(key=lambda pair: (pair[0], pair[1]), reverse=True)
    return [item for _, _, item in ranked[:top_k]]
