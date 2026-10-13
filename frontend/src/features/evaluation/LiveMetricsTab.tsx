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
      <div className="py-24 text-center text-zinc-500">Loading live chat telemetry...</div>
    );
  }

  const satisfactionRatio = metrics.satisfaction_gauge.ratio;
  const satisfactionPct = Number((satisfactionRatio * 100).toFixed(1));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-zinc-200">
        <div>
          <h2 className="text-base font-semibold text-zinc-900 flex items-center gap-2 text-balance">
            <Activity className="size-4 text-emerald-600" />
            Live Chat Telemetry & Production Monitoring
          </h2>
          <p className="text-xs text-zinc-500 text-pretty">
            Real-time evaluation signals collected from user chat sessions over the past 7 days (§14.4).
          </p>
        </div>

        <button
          onClick={fetchLiveMetrics}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-zinc-50 border border-zinc-200 rounded-lg text-xs font-medium text-zinc-700 transition-colors cursor-pointer shadow-xs"
        >
          <RefreshCw className="size-3.5" />
          Refresh Telemetry
        </button>
      </div>

      {/* Top Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-zinc-200 rounded-xl p-4 shadow-xs">
          <div className="flex items-center justify-between text-zinc-500 text-xs">
            <span className="font-mono uppercase">User Satisfaction</span>
            <ThumbsUp className="size-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-zinc-900 mt-2 tabular-nums">
            {satisfactionPct}% Positive
          </div>
          <div className="text-[11px] text-zinc-500 mt-1 tabular-nums">
            {metrics.satisfaction_gauge.positive_ratings} 👍 /{" "}
            {metrics.satisfaction_gauge.negative_ratings} 👎 ratings
          </div>
        </div>

        <div className="bg-white border border-zinc-200 rounded-xl p-4 shadow-xs">
          <div className="flex items-center justify-between text-zinc-500 text-xs">
            <span className="font-mono uppercase">Total Queries (7d)</span>
            <TrendingUp className="size-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-zinc-900 mt-2 tabular-nums">
            {metrics.questions_per_day.reduce((acc, cur) => acc + cur.count, 0)}
          </div>
          <div className="text-[11px] text-zinc-500 mt-1 tabular-nums">
            Avg ~
            {(
              metrics.questions_per_day.reduce((acc, cur) => acc + cur.count, 0) / 7
            ).toFixed(0)}{" "}
            questions/day
          </div>
        </div>

        <div className="bg-white border border-zinc-200 rounded-xl p-4 shadow-xs">
          <div className="flex items-center justify-between text-zinc-500 text-xs">
            <span className="font-mono uppercase">Total LLM Tokens</span>
            <Cpu className="size-4 text-amber-600" />
          </div>
          <div className="text-2xl font-bold text-zinc-900 mt-2 tabular-nums">
            {metrics.tokens_and_cost
              .reduce((acc, cur) => acc + cur.tokens, 0)
              .toLocaleString()}
          </div>
          <div className="text-[11px] text-zinc-500 mt-1">Across all user queries</div>
        </div>

        <div className="bg-white border border-zinc-200 rounded-xl p-4 shadow-xs">
          <div className="flex items-center justify-between text-zinc-500 text-xs">
            <span className="font-mono uppercase">Estimated Cost (7d)</span>
            <DollarSign className="size-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-emerald-600 mt-2 tabular-nums">
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
        <div className="bg-white border border-zinc-200 rounded-xl p-5 space-y-4 shadow-xs">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-zinc-900">Questions Per Day (Volume)</h3>
            <span className="text-[11px] text-zinc-500">Past 7 days</span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={metrics.questions_per_day}
                margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
                <XAxis dataKey="date" stroke="#71717a" fontSize={11} />
                <YAxis stroke="#71717a" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#ffffff",
                    borderColor: "#e4e4e7",
                    color: "#18181b",
                    fontSize: "12px",
                    boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="count"
                  name="Questions"
                  stroke="#10b981"
                  fill="#10b981"
                  fillOpacity={0.15}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Latency Percentiles (p50 / p95) Line Chart */}
        <div className="bg-white border border-zinc-200 rounded-xl p-5 space-y-4 shadow-xs">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-zinc-900">Latency Percentiles (ms)</h3>
            <span className="text-[11px] text-zinc-500">p50 vs p95 response time</span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={metrics.latency_p50_p95}
                margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
                <XAxis dataKey="date" stroke="#71717a" fontSize={11} />
                <YAxis stroke="#71717a" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#ffffff",
                    borderColor: "#e4e4e7",
                    color: "#18181b",
                    fontSize: "12px",
                    boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
                  }}
                />
                <Legend wrapperStyle={{ fontSize: "11px" }} />
                <Line
                  type="monotone"
                  dataKey="p50"
                  name="p50 Latency (ms)"
                  stroke="#0284c7"
                  strokeWidth={2}
                />
                <Line
                  type="monotone"
                  dataKey="p95"
                  name="p95 Latency (ms)"
                  stroke="#e11d48"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Confidence Score Distribution Histogram (10 bins) */}
        <div className="bg-white border border-zinc-200 rounded-xl p-5 space-y-4 lg:col-span-2 shadow-xs">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-zinc-900 text-balance">
                Live Confidence Distribution (10 Bins)
              </h3>
              <p className="text-xs text-zinc-500 text-pretty">
                Calibrated confidence histogram across live user chat responses.
              </p>
            </div>
            <BarChart2 className="size-4 text-zinc-400" />
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={metrics.confidence_distribution}
                margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
                <XAxis dataKey="range" stroke="#71717a" fontSize={11} />
                <YAxis stroke="#71717a" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#ffffff",
                    borderColor: "#e4e4e7",
                    color: "#18181b",
                    fontSize: "12px",
                    boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
                  }}
                />
                <Bar dataKey="count" name="Queries in Bin" fill="#059669" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};
