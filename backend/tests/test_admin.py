from fastapi.testclient import TestClient

from app.main import app
from app.store import reset_store
from tests.jwt_util import auth_header

client = TestClient(app)


def setup_function() -> None:
    reset_store()


def _role(sub: str, role: str, email: str | None = None) -> dict[str, str]:
    extra = {"cognito:username": sub}
    if email:
        extra["email"] = email
    headers = auth_header(sub, **extra)
    chosen = client.post("/me/role", headers=headers, json={"role": role})
    assert chosen.status_code == 200
    return headers


def test_chooser_cannot_pick_admin() -> None:
    headers = auth_header("no-admin", **{"cognito:username": "no-admin"})
    response = client.post("/me/role", headers=headers, json={"role": "Admin"})
    assert response.status_code == 422


def test_allowlisted_email_promoted_on_me(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_ALLOWLIST_EMAIL", "ops@example.com")
    headers = auth_header("ops-user", email="ops@example.com", **{"cognito:username": "ops-user"})
    me = client.get("/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["role"] == "Admin"
    assert me.json()["roleChosen"] is True
    locked = client.post("/me/role", headers=headers, json={"role": "Applicant"})
    assert locked.status_code == 409


def test_existing_applicant_is_not_stolen(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_ALLOWLIST_EMAIL", "taken@example.com")
    headers = _role("taken-user", "Applicant", email="taken@example.com")
    me = client.get("/me", headers=headers)
    assert me.json()["role"] == "Applicant"
    admin = client.get("/admin/me", headers=headers)
    assert admin.status_code == 403


def test_applicant_cannot_use_admin_routes() -> None:
    headers = _role("app-admin", "Applicant")
    assert client.get("/admin/attorneys", headers=headers).status_code == 403
    assert client.get("/admin/me", headers=headers).status_code == 403


def test_attorney_cannot_use_admin_routes() -> None:
    headers = _role("atty-admin", "Attorney")
    assert client.get("/admin/attorneys", headers=headers).status_code == 403
    assert client.put("/admin/me", headers=headers, json={"displayName": "Nope"}).status_code == 403


def test_admin_cannot_list_cases(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_ALLOWLIST_EMAIL", "ops@example.com")
    headers = auth_header("ops-cases", email="ops@example.com", **{"cognito:username": "ops-cases"})
    client.get("/me", headers=headers)
    assert client.get("/cases", headers=headers).status_code == 403
    assert client.post("/prefill/extract", headers=headers, json={"jobId": "x"}).status_code == 403


def test_admin_sees_unpublished_and_can_publish(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_ALLOWLIST_EMAIL", "ops@example.com")
    attorney = _role("self-att", "Attorney")
    card = client.put(
        "/attorneys/me",
        headers=attorney,
        json={"displayName": "Self Serve", "usState": "NY", "specialties": ["h1b"], "bio": "Short bio."},
    )
    attorney_id = card.json()["attorneyId"]
    assert card.json()["published"] is False
    peek = _role("peek-dir", "Applicant")
    hidden = client.get("/attorneys", headers=peek)
    assert attorney_id not in {item["attorneyId"] for item in hidden.json()["attorneys"]}
    admin = auth_header("ops-user", email="ops@example.com", **{"cognito:username": "ops-user"})
    client.get("/me", headers=admin)
    listed = client.get("/admin/attorneys", headers=admin)
    ids = {item["attorneyId"] for item in listed.json()["attorneys"]}
    assert attorney_id in ids
    assert "demo-chen" in ids
    patched = client.patch(
        f"/admin/attorneys/{attorney_id}",
        headers=admin,
        json={"published": True, "verified": True, "flag": "none"},
    )
    assert patched.status_code == 200
    assert patched.json()["published"] is True
    assert patched.json()["verified"] is True
    applicant = _role("reader", "Applicant")
    public = client.get("/attorneys", headers=applicant)
    assert attorney_id in {item["attorneyId"] for item in public.json()["attorneys"]}


def test_admin_can_flag_incomplete(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_ALLOWLIST_EMAIL", "ops@example.com")
    admin = auth_header("flag-ops", email="ops@example.com", **{"cognito:username": "flag-ops"})
    client.get("/me", headers=admin)
    saved = client.patch(
        "/admin/attorneys/demo-chen",
        headers=admin,
        json={"flag": "incomplete", "flagNote": "Need a longer bio."},
    )
    assert saved.status_code == 200
    assert saved.json()["flag"] == "incomplete"
    assert saved.json()["flagNote"] == "Need a longer bio."
    flagged = client.get("/admin/attorneys", headers=admin, params={"flagged": True})
    assert {item["attorneyId"] for item in flagged.json()["attorneys"]} == {"demo-chen"}
