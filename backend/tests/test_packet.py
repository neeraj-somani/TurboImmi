from fastapi.testclient import TestClient

from app.main import app
from app.packet import build_packet, sanitize_form_fields
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


def test_build_packet_maps_profile_and_interview() -> None:
    packet = build_packet(
        {
            "legalName": {"given": "Ada", "family": "Lovelace"},
            "passportNumber": "FIXTURE123",
            "employerLegalName": "Example Robotics Inc",
            "jobTitle": "Software engineer",
            "wageAmount": "120000",
            "wageUnit": "year",
        },
        {"intent": "cap", "entryPath": "change_of_status", "lcaEtaNumber": "I-200-12345"},
    )
    assert packet["beneficiaryGiven"] == "Ada"
    assert packet["petitionerLegalName"] == "Example Robotics Inc"
    assert packet["intent"] == "cap"
    assert packet["evidencePassport"] is True
    assert packet["evidenceOfferLetter"] is True
    assert packet["evidenceLca"] is True


def test_sanitize_drops_unknown_and_essays() -> None:
    cleaned = sanitize_form_fields(
        {"jobTitle": "Engineer", "specialtyEssay": "long argument", "offsiteItinerary": True}
    )
    assert cleaned == {"jobTitle": "Engineer", "offsiteItinerary": True}


def test_get_case_includes_derived_packet_and_saved_overrides() -> None:
    headers = _applicant("packet-user")
    client.put(
        "/me/profile",
        headers=headers,
        json={"legalName": {"given": "Grace", "family": "Hopper"}, "jobTitle": "Engineer"},
    )
    case_id = client.get("/cases", headers=headers).json()["cases"][0]["caseId"]
    listed = client.get("/cases", headers=headers).json()["cases"][0]
    assert listed["packet"]["beneficiaryGiven"] == "Grace"
    assert listed["packet"]["jobTitle"] == "Engineer"
    saved = client.patch(
        f"/cases/{case_id}",
        headers=headers,
        json={"formFields": {"hoursPerWeek": "40", "petitionerOrgType": "corporation", "junk": "nope"}},
    )
    assert saved.status_code == 200
    assert saved.json()["packet"]["hoursPerWeek"] == "40"
    assert saved.json()["packet"]["petitionerOrgType"] == "corporation"
    assert "junk" not in saved.json()["packet"]
    fetched = client.get(f"/cases/{case_id}", headers=headers)
    assert fetched.json()["packet"]["hoursPerWeek"] == "40"
    assert fetched.json()["formFields"]["hoursPerWeek"] == "40"
