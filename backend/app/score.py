"""Completeness / consistency rules. Not approval odds."""

from __future__ import annotations

from typing import Any

from app.packet import merge_packet

COMPLETENESS_IDS = ("C-01", "C-02", "C-03", "C-04", "C-05", "C-06", "C-07", "C-08", "C-09")
CONSISTENCY_BLOCKERS = ("X-01", "X-02", "X-03", "X-04")


def _filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return True
    return bool(str(value).strip())


def _lower(value: Any) -> str:
    return str(value or "").strip().lower()


def evaluate(profile: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    packet = merge_packet(profile, case)
    given = packet.get("beneficiaryGiven") or ""
    family = packet.get("beneficiaryFamily") or ""
    deductions: list[dict[str, str]] = []

    def add(rule_id: str, kind: str, severity: str, message: str) -> None:
        deductions.append({"id": rule_id, "kind": kind, "severity": severity, "message": message})

    if not (_filled(given) and _filled(family)):
        add("C-01", "completeness", "blocker", "Missing legal name")
    if not _filled(packet.get("beneficiaryDateOfBirth")):
        add("C-02", "completeness", "blocker", "Missing date of birth")
    if not _filled(packet.get("beneficiaryPassportNumber")):
        add("C-03", "completeness", "blocker", "Missing passport number")
    if not _filled(packet.get("petitionerLegalName")):
        add("C-04", "completeness", "blocker", "Missing employer legal name")
    if not _filled(packet.get("jobTitle")):
        add("C-05", "completeness", "blocker", "Missing job title")
    if not _filled(packet.get("wageAmount")):
        add("C-06", "completeness", "blocker", "Missing wage")
    if not _filled(packet.get("worksiteAddress")):
        add("C-07", "completeness", "blocker", "Missing worksite")
    if not _filled(packet.get("intent")):
        add("C-08", "completeness", "blocker", "Missing intent")
    if not _filled(packet.get("entryPath")):
        add("C-09", "completeness", "blocker", "Missing entry path")
    if case.get("status") == "ready_to_file" and not case.get("attestationAcceptedAt"):
        add("C-10", "completeness", "blocker", "ready_to_file requires attorney-review attestation")

    expiry = _lower(packet.get("beneficiaryPassportExpiry"))
    start = _lower(packet.get("requestedStart"))
    end = _lower(packet.get("requestedEnd"))
    if expiry and start and expiry < start:
        add("X-01", "consistency", "blocker", "Passport expiry is before the requested start")
    if start and end and end < start:
        add("X-02", "consistency", "blocker", "Requested end is before start")
    saved_employer = _lower((case.get("formFields") or {}).get("petitionerLegalName"))
    profile_employer = _lower(profile.get("employerLegalName"))
    if saved_employer and profile_employer and saved_employer != profile_employer:
        add("X-03", "consistency", "blocker", "Packet employer does not match profile employer")
    if _filled(packet.get("wageAmount")) and not _filled(packet.get("wageUnit")):
        add("X-04", "consistency", "blocker", "Wage is present without a wage unit")
    dependents = profile.get("dependents") or []
    stage = _lower(profile.get("journeyStage"))
    status = _lower(profile.get("currentStatus"))
    if dependents and stage not in {"h4", "h4_ead"} and "h-4" not in status and "h4" not in status:
        add("X-05", "consistency", "warning", "Dependents are listed without an H-4 note on the profile")

    complete_hits = sum(1 for item in deductions if item["id"] in COMPLETENESS_IDS)
    consistency_hits = sum(1 for item in deductions if item["id"] in CONSISTENCY_BLOCKERS)
    return {
        "completeness": round(100 * (1 - complete_hits / len(COMPLETENESS_IDS))),
        "consistency": round(100 * (1 - consistency_hits / len(CONSISTENCY_BLOCKERS))),
        "deductions": deductions,
    }
