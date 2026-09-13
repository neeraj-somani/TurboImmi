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


def test_directory_is_auth_only_and_published() -> None:
    assert client.get("/attorneys").status_code == 401
    headers = _role("dir-user", "Applicant")
    listed = client.get("/attorneys", headers=headers)
    assert listed.status_code == 200
    ids = {item["attorneyId"] for item in listed.json()["attorneys"]}
    assert ids == {"demo-chen", "demo-okonkwo"}
    assert all(item["published"] is True for item in listed.json()["attorneys"])
    assert all(item["verified"] is False for item in listed.json()["attorneys"])


def test_directory_filters_state_and_specialty() -> None:
    headers = _role("filter-user", "Applicant")
    california = client.get("/attorneys", headers=headers, params={"state": "CA"})
    assert {item["attorneyId"] for item in california.json()["attorneys"]} == {"demo-chen"}
    perm = client.get("/attorneys", headers=headers, params={"specialty": "perm"})
    assert {item["attorneyId"] for item in perm.json()["attorneys"]} == {"demo-okonkwo"}


def test_self_serve_attorney_stays_unpublished() -> None:
    headers = _role("self-att", "Attorney")
    saved = client.put(
        "/attorneys/me",
        headers=headers,
        json={
            "displayName": "Self Serve",
            "firmName": "Unpublished Demo",
            "usState": "NY",
            "specialties": ["h1b"],
            "bio": "I tried to publish myself.",
            "published": True,
            "verified": True,
        },
    )
    assert saved.status_code == 200
    assert saved.json()["published"] is False
    assert saved.json()["verified"] is False
    applicant = _role("reader", "Applicant")
    listed = client.get("/attorneys", headers=applicant)
    ids = {item["attorneyId"] for item in listed.json()["attorneys"]}
    assert saved.json()["attorneyId"] not in ids
    hidden = client.get(f"/attorneys/{saved.json()['attorneyId']}", headers=applicant)
    assert hidden.status_code == 404
    own = client.get(f"/attorneys/{saved.json()['attorneyId']}", headers=headers)
    assert own.status_code == 200


def test_published_detail_and_unknown_filter() -> None:
    headers = _role("detail-user", "Applicant")
    ok = client.get("/attorneys/demo-chen", headers=headers)
    assert ok.status_code == 200
    assert ok.json()["usState"] == "CA"
    bad = client.get("/attorneys", headers=headers, params={"state": "ZZ"})
    assert bad.status_code == 400


def test_applicant_cannot_put_attorney_me() -> None:
    headers = _role("app-put", "Applicant")
    response = client.put(
        "/attorneys/me",
        headers=headers,
        json={"displayName": "Nope", "usState": "CA", "specialties": ["h1b"]},
    )
    assert response.status_code == 403
