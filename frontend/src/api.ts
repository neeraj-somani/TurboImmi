import { getIdToken, type SpaConfig } from "./auth";

export type { SpaConfig };

export type Me = {
  sub: string;
  email?: string | null;
  groups: string[];
  roleChosen: boolean;
  role: "Applicant" | "Attorney" | "Admin" | null;
};

export type ProfileResponse = {
  roleChosen: boolean;
  role: "Applicant" | "Attorney" | "Admin" | null;
  profile: {
    legalName?: { given?: string; family?: string };
    email?: string;
    dateOfBirth?: string;
    countryOfCitizenship?: string;
    currentStatus?: string;
    journeyStage?: string;
    employerLegalName?: string;
    jobTitle?: string;
    wageAmount?: string;
    worksiteAddress?: string;
    passportNumber?: string;
    passportExpiry?: string;
    confirmedPrefillAt?: string;
  };
};

export type PacketFields = {
  petitionerLegalName?: string;
  petitionerUsAddress?: string;
  petitionerFein?: string;
  petitionerOrgType?: string;
  beneficiaryGiven?: string;
  beneficiaryFamily?: string;
  beneficiaryDateOfBirth?: string;
  beneficiaryCountryOfBirth?: string;
  beneficiaryCitizenship?: string;
  beneficiaryPassportNumber?: string;
  beneficiaryPassportExpiry?: string;
  beneficiaryAlienNumber?: string;
  intent?: string;
  entryPath?: string;
  capExemptClaim?: boolean;
  jobTitle?: string;
  socCode?: string;
  wageAmount?: string;
  wageUnit?: string;
  hoursPerWeek?: string;
  worksiteAddress?: string;
  lcaEtaNumber?: string;
  requestedStart?: string;
  requestedEnd?: string;
  offsiteItinerary?: boolean;
  evidencePassport?: boolean;
  evidenceOfferLetter?: boolean;
  evidenceLca?: boolean;
};

export type ScoreDeduction = {
  id: string;
  kind: string;
  severity: string;
  message: string;
};

export type CaseScore = {
  completeness: number;
  consistency: number;
  deductions: ScoreDeduction[];
  scoredAt?: string;
  explanation?: string;
};

export type CaseRecord = {
  caseId: string;
  visaClass: string;
  status: string;
  intent?: string;
  entryPath?: string;
  capExemptClaim?: boolean;
  requestedStart?: string;
  requestedEnd?: string;
  formFields?: Record<string, string | boolean>;
  packet?: PacketFields;
  score?: CaseScore;
  attestationAcceptedAt?: string;
  createdAt?: string;
  updatedAt?: string;
};

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

function detailOf(body: unknown): { code?: string; message?: string } {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail?: unknown }).detail;
    if (detail && typeof detail === "object") {
      return detail as { code?: string; message?: string };
    }
  }
  if (body && typeof body === "object") {
    return body as { code?: string; message?: string };
  }
  return {};
}

export async function apiJson<T>(config: SpaConfig, path: string, init?: RequestInit): Promise<T> {
  const token = getIdToken();
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type") && init?.body) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(`${config.apiBaseUrl}${path}`, { ...init, headers });
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = detailOf(body);
    throw new ApiError(
      response.status,
      detail.code ?? "ERROR",
      detail.message ?? `Request failed (${response.status})`,
    );
  }
  return body as T;
}

export type AttorneyRecord = {
  attorneyId: string;
  displayName: string;
  firmName: string;
  usState: string;
  specialties: string[];
  bio: string;
  published: boolean;
  verified: boolean;
  flag?: string;
  flagNote?: string;
  checks?: { ok: boolean; missing: string[] };
  createdAt?: string;
  updatedAt?: string;
};

export type AdminProfile = {
  displayName: string;
  updatedAt?: string;
};

export type AlertRecord = {
  alertId: string;
  title: string;
  sourceUrl: string;
  publishedOn: string;
  tag: string;
  summary: string;
};

export type PolicyCitation = {
  title: string;
  source_url: string;
  retrieved_at: string;
};

export type ChatResponse = {
  answer: string;
  refused: boolean;
  citations: PolicyCitation[];
  remaining: number;
};

export type ConsultRecord = {
  consultId: string;
  attorneyId: string;
  applicantSub?: string;
  caseId?: string | null;
  message: string;
  status: string;
  createdAt?: string;
  attorneyDisplayName?: string;
  applicantDisplayName?: string;
};

export function homePath(me: Me): string {
  if (!me.roleChosen || !me.role) {
    return "/choose-role";
  }
  if (me.role === "Admin") {
    return "/admin";
  }
  return me.role === "Attorney" ? "/attorney" : "/app";
}
