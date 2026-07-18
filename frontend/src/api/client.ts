import type { TokenPair } from "./types";

export const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api/v1";
export const WS_URL = API_URL.replace(/^http/, "ws");

const ACCESS_KEY = "th_access";
const REFRESH_KEY = "th_refresh";

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
  }
}

export const tokenStore = {
  get access(): string | null {
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh(): string | null {
    return localStorage.getItem(REFRESH_KEY);
  },
  set(tokens: TokenPair) {
    localStorage.setItem(ACCESS_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

/** Called when a refresh attempt fails — the AuthContext registers a
 * handler so the app can drop to the login screen. */
let onSessionExpired: (() => void) | null = null;
export function setSessionExpiredHandler(handler: () => void) {
  onSessionExpired = handler;
}

async function tryRefresh(): Promise<boolean> {
  const refresh = tokenStore.refresh;
  if (!refresh) return false;
  const resp = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!resp.ok) return false;
  tokenStore.set((await resp.json()) as TokenPair);
  return true;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  form?: Record<string, string>;
  query?: Record<string, string | number | boolean | undefined>;
}

/** Fetch wrapper: attaches the access token, retries exactly once after a
 * transparent refresh on 401, and normalizes errors into ApiError. */
export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const doFetch = async (): Promise<Response> => {
    const headers: Record<string, string> = {};
    const access = tokenStore.access;
    if (access) headers.Authorization = `Bearer ${access}`;

    let body: BodyInit | undefined;
    if (options.form) {
      body = new URLSearchParams(options.form);
    } else if (options.body !== undefined) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(options.body);
    }

    let url = `${API_URL}${path}`;
    if (options.query) {
      const params = new URLSearchParams();
      for (const [key, value] of Object.entries(options.query)) {
        if (value !== undefined) params.set(key, String(value));
      }
      const qs = params.toString();
      if (qs) url += `?${qs}`;
    }

    return fetch(url, { method: options.method ?? "GET", headers, body });
  };

  let resp = await doFetch();

  if (resp.status === 401 && tokenStore.refresh) {
    if (await tryRefresh()) {
      resp = await doFetch();
    } else {
      tokenStore.clear();
      onSessionExpired?.();
    }
  }

  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const data = await resp.json();
      if (typeof data.detail === "string") detail = data.detail;
      else if (Array.isArray(data.detail)) {
        detail = data.detail
          .map((d: { loc?: unknown[]; msg?: string }) => {
            const field = d.loc?.slice(1).join(".") ?? "";
            return field ? `${field}: ${d.msg}` : (d.msg ?? "");
          })
          .join("; ");
      }
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(resp.status, detail);
  }

  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}
