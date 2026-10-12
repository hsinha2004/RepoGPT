import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router";
import {
  BarChart3,
  BookOpen,
  Activity,
  GitPullRequest,
  RefreshCw,
} from "lucide-react";
import { Benchmark, EvalRunSummary } from "./types";
import { BenchmarksTab } from "./BenchmarksTab";
import { RunsTab } from "./RunsTab";
import { RunDetailView } from "./RunDetailView";
import { LiveMetricsTab } from "./LiveMetricsTab";
import { CodeReviewTab } from "./CodeReviewTab";
import { getAccessToken } from "../../api/client";

export const EvaluationPage: React.FC = () => {
  const { runId } = useParams<{ runId?: string }>();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<"runs" | "benchmarks" | "live" | "review">("runs");
  const [benchmarks, setBenchmarks] = useState<Benchmark[]>([]);
  const [runs, setRuns] = useState<EvalRunSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [presetBenchmark, setPresetBenchmark] = useState<Benchmark | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const token = getAccessToken();
      const headers = {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      };

      const [benchmarksRes, runsRes] = await Promise.all([
        fetch("/api/v1/eval/benchmarks", { headers }),
        fetch("/api/v1/eval/runs", { headers }),
      ]);

      if (benchmarksRes.ok) {
        const bData = await benchmarksRes.json();
        setBenchmarks(bData);
      }
      if (runsRes.ok) {
        const rData = await runsRes.json();
        setRuns(rData);
      }
    } catch {
      // Handle error gracefully
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectRun = (id: string) => {
    navigate(`/app/evaluation/runs/${id}`);
  };

  const handleBackFromRunDetail = () => {
    navigate("/app/evaluation");
    fetchData();
  };

  const handleSelectRunBenchmark = (b: Benchmark) => {
    setPresetBenchmark(b);
    setActiveTab("runs");
  };

  const handleRerun = async (benchmarkId: string, strategies: string[]) => {
    try {
      const token = getAccessToken();
      const res = await fetch("/api/v1/eval/runs", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          benchmark_id: benchmarkId,
          strategies,
          generate_answers: true,
        }),
      });

      if (res.ok) {
        const newRun: EvalRunSummary = await res.json();
        navigate(`/app/evaluation/runs/${newRun.id}`);
      }
    } catch {
      alert("Failed to start rerun.");
    }
  };

  // If URL has runId, display RunDetailView
  if (runId) {
    return (
      <div className="max-w-7xl mx-auto p-6 space-y-6">
        <RunDetailView
          runId={runId}
          allRuns={runs}
          onBack={handleBackFromRunDetail}
          onRerun={handleRerun}
        />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-12">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <BarChart3 className="w-6 h-6 text-indigo-400" />
            Evaluation Dashboard
          </h1>
          <p className="text-sm text-zinc-400 mt-1">
            Empirical benchmark evaluation (§14): multi-strategy comparison, confidence reliability
            diagrams, and live chat telemetry.
          </p>
        </div>

        <button
          onClick={fetchData}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-[#18181b] hover:bg-zinc-800 border border-[#27272a] rounded-lg text-xs font-medium text-zinc-300 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
          Refresh Data
        </button>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-1 border-b border-[#27272a]">
        <button
          onClick={() => setActiveTab("runs")}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
            activeTab === "runs"
              ? "border-indigo-500 text-white"
              : "border-transparent text-zinc-400 hover:text-zinc-200"
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          Evaluation Runs
          {runs.length > 0 && (
            <span className="px-1.5 py-0.2 rounded-full text-[11px] bg-zinc-800 text-zinc-400">
              {runs.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab("benchmarks")}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
            activeTab === "benchmarks"
              ? "border-indigo-500 text-white"
              : "border-transparent text-zinc-400 hover:text-zinc-200"
          }`}
        >
          <BookOpen className="w-4 h-4" />
          Benchmark Suites
          {benchmarks.length > 0 && (
            <span className="px-1.5 py-0.2 rounded-full text-[11px] bg-zinc-800 text-zinc-400">
              {benchmarks.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab("live")}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
            activeTab === "live"
              ? "border-indigo-500 text-white"
              : "border-transparent text-zinc-400 hover:text-zinc-200"
          }`}
        >
          <Activity className="w-4 h-4" />
          Live Chat Metrics
        </button>

        <button
          onClick={() => setActiveTab("review")}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
            activeTab === "review"
              ? "border-indigo-500 text-white"
              : "border-transparent text-zinc-400 hover:text-zinc-200"
          }`}
        >
          <GitPullRequest className="w-4 h-4" />
          Code Review
          <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
            Phase 2
          </span>
        </button>
      </div>

      {/* Tab Contents */}
      {activeTab === "runs" && (
        <RunsTab
          runs={runs}
          benchmarks={benchmarks}
          isLoading={isLoading}
          onRefresh={fetchData}
          onSelectRun={handleSelectRun}
          presetBenchmark={presetBenchmark}
          onClearPresetBenchmark={() => setPresetBenchmark(null)}
        />
      )}

      {activeTab === "benchmarks" && (
        <BenchmarksTab
          benchmarks={benchmarks}
          isLoading={isLoading}
          onRefresh={fetchData}
          onSelectRunBenchmark={handleSelectRunBenchmark}
        />
      )}

      {activeTab === "live" && <LiveMetricsTab />}

      {activeTab === "review" && <CodeReviewTab />}
    </div>
  );
};
