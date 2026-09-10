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


def test_prefill_rejects_non_applicant() -> None:
    headers = auth_header("plain")
    response = client.post(
        "/prefill/upload-url",
        headers=headers,
        json={"docType": "passport", "contentType": "image/jpeg", "contentLength": 100},
    )
    assert response.status_code == 403


def test_prefill_rejects_attorney() -> None:
    headers = auth_header("atty", **{"cognito:username": "atty"})
    chosen = client.post("/me/role", headers=headers, json={"role": "Attorney"})
    assert chosen.status_code == 200
    response = client.post(
        "/prefill/upload-url",
        headers=headers,
        json={"docType": "passport", "contentType": "image/jpeg", "contentLength": 100},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "FORBIDDEN"


def test_prefill_rejects_too_large() -> None:
    headers = _applicant("size-user")
    response = client.post(
        "/prefill/upload-url",
        headers=headers,
        json={
            "docType": "passport",
            "contentType": "image/jpeg",
            "contentLength": 9 * 1024 * 1024,
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VALIDATION"


def test_extract_does_not_write_profile_until_confirm() -> None:
    headers = _applicant("confirm-user")
    uploaded = client.post(
        "/prefill/upload-url",
        headers=headers,
        json={"docType": "passport", "contentType": "image/jpeg", "contentLength": 1200},
    )
    assert uploaded.status_code == 200
    body = uploaded.json()
    assert body["skipUpload"] is True
    job_id = body["jobId"]
    too_soon = client.post(
        "/prefill/confirm",
        headers=headers,
        json={"jobId": job_id, "fields": {"passportNumber": "X"}},
    )
    assert too_soon.status_code == 400
    assert too_soon.json()["detail"]["code"] == "CONFIRM_REQUIRED"
    extracted = client.post("/prefill/extract", headers=headers, json={"jobId": job_id})
    assert extracted.status_code == 200
    assert extracted.json()["status"] == "extracted"
    assert extracted.json()["suggestions"]["legalName"]["given"] == "Ada"
    profile = client.get("/me/profile", headers=headers).json()["profile"]
    assert profile.get("legalName", {}).get("given") in ("", None)
    assert "confirmedPrefillAt" not in profile
    missing = client.post("/prefill/confirm", headers=headers, json={"jobId": "nope", "fields": {}})
    assert missing.status_code == 404
    saved = client.post(
        "/prefill/confirm",
        headers=headers,
        json={
            "jobId": job_id,
            "fields": {
                "legalName": {"given": "Ada", "family": "Lovelace"},
                "passportNumber": "FIXTURE123",
            },
        },
    )
    assert saved.status_code == 200
    out = saved.json()["profile"]
    assert out["legalName"]["family"] == "Lovelace"
    assert out["passportNumber"] == "FIXTURE123"
    assert out["confirmedPrefillAt"]
    stamped = out["confirmedPrefillAt"]
    spoofed = client.put(
        "/me/profile",
        headers=headers,
        json={"jobTitle": "Engineer", "confirmedPrefillAt": "2099-01-01T00:00:00Z"},
    )
    assert spoofed.status_code == 200
    assert spoofed.json()["profile"]["confirmedPrefillAt"] == stamped
    assert spoofed.json()["profile"]["jobTitle"] == "Engineer"


def test_max_two_active_uploads_and_delete() -> None:
    headers = _applicant("two-user")
    for _ in range(2):
        ok = client.post(
            "/prefill/upload-url",
            headers=headers,
            json={"docType": "passport", "contentType": "image/png", "contentLength": 50},
        )
        assert ok.status_code == 200
    third = client.post(
        "/prefill/upload-url",
        headers=headers,
        json={"docType": "offer_letter", "contentType": "application/pdf", "contentLength": 50},
    )
    assert third.status_code == 400
    deleted = client.delete("/prefill/uploads", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] == 2
    again = client.post(
        "/prefill/upload-url",
        headers=headers,
        json={"docType": "offer_letter", "contentType": "application/pdf", "contentLength": 50},
    )
    assert again.status_code == 200


def test_extract_daily_cap() -> None:
    headers = _applicant("cap-user")
    for _ in range(3):
        job = client.post(
            "/prefill/upload-url",
            headers=headers,
            json={"docType": "passport", "contentType": "image/jpeg", "contentLength": 10},
        ).json()["jobId"]
        extracted = client.post("/prefill/extract", headers=headers, json={"jobId": job})
        assert extracted.status_code == 200
        client.delete("/prefill/uploads", headers=headers)
    job = client.post(
        "/prefill/upload-url",
        headers=headers,
        json={"docType": "passport", "contentType": "image/jpeg", "contentLength": 10},
    ).json()["jobId"]
    blocked = client.post("/prefill/extract", headers=headers, json={"jobId": job})
    assert blocked.status_code == 429
    assert blocked.json()["detail"]["code"] == "RATE_LIMIT"


def test_manual_profile_still_works_without_prefill() -> None:
    headers = _applicant("manual-user")
    saved = client.put(
        "/me/profile",
        headers=headers,
        json={"legalName": {"given": "Grace", "family": "Hopper"}, "jobTitle": "Engineer"},
    )
    assert saved.status_code == 200
    assert saved.json()["profile"]["legalName"]["given"] == "Grace"
    assert "confirmedPrefillAt" not in saved.json()["profile"]


def test_offer_letter_fixture() -> None:
    headers = _applicant("offer-user")
    job = client.post(
        "/prefill/upload-url",
        headers=headers,
        json={"docType": "offer_letter", "contentType": "application/pdf", "contentLength": 80},
    ).json()["jobId"]
    extracted = client.post("/prefill/extract", headers=headers, json={"jobId": job})
    assert extracted.status_code == 200
    suggestions = extracted.json()["suggestions"]
    assert suggestions["employerLegalName"] == "Example Robotics Inc"
    assert suggestions["jobTitle"] == "Software engineer"
    profile = client.get("/me/profile", headers=headers).json()["profile"]
    assert profile.get("employerLegalName") in ("", None)
