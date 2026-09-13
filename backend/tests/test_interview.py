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


def test_interview_writes_case_and_marks_in_progress() -> None:
    headers = _applicant("intent-user")
    case_id = client.get("/cases", headers=headers).json()["cases"][0]["caseId"]
    saved = client.patch(
        f"/cases/{case_id}",
        headers=headers,
        json={
            "intent": "transfer",
            "entryPath": "consular",
            "capExemptClaim": False,
            "requestedStart": "2026-10-01",
            "requestedEnd": "2029-09-30",
        },
    )
    assert saved.status_code == 200
    body = saved.json()
    assert body["intent"] == "transfer"
    assert body["entryPath"] == "consular"
    assert body["requestedStart"] == "2026-10-01"
    assert body["status"] == "in_progress"


def test_interview_rejects_end_before_start() -> None:
    headers = _applicant("dates-user")
    case_id = client.get("/cases", headers=headers).json()["cases"][0]["caseId"]
    bad = client.patch(
        f"/cases/{case_id}",
        headers=headers,
        json={"requestedStart": "2027-01-01", "requestedEnd": "2026-01-01"},
    )
    assert bad.status_code == 400
    assert bad.json()["detail"]["code"] == "VALIDATION"


def test_interview_rejects_unknown_entry_path() -> None:
    headers = _applicant("path-user")
    case_id = client.get("/cases", headers=headers).json()["cases"][0]["caseId"]
    bad = client.patch(
        f"/cases/{case_id}",
        headers=headers,
        json={"entryPath": "premium"},
    )
    assert bad.status_code == 422
