import { describe, it, expect, vi } from "vitest";
import { streamSSE } from "./sse";

describe("streamSSE parser", () => {
  it("parses single-line and multi-line SSE messages correctly", async () => {
    const mockEvents: { event: string; data: unknown }[] = [];
    const ssePayload = "event: status\ndata: {\"stage\": \"routing\"}\n\nevent: token\ndata: {\"text\": \"Hello\"}\n\n";

    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(ssePayload));
        controller.close();
      },
    });

    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(stream, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      })
    );

    await streamSSE({
      url: "/api/v1/mock-stream",
      onEvent: (e) => mockEvents.push(e),
    });

    expect(mockEvents).toHaveLength(2);
    expect(mockEvents[0]).toEqual({
      event: "status",
      data: { stage: "routing" },
    });
    expect(mockEvents[1]).toEqual({
      event: "token",
      data: { text: "Hello" },
    });
  });
});
