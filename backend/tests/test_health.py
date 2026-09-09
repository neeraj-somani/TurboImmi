from fastapi.testclient import TestClient

from app.main import app
from tests.jwt_util import auth_header

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_disclaimer_has_educational_posture() -> None:
    response = client.get("/disclaimer")
    assert response.status_code == 200
    body = response.json()
    text = f"{body.get('short', '')} {body.get('full', '')}".lower()
    assert "not a law firm" in text
    assert "not provide legal advice" in text
    assert "attorney" in text
    assert body.get("tosPath") == "/terms"
    assert body.get("privacyPath") == "/privacy"


def test_health_auth_requires_sign_in() -> None:
    response = client.get("/health/auth")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "UNAUTHORIZED"


def test_health_auth_accepts_bearer() -> None:
    response = client.get("/health/auth", headers=auth_header("sub-health"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "sub": "sub-health"}
