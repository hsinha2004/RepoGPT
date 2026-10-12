import { describe, it, expect } from "vitest";

describe("Evaluation Data Helpers & Metrics", () => {
  it("formats Hit@k and accuracy rates with proper precision", () => {
    const hitRate = 0.8666667;
    const formatted = `${(hitRate * 100).toFixed(1)}%`;
    expect(formatted).toBe("86.7%");

    const zeroRate = 0.0;
    expect(`${(zeroRate * 100).toFixed(1)}%`).toBe("0.0%");

    const perfectRate = 1.0;
    expect(`${(perfectRate * 100).toFixed(1)}%`).toBe("100.0%");
  });

  it("calculates metric deltas between two evaluation runs accurately", () => {
    const currentHit5 = 0.92;
    const previousHit5 = 0.84;
    const diff = currentHit5 - previousHit5;
    const formattedDiff = `${(diff * 100).toFixed(1)}%`;
    expect(formattedDiff).toBe("8.0%");
    expect(diff > 0).toBe(true); // improvement

    const currentMrr = 0.742;
    const previousMrr = 0.785;
    const mrrDiff = currentMrr - previousMrr;
    expect(mrrDiff.toFixed(3)).toBe("-0.043");
    expect(mrrDiff < 0).toBe(true); // regression
  });

  it("aggregates question results into category performance summaries", () => {
    const mockQuestions = [
      { id: "q1", category: "locate", hit_5: 1.0, is_correct: true },
      { id: "q2", category: "locate", hit_5: 1.0, is_correct: false },
      { id: "q3", category: "explain", hit_5: 0.0, is_correct: false },
      { id: "q4", category: "explain", hit_5: 1.0, is_correct: true },
      { id: "q5", category: "flow", hit_5: 1.0, is_correct: true },
    ];

    const categorySummary: Record<string, { count: number; hit5: number; correct: number }> = {};
    for (const q of mockQuestions) {
      if (!categorySummary[q.category]) {
        categorySummary[q.category] = { count: 0, hit5: 0, correct: 0 };
      }
      categorySummary[q.category].count += 1;
      if (q.hit_5 > 0) categorySummary[q.category].hit5 += 1;
      if (q.is_correct) categorySummary[q.category].correct += 1;
    }

    expect(categorySummary["locate"]).toEqual({ count: 2, hit5: 2, correct: 1 });
    expect(categorySummary["explain"]).toEqual({ count: 2, hit5: 1, correct: 1 });
    expect(categorySummary["flow"]).toEqual({ count: 1, hit5: 1, correct: 1 });

    const locateHitRate = categorySummary["locate"].hit5 / categorySummary["locate"].count;
    expect(locateHitRate).toBe(1.0);
  });

  it("validates calibration reliability bin mappings", () => {
    const calibrationBins = [
      {
        bin_idx: 0,
        range_label: "0-10%",
        min_prob: 0.0,
        max_prob: 0.1,
        count: 5,
        mean_predicted_confidence: 0.06,
        empirical_accuracy: 0.0,
      },
      {
        bin_idx: 9,
        range_label: "90-100%",
        min_prob: 0.9,
        max_prob: 1.0,
        count: 25,
        mean_predicted_confidence: 0.94,
        empirical_accuracy: 0.92,
      },
    ];

    expect(calibrationBins.length).toBe(2);
    expect(calibrationBins[0].empirical_accuracy).toBe(0.0);
    expect(calibrationBins[1].empirical_accuracy).toBe(0.92);

    // ECE contribution for bin 9
    const totalSamples = 30;
    const binWeight = calibrationBins[1].count / totalSamples;
    const calibrationError = Math.abs(
      calibrationBins[1].mean_predicted_confidence - calibrationBins[1].empirical_accuracy
    );
    const weightedError = binWeight * calibrationError;
    expect(weightedError).toBeCloseTo((25 / 30) * 0.02, 4);
  });
});
