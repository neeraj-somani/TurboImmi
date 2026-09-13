import os

import pytest

os.environ["TURBOIMMI_STORE"] = "memory"
os.environ.pop("USERS_TABLE", None)
os.environ.pop("CASES_TABLE", None)
os.environ.pop("USER_POOL_ID", None)
os.environ.pop("DOCS_BUCKET", None)
os.environ.pop("BEDROCK_VISION_MODEL_ID", None)
os.environ.pop("BEDROCK_CHAT_MODEL_ID", None)
os.environ.pop("BEDROCK_EMBED_MODEL_ID", None)
os.environ.pop("PREFILL_TABLE", None)
os.environ.pop("AUDIT_TABLE", None)
os.environ.pop("ATTORNEYS_TABLE", None)
os.environ.pop("CONSULTS_TABLE", None)
os.environ.pop("ATTORNEY_DEMO_SUB", None)
os.environ.pop("ADMIN_ALLOWLIST_EMAIL", None)

from app.store import reset_store


@pytest.fixture(autouse=True)
def _clean_store() -> None:
    reset_store()
    yield
    reset_store()
