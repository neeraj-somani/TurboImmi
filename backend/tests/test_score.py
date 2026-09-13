from fastapi.testclient import TestClient

from app.disclaimer import load_disclaimer
from app.main import app
from app.policy_corpus import hash_text, load_policy_excerpts
from app.score import evaluate
from app.score_explain import explain_hits
from app.store import reset_store
from tests.jwt_util import auth_header

client = TestClient(app)

COMPLETE_PROFILE = {
    "legalName": {"given": "Ada", "family": "Lovelace"},
    "dateOfBirth": "1990-01-15",
    "passportNumber": "P123456",
    "passportExpiry": "2030-01-01",
    "employerLegalName": "Example Robotics Inc",
    "jobTitle": "Software engineer",
    "wageAmount": "120000",
    "wageUnit": "year",
    "worksiteAddress": "1 Main St, Austin, TX",
}


def setup_function() -> None:
    reset_store()


def _applicant(sub: str) -> dict[str, str]:
    headers = auth_header(sub, **{"cognito:username": sub})
    chosen = client.post("/me/role", headers=headers, json={"role": "Applicant"})
    assert chosen.status_code == 200
    return headers


def test_empty_profile_is_incomplete_not_inconsistent() -> None:
    result = evaluate({}, {"status": "draft"})
    ids = {item["id"] for item in result["deductions"]}
    assert ids == {"C-01", "C-02", "C-03", "C-04", "C-05", "C-06", "C-07", "C-08", "C-09"}
    assert result["completeness"] == 0
    assert result["consistency"] == 100


def test_complete_packet_scores_100() -> None:
    result = evaluate(
        COMPLETE_PROFILE,
        {"intent": "cap", "entryPath": "change_of_status", "status": "in_progress"},
    )
    assert result["completeness"] == 100
    assert result["consistency"] == 100
    assert result["deductions"] == []


def test_consistency_blockers_and_dependent_warning() -> None:
    result = evaluate(
        {
            **COMPLETE_PROFILE,
            "passportExpiry": "2026-01-01",
            "wageUnit": "",
            "dependents": [{"name": "Child"}],
        },
        {
            "intent": "cap",
            "entryPath": "change_of_status",
            "requestedStart": "2026-10-01",
            "requestedEnd": "2026-01-01",
            "formFields": {"petitionerLegalName": "Other Corp"},
        },
    )
    ids = {item["id"] for item in result["deductions"]}
    assert ids == {"X-01", "X-02", "X-03", "X-04", "X-05"}
    assert result["consistency"] == 0
    assert result["completeness"] == 100
    warning = next(item for item in result["deductions"] if item["id"] == "X-05")
    assert warning["severity"] == "warning"


def test_c10_ready_to_file_without_attestation() -> None:
    result = evaluate(COMPLETE_PROFILE, {"status": "ready_to_file", "intent": "cap", "entryPath": "consular"})
    assert any(item["id"] == "C-10" for item in result["deductions"])


def test_explain_without_model_is_silent() -> None:
    text, meta = explain_hits([{"id": "C-01", "message": "Missing legal name"}])
    assert text is None
    assert meta["modelId"] == ""


def test_score_api_persists_and_explain_skips_without_model() -> None:
    headers = _applicant("score-user")
    client.put("/me/profile", headers=headers, json=COMPLETE_PROFILE)
    case_id = client.get("/cases", headers=headers).json()["cases"][0]["caseId"]
    client.patch(
        f"/cases/{case_id}",
        headers=headers,
        json={"intent": "cap", "entryPath": "change_of_status"},
    )
    scored = client.post(f"/cases/{case_id}/score", headers=headers, json={"explain": True})
    assert scored.status_code == 200
    body = scored.json()
    assert body["score"]["completeness"] == 100
    assert body["score"]["consistency"] == 100
    assert "explanation" not in body["score"]
    listed = client.get("/cases", headers=headers).json()["cases"][0]
    assert listed["score"]["completeness"] == 100


def test_score_api_reports_missing_intent() -> None:
    headers = _applicant("gap-user")
    case_id = client.get("/cases", headers=headers).json()["cases"][0]["caseId"]
    scored = client.post(f"/cases/{case_id}/score", headers=headers, json={})
    ids = {item["id"] for item in scored.json()["score"]["deductions"]}
    assert "C-08" in ids
    assert "C-09" in ids


def test_attestation_sets_ready_to_file() -> None:
    headers = _applicant("attest-user")
    case_id = client.get("/cases", headers=headers).json()["cases"][0]["caseId"]
    text = load_disclaimer()["attestation"]
    bad = client.post(
        f"/cases/{case_id}/attestation",
        headers=headers,
        json={"accepted": True, "text": "wrong"},
    )
    assert bad.status_code == 400
    ok = client.post(
        f"/cases/{case_id}/attestation",
        headers=headers,
        json={"accepted": True, "text": text},
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "ready_to_file"
    assert ok.json()["attestationAcceptedAt"]


def test_patch_cannot_set_ready_to_file() -> None:
    headers = _applicant("status-user")
    case_id = client.get("/cases", headers=headers).json()["cases"][0]["caseId"]
    response = client.patch(f"/cases/{case_id}", headers=headers, json={"status": "ready_to_file"})
    assert response.status_code == 422


def test_attorney_cannot_score() -> None:
    headers = auth_header("att-score", **{"cognito:username": "att-score"})
    client.post("/me/role", headers=headers, json={"role": "Attorney"})
    response = client.post("/cases/nope/score", headers=headers, json={})
    assert response.status_code == 403


def test_policy_excerpts_have_provenance() -> None:
    chunks = load_policy_excerpts()
    assert len(chunks) >= 3
    for chunk in chunks:
        assert "uscis.gov" in chunk["source_url"]
        assert chunk["content_hash"] == hash_text(chunk["text"])
        assert chunk["retrieved_at"]
        assert chunk["title"]
