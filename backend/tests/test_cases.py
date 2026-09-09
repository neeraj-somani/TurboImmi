from fastapi.testclient import TestClient

from app.main import app
from app.store import reset_store
from tests.jwt_util import auth_header

client = TestClient(app)


def setup_function() -> None:
    reset_store()


def _applicant(sub: str) -> dict[str, str]:
    headers = auth_header(sub, **{"cognito:username": sub})
    chosen = client.post("/me/role", headers=headers, json={"role": "Applicant"})
    assert chosen.status_code == 200
    return headers


def test_cases_forbidden_without_applicant_role() -> None:
    headers = auth_header("plain-user")
    response = client.get("/cases", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "FORBIDDEN"


def test_attorney_cannot_list_cases() -> None:
    headers = auth_header("att-user", **{"cognito:username": "att-user"})
    client.post("/me/role", headers=headers, json={"role": "Attorney"})
    response = client.get("/cases", headers=headers)
    assert response.status_code == 403


def test_applicant_gets_seed_case_and_can_patch() -> None:
    headers = _applicant("case-user")
    listed = client.get("/cases", headers=headers)
    assert listed.status_code == 200
    cases = listed.json()["cases"]
    assert len(cases) == 1
    case_id = cases[0]["caseId"]
    patched = client.patch(
        f"/cases/{case_id}",
        headers=headers,
        json={"intent": "cap", "entryPath": "change_of_status"},
    )
    assert patched.status_code == 200
    assert patched.json()["intent"] == "cap"
    fetched = client.get(f"/cases/{case_id}", headers=headers)
    assert fetched.json()["entryPath"] == "change_of_status"


def test_create_case_and_missing_case() -> None:
    headers = _applicant("create-user")
    created = client.post("/cases", headers=headers, json={"intent": "transfer"})
    assert created.status_code == 200
    assert created.json()["intent"] == "transfer"
    listed = client.get("/cases", headers=headers)
    assert len(listed.json()["cases"]) == 2
    missing = client.get("/cases/does-not-exist", headers=headers)
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "NOT_FOUND"
