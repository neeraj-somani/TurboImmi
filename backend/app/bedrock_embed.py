"""Titan Text Embeddings V2. Never log input text."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger("turboimmi.embed")


def _client() -> Any:
    import boto3
    from botocore.config import Config

    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-2"
    return boto3.client(
        "bedrock-runtime",
        region_name=region,
        config=Config(retries={"max_attempts": 2, "mode": "standard"}),
    )


def embed_texts(texts: list[str], *, model_id: str) -> list[list[float]]:
    client = _client()
    vectors: list[list[float]] = []
    for text in texts:
        response = client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps({"inputText": text[:8000], "dimensions": 256, "normalize": True}),
        )
        payload = json.loads(response["body"].read())
        embedding = payload.get("embedding")
        if not isinstance(embedding, list):
            logger.warning("embed response missing vector")
            vectors.append([])
            continue
        vectors.append([float(value) for value in embedding])
    return vectors
