import os

import pytest

os.environ["TURBOIMMI_STORE"] = "memory"
os.environ.pop("USERS_TABLE", None)
os.environ.pop("CASES_TABLE", None)
os.environ.pop("USER_POOL_ID", None)

from app.store import reset_store


@pytest.fixture(autouse=True)
def _clean_store() -> None:
    reset_store()
    yield
    reset_store()
