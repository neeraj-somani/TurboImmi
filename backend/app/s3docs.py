"""Private docs bucket helpers. Never log object bytes."""

from __future__ import annotations

import os
from typing import Any


def docs_bucket() -> str:
    return (os.environ.get("DOCS_BUCKET") or "").strip()


def _client() -> Any:
    import boto3

    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-2"
    return boto3.client("s3", region_name=region)


def object_key(sub: str, job_id: str) -> str:
    return f"users/{sub}/prefill/{job_id}"


def presign_put(key: str, content_type: str, expires: int = 300) -> str:
    return _client().generate_presigned_url(
        "put_object",
        Params={"Bucket": docs_bucket(), "Key": key, "ContentType": content_type},
        ExpiresIn=expires,
        HttpMethod="PUT",
    )


def get_object_bytes(key: str) -> tuple[bytes, str] | None:
    try:
        resp = _client().get_object(Bucket=docs_bucket(), Key=key)
    except Exception:
        return None
    body = resp["Body"].read()
    content_type = str(resp.get("ContentType") or "application/octet-stream")
    return body, content_type


def delete_object(key: str) -> None:
    if not docs_bucket() or not key:
        return
    _client().delete_object(Bucket=docs_bucket(), Key=key)
