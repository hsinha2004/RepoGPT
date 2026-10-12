import createFetchClient, { type Middleware } from "openapi-fetch";
import type { paths } from "./schema";

let inMemoryAccessToken: string | null = null;
let refreshPromise: Promise<string | null> | null = null;

export function getAccessToken(): string | null {
  if (!inMemoryAccessToken) {
    try {
      const stored = localStorage.getItem("rg_access_token");
      if (stored && stored !== "null" && stored !== "undefined") {
        inMemoryAccessToken = stored;
      }
    } catch {
      // Ignore localStorage access restrictions
    }
  }
  return inMemoryAccessToken;
}

export function setAccessToken(token: string | null): void {
  if (token && token !== "null" && token !== "undefined") {
    inMemoryAccessToken = token;
    try {
      localStorage.setItem("rg_access_token", token);
    } catch {}
  } else {
    inMemoryAccessToken = null;
    try {
      localStorage.removeItem("rg_access_token");
    } catch {}
  }
}

export function getCsrfTokenFromCookie(): string | null {
  const match = document.cookie.match(/(^|;\s*)rg_csrf=([^;]+)/);
  return match ? decodeURIComponent(match[2]) : null;
}

/**
 * Single-flight refresh token handler to prevent concurrent refresh races.
 */
export async function performRefreshToken(): Promise<string | null> {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    try {
      const csrfToken = getCsrfTokenFromCookie() || "";
      const res = await fetch("/api/v1/auth/refresh", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrfToken,
        },
      });

      if (!res.ok) {
        setAccessToken(null);
        return null;
      }

      const data = await res.json();
      const newToken = data.access_token as string;
      setAccessToken(newToken);
      return newToken;
    } catch {
      setAccessToken(null);
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

/**
 * Robust fetch wrapper that attaches the Bearer token,
 * automatically attempts token refresh if token is absent,
 * and retries on 401 Unauthorized.
 */
export async function authFetch(
  input: RequestInfo | URL,
  init: RequestInit = {}
): Promise<Response> {
  let token = getAccessToken();
  if (!token) {
    token = await performRefreshToken();
  }

  const headers = new Headers(init.headers || {});
  if (token && token !== "null" && token !== "undefined") {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(input, {
    ...init,
    headers,
    credentials: "include",
  });

  const urlStr = typeof input === "string" ? input : input.toString();
  if (
    res.status === 401 &&
    !urlStr.includes("/auth/refresh") &&
    !urlStr.includes("/auth/login")
  ) {
    const newToken = await performRefreshToken();
    if (newToken) {
      headers.set("Authorization", `Bearer ${newToken}`);
      return fetch(input, {
        ...init,
        headers,
        credentials: "include",
      });
    }
  }

  return res;
}

const authMiddleware: Middleware = {
  async onRequest({ request }) {
    let token = getAccessToken();
    if (!token && !request.url.includes("/auth/")) {
      token = await performRefreshToken();
    }
    if (token && token !== "null" && token !== "undefined") {
      request.headers.set("Authorization", `Bearer ${token}`);
    }
    return request;
  },
  async onResponse({ request, response }) {
    if (response.status === 401 && !request.url.includes("/auth/refresh")) {
      const newToken = await performRefreshToken();
      if (newToken) {
        request.headers.set("Authorization", `Bearer ${newToken}`);
        return fetch(request);
      }
    }
    return response;
  },
};

export const apiClient = createFetchClient<paths>({
  baseUrl: "",
  credentials: "include",
});

apiClient.use(authMiddleware);
