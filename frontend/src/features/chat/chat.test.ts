import { describe, it, expect } from "vitest";

describe("Chat Citations and Confidence UI helpers", () => {
  it("extracts citation IDs from response text", () => {
    const text = "The access token is generated in `security.py` [S1] and verified in dependencies [S2].";
    const matches = Array.from(text.matchAll(/\[S(\d+)\]/g)).map((m) => `S${m[1]}`);
    expect(matches).toEqual(["S1", "S2"]);
  });

  it("assigns appropriate label and color thresholds for confidence score", () => {
    function getConfidenceBadge(score: number): { label: string; color: string } {
      if (score >= 0.75) return { label: "High", color: "text-[#22c55e]" };
      if (score >= 0.50) return { label: "Medium", color: "text-[#f59e0b]" };
      return { label: "Low", color: "text-[#ef4444]" };
    }

    expect(getConfidenceBadge(0.92)).toEqual({ label: "High", color: "text-[#22c55e]" });
    expect(getConfidenceBadge(0.65)).toEqual({ label: "Medium", color: "text-[#f59e0b]" });
    expect(getConfidenceBadge(0.35)).toEqual({ label: "Low", color: "text-[#ef4444]" });
  });

  it("truncates long initial prompt for conversation title", () => {
    const longPrompt = "Where in this entire repository is the logic for handling user password hashing and token generation implemented?";
    const title = longPrompt.slice(0, 60);
    expect(title.length).toBeLessThanOrEqual(60);
    expect(title).toBe("Where in this entire repository is the logic for handling us");
  });
});
