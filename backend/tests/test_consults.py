from fastapi.testclient import TestClient

from app.main import app
from app.store import reset_store
from tests.jwt_util import auth_header

client = TestClient(app)


def setup_function() -> None:
    reset_store()


def _role(sub: str, role: str) -> dict[str, str]:
    headers = auth_header(sub, **{"cognito:username": sub})
    chosen = client.post("/me/role", headers=headers, json={"role": role})
    assert chosen.status_code == 200
    return headers


def test_applicant_requests_consult_and_lists_mine() -> None:
    headers = _role("consult-app", "Applicant")
    case_id = client.get("/cases", headers=headers).json()["cases"][0]["caseId"]
    created = client.post(
        "/consults",
        headers=headers,
        json={"attorneyId": "demo-chen", "caseId": case_id, "message": "Please review my H-1B packet."},
    )
    assert created.status_code == 200
    assert created.json()["status"] == "requested"
    assert created.json()["attorneyId"] == "demo-chen"
    mine = client.get("/consults", headers=headers)
    assert mine.status_code == 200
    assert len(mine.json()["consults"]) == 1
    assert mine.json()["consults"][0]["message"] == "Please review my H-1B packet."


def test_consult_rejects_unpublished_and_empty_message() -> None:
    attorney = _role("hidden-att", "Attorney")
    card = client.put(
        "/attorneys/me",
        headers=attorney,
        json={"displayName": "Hidden", "usState": "OR", "specialties": ["h1b"]},
    )
    headers = _role("consult-bad", "Applicant")
    missing = client.post(
        "/consults",
        headers=headers,
        json={"attorneyId": card.json()["attorneyId"], "message": "hello"},
    )
    assert missing.status_code == 404
    empty = client.post("/consults", headers=headers, json={"attorneyId": "demo-chen", "message": "  "})
    assert empty.status_code == 400


def test_attorney_inbox_marks_seen(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_ALLOWLIST_EMAIL", "ops@example.com")
    attorney = _role("inbox-att", "Attorney")
    card = client.put(
        "/attorneys/me",
        headers=attorney,
        json={"displayName": "Demo Inbox", "usState": "WA", "specialties": ["h1b"], "bio": "Demo inbox bio."},
    )
    assert card.json()["published"] is False
    admin = auth_header("ops-inbox", email="ops@example.com", **{"cognito:username": "ops-inbox"})
    client.get("/me", headers=admin)
    client.patch(
        f"/admin/attorneys/{card.json()['attorneyId']}",
        headers=admin,
        json={"published": True},
    )
    applicant = _role("inbox-app", "Applicant")
    client.post(
        "/consults",
        headers=applicant,
        json={"attorneyId": card.json()["attorneyId"], "message": "Need a consult on cap vs transfer."},
    )
    inbox = client.get("/consults", headers=attorney)
    assert inbox.status_code == 200
    assert len(inbox.json()["consults"]) == 1
    assert inbox.json()["consults"][0]["status"] == "seen"
    assert inbox.json()["consults"][0]["message"] == "Need a consult on cap vs transfer."


def test_attorney_cannot_create_consult() -> None:
    headers = _role("att-consult", "Attorney")
    response = client.post(
        "/consults",
        headers=headers,
        json={"attorneyId": "demo-chen", "message": "nope"},
    )
    assert response.status_code == 403
