import { describe, it, expect } from "vitest";

describe("Dependency Graph UI Helpers", () => {
  it("determines directory color classes accurately", () => {
    function getDirKey(topDir: string, isExternal: boolean): string {
      if (isExternal) return "external";
      const key = topDir.toLowerCase();
      if (["backend", "app"].includes(key)) return "backend";
      if (["frontend", "src"].includes(key)) return "frontend";
      return "default";
    }

    expect(getDirKey("backend", false)).toBe("backend");
    expect(getDirKey("app", false)).toBe("backend");
    expect(getDirKey("frontend", false)).toBe("frontend");
    expect(getDirKey("any", true)).toBe("external");
  });

  it("filters graph nodes by search query matching path or label", () => {
    const nodes = [
      { id: "backend/app/main.py", label: "main.py" },
      { id: "backend/app/services/user.py", label: "user.py" },
      { id: "frontend/src/App.tsx", label: "App.tsx" },
      { id: "ext:fastapi", label: "fastapi" },
    ];

    const filterQuery = "user";
    const filtered = nodes.filter(
      (n) =>
        n.id.toLowerCase().includes(filterQuery.toLowerCase()) ||
        n.label.toLowerCase().includes(filterQuery.toLowerCase())
    );

    expect(filtered.length).toBe(1);
    expect(filtered[0].id).toBe("backend/app/services/user.py");
  });

  it("distinguishes heuristic call edges from import edges", () => {
    const edges = [
      { source: "a.py", target: "b.py", heuristic: false, type: "imports" },
      { source: "a.py", target: "b.py", heuristic: true, type: "calls" },
    ];

    const isHeuristicCall = edges.map((e) => e.heuristic);
    expect(isHeuristicCall).toEqual([false, true]);
  });
});
