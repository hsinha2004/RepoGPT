import { getAccessToken } from "./client";

export interface SSEEvent<T = unknown> {
  event: string;
  data: T;
}

export interface StreamSSEOptions {
  url: string;
  method?: "GET" | "POST";
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  onEvent: (event: SSEEvent) => void;
  onError?: (error: Error) => void;
  onDone?: () => void;
}

/**
 * Universal Server-Sent Events parser supporting POST requests, Authorization headers, and streaming.
 */
export async function streamSSE({
  url,
  method = "GET",
  body,
  headers = {},
  signal,
  onEvent,
  onError,
  onDone,
}: StreamSSEOptions): Promise<void> {
  const reqHeaders: Record<string, string> = {
    Accept: "text/event-stream",
    ...headers,
  };

  const token = getAccessToken();
  if (token) {
    reqHeaders["Authorization"] = `Bearer ${token}`;
  }

  let reqBody: string | undefined = undefined;
  if (body !== undefined) {
    reqHeaders["Content-Type"] = "application/json";
    reqBody = typeof body === "string" ? body : JSON.stringify(body);
  }

  try {
    const res = await fetch(url, {
      method,
      headers: reqHeaders,
      body: reqBody,
      signal,
    });

    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`SSE Request Failed [${res.status}]: ${errText}`);
    }

    if (!res.body) {
      throw new Error("No response body available for SSE stream");
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      let currentEvent = "message";
      let currentData = "";

      for (const line of lines) {
        const trimmed = line.replace(/\r$/, "");
        if (trimmed.startsWith(":")) {
          // Keepalive ping or comment
          continue;
        }

        if (trimmed === "") {
          if (currentData) {
            try {
              const parsed = JSON.parse(currentData);
              onEvent({ event: currentEvent, data: parsed });
            } catch {
              onEvent({ event: currentEvent, data: currentData });
            }
            currentEvent = "message";
            currentData = "";
          }
          continue;
        }

        if (trimmed.startsWith("event:")) {
          currentEvent = trimmed.slice(6).trim();
        } else if (trimmed.startsWith("data:")) {
          const content = trimmed.slice(5).trim();
          currentData = currentData ? currentData + "\n" + content : content;
        }
      }

      if (currentData) {
        try {
          const parsed = JSON.parse(currentData);
          onEvent({ event: currentEvent, data: parsed });
        } catch {
          onEvent({ event: currentEvent, data: currentData });
        }
      }
    }

    onDone?.();
  } catch (err: unknown) {
    if (signal?.aborted) {
      return;
    }
    const errorObj = err instanceof Error ? err : new Error(String(err));
    onError?.(errorObj);
  }
}
