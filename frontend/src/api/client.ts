import type { TokenPair } from "./types";

const API_URL = (import.meta.env.VITE_API_URL || "/api/v1").replace(/\/$/, "");
const REFRESH_KEY = "biblioteca_refresh";

let accessToken: string | null = null;
let refreshInFlight: Promise<string | null> | null = null;

export class ApiError extends Error {
  readonly fieldErrors: Record<string, string>;

  constructor(
    readonly status: number,
    message: string,
    fieldErrors: Record<string, string> = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.fieldErrors = fieldErrors;
  }
}

export function clearSession(): void {
  accessToken = null;
  localStorage.removeItem(REFRESH_KEY);
  window.dispatchEvent(new Event("biblioteca:session-expired"));
}

export function setTokens(tokens: TokenPair): void {
  accessToken = tokens.access_token;
  localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
}

function readValidationErrors(detail: unknown): Record<string, string> {
  if (!Array.isArray(detail)) return {};
  const errors: Record<string, string> = {};
  for (const entry of detail) {
    if (typeof entry !== "object" || entry === null || !("loc" in entry) || !("msg" in entry)) {
      continue;
    }
    const loc = Array.isArray(entry.loc) ? entry.loc.filter((part: unknown) => part !== "body") : [];
    const field = loc.length ? String(loc[loc.length - 1]) : "general";
    errors[field] = String(entry.msg);
  }
  return errors;
}

async function errorFromResponse(response: Response): Promise<ApiError> {
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  const detail =
    typeof payload === "object" && payload !== null && "detail" in payload
      ? payload.detail
      : null;
  const fieldErrors = readValidationErrors(detail);
  const message =
    typeof detail === "string"
      ? detail
      : fieldErrors.general || (response.status === 429
          ? "Has realizado demasiadas solicitudes. Inténtalo de nuevo en un momento."
          : "No se pudo completar la solicitud.");
  return new ApiError(response.status, message, fieldErrors);
}

async function refreshAccessToken(): Promise<string | null> {
  if (refreshInFlight) return refreshInFlight;
  const refreshToken = localStorage.getItem(REFRESH_KEY);
  if (!refreshToken) return null;

  refreshInFlight = (async () => {
    try {
      const response = await fetch(`${API_URL}/auth/refresh`, {
        method: "POST",
        headers: { Authorization: `Bearer ${refreshToken}` },
      });
      if (!response.ok) {
        clearSession();
        return null;
      }
      const tokens = (await response.json()) as TokenPair;
      setTokens(tokens);
      return tokens.access_token;
    } catch {
      clearSession();
      return null;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

export async function restoreSession(): Promise<boolean> {
  const token = await refreshAccessToken();
  return token !== null;
}

export async function api<T>(
  path: string,
  options: RequestInit & { skipRefresh?: boolean } = {},
): Promise<T> {
  const { skipRefresh = false, ...init } = options;
  const headers = new Headers(init.headers);
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const send = () => fetch(`${API_URL}${path}`, { ...init, headers });
  let response = await send();
  if (response.status === 401 && !skipRefresh) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      headers.set("Authorization", `Bearer ${newToken}`);
      response = await send();
    } else {
      clearSession();
    }
  }
  if (!response.ok) throw await errorFromResponse(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function loginRequest(email: string, password: string): Promise<TokenPair> {
  const body = new URLSearchParams({ username: email, password });
  const tokens = await api<TokenPair>("/auth/login", {
    method: "POST",
    body,
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    skipRefresh: true,
  });
  setTokens(tokens);
  return tokens;
}

export async function logoutRequest(): Promise<void> {
  try {
    await api<void>("/auth/logout", { method: "POST" });
  } finally {
    clearSession();
  }
}

export function queryString(values: Record<string, string | number | boolean | undefined>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}
