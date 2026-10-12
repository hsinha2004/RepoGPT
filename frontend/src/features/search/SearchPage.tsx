import React, { useState } from "react";
import { useParams, Link } from "react-router";
import { useMutation } from "@tanstack/react-query";
import { apiClient } from "../../api/client";
import {
  Search,
  Compass,
  FileCode,
  Clock,
  Sparkles,
  ExternalLink,
  Copy,
  Check,
  Code2,
  Filter,
} from "lucide-react";

type StrategyOption = "auto" | "keyword" | "vector" | "hybrid" | "hybrid_rerank";

interface RouteResultUI {
  intent: string;
  strategy: string;
  weights: { bm25: number; vector: number };
  enrich: { symbol_lookup: boolean; graph_expand: boolean; summary_scope: boolean };
  identifiers: string[];
  search_queries: string[];
  reason: string;
}

interface RetrievedChunkUI {
  chunk_id: string;
  repo_id: string;
  commit_sha: string;
  path: string;
  language: string;
  chunk_type: string;
  symbol_name?: string | null;
  symbol_kind?: string | null;
  parent_symbol?: string | null;
  start_line: number;
  end_line: number;
  part: number;
  parts: number;
  text: string;
  embed_text: string;
  token_count: number;
  score: number;
  ranks: {
    bm25?: number | null;
    vector?: number | null;
    symbol?: number | null;
    graph?: number | null;
  };
  rerank_score?: number | null;
}

interface SearchResponseUI {
  query: string;
  route: RouteResultUI;
  results: RetrievedChunkUI[];
  context: string;
  total_candidates: number;
  latency_ms: Record<string, number>;
}

const SAMPLE_QUERIES = [
  "Where is authentication implemented?",
  "AuthService.login",
  "How does a request flow from API to database?",
  "Tech stack and repository architecture",
  "How to configure environment variables and docker",
  "TaskService.create_task",
];

export const SearchPage: React.FC = () => {
  const { repoId } = useParams<{ repoId: string }>();

  const [query, setQuery] = useState("");
  const [strategy, setStrategy] = useState<StrategyOption>("auto");
  const [filePattern, setFilePattern] = useState("");
  const [language, setLanguage] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [activeTab, setActiveTab] = useState<"results" | "context">("results");
  const [copiedContext, setCopiedContext] = useState(false);

  // Search Mutation
  const searchMutation = useMutation({
    mutationFn: async () => {
      if (!repoId || !query.trim()) return null;
      const res = await apiClient.POST("/api/v1/repos/{repo_id}/search", {
        params: { path: { repo_id: repoId } },
        body: {
          query: query.trim(),
          strategy: strategy,
          top_k: 12,
          file_pattern: filePattern.trim() || undefined,
          language: language.trim() || undefined,
        },
      });
      if (res.error) {
        throw new Error("Search failed: " + JSON.stringify(res.error));
      }
      return res.data as SearchResponseUI;
    },
  });

  const handleSearch = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;
    searchMutation.mutate();
  };

  const handleSelectSample = (sample: string) => {
    setQuery(sample);
    setTimeout(() => {
      searchMutation.mutate();
    }, 0);
  };

  const handleCopyContext = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedContext(true);
    setTimeout(() => setCopiedContext(false), 2000);
  };

  const data = searchMutation.data;

  const getIntentBadgeColor = (intent: string) => {
    switch (intent) {
      case "locate":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
      case "explain":
        return "bg-blue-500/10 text-blue-400 border-blue-500/30";
      case "flow":
        return "bg-purple-500/10 text-purple-400 border-purple-500/30";
      case "architecture":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30";
      case "dependency":
        return "bg-indigo-500/10 text-indigo-400 border-indigo-500/30";
      case "config":
        return "bg-teal-500/10 text-teal-400 border-teal-500/30";
      case "general":
        return "bg-zinc-500/10 text-zinc-400 border-zinc-500/30";
      case "out_of_scope":
        return "bg-rose-500/10 text-rose-400 border-rose-500/30";
      default:
        return "bg-zinc-800 text-zinc-300 border-zinc-700";
    }
  };

  return (
    <div className="space-y-6 pb-12 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col gap-1 border-b border-[#27272a] pb-4">
        <div className="flex items-center gap-2 text-xs text-[#a1a1aa]">
          <Link to="/app" className="hover:text-white transition">
            Repositories
          </Link>
          <span>/</span>
          <span className="text-zinc-300 font-mono">{repoId}</span>
          <span>/</span>
          <span className="text-white font-medium">Search Playground</span>
        </div>
        <div className="flex items-center justify-between mt-2">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <Search className="h-6 w-6 text-purple-400" />
              Retrieval & Router Playground
            </h1>
            <p className="text-sm text-[#a1a1aa] mt-1">
              Test multi-index retrieval (BM25 keyword, vector similarity, symbol lookup, graph expansion) and router classification.
            </p>
          </div>
          <Link
            to={`/app/repos/${repoId}/explorer`}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#18181b] border border-[#27272a] text-xs font-medium text-zinc-300 hover:text-white hover:border-zinc-700 transition"
          >
            <Code2 className="h-4 w-4" />
            Open Code Explorer
          </Link>
        </div>
      </div>

      {/* Search Input Bar */}
      <div className="bg-[#18181b] border border-[#27272a] rounded-xl p-4 shadow-xl">
        <form onSubmit={handleSearch} className="space-y-3">
          <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center">
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-3 h-5 w-5 text-zinc-500" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Enter query or symbol name (e.g. 'Where is auth implemented?', 'AuthService.login')..."
                className="w-full pl-11 pr-4 py-2.5 rounded-lg bg-[#09090b] border border-[#27272a] text-white placeholder-zinc-500 text-sm focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition"
              />
            </div>

            {/* Strategy Picker */}
            <div className="flex items-center gap-2">
              <select
                value={strategy}
                onChange={(e) => setStrategy(e.target.value as StrategyOption)}
                className="px-3 py-2.5 rounded-lg bg-[#09090b] border border-[#27272a] text-zinc-200 text-sm focus:outline-none focus:border-purple-500 transition"
              >
                <option value="auto">Strategy: Auto (Router)</option>
                <option value="hybrid_rerank">Hybrid + Rerank</option>
                <option value="hybrid">Hybrid (RRF)</option>
                <option value="vector">Vector Only</option>
                <option value="keyword">Keyword (BM25)</option>
              </select>

              <button
                type="button"
                onClick={() => setShowFilters(!showFilters)}
                className={`p-2.5 rounded-lg border transition ${
                  showFilters
                    ? "bg-purple-950/40 border-purple-500/50 text-purple-300"
                    : "bg-[#09090b] border-[#27272a] text-zinc-400 hover:text-white"
                }`}
                title="Toggle Filters"
              >
                <Filter className="h-4 w-4" />
              </button>

              <button
                type="submit"
                disabled={searchMutation.isPending || !query.trim()}
                className="px-5 py-2.5 rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 text-white font-medium text-sm transition shadow-lg shadow-emerald-950/20 flex items-center gap-2"
              >
                {searchMutation.isPending ? (
                  <>
                    <div className="h-4 w-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                    Searching...
                  </>
                ) : (
                  <>
                    <Search className="h-4 w-4" />
                    Search
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Optional Filters */}
          {showFilters && (
            <div className="pt-3 border-t border-[#27272a] flex flex-wrap gap-4 items-center text-xs">
              <div className="flex items-center gap-2">
                <span className="text-zinc-400">File Pattern:</span>
                <input
                  type="text"
                  value={filePattern}
                  onChange={(e) => setFilePattern(e.target.value)}
                  placeholder="e.g. *.py, src/*"
                  className="px-2.5 py-1.5 rounded bg-[#09090b] border border-[#27272a] text-white text-xs placeholder-zinc-600 focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="flex items-center gap-2">
                <span className="text-zinc-400">Language:</span>
                <input
                  type="text"
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  placeholder="e.g. python, typescript"
                  className="px-2.5 py-1.5 rounded bg-[#09090b] border border-[#27272a] text-white text-xs placeholder-zinc-600 focus:outline-none focus:border-purple-500"
                />
              </div>

              {(filePattern || language) && (
                <button
                  type="button"
                  onClick={() => {
                    setFilePattern("");
                    setLanguage("");
                  }}
                  className="text-xs text-purple-400 hover:underline"
                >
                  Clear filters
                </button>
              )}
            </div>
          )}
        </form>

        {/* Sample Queries */}
        {!data && (
          <div className="mt-4 pt-3 border-t border-[#27272a]/70">
            <div className="flex items-center gap-1.5 text-xs text-zinc-500 mb-2">
              <Sparkles className="h-3.5 w-3.5 text-purple-400" />
              <span>Try sample queries:</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {SAMPLE_QUERIES.map((sq) => (
                <button
                  key={sq}
                  type="button"
                  onClick={() => handleSelectSample(sq)}
                  className="px-2.5 py-1 rounded-md bg-[#09090b] hover:bg-purple-950/30 border border-[#27272a] hover:border-purple-500/40 text-xs text-zinc-300 hover:text-purple-300 transition"
                >
                  {sq}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Error Banner */}
      {searchMutation.isError && (
        <div className="p-4 rounded-xl bg-red-950/30 border border-red-500/40 text-red-300 text-sm">
          Failed to perform search. Ensure the repository has been indexed.
        </div>
      )}

      {/* Results Section */}
      {data && (
        <div className="space-y-6">
          {/* Router Decision Banner */}
          <div className="bg-[#18181b] border border-[#27272a] rounded-xl p-5 shadow-lg space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#27272a] pb-3">
              <div className="flex items-center gap-2">
                <Compass className="h-5 w-5 text-purple-400" />
                <h3 className="text-sm font-semibold text-white">Router Decision & Telemetry</h3>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`px-2.5 py-0.5 rounded-full text-xs font-medium border uppercase tracking-wider ${getIntentBadgeColor(
                    data.route.intent
                  )}`}
                >
                  {data.route.intent}
                </span>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-950/40 text-purple-300 border border-purple-500/30">
                  {data.route.strategy}
                </span>
              </div>
            </div>

            <p className="text-sm text-zinc-300 italic">
              &ldquo;{data.route.reason}&rdquo;
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1 text-xs">
              {/* Identifiers */}
              <div className="space-y-1.5">
                <span className="text-zinc-500 font-medium">Extracted Identifiers:</span>
                <div className="flex flex-wrap gap-1.5">
                  {data.route.identifiers.length > 0 ? (
                    data.route.identifiers.map((ident) => (
                      <span
                        key={ident}
                        className="px-2 py-0.5 rounded bg-[#09090b] border border-purple-500/20 text-purple-300 font-mono text-[11px]"
                      >
                        {ident}
                      </span>
                    ))
                  ) : (
                    <span className="text-zinc-500 italic">None extracted</span>
                  )}
                </div>
              </div>

              {/* Enrichments & Weights */}
              <div className="space-y-1.5">
                <span className="text-zinc-500 font-medium">Enrichments & Weights:</span>
                <div className="flex flex-wrap gap-1.5 text-[11px]">
                  {data.route.enrich.symbol_lookup && (
                    <span className="px-1.5 py-0.5 rounded bg-emerald-950/40 border border-emerald-500/30 text-emerald-300">
                      Symbol Lookup
                    </span>
                  )}
                  {data.route.enrich.graph_expand && (
                    <span className="px-1.5 py-0.5 rounded bg-purple-950/40 border border-purple-500/30 text-purple-300">
                      Graph Expand
                    </span>
                  )}
                  {data.route.enrich.summary_scope && (
                    <span className="px-1.5 py-0.5 rounded bg-amber-950/40 border border-amber-500/30 text-amber-300">
                      Summary Scope
                    </span>
                  )}
                  <span className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400">
                    BM25: {Math.round(data.route.weights.bm25 * 100)}% / Vector:{" "}
                    {Math.round(data.route.weights.vector * 100)}%
                  </span>
                </div>
              </div>

              {/* Latency Telemetry */}
              <div className="space-y-1.5">
                <span className="text-zinc-500 font-medium flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5 text-zinc-400" />
                  Latency Breakdown:
                </span>
                <div className="flex flex-wrap gap-1.5 text-[11px] text-zinc-300 font-mono">
                  {Object.entries(data.latency_ms).map(([k, v]) => (
                    <span key={k} className="px-1.5 py-0.5 rounded bg-[#09090b] border border-[#27272a]">
                      {k}: {v}ms
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* View Mode Tabs */}
          <div className="flex items-center justify-between border-b border-[#27272a] pb-2">
            <div className="flex items-center gap-4">
              <button
                type="button"
                onClick={() => setActiveTab("results")}
                className={`pb-2 text-sm font-medium transition relative ${
                  activeTab === "results"
                    ? "text-white border-b-2 border-purple-500"
                    : "text-zinc-400 hover:text-white"
                }`}
              >
                Retrieved Chunks ({data.results.length})
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("context")}
                className={`pb-2 text-sm font-medium transition relative ${
                  activeTab === "context"
                    ? "text-white border-b-2 border-purple-500"
                    : "text-zinc-400 hover:text-white"
                }`}
              >
                Formatted LLM Context (XML)
              </button>
            </div>
            <span className="text-xs text-zinc-500">
              Total candidate pool: {data.total_candidates} chunks
            </span>
          </div>

          {/* Tab 1: Retrieved Chunks List */}
          {activeTab === "results" && (
            <div className="space-y-4">
              {data.results.length === 0 ? (
                <div className="p-12 text-center text-zinc-500 border border-dashed border-[#27272a] rounded-xl">
                  No matching chunks retrieved for this query.
                </div>
              ) : (
                data.results.map((chunk, idx) => (
                  <div
                    key={chunk.chunk_id}
                    className="bg-[#18181b] border border-[#27272a] hover:border-zinc-700 rounded-xl p-4 transition shadow-md space-y-3"
                  >
                    {/* Header */}
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded bg-purple-950/60 text-purple-300 font-mono text-xs font-semibold">
                          #{idx + 1}
                        </span>
                        <FileCode className="h-4 w-4 text-zinc-400" />
                        <span className="font-mono text-xs text-white font-medium">
                          {chunk.path}:{chunk.start_line}-{chunk.end_line}
                        </span>
                        {chunk.symbol_name && (
                          <span className="px-2 py-0.5 rounded bg-blue-950/40 border border-blue-500/30 text-blue-300 font-mono text-[11px]">
                            {chunk.symbol_name}
                            {chunk.symbol_kind ? ` (${chunk.symbol_kind})` : ""}
                          </span>
                        )}
                        <span className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 text-[10px] uppercase font-mono">
                          {chunk.chunk_type}
                        </span>
                      </div>

                      {/* Explorer Deep Link */}
                      <Link
                        to={`/app/repos/${repoId}/explorer?file=${encodeURIComponent(
                          chunk.path
                        )}#L${chunk.start_line}-L${chunk.end_line}`}
                        className="flex items-center gap-1 text-xs text-purple-400 hover:text-purple-300 transition"
                      >
                        <span>Open in Explorer</span>
                        <ExternalLink className="h-3 w-3" />
                      </Link>
                    </div>

                    {/* Rank pills & Scores */}
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      <span className="text-zinc-500 font-medium">Score:</span>
                      <span className="px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 font-mono font-medium">
                        {chunk.rerank_score !== null && chunk.rerank_score !== undefined
                          ? `Rerank: ${chunk.rerank_score.toFixed(4)}`
                          : `RRF: ${chunk.score.toFixed(4)}`}
                      </span>

                      {chunk.ranks.bm25 && (
                        <span className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300 font-mono text-[11px]">
                          BM25 #{chunk.ranks.bm25}
                        </span>
                      )}
                      {chunk.ranks.vector && (
                        <span className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300 font-mono text-[11px]">
                          Vector #{chunk.ranks.vector}
                        </span>
                      )}
                      {chunk.ranks.symbol && (
                        <span className="px-1.5 py-0.5 rounded bg-emerald-950/40 text-emerald-300 font-mono text-[11px]">
                          Symbol #{chunk.ranks.symbol}
                        </span>
                      )}
                      {chunk.ranks.graph && (
                        <span className="px-1.5 py-0.5 rounded bg-indigo-950/40 text-indigo-300 font-mono text-[11px]">
                          Graph #{chunk.ranks.graph}
                        </span>
                      )}
                    </div>

                    {/* Code Snippet with line numbers */}
                    <div className="bg-[#09090b] border border-[#27272a] rounded-lg p-3 font-mono text-xs overflow-x-auto max-h-60 leading-relaxed text-zinc-300">
                      <pre>
                        {chunk.text.split("\n").map((line, lIdx) => {
                          const lineNum = chunk.start_line + lIdx;
                          return (
                            <div key={lIdx} className="table-row">
                              <span className="table-cell pr-4 text-zinc-600 select-none text-right">
                                {lineNum}
                              </span>
                              <span className="table-cell">{line}</span>
                            </div>
                          );
                        })}
                      </pre>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Tab 2: Formatted XML Context */}
          {activeTab === "context" && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-zinc-400">
                  Exact context packed with original line numbers for LLM prompts:
                </span>
                <button
                  type="button"
                  onClick={() => handleCopyContext(data.context)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#18181b] border border-[#27272a] hover:border-zinc-700 text-xs text-zinc-300 hover:text-white transition"
                >
                  {copiedContext ? (
                    <>
                      <Check className="h-3.5 w-3.5 text-emerald-400" />
                      <span>Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5" />
                      <span>Copy Context</span>
                    </>
                  )}
                </button>
              </div>

              <div className="bg-[#09090b] border border-[#27272a] rounded-xl p-4 font-mono text-xs text-zinc-300 overflow-x-auto max-h-[600px] whitespace-pre">
                {data.context}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
