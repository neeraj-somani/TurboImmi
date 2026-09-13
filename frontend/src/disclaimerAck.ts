const STORAGE_KEY = "turboimmi_disclaimer_ack";

type Ack = {
  accepted: boolean;
  version: number;
};

export function isDisclaimerAccepted(version: number): boolean {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return false;
    }
    const parsed = JSON.parse(raw) as Ack;
    return parsed.accepted === true && parsed.version === version;
  } catch {
    return false;
  }
}

export function acceptDisclaimer(version: number): void {
  const ack: Ack = { accepted: true, version };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(ack));
}

export function isLegalPath(pathname: string): boolean {
  return pathname === "/terms" || pathname === "/privacy";
}
