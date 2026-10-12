import { describe, it, expect } from "vitest";

describe("Overview Page Data Helpers", () => {
  it("calculates language breakdown percentages correctly", () => {
    const languages: Record<string, number> = {
      python: 6000,
      typescript: 3000,
      go: 1000,
    };
    const total = Object.values(languages).reduce((a, b) => a + b, 0);
    expect(total).toBe(10000);

    const breakdown = Object.entries(languages)
      .sort(([, a], [, b]) => b - a)
      .map(([name, loc]) => ({
        name,
        loc,
        pct: ((loc / total) * 100).toFixed(1),
      }));

    expect(breakdown[0]).toEqual({ name: "python", loc: 6000, pct: "60.0" });
    expect(breakdown[1]).toEqual({ name: "typescript", loc: 3000, pct: "30.0" });
    expect(breakdown[2]).toEqual({ name: "go", loc: 1000, pct: "10.0" });
  });

  it("groups tech stack items into categorized collections", () => {
    const techStack = [
      { name: "FastAPI", category: "framework", evidence: "requirements.txt" },
      { name: "React", category: "framework", evidence: "package.json" },
      { name: "MongoDB", category: "database", evidence: "requirements.txt" },
      { name: "pytest", category: "testing", evidence: "setup.cfg" },
    ];

    const grouped: Record<string, string[]> = {};
    for (const item of techStack) {
      const cat = item.category.toLowerCase();
      if (!grouped[cat]) grouped[cat] = [];
      grouped[cat].push(item.name);
    }

    expect(grouped["framework"]).toEqual(["FastAPI", "React"]);
    expect(grouped["database"]).toEqual(["MongoDB"]);
    expect(grouped["testing"]).toEqual(["pytest"]);
  });

  it("extracts and maps citation sources in overview text", () => {
    const markdown = "The API is powered by FastAPI [S1] and persists data into MongoDB [S2].";
    const matches = Array.from(markdown.matchAll(/\[(S\d+)\]/g)).map((m) => m[1]);
    expect(matches).toEqual(["S1", "S2"]);
  });
});
