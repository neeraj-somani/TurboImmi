from fastapi.testclient import TestClient

from app.alerts import SEED_ALERTS
from app.main import app
from tests.jwt_util import auth_header

client = TestClient(app)


def test_alerts_require_jwt() -> None:
    assert client.get("/alerts").status_code == 401


def test_alerts_are_seeded_uscis_cards() -> None:
    headers = auth_header("alert-user", **{"cognito:username": "alert-user"})
    response = client.get("/alerts", headers=headers)
    assert response.status_code == 200
    rows = response.json()["alerts"]
    assert {item["alertId"] for item in rows} == {item["alertId"] for item in SEED_ALERTS}
    assert all("uscis.gov" in item["sourceUrl"] for item in rows)
    assert all(item["title"] and item["summary"] and item["publishedOn"] for item in rows)
    assert all(item["tag"] in {"policy_alert", "news_release", "fee_change"} for item in rows)
    assert all("x.com" not in item["sourceUrl"] for item in rows)
