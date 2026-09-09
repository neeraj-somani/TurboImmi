export type SpaConfig = {
  apiBaseUrl: string;
  userPoolId: string;
  userPoolClientId: string;
  cognitoDomain: string;
  region: string;
  redirectUri: string;
};

const PKCE_KEY = "turboimmi_pkce_verifier";
const ID_TOKEN_KEY = "turboimmi_id_token";
const ACCESS_TOKEN_KEY = "turboimmi_access_token";
const REFRESH_TOKEN_KEY = "turboimmi_refresh_token";

function randomString(bytes: number): string {
  const array = new Uint8Array(bytes);
  crypto.getRandomValues(array);
  return Array.from(array, (b) => b.toString(16).padStart(2, "0")).join("");
}

function base64Url(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  bytes.forEach((b) => {
    binary += String.fromCharCode(b);
  });
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function sha256(value: string): Promise<string> {
  const data = new TextEncoder().encode(value);
  const hash = await crypto.subtle.digest("SHA-256", data);
  return base64Url(hash);
}

export function getIdToken(): string | null {
  return sessionStorage.getItem(ID_TOKEN_KEY);
}

export function signOutLocal(): void {
  sessionStorage.removeItem(ID_TOKEN_KEY);
  sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  sessionStorage.removeItem(REFRESH_TOKEN_KEY);
  sessionStorage.removeItem(PKCE_KEY);
}

export async function startHostedUiLogin(config: SpaConfig): Promise<void> {
  const verifier = randomString(32);
  sessionStorage.setItem(PKCE_KEY, verifier);
  const challenge = await sha256(verifier);
  const params = new URLSearchParams({
    client_id: config.userPoolClientId,
    response_type: "code",
    scope: "openid email profile",
    redirect_uri: config.redirectUri,
    code_challenge: challenge,
    code_challenge_method: "S256",
  });
  const domain = config.cognitoDomain.replace(/\/$/, "");
  window.location.assign(`${domain}/oauth2/authorize?${params.toString()}`);
}

export async function completeHostedUiLogin(config: SpaConfig): Promise<boolean> {
  const params = new URLSearchParams(window.location.search);
  const code = params.get("code");
  if (!code) {
    return false;
  }
  const verifier = sessionStorage.getItem(PKCE_KEY);
  if (!verifier) {
    return false;
  }
  const domain = config.cognitoDomain.replace(/\/$/, "");
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    client_id: config.userPoolClientId,
    code,
    redirect_uri: config.redirectUri,
    code_verifier: verifier,
  });
  const response = await fetch(`${domain}/oauth2/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!response.ok) {
    return false;
  }
  const tokens = (await response.json()) as {
    id_token?: string;
    access_token?: string;
    refresh_token?: string;
  };
  if (tokens.id_token) {
    sessionStorage.setItem(ID_TOKEN_KEY, tokens.id_token);
  }
  if (tokens.access_token) {
    sessionStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  }
  if (tokens.refresh_token) {
    sessionStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
  }
  sessionStorage.removeItem(PKCE_KEY);
  window.history.replaceState({}, document.title, window.location.pathname);
  return true;
}

export async function refreshSession(config: SpaConfig): Promise<boolean> {
  const refreshToken = sessionStorage.getItem(REFRESH_TOKEN_KEY);
  if (!refreshToken) {
    return false;
  }
  const domain = config.cognitoDomain.replace(/\/$/, "");
  const body = new URLSearchParams({
    grant_type: "refresh_token",
    client_id: config.userPoolClientId,
    refresh_token: refreshToken,
  });
  const response = await fetch(`${domain}/oauth2/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!response.ok) {
    return false;
  }
  const tokens = (await response.json()) as { id_token?: string; access_token?: string };
  if (tokens.id_token) {
    sessionStorage.setItem(ID_TOKEN_KEY, tokens.id_token);
  }
  if (tokens.access_token) {
    sessionStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  }
  return Boolean(tokens.id_token);
}

export function startHostedUiLogout(config: SpaConfig): void {
  const domain = config.cognitoDomain.replace(/\/$/, "");
  signOutLocal();
  const params = new URLSearchParams({
    client_id: config.userPoolClientId,
    logout_uri: config.redirectUri,
  });
  window.location.assign(`${domain}/logout?${params.toString()}`);
}

export async function loadSpaConfig(): Promise<SpaConfig> {
  if (import.meta.env.DEV) {
    return {
      apiBaseUrl: "",
      userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID ?? "",
      userPoolClientId: import.meta.env.VITE_COGNITO_CLIENT_ID ?? "",
      cognitoDomain: import.meta.env.VITE_COGNITO_DOMAIN ?? "",
      region: import.meta.env.VITE_COGNITO_REGION ?? "us-east-2",
      redirectUri: import.meta.env.VITE_SPA_REDIRECT_URI ?? "http://localhost:5173",
    };
  }
  const response = await fetch("/config.json");
  if (!response.ok) {
    throw new Error("config.json missing");
  }
  return response.json() as Promise<SpaConfig>;
}
