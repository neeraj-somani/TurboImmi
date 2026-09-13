"""Pydantic bodies for Day 3 profile / case / role routes."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RoleBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["Applicant", "Attorney"]


class LegalName(BaseModel):
    model_config = ConfigDict(extra="ignore")
    given: str | None = None
    family: str | None = None


class ProfileBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    legalName: LegalName | None = None
    dateOfBirth: str | None = None
    countryOfBirth: str | None = None
    countryOfCitizenship: str | None = None
    passportNumber: str | None = None
    passportExpiry: str | None = None
    alienNumber: str | None = None
    email: str | None = None
    currentStatus: str | None = None
    journeyStage: str | None = None
    employerLegalName: str | None = None
    employerFein: str | None = None
    jobTitle: str | None = None
    socCode: str | None = None
    wageAmount: str | float | int | None = None
    wageUnit: str | None = None
    worksiteAddress: str | None = None
    dependents: list[Any] | None = None


class CreateCaseBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    visaClass: Literal["H-1B"] = "H-1B"
    intent: Literal["cap", "transfer", "extension"] | None = None
    entryPath: Literal["change_of_status", "consular"] | None = None


class PatchCaseBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    intent: Literal["cap", "transfer", "extension"] | None = None
    entryPath: Literal["change_of_status", "consular"] | None = None
    capExemptClaim: bool | None = None
    requestedStart: str | None = None
    requestedEnd: str | None = None
    lcaEtaNumber: str | None = None
    status: Literal["draft", "in_progress"] | None = None
    formFields: dict[str, Any] | None = Field(default=None)


class ScoreBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    explain: bool = False


class AttestationBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    accepted: bool
    text: str


class UploadUrlBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    docType: Literal["passport", "offer_letter"]
    contentType: Literal["image/jpeg", "image/png", "application/pdf"]
    contentLength: int


class ExtractBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    jobId: str


class ConfirmPrefillBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    jobId: str
    fields: ProfileBody


class AttorneyBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    displayName: str
    firmName: str | None = None
    usState: str
    specialties: list[str] = Field(default_factory=list)
    bio: str | None = None


class ConsultBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    attorneyId: str
    caseId: str | None = None
    message: str


class AdminProfileBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    displayName: str


class AdminAttorneyPatch(BaseModel):
    model_config = ConfigDict(extra="ignore")
    published: bool | None = None
    verified: bool | None = None
    flag: str | None = None
    flagNote: str | None = None


class ChatBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str
