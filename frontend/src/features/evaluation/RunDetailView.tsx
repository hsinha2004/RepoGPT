import React, { useState, useEffect } from "react";
import {
  ArrowLeft,
  FileSpreadsheet,
  FileText,
  FileCode,
  CheckCircle2,
  XCircle,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Search,
  GitCompare,
  TrendingUp,
  Percent,
  Timer,
  ShieldCheck,
  Target,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  LineChart,
  Line,
  ReferenceLine,
} from "recharts";
import {
  CalibrationBin,
  EvalQuestionResult,
  EvalRunSummary,
  StrategyMetrics,
} from "./types";
import { getAccessToken } from "../../api/client";

interface RunDetailViewProps {
  runId: string;
  allRuns: EvalRunSummary[];
  onBack: () => void;
  onRerun: (benchmarkId: string, strategies: string[]) => void;
}

export const RunDetailView: React.FC<RunDetailViewProps> = ({
  runId,
  allRuns,
  onBack,
  onRerun,
}) => {
  const [run, setRun] = useState<EvalRunSummary | null>(null);
  const [questions, setQuestions] = useState<EvalQuestionResult[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedStrategy, setSelectedStrategy] = useState<string>("all");
  const [compareRunId, setCompareRunId] = useState<string>("");
  const [expandedQuestionId, setExpandedQuestionId] = useState<string | null>(null);
  const [filterCategory, setFilterCategory] = useState<string>("all");
  const [searchQuestion, setSearchQuestion] = useState<string>("");

  useEffect(() => {
    fetchRunDetail();
    fetchQuestions();
  }, [runId]);

  const fetchRunDetail = async () => {
    setIsLoading(true);
    try {
      const token = getAccessToken();
      const res = await fetch(`/api/v1/eval/runs/${runId}`, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (res.ok) {
        const data = await res.json();
        setRun(data);
      }
    } catch {
      // Handle network error
    } finally {
      setIsLoading(false);
    }
  };

  const fetchQuestions = async () => {
    try {
      const token = getAccessToken();
      const res = await fetch(`/api/v1/eval/runs/${runId}/results?limit=500`, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (res.ok) {
        const data = await res.json();
        setQuestions(data);
      }
    } catch {
      // Handle network error
    }
  };

  const handleExport = (format: "csv" | "markdown" | "json") => {
    const token = getAccessToken();
    const url = `/api/v1/eval/runs/${runId}/export?format=${format}`;
    fetch(url, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    })
      .then((res) => res.blob())
      .then((blob) => {
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = downloadUrl;
        a.download = `eval_run_${runId}.${format === "markdown" ? "md" : format}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
      });
  };

  if (isLoading || !run) {
    return (
      <div className="py-24 text-center text-zinc-400">Loading evaluation run details...</div>
    );
  }

  const compareRun = allRuns.find((r) => r.id === compareRunId);

  // Determine active strategy metrics to display in KPI cards
  const activeMetricsList = Object.values(run.strategy_metrics || {});
  const activeMetrics: StrategyMetrics | undefined =
    selectedStrategy === "all"
      ? activeMetricsList.reduce(
          (best, cur) => (cur.hit_5 > (best?.hit_5 || 0) ? cur : best),
          activeMetricsList[0]
        )
      : run.strategy_metrics[selectedStrategy];

  // Strategy comparison bar chart data
  const comparisonBarData = Object.entries(run.strategy_metrics || {}).map(
    ([strat, m]) => ({
      strategy: strat,
      "Hit@5 (%)": Number((m.hit_5 * 100).toFixed(1)),
      "MRR (x100)": Number((m.mrr * 100).toFixed(1)),
      "Answer Acc (%)": Number((m.answer_correctness * 100).toFixed(1)),
      "Symbol Recall (%)": Number((m.symbol_recall_5 * 100).toFixed(1)),
    })
  );

  // Latency breakdown stacked bar chart data
  const latencyStackedData = Object.entries(run.strategy_metrics || {}).map(
    ([strat, m]) => ({
      strategy: strat,
      Route: Number(m.latency_route_p50.toFixed(1)),
      Retrieve: Number(m.latency_retrieve_p50.toFixed(1)),
      Rerank: Number(m.latency_rerank_p50.toFixed(1)),
      Generate: Number(m.latency_generate_p50.toFixed(1)),
      Total: Number(m.latency_p50.toFixed(1)),
    })
  );

  // Confidence Calibration Reliability data (for active strategy)
  const calibrationBins: CalibrationBin[] =
    (selectedStrategy === "all"
      ? run.calibration_bins[Object.keys(run.calibration_bins)[0]]
      : run.calibration_bins[selectedStrategy]) || [];

  const calibrationChartData = calibrationBins.map((bin) => ({
    label: bin.range_label,
    Confidence: Number((bin.mean_predicted_confidence * 100).toFixed(1)),
    Accuracy: Number((bin.empirical_accuracy * 100).toFixed(1)),
    Ideal: Number((bin.mean_predicted_confidence * 100).toFixed(1)),
    Count: bin.count,
  }));

  // Per-category breakdown calculation from questions
  const categorySummary: Record<
    string,
    { count: number; hit5Count: number; correctCount: number; mrrSum: number }
  > = {};

  const filteredQuestions = questions.filter((q) => {
    const matchesStrat =
      selectedStrategy === "all" || q.strategy === selectedStrategy;
    const matchesCat =
      filterCategory === "all" || q.category.toLowerCase() === filterCategory.toLowerCase();
    const matchesSearch =
      !searchQuestion ||
      q.query.toLowerCase().includes(searchQuestion.toLowerCase()) ||
      q.question_id.toLowerCase().includes(searchQuestion.toLowerCase());
    return matchesStrat && matchesCat && matchesSearch;
  });

  questions.forEach((q) => {
    if (selectedStrategy !== "all" && q.strategy !== selectedStrategy) return;
    const cat = q.category || "general";
    if (!categorySummary[cat]) {
      categorySummary[cat] = { count: 0, hit5Count: 0, correctCount: 0, mrrSum: 0 };
    }
    categorySummary[cat].count += 1;
    if (q.hit_5 > 0) categorySummary[cat].hit5Count += 1;
    if (q.is_correct) categorySummary[cat].correctCount += 1;
  });

  return (
    <div className="space-y-6">
      {/* Top Header & Actions */}
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 pb-4 border-b border-[#27272a]">
        <div>
          <button
            onClick={onBack}
            className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white transition-colors mb-2"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Evaluation Runs
          </button>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-white tracking-tight">
              {run.benchmark_name}
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              {run.status}
            </span>
          </div>
          <p className="text-xs text-zinc-400 mt-1 font-mono">
            Run ID: {run.id} • Completed in {run.duration_seconds.toFixed(1)}s •{" "}
            {new Date(run.created_at).toLocaleString()}
          </p>
        </div>

        {/* Toolbar: Comparison & Exports */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Comparison Run Selector */}
          <div className="flex items-center gap-2 bg-[#18181b] border border-[#27272a] rounded-lg px-2.5 py-1.5 text-xs">
            <GitCompare className="w-3.5 h-3.5 text-zinc-400" />
            <select
              value={compareRunId}
              onChange={(e) => setCompareRunId(e.target.value)}
              className="bg-transparent text-zinc-200 focus:outline-none"
            >
              <option value="">Compare with another run...</option>
              {allRuns
                .filter((r) => r.id !== run.id)
                .map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.benchmark_name} ({r.id.slice(0, 8)})
                  </option>
                ))}
            </select>
          </div>

          {/* Export Dropdown / Buttons */}
          <div className="flex items-center gap-1 bg-[#18181b] border border-[#27272a] rounded-lg p-1">
            <button
              onClick={() => handleExport("csv")}
              title="Export CSV"
              className="px-2.5 py-1 rounded text-xs text-zinc-300 hover:text-white hover:bg-zinc-800 transition-colors flex items-center gap-1"
            >
              <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
              CSV
            </button>
            <button
              onClick={() => handleExport("markdown")}
              title="Export Markdown Report"
              className="px-2.5 py-1 rounded text-xs text-zinc-300 hover:text-white hover:bg-zinc-800 transition-colors flex items-center gap-1"
            >
              <FileText className="w-3.5 h-3.5 text-blue-400" />
              MD
            </button>
            <button
              onClick={() => handleExport("json")}
              title="Export JSON"
              className="px-2.5 py-1 rounded text-xs text-zinc-300 hover:text-white hover:bg-zinc-800 transition-colors flex items-center gap-1"
            >
              <FileCode className="w-3.5 h-3.5 text-amber-400" />
              JSON
            </button>
          </div>

          <button
            onClick={() => onRerun(run.benchmark_id, run.strategies)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition-colors"
          >
            Rerun Benchmark
          </button>
        </div>
      </div>

      {/* Strategy Pills Selector */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider font-mono mr-1">
          Strategy:
        </span>
        <button
          onClick={() => setSelectedStrategy("all")}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            selectedStrategy === "all"
              ? "bg-indigo-600 text-white shadow-sm"
              : "bg-[#18181b] border border-[#27272a] text-zinc-400 hover:text-white"
          }`}
        >
          All Strategies (Best View)
        </button>
        {run.strategies?.map((strat) => (
          <button
            key={strat}
            onClick={() => setSelectedStrategy(strat)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              selectedStrategy === strat
                ? "bg-indigo-600 text-white shadow-sm"
                : "bg-[#18181b] border border-[#27272a] text-zinc-400 hover:text-white"
            }`}
          >
            {strat}
          </button>
        ))}
      </div>

      {/* KPI Cards Grid (§14.2) */}
      {activeMetrics && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="bg-[#111113] border border-[#27272a] rounded-xl p-3.5">
            <div className="text-[11px] font-mono text-zinc-400 uppercase flex items-center gap-1">
              <Target className="w-3.5 h-3.5 text-emerald-400" />
              Hit@5
            </div>
            <div className="text-2xl font-bold text-white mt-1">
              {(activeMetrics.hit_5 * 100).toFixed(1)}%
            </div>
            <div className="text-[10px] text-zinc-500 mt-0.5">
              Hit@1: {(activeMetrics.hit_1 * 100).toFixed(0)}% • Hit@10:{" "}
              {(activeMetrics.hit_10 * 100).toFixed(0)}%
            </div>
          </div>

          <div className="bg-[#111113] border border-[#27272a] rounded-xl p-3.5">
            <div className="text-[11px] font-mono text-zinc-400 uppercase flex items-center gap-1">
              <TrendingUp className="w-3.5 h-3.5 text-indigo-400" />
              MRR
            </div>
            <div className="text-2xl font-bold text-white mt-1">
              {activeMetrics.mrr.toFixed(3)}
            </div>
            <div className="text-[10px] text-zinc-500 mt-0.5">Mean Reciprocal Rank</div>
          </div>

          <div className="bg-[#111113] border border-[#27272a] rounded-xl p-3.5">
            <div className="text-[11px] font-mono text-zinc-400 uppercase flex items-center gap-1">
              <Percent className="w-3.5 h-3.5 text-purple-400" />
              nDCG@5
            </div>
            <div className="text-2xl font-bold text-white mt-1">
              {activeMetrics.ndcg_5.toFixed(3)}
            </div>
            <div className="text-[10px] text-zinc-500 mt-0.5">
              nDCG@10: {activeMetrics.ndcg_10.toFixed(3)} (graded)
            </div>
          </div>

          <div className="bg-[#111113] border border-[#27272a] rounded-xl p-3.5">
            <div className="text-[11px] font-mono text-zinc-400 uppercase flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
              Citation Valid
            </div>
            <div className="text-2xl font-bold text-white mt-1">
              {(activeMetrics.citation_validity * 100).toFixed(1)}%
            </div>
            <div className="text-[10px] text-zinc-500 mt-0.5">
              Prec: {(activeMetrics.citation_precision * 100).toFixed(0)}% • Rec:{" "}
              {(activeMetrics.citation_recall * 100).toFixed(0)}%
            </div>
          </div>

          <div className="bg-[#111113] border border-[#27272a] rounded-xl p-3.5">
            <div className="text-[11px] font-mono text-zinc-400 uppercase flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              Answer Acc
            </div>
            <div className="text-2xl font-bold text-white mt-1">
              {(activeMetrics.answer_correctness * 100).toFixed(1)}%
            </div>
            <div className="text-[10px] text-zinc-500 mt-0.5">
              Coverage: {(activeMetrics.must_mention_coverage * 100).toFixed(0)}%
            </div>
          </div>

          <div className="bg-[#111113] border border-[#27272a] rounded-xl p-3.5">
            <div className="text-[11px] font-mono text-zinc-400 uppercase flex items-center gap-1">
              <Timer className="w-3.5 h-3.5 text-rose-400" />
              ECE / Latency
            </div>
            <div className="text-2xl font-bold text-white mt-1">
              {activeMetrics.ece.toFixed(3)}
            </div>
            <div className="text-[10px] text-zinc-500 mt-0.5 font-mono">
              p50: {activeMetrics.latency_p50.toFixed(0)}ms • Brier:{" "}
              {activeMetrics.brier_score.toFixed(3)}
            </div>
          </div>
        </div>
      )}

      {/* Comparison Delta View (when comparison run is picked) */}
      {compareRun && (
        <div className="p-4 bg-indigo-950/20 border border-indigo-500/30 rounded-xl space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold text-indigo-300 flex items-center gap-1.5 uppercase tracking-wider font-mono">
              <GitCompare className="w-3.5 h-3.5" />
              Run Delta: {run.benchmark_name} vs {compareRun.benchmark_name}
            </h3>
            <button
              onClick={() => setCompareRunId("")}
              className="text-xs text-zinc-400 hover:text-white"
            >
              Clear Comparison
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="text-zinc-400 border-b border-[#27272a]">
                <tr>
                  <th className="py-2 px-3">Metric</th>
                  <th className="py-2 px-3">Current Run</th>
                  <th className="py-2 px-3">Comparison Run</th>
                  <th className="py-2 px-3">Delta</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#27272a]/60">
                {activeMetrics && (
                  <>
                    {(() => {
                      const cMetrics =
                        selectedStrategy === "all"
                          ? Object.values(compareRun.strategy_metrics || {})[0]
                          : compareRun.strategy_metrics[selectedStrategy];

                      const renderDelta = (val1: number, val2: number | undefined, isPct = false) => {
                        if (val2 === undefined) return "—";
                        const diff = val1 - val2;
                        const isPositive = diff >= 0;
                        const formatted = isPct
                          ? `${(diff * 100).toFixed(1)}%`
                          : diff.toFixed(3);
                        return (
                          <span
                            className={
                              isPositive ? "text-emerald-400 font-semibold" : "text-rose-400 font-semibold"
                            }
                          >
                            {isPositive ? `+${formatted}` : formatted}
                          </span>
                        );
                      };

                      return (
                        <>
                          <tr>
                            <td className="py-2 px-3 font-medium text-white">Hit@5 Rate</td>
                            <td className="py-2 px-3 text-zinc-300 font-mono">
                              {(activeMetrics.hit_5 * 100).toFixed(1)}%
                            </td>
                            <td className="py-2 px-3 text-zinc-400 font-mono">
                              {cMetrics ? `${(cMetrics.hit_5 * 100).toFixed(1)}%` : "—"}
                            </td>
                            <td className="py-2 px-3 font-mono">
                              {renderDelta(activeMetrics.hit_5, cMetrics?.hit_5, true)}
                            </td>
                          </tr>
                          <tr>
                            <td className="py-2 px-3 font-medium text-white">MRR</td>
                            <td className="py-2 px-3 text-zinc-300 font-mono">
                              {activeMetrics.mrr.toFixed(3)}
                            </td>
                            <td className="py-2 px-3 text-zinc-400 font-mono">
                              {cMetrics ? cMetrics.mrr.toFixed(3) : "—"}
                            </td>
                            <td className="py-2 px-3 font-mono">
                              {renderDelta(activeMetrics.mrr, cMetrics?.mrr, false)}
                            </td>
                          </tr>
                          <tr>
                            <td className="py-2 px-3 font-medium text-white">Answer Accuracy</td>
                            <td className="py-2 px-3 text-zinc-300 font-mono">
                              {(activeMetrics.answer_correctness * 100).toFixed(1)}%
                            </td>
                            <td className="py-2 px-3 text-zinc-400 font-mono">
                              {cMetrics ? `${(cMetrics.answer_correctness * 100).toFixed(1)}%` : "—"}
                            </td>
                            <td className="py-2 px-3 font-mono">
                              {renderDelta(activeMetrics.answer_correctness, cMetrics?.answer_correctness, true)}
                            </td>
                          </tr>
                          <tr>
                            <td className="py-2 px-3 font-medium text-white">Expected Calibration Error</td>
                            <td className="py-2 px-3 text-zinc-300 font-mono">
                              {activeMetrics.ece.toFixed(3)}
                            </td>
                            <td className="py-2 px-3 text-zinc-400 font-mono">
                              {cMetrics ? cMetrics.ece.toFixed(3) : "—"}
                            </td>
                            <td className="py-2 px-3 font-mono">
                              {renderDelta(activeMetrics.ece, cMetrics?.ece, false)}
                            </td>
                          </tr>
                        </>
                      );
                    })()}
                  </>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Strategy Performance Comparison Bar Chart */}
        <div className="bg-[#111113] border border-[#27272a] rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Strategy Metrics Comparison</h3>
            <span className="text-[11px] text-zinc-400">All tested retrieval strategies</span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={comparisonBarData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis dataKey="strategy" stroke="#71717a" fontSize={11} />
                <YAxis stroke="#71717a" fontSize={11} domain={[0, 100]} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#18181b", borderColor: "#27272a", fontSize: "12px" }}
                />
                <Legend wrapperStyle={{ fontSize: "11px" }} />
                <Bar dataKey="Hit@5 (%)" fill="#10b981" radius={[4, 4, 0, 0]} />
                <Bar dataKey="MRR (x100)" fill="#6366f1" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Answer Acc (%)" fill="#f59e0b" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Stage Latency Breakdown Stacked Bar Chart */}
        <div className="bg-[#111113] border border-[#27272a] rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Stage Latency Breakdown (p50 ms)</h3>
            <span className="text-[11px] text-zinc-400">Route + Retrieve + Rerank + Generate</span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={latencyStackedData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis dataKey="strategy" stroke="#71717a" fontSize={11} />
                <YAxis stroke="#71717a" fontSize={11} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#18181b", borderColor: "#27272a", fontSize: "12px" }}
                />
                <Legend wrapperStyle={{ fontSize: "11px" }} />
                <Bar dataKey="Route" stackId="a" fill="#38bdf8" />
                <Bar dataKey="Retrieve" stackId="a" fill="#818cf8" />
                <Bar dataKey="Rerank" stackId="a" fill="#c084fc" />
                <Bar dataKey="Generate" stackId="a" fill="#fb7185" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Confidence Calibration Reliability Diagram */}
        <div className="bg-[#111113] border border-[#27272a] rounded-xl p-5 space-y-4 lg:col-span-2">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-white">
                Reliability Diagram (Confidence Calibration)
              </h3>
              <p className="text-xs text-zinc-400">
                10-bin distribution comparing mean predicted confidence against actual empirical accuracy.
              </p>
            </div>
            <div className="text-xs font-mono text-zinc-400">
              ECE: {activeMetrics?.ece.toFixed(3)} • Brier: {activeMetrics?.brier_score.toFixed(3)}
            </div>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={calibrationChartData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis dataKey="label" stroke="#71717a" fontSize={11} />
                <YAxis stroke="#71717a" fontSize={11} domain={[0, 100]} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#18181b", borderColor: "#27272a", fontSize: "12px" }}
                />
                <Legend wrapperStyle={{ fontSize: "11px" }} />
                <ReferenceLine stroke="#52525b" strokeDasharray="4 4" />
                <Line
                  type="monotone"
                  dataKey="Ideal"
                  stroke="#71717a"
                  strokeDasharray="4 4"
                  name="Perfect Calibration (y = x)"
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="Accuracy"
                  stroke="#10b981"
                  strokeWidth={2}
                  name="Empirical Accuracy (%)"
                  dot={{ r: 4, fill: "#10b981" }}
                />
                <Line
                  type="monotone"
                  dataKey="Confidence"
                  stroke="#6366f1"
                  strokeWidth={2}
                  name="Mean Confidence (%)"
                  dot={{ r: 4, fill: "#6366f1" }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Per-Category Performance Table */}
      <div className="bg-[#111113] border border-[#27272a] rounded-xl overflow-hidden space-y-0">
        <div className="px-5 py-3 border-b border-[#27272a] flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white">Performance by Question Category</h3>
          <span className="text-xs text-zinc-400">
            {Object.keys(categorySummary).length} categories detected
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#18181b] border-b border-[#27272a] text-zinc-400 uppercase font-mono text-[11px]">
              <tr>
                <th className="py-2.5 px-4">Category</th>
                <th className="py-2.5 px-4">Questions</th>
                <th className="py-2.5 px-4">Hit@5 Rate</th>
                <th className="py-2.5 px-4">Answer Accuracy</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#27272a]">
              {Object.entries(categorySummary).map(([cat, stats]) => (
                <tr key={cat} className="hover:bg-zinc-800/30">
                  <td className="py-2.5 px-4 font-medium text-white capitalize">{cat}</td>
                  <td className="py-2.5 px-4 text-zinc-300 font-mono">{stats.count}</td>
                  <td className="py-2.5 px-4 font-mono text-emerald-400">
                    {stats.count > 0
                      ? `${((stats.hit5Count / stats.count) * 100).toFixed(1)}%`
                      : "—"}
                  </td>
                  <td className="py-2.5 px-4 font-mono text-indigo-300">
                    {stats.count > 0
                      ? `${((stats.correctCount / stats.count) * 100).toFixed(1)}%`
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Per-Question Drill-Down Table */}
      <div className="bg-[#111113] border border-[#27272a] rounded-xl overflow-hidden space-y-0">
        <div className="p-4 border-b border-[#27272a] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-white">Question-Level Drill-Down</h3>
            <p className="text-xs text-zinc-400">
              Inspect retrieval results, citations, and answers for each benchmark question.
            </p>
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <div className="relative flex-1 sm:w-56">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
              <input
                type="text"
                placeholder="Search questions..."
                value={searchQuestion}
                onChange={(e) => setSearchQuestion(e.target.value)}
                className="w-full bg-[#18181b] border border-[#27272a] rounded-lg pl-8 pr-3 py-1.5 text-xs text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              className="bg-[#18181b] border border-[#27272a] rounded-lg px-2.5 py-1.5 text-xs text-zinc-200 focus:outline-none"
            >
              <option value="all">All Categories</option>
              {Object.keys(categorySummary).map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#18181b] border-b border-[#27272a] text-zinc-400 uppercase font-mono text-[11px]">
              <tr>
                <th className="py-2.5 px-4">Q ID</th>
                <th className="py-2.5 px-4">Category</th>
                <th className="py-2.5 px-4">Question Query</th>
                <th className="py-2.5 px-4">Strategy</th>
                <th className="py-2.5 px-4">Hit@5</th>
                <th className="py-2.5 px-4">Citations</th>
                <th className="py-2.5 px-4">Correct</th>
                <th className="py-2.5 px-4">Confidence</th>
                <th className="py-2.5 px-4">Latency</th>
                <th className="py-2.5 px-4 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#27272a]">
              {filteredQuestions.map((q) => {
                const isExpanded = expandedQuestionId === `${q.question_id}_${q.strategy}`;
                return (
                  <React.Fragment key={`${q.question_id}_${q.strategy}`}>
                    <tr
                      onClick={() =>
                        setExpandedQuestionId(isExpanded ? null : `${q.question_id}_${q.strategy}`)
                      }
                      className="hover:bg-zinc-800/40 cursor-pointer transition-colors"
                    >
                      <td className="py-2.5 px-4 font-mono text-zinc-400">{q.question_id}</td>
                      <td className="py-2.5 px-4">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-zinc-800 text-zinc-300 border border-zinc-700">
                          {q.category}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 max-w-xs truncate font-medium text-white">
                        {q.query}
                      </td>
                      <td className="py-2.5 px-4 font-mono text-zinc-400">{q.strategy}</td>
                      <td className="py-2.5 px-4 font-mono">
                        {q.hit_5 > 0 ? (
                          <span className="text-emerald-400">HIT</span>
                        ) : (
                          <span className="text-rose-400">MISS</span>
                        )}
                      </td>
                      <td className="py-2.5 px-4 font-mono">
                        {q.citations?.length > 0 ? (
                          <span className="text-cyan-400">{q.citations.length} cited</span>
                        ) : (
                          <span className="text-zinc-500">None</span>
                        )}
                      </td>
                      <td className="py-2.5 px-4">
                        {q.is_correct ? (
                          <span className="flex items-center gap-1 text-emerald-400">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Correct
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-zinc-500">
                            <XCircle className="w-3.5 h-3.5" /> Incorrect
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-4 font-mono text-zinc-300">
                        {(q.confidence_score * 100).toFixed(0)}%
                      </td>
                      <td className="py-2.5 px-4 font-mono text-zinc-400">
                        {q.latency_ms.toFixed(0)}ms
                      </td>
                      <td className="py-2.5 px-4 text-right">
                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4 text-zinc-400 inline" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-zinc-400 inline" />
                        )}
                      </td>
                    </tr>

                    {/* Expanded Detail Row */}
                    {isExpanded && (
                      <tr className="bg-[#18181b]/70 border-b border-[#27272a]">
                        <td colSpan={10} className="p-4 space-y-3">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                              <div className="text-xs font-semibold text-zinc-300 mb-1">
                                Generated Answer:
                              </div>
                              <div className="p-3 bg-[#111113] border border-[#27272a] rounded-lg text-xs text-zinc-200 leading-relaxed font-sans">
                                {q.answer || "No answer generated."}
                              </div>
                            </div>
                            <div className="space-y-2">
                              <div className="text-xs font-semibold text-zinc-300">
                                Trace & Citations:
                              </div>
                              <div className="p-3 bg-[#111113] border border-[#27272a] rounded-lg text-xs space-y-1.5 font-mono">
                                <div>
                                  <span className="text-zinc-500">Predicted Intent:</span>{" "}
                                  <span className="text-zinc-200">{q.predicted_intent}</span>
                                </div>
                                <div>
                                  <span className="text-zinc-500">Citations:</span>{" "}
                                  <span className="text-cyan-400">
                                    {q.citations?.join(", ") || "None"}
                                  </span>
                                </div>
                                <div>
                                  <span className="text-zinc-500">Citation Validity:</span>{" "}
                                  <span className="text-emerald-400">
                                    {(q.citation_validity * 100).toFixed(1)}%
                                  </span>
                                </div>
                                <div>
                                  <span className="text-zinc-500">Must-Mention Coverage:</span>{" "}
                                  <span className="text-amber-400">
                                    {(q.must_mention_coverage * 100).toFixed(1)}%
                                  </span>
                                </div>
                              </div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
