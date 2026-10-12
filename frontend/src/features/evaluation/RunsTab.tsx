import React, { useState, useEffect } from "react";
import {
  Play,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ChevronRight,
  TrendingUp,
  Cpu,
  Sparkles,
  X,
} from "lucide-react";
import { Benchmark, EvalEstimateResponse, EvalRunSummary } from "./types";
import { getAccessToken } from "../../api/client";

interface RunsTabProps {
  runs: EvalRunSummary[];
  benchmarks: Benchmark[];
  isLoading: boolean;
  onRefresh: () => void;
  onSelectRun: (runId: string) => void;
  presetBenchmark?: Benchmark | null;
  onClearPresetBenchmark?: () => void;
}

const AVAILABLE_STRATEGIES = [
  { id: "keyword", label: "BM25 Keyword", desc: "Sparse inverted-index search" },
  { id: "vector", label: "Vector Dense", desc: "Embedding similarity search" },
  { id: "hybrid", label: "Hybrid RRF", desc: "Reciprocal Rank Fusion (BM25 + Vector)" },
  { id: "hybrid_rerank", label: "Hybrid + Reranker", desc: "Cross-encoder neural reranking" },
  { id: "auto", label: "Auto / Router", desc: "Dynamic heuristic / LLM query router" },
];

export const RunsTab: React.FC<RunsTabProps> = ({
  runs,
  benchmarks,
  isLoading,
  onRefresh,
  onSelectRun,
  presetBenchmark,
  onClearPresetBenchmark,
}) => {
  const [isNewRunOpen, setIsNewRunOpen] = useState(Boolean(presetBenchmark));
  const [selectedBenchmarkId, setSelectedBenchmarkId] = useState<string>(
    presetBenchmark?.id || benchmarks[0]?.id || ""
  );
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>([
    "keyword",
    "vector",
    "hybrid",
    "hybrid_rerank",
  ]);
  const [generateAnswers, setGenerateAnswers] = useState(true);
  const [isStarting, setIsStarting] = useState(false);
  const [estimate, setEstimate] = useState<EvalEstimateResponse | null>(null);
  const [isEstimating, setIsEstimating] = useState(false);

  useEffect(() => {
    if (presetBenchmark) {
      setSelectedBenchmarkId(presetBenchmark.id);
      setIsNewRunOpen(true);
    }
  }, [presetBenchmark]);

  useEffect(() => {
    if (!selectedBenchmarkId && benchmarks.length > 0) {
      setSelectedBenchmarkId(benchmarks[0].id);
    }
  }, [benchmarks, selectedBenchmarkId]);

  // Query pre-flight estimate
  useEffect(() => {
    if (!selectedBenchmarkId || selectedStrategies.length === 0) {
      setEstimate(null);
      return;
    }

    let active = true;
    const fetchEstimate = async () => {
      setIsEstimating(true);
      try {
        const token = getAccessToken();
        const res = await fetch("/api/v1/eval/estimate", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            benchmark_id: selectedBenchmarkId,
            strategies: selectedStrategies,
            generate_answers: generateAnswers,
            llm_judge: false,
          }),
        });

        if (res.ok && active) {
          const data = await res.json();
          setEstimate(data);
        }
      } catch {
        // Ignore background estimation error
      } finally {
        if (active) setIsEstimating(false);
      }
    };

    fetchEstimate();
    return () => {
      active = false;
    };
  }, [selectedBenchmarkId, selectedStrategies, generateAnswers]);

  const handleToggleStrategy = (stratId: string) => {
    setSelectedStrategies((prev) =>
      prev.includes(stratId) ? prev.filter((s) => s !== stratId) : [...prev, stratId]
    );
  };

  const handleStartRun = async () => {
    if (!selectedBenchmarkId || selectedStrategies.length === 0) return;
    setIsStarting(true);
    try {
      const token = getAccessToken();
      const res = await fetch("/api/v1/eval/runs", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          benchmark_id: selectedBenchmarkId,
          strategies: selectedStrategies,
          generate_answers: generateAnswers,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.message || "Failed to initiate evaluation run");
      }

      const runSummary: EvalRunSummary = await res.json();
      setIsNewRunOpen(false);
      if (onClearPresetBenchmark) onClearPresetBenchmark();
      onRefresh();
      onSelectRun(runSummary.id);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Error starting evaluation run");
    } finally {
      setIsStarting(false);
    }
  };

  const getStatusBadge = (status: EvalRunSummary["status"]) => {
    switch (status) {
      case "completed":
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="size-3.5" />
            Completed
          </span>
        );
      case "running":
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 animate-pulse">
            <Loader2 className="size-3.5 animate-spin" />
            Running
          </span>
        );
      case "failed":
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/20">
            <AlertCircle className="size-3.5" />
            Failed
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-zinc-800 text-zinc-400 border border-zinc-700">
            <Clock className="size-3.5" />
            Pending
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Action Bar */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-white text-balance">Evaluation Runs</h2>
          <p className="text-xs text-zinc-400 text-pretty">
            Inspect quantitative retrieval metrics, confidence reliability diagrams, and question traces.
          </p>
        </div>

        <button
          onClick={() => setIsNewRunOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium transition-colors shadow-sm shadow-emerald-600/30 cursor-pointer"
        >
          <Play className="size-4 fill-current" />
          New Evaluation Run
        </button>
      </div>

      {/* Runs Table */}
      {isLoading ? (
        <div className="py-16 text-center text-zinc-400">Loading evaluation runs...</div>
      ) : runs.length === 0 ? (
        <div className="py-16 text-center border border-dashed border-[#27272a] rounded-xl bg-[#111113]">
          <TrendingUp className="size-10 text-zinc-500 mx-auto mb-3" />
          <p className="text-zinc-300 font-medium">No evaluation runs recorded yet</p>
          <p className="text-xs text-zinc-500 mt-1 mb-4 text-pretty">
            Launch your first multi-strategy run against a built-in or custom benchmark.
          </p>
          <button
            onClick={() => setIsNewRunOpen(true)}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-medium transition-colors cursor-pointer"
          >
            Launch Run Now
          </button>
        </div>
      ) : (
        <div className="border border-[#27272a] rounded-xl bg-[#111113] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#18181b] border-b border-[#27272a] text-zinc-400 uppercase font-mono text-[11px]">
                <tr>
                  <th className="py-3 px-4">Run Details</th>
                  <th className="py-3 px-4">Strategies</th>
                  <th className="py-3 px-4">Hit@5</th>
                  <th className="py-3 px-4">MRR</th>
                  <th className="py-3 px-4">Accuracy</th>
                  <th className="py-3 px-4">Duration</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#27272a]">
                {runs.map((r) => {
                  // Find best strategy by Hit@5
                  const metricsList = Object.values(r.strategy_metrics || {});
                  const bestMetrics = metricsList.reduce(
                    (best, cur) => (cur.hit_5 > (best?.hit_5 || 0) ? cur : best),
                    metricsList[0]
                  );

                  return (
                    <tr
                      key={r.id}
                      onClick={() => onSelectRun(r.id)}
                      className="hover:bg-zinc-800/40 cursor-pointer transition-colors"
                    >
                      <td className="py-3 px-4">
                        <div className="font-medium text-white text-sm">{r.benchmark_name}</div>
                        <div className="text-[11px] font-mono text-zinc-400 mt-0.5">
                          ID: {r.id.slice(0, 10)}... • {new Date(r.created_at).toLocaleDateString()}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex flex-wrap gap-1 max-w-xs">
                          {r.strategies?.map((strat) => (
                            <span
                              key={strat}
                              className="px-1.5 py-0.5 rounded bg-[#18181b] border border-[#27272a] text-[11px] font-mono text-zinc-300"
                            >
                              {strat}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span className="font-semibold text-emerald-400 tabular-nums">
                          {bestMetrics ? `${(bestMetrics.hit_5 * 100).toFixed(1)}%` : "—"}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className="font-mono text-zinc-200 tabular-nums">
                          {bestMetrics ? bestMetrics.mrr.toFixed(3) : "—"}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-zinc-200 tabular-nums">
                          {bestMetrics && r.generate_answers
                            ? `${(bestMetrics.answer_correctness * 100).toFixed(1)}%`
                            : "—"}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-zinc-400 font-mono tabular-nums">
                        {r.duration_seconds > 0 ? `${r.duration_seconds.toFixed(1)}s` : "—"}
                      </td>
                      <td className="py-3 px-4">{getStatusBadge(r.status)}</td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectRun(r.id);
                          }}
                          aria-label="View run details"
                          className="p-1 rounded hover:bg-zinc-700 text-zinc-400 hover:text-white transition-colors cursor-pointer"
                        >
                          <ChevronRight className="size-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* New Run Modal with Pre-flight Estimation */}
      {isNewRunOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-[#111113] border border-[#27272a] rounded-xl max-w-xl w-full p-6 shadow-2xl flex flex-col max-h-[90vh]">
            <div className="flex items-center justify-between pb-3 border-b border-[#27272a] mb-4">
              <div>
                <h3 className="text-base font-semibold text-white">Start Evaluation Run</h3>
                <p className="text-xs text-zinc-400">
                  Select benchmark and retrieval strategies to benchmark.
                </p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setIsNewRunOpen(false);
                  if (onClearPresetBenchmark) onClearPresetBenchmark();
                }}
                aria-label="Close dialog"
                className="text-zinc-400 hover:text-white cursor-pointer"
              >
                <X className="size-5" />
              </button>
            </div>

            <div className="overflow-y-auto space-y-4 pr-1">
              {/* Benchmark Picker */}
              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                  Benchmark Suite
                </label>
                <select
                  value={selectedBenchmarkId}
                  onChange={(e) => setSelectedBenchmarkId(e.target.value)}
                  className="w-full bg-[#18181b] border border-[#27272a] rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-emerald-500"
                >
                  {benchmarks.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.name} ({b.question_count} questions) {b.is_builtin ? "• Built-in" : ""}
                    </option>
                  ))}
                </select>
              </div>

              {/* Strategy Checkboxes */}
              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                  Strategies to Benchmark
                </label>
                <div className="space-y-2">
                  {AVAILABLE_STRATEGIES.map((strat) => {
                    const checked = selectedStrategies.includes(strat.id);
                    return (
                      <div
                        key={strat.id}
                        onClick={() => handleToggleStrategy(strat.id)}
                        className={`flex items-start gap-3 p-2.5 rounded-lg border cursor-pointer transition-colors ${
                          checked
                            ? "bg-emerald-500/10 border-emerald-500/40 text-white"
                            : "bg-[#18181b] border-[#27272a] text-zinc-400 hover:border-zinc-700"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => {}}
                          className="mt-0.5 accent-emerald-600 rounded cursor-pointer"
                        />
                        <div>
                          <div className="text-xs font-semibold text-zinc-100">{strat.label}</div>
                          <div className="text-[11px] text-zinc-400">{strat.desc}</div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Generate Answers Toggle */}
              <div className="flex items-center justify-between p-3 rounded-lg border border-[#27272a] bg-[#18181b]">
                <div>
                  <div className="text-xs font-medium text-white flex items-center gap-1.5">
                    <Sparkles className="size-3.5 text-emerald-400" />
                    Generate & Score LLM Answers
                  </div>
                  <div className="text-[11px] text-zinc-400">
                    Produces answers, citation verification, and calibrated confidence scores.
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={generateAnswers}
                  onChange={(e) => setGenerateAnswers(e.target.checked)}
                  className="size-4 accent-emerald-600 rounded cursor-pointer"
                />
              </div>

              {/* Pre-Flight Estimate Card (§14.3) */}
              <div className="p-3.5 rounded-xl border border-emerald-500/20 bg-emerald-950/20 space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-emerald-300 flex items-center gap-1.5">
                    <Cpu className="size-3.5" />
                    Pre-Flight Run Estimate
                  </span>
                  {isEstimating && <Loader2 className="size-3.5 text-emerald-400 animate-spin" />}
                </div>

                {estimate ? (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
                    <div className="p-2 rounded bg-[#111113]/80 border border-[#27272a]">
                      <div className="text-[10px] text-zinc-400 uppercase font-mono">LLM Calls</div>
                      <div className="text-sm font-bold text-white mt-0.5 tabular-nums">
                        {estimate.estimated_llm_calls}
                      </div>
                    </div>
                    <div className="p-2 rounded bg-[#111113]/80 border border-[#27272a]">
                      <div className="text-[10px] text-zinc-400 uppercase font-mono">Est. Tokens</div>
                      <div className="text-sm font-bold text-white mt-0.5 tabular-nums">
                        {estimate.estimated_tokens.toLocaleString()}
                      </div>
                    </div>
                    <div className="p-2 rounded bg-[#111113]/80 border border-[#27272a]">
                      <div className="text-[10px] text-zinc-400 uppercase font-mono">Est. Cost</div>
                      <div className="text-sm font-bold text-emerald-400 mt-0.5 tabular-nums">
                        ${estimate.estimated_cost_usd.toFixed(4)}
                      </div>
                    </div>
                    <div className="p-2 rounded bg-[#111113]/80 border border-[#27272a]">
                      <div className="text-[10px] text-zinc-400 uppercase font-mono">Est. Time</div>
                      <div className="text-sm font-bold text-emerald-400 mt-0.5 tabular-nums">
                        ~{estimate.estimated_duration_seconds}s
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-xs text-zinc-500 text-center py-2">
                    Calculating estimate...
                  </div>
                )}
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-[#27272a] mt-4">
              <button
                type="button"
                onClick={() => {
                  setIsNewRunOpen(false);
                  if (onClearPresetBenchmark) onClearPresetBenchmark();
                }}
                className="px-4 py-2 rounded-lg text-sm font-medium text-zinc-400 hover:text-white cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleStartRun}
                disabled={isStarting || selectedStrategies.length === 0}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors shadow-sm shadow-emerald-600/30 cursor-pointer"
              >
                {isStarting ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    Launching...
                  </>
                ) : (
                  <>
                    <Play className="size-4 fill-current" />
                    Start Evaluation Run
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
