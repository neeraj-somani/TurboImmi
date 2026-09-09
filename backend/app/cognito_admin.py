"""Cognito admin calls for the in-app role chooser. No-op when USER_POOL_ID is unset (tests)."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any


@lru_cache(maxsize=1)
def _client() -> Any:
    import boto3

    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-2"
    return boto3.client("cognito-idp", region_name=region)


def _pool_id() -> str | None:
    pool = (os.environ.get("USER_POOL_ID") or "").strip()
    return pool or None


def list_groups(username: str) -> list[str]:
    pool = _pool_id()
    if not pool:
        return []
    resp = _client().admin_list_groups_for_user(UserPoolId=pool, Username=username)
    return [str(group.get("GroupName")) for group in resp.get("Groups") or [] if group.get("GroupName")]


def add_user_to_group(username: str, group: str) -> None:
    pool = _pool_id()
    if not pool:
        return
    _client().admin_add_user_to_group(
        UserPoolId=pool,
        Username=username,
        GroupName=group,
    )
