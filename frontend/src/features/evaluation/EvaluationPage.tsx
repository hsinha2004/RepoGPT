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
          <h1 className="text-2xl font-bold text-zinc-900 text-balance flex items-center gap-2.5">
            <BarChart3 className="size-6 text-emerald-600" />
            Evaluation Dashboard
          </h1>
          <p className="text-sm text-zinc-500 mt-1 text-pretty">
            Empirical benchmark evaluation (§14): multi-strategy comparison, confidence reliability
            diagrams, and live chat telemetry.
          </p>
        </div>

        <button
          onClick={fetchData}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-zinc-50 border border-zinc-200 rounded-lg text-xs font-medium text-zinc-700 transition-colors cursor-pointer shadow-xs"
        >
          <RefreshCw className={`size-3.5 ${isLoading ? "animate-spin" : ""}`} />
          Refresh Data
        </button>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-1 border-b border-zinc-200">
        <button
          onClick={() => setActiveTab("runs")}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px cursor-pointer ${
            activeTab === "runs"
              ? "border-emerald-600 text-emerald-600"
              : "border-transparent text-zinc-500 hover:text-zinc-900"
          }`}
        >
          <BarChart3 className="size-4" />
          Evaluation Runs
          {runs.length > 0 && (
            <span className="px-1.5 py-0.2 rounded-full text-[11px] bg-zinc-100 text-zinc-600 tabular-nums">
              {runs.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab("benchmarks")}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px cursor-pointer ${
            activeTab === "benchmarks"
              ? "border-emerald-600 text-emerald-600"
              : "border-transparent text-zinc-500 hover:text-zinc-900"
          }`}
        >
          <BookOpen className="size-4" />
          Benchmark Suites
          {benchmarks.length > 0 && (
            <span className="px-1.5 py-0.2 rounded-full text-[11px] bg-zinc-100 text-zinc-600 tabular-nums">
              {benchmarks.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab("live")}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px cursor-pointer ${
            activeTab === "live"
              ? "border-emerald-600 text-emerald-600"
              : "border-transparent text-zinc-500 hover:text-zinc-900"
          }`}
        >
          <Activity className="size-4" />
          Live Chat Metrics
        </button>

        <button
          onClick={() => setActiveTab("review")}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px cursor-pointer ${
            activeTab === "review"
              ? "border-emerald-600 text-emerald-600"
              : "border-transparent text-zinc-500 hover:text-zinc-900"
          }`}
        >
          <GitPullRequest className="size-4" />
          Code Review
          <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200">
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
