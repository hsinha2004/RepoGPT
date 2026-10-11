import createFetchClient, { type Middleware } from "openapi-fetch";
import type { paths } from "./schema";

let inMemoryAccessToken: string | null = null;
let refreshPromise: Promise<string | null> | null = null;

export function getAccessToken(): string | null {
  return inMemoryAccessToken;
}

export function setAccessToken(token: string | null): void {
  inMemoryAccessToken = token;
}

export function getCsrfTokenFromCookie(): string | null {
  const match = document.cookie.match(/(^|;\s*)rg_csrf=([^;]+)/);
  return match ? decodeURIComponent(match[2]) : null;
}

/**
 * Single-flight refresh token handler to prevent concurrent refresh races.
 */
async function performRefreshToken(): Promise<string | null> {
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

const authMiddleware: Middleware = {
  async onRequest({ request }) {
    if (inMemoryAccessToken) {
      request.headers.set("Authorization", `Bearer ${inMemoryAccessToken}`);
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
  baseUrl: "/api/v1",
});

apiClient.use(authMiddleware);
