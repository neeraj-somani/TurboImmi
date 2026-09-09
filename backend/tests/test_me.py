from fastapi.testclient import TestClient

from app.main import app
from app.store import reset_store
from tests.jwt_util import auth_header

client = TestClient(app)


def setup_function() -> None:
    reset_store()


def test_me_seeds_on_first_login() -> None:
    response = client.get("/me", headers=auth_header("seed-user", email="a@example.com"))
    assert response.status_code == 200
    body = response.json()
    assert body["sub"] == "seed-user"
    assert body["roleChosen"] is False
    assert body["role"] is None
    assert body["email"] == "a@example.com"


def test_role_choose_then_lock() -> None:
    headers = auth_header("role-user", **{"cognito:username": "role-user"})
    first = client.post("/me/role", headers=headers, json={"role": "Applicant"})
    assert first.status_code == 200
    assert first.json() == {
        "role": "Applicant",
        "roleChosen": True,
        "refreshRequired": True,
    }
    second = client.post("/me/role", headers=headers, json={"role": "Attorney"})
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "ROLE_LOCKED"


def test_role_lock_when_jwt_already_has_group() -> None:
    headers = auth_header(
        "grouped-user",
        **{"cognito:groups": ["Attorney"], "cognito:username": "grouped-user"},
    )
    response = client.post("/me/role", headers=headers, json={"role": "Applicant"})
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ROLE_LOCKED"


def test_put_profile_persists() -> None:
    headers = auth_header("profile-user")
    saved = client.put(
        "/me/profile",
        headers=headers,
        json={
            "legalName": {"given": "Ada", "family": "Lovelace"},
            "jobTitle": "Software engineer",
            "journeyStage": "h1b",
        },
    )
    assert saved.status_code == 200
    profile = saved.json()["profile"]
    assert profile["legalName"]["given"] == "Ada"
    assert profile["jobTitle"] == "Software engineer"
    again = client.get("/me/profile", headers=headers)
    assert again.json()["profile"]["legalName"]["family"] == "Lovelace"
