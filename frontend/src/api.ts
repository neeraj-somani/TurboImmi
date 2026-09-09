import { getIdToken, type SpaConfig } from "./auth";

export type Me = {
  sub: string;
  email?: string | null;
  groups: string[];
  roleChosen: boolean;
  role: "Applicant" | "Attorney" | null;
};

export type ProfileResponse = {
  roleChosen: boolean;
  role: "Applicant" | "Attorney" | null;
  profile: {
    legalName?: { given?: string; family?: string };
    email?: string;
    dateOfBirth?: string;
    countryOfCitizenship?: string;
    currentStatus?: string;
    journeyStage?: string;
    employerLegalName?: string;
    jobTitle?: string;
  };
};

export type CaseRecord = {
  caseId: string;
  visaClass: string;
  status: string;
  intent?: string;
  entryPath?: string;
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

export function homePath(me: Me): string {
  if (!me.roleChosen || !me.role) {
    return "/choose-role";
  }
  return me.role === "Attorney" ? "/attorney" : "/app";
}
