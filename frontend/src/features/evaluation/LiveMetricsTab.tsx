import React, { useState, useEffect } from "react";
import {
  Activity,
  TrendingUp,
  ThumbsUp,
  DollarSign,
  Cpu,
  BarChart2,
  RefreshCw,
} from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { EvalLiveMetrics } from "./types";
import { getAccessToken } from "../../api/client";

export const LiveMetricsTab: React.FC = () => {
  const [metrics, setMetrics] = useState<EvalLiveMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchLiveMetrics();
  }, []);

  const fetchLiveMetrics = async () => {
    setIsLoading(true);
    try {
      const token = getAccessToken();
      const res = await fetch("/api/v1/eval/live", {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (res.ok) {
        const data = await res.json();
        setMetrics(data);
      }
    } catch {
      // Handle error
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading || !metrics) {
    return (
      <div className="py-24 text-center text-zinc-400">Loading live chat telemetry...</div>
    );
  }

  const satisfactionRatio = metrics.satisfaction_gauge.ratio;
  const satisfactionPct = Number((satisfactionRatio * 100).toFixed(1));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-[#27272a]">
        <div>
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Activity className="w-4 h-4 text-emerald-400" />
            Live Chat Telemetry & Production Monitoring
          </h2>
          <p className="text-xs text-zinc-400">
            Real-time evaluation signals collected from user chat sessions over the past 7 days (§14.4).
          </p>
        </div>

        <button
          onClick={fetchLiveMetrics}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-[#18181b] hover:bg-zinc-800 border border-[#27272a] rounded-lg text-xs font-medium text-zinc-300 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh Telemetry
        </button>
      </div>

      {/* Top Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#111113] border border-[#27272a] rounded-xl p-4">
          <div className="flex items-center justify-between text-zinc-400 text-xs">
            <span className="font-mono uppercase">User Satisfaction</span>
            <ThumbsUp className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">
            {satisfactionPct}% Positive
          </div>
          <div className="text-[11px] text-zinc-500 mt-1">
            {metrics.satisfaction_gauge.positive_ratings} 👍 /{" "}
            {metrics.satisfaction_gauge.negative_ratings} 👎 ratings
          </div>
        </div>

        <div className="bg-[#111113] border border-[#27272a] rounded-xl p-4">
          <div className="flex items-center justify-between text-zinc-400 text-xs">
            <span className="font-mono uppercase">Total Queries (7d)</span>
            <TrendingUp className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">
            {metrics.questions_per_day.reduce((acc, cur) => acc + cur.count, 0)}
          </div>
          <div className="text-[11px] text-zinc-500 mt-1">
            Avg ~
            {(
              metrics.questions_per_day.reduce((acc, cur) => acc + cur.count, 0) / 7
            ).toFixed(0)}{" "}
            questions/day
          </div>
        </div>

        <div className="bg-[#111113] border border-[#27272a] rounded-xl p-4">
          <div className="flex items-center justify-between text-zinc-400 text-xs">
            <span className="font-mono uppercase">Total LLM Tokens</span>
            <Cpu className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">
            {metrics.tokens_and_cost
              .reduce((acc, cur) => acc + cur.tokens, 0)
              .toLocaleString()}
          </div>
          <div className="text-[11px] text-zinc-500 mt-1">Across all user queries</div>
        </div>

        <div className="bg-[#111113] border border-[#27272a] rounded-xl p-4">
          <div className="flex items-center justify-between text-zinc-400 text-xs">
            <span className="font-mono uppercase">Estimated Cost (7d)</span>
            <DollarSign className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 mt-2">
            $
            {metrics.tokens_and_cost
              .reduce((acc, cur) => acc + cur.cost_usd, 0)
              .toFixed(4)}
          </div>
          <div className="text-[11px] text-zinc-500 mt-1">Zero-key offline mode free</div>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Questions Per Day Area Chart */}
        <div className="bg-[#111113] border border-[#27272a] rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Questions Per Day (Volume)</h3>
            <span className="text-[11px] text-zinc-400">Past 7 days</span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={metrics.questions_per_day}
                margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis dataKey="date" stroke="#71717a" fontSize={11} />
                <YAxis stroke="#71717a" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#18181b",
                    borderColor: "#27272a",
                    fontSize: "12px",
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="count"
                  name="Questions"
                  stroke="#6366f1"
                  fill="#6366f1"
                  fillOpacity={0.2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Latency Percentiles (p50 / p95) Line Chart */}
        <div className="bg-[#111113] border border-[#27272a] rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Latency Percentiles (ms)</h3>
            <span className="text-[11px] text-zinc-400">p50 vs p95 response time</span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={metrics.latency_p50_p95}
                margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis dataKey="date" stroke="#71717a" fontSize={11} />
                <YAxis stroke="#71717a" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#18181b",
                    borderColor: "#27272a",
                    fontSize: "12px",
                  }}
                />
                <Legend wrapperStyle={{ fontSize: "11px" }} />
                <Line
                  type="monotone"
                  dataKey="p50"
                  name="p50 Latency (ms)"
                  stroke="#38bdf8"
                  strokeWidth={2}
                />
                <Line
                  type="monotone"
                  dataKey="p95"
                  name="p95 Latency (ms)"
                  stroke="#f43f5e"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Confidence Score Distribution Histogram (10 bins) */}
        <div className="bg-[#111113] border border-[#27272a] rounded-xl p-5 space-y-4 lg:col-span-2">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-white">
                Live Confidence Distribution (10 Bins)
              </h3>
              <p className="text-xs text-zinc-400">
                Calibrated confidence histogram across live user chat responses.
              </p>
            </div>
            <BarChart2 className="w-4 h-4 text-zinc-500" />
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={metrics.confidence_distribution}
                margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis dataKey="range" stroke="#71717a" fontSize={11} />
                <YAxis stroke="#71717a" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#18181b",
                    borderColor: "#27272a",
                    fontSize: "12px",
                  }}
                />
                <Bar dataKey="count" name="Queries in Bin" fill="#10b981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};
