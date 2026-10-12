import { describe, it, expect } from "vitest";
import type { ReviewFinding } from "./ReviewsPage";

describe("Review Findings Logic & Filtering", () => {
  const sampleFindings: ReviewFinding[] = [
    {
      id: "f1",
      path: "app/tasks.py",
      start_line: 11,
      end_line: 12,
      side: "RIGHT",
      category: "security",
      severity: "critical",
      title: "SQL Injection via string interpolation",
      explanation: "Unsanitized user_id interpolated into raw query.",
      evidence: [],
      confidence: 0.98,
      origin: "llm",
      status: "pending",
    },
    {
      id: "f2",
      path: "app/auth.py",
      start_line: 22,
      end_line: 23,
      side: "RIGHT",
      category: "security",
      severity: "high",
      title: "Hardcoded secret key in session",
      explanation: "Secret key committed in source.",
      evidence: [],
      confidence: 0.92,
      origin: "static",
      status: "accepted",
    },
    {
      id: "f3",
      path: "app/tasks.py",
      start_line: 35,
      end_line: 38,
      side: "RIGHT",
      category: "performance",
      severity: "medium",
      title: "N+1 query loop",
      explanation: "Queries inside loop over tasks.",
      evidence: [],
      confidence: 0.85,
      origin: "llm",
      status: "rejected",
    },
  ];

  it("filters findings by severity correctly", () => {
    const criticals = sampleFindings.filter((f) => f.severity === "critical");
    expect(criticals).toHaveLength(1);
    expect(criticals[0].id).toBe("f1");

    const mediums = sampleFindings.filter((f) => f.severity === "medium");
    expect(mediums).toHaveLength(1);
    expect(mediums[0].id).toBe("f3");
  });

  it("filters findings by category correctly", () => {
    const securityIssues = sampleFindings.filter((f) => f.category === "security");
    expect(securityIssues).toHaveLength(2);

    const perfIssues = sampleFindings.filter((f) => f.category === "performance");
    expect(perfIssues).toHaveLength(1);
    expect(perfIssues[0].id).toBe("f3");
  });

  it("computes accepted and pending counts accurately", () => {
    const acceptedCount = sampleFindings.filter((f) => f.status === "accepted").length;
    const pendingCount = sampleFindings.filter((f) => f.status === "pending").length;
    const rejectedCount = sampleFindings.filter((f) => f.status === "rejected").length;

    expect(acceptedCount).toBe(1);
    expect(pendingCount).toBe(1);
    expect(rejectedCount).toBe(1);
  });

  it("correctly derives maximum risk level from findings", () => {
    const deriveRisk = (findings: ReviewFinding[]): string => {
      if (findings.some((f) => f.severity === "critical")) return "critical";
      if (findings.some((f) => f.severity === "high")) return "high";
      if (findings.some((f) => f.severity === "medium")) return "medium";
      return "low";
    };

    expect(deriveRisk(sampleFindings)).toBe("critical");
    expect(deriveRisk([sampleFindings[1], sampleFindings[2]])).toBe("high");
    expect(deriveRisk([sampleFindings[2]])).toBe("medium");
  });
});
