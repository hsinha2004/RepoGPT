import React, { useState } from "react";
import { useParams, Link, useNavigate } from "react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../../api/client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";
import { toast } from "sonner";
import {
  Layers,
  RefreshCw,
  Code2,
  Boxes,
  Compass,
  ShieldCheck,
  ExternalLink,
  BookOpen,
  Terminal,
  Calendar,
  X,
  FileText,
  Sparkles,
  ArrowRight,
} from "lucide-react";

interface OverviewSourceItem {
  id: string;
  path: string;
  start_line: number;
  end_line: number;
  symbol?: string | null;
  snippet?: string;
}

interface TechStackItem {
  name: string;
  category: string;
  evidence?: string;
}

interface EntryPointItem {
  path: string;
  kind: string;
  description: string;
  line: number;
}

interface ReadingOrderItem {
  step: number;
  path: string;
  category: string;
  reason: string;
}

interface OverviewData {
  repo_id: string;
  commit_sha?: string;
  markdown: string;
  suggested_questions: string[];
  tech_stack: TechStackItem[];
  entry_points: EntryPointItem[];
  reading_order: ReadingOrderItem[];
  sources: OverviewSourceItem[];
  updated_at?: string;
}

interface RepoDetails {
  id: string;
  display_name?: string;
  commit_sha?: string;
  source?: {
    type?: string;
    url?: string;
    ref?: string;
  };
  stats?: {
    loc?: number;
    files_indexed?: number;
    symbols?: number;
    chunks?: number;
    redactions?: number;
    languages?: Record<string, number>;
  };
}

interface RepoStats {
  total_files: number;
  total_loc: number;
  total_symbols: number;
  total_chunks: number;
  total_redactions: number;
  languages: Record<string, number>;
  file_counts_by_kind: Record<string, number>;
}

const LANGUAGE_COLORS: Record<string, string> = {
  python: "#3572A5",
  typescript: "#3178C6",
  javascript: "#F7DF1E",
  go: "#00ADD8",
  java: "#B07219",
  rust: "#DEA584",
  cpp: "#F34B7D",
  c: "#555555",
  csharp: "#178600",
  ruby: "#701516",
  php: "#4F5D95",
  markdown: "#083fa1",
  json: "#292929",
  yaml: "#cb171e",
  html: "#e34c26",
  dockerfile: "#384d54",
  generic: "#71717a",
  text: "#52525b",
};

export const OverviewPage: React.FC = () => {
  const { repoId } = useParams<{ repoId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [activeSource, setActiveSource] = useState<OverviewSourceItem | null>(null);

  // 1. Fetch Repository Details
  const { data: repo, isLoading: repoLoading } = useQuery<RepoDetails>({
    queryKey: ["repo", repoId],
    queryFn: async () => {
      const res = await apiClient.GET("/api/v1/repos/{repo_id}", {
        params: { path: { repo_id: repoId! } },
      });
      if (res.error) throw new Error("Failed to load repository");
      return res.data as unknown as RepoDetails;
    },
    enabled: !!repoId,
  });

  // 2. Fetch Overview Data
  const {
    data: overview,
    isLoading: overviewLoading,
    isRefetching: overviewRefetching,
  } = useQuery<OverviewData>({
    queryKey: ["repo-overview", repoId],
    queryFn: async () => {
      const res = await apiClient.GET("/api/v1/repos/{repo_id}/overview", {
        params: { path: { repo_id: repoId! } },
      });
      if (res.error) throw new Error("Failed to load overview");
      return res.data as unknown as OverviewData;
    },
    enabled: !!repoId,
  });

  // 3. Fetch Stats Data
  const { data: stats } = useQuery<RepoStats>({
    queryKey: ["repo-stats", repoId],
    queryFn: async () => {
      const res = await apiClient.GET("/api/v1/repos/{repo_id}/stats", {
        params: { path: { repo_id: repoId! } },
      });
      if (res.error) throw new Error("Failed to load repo stats");
      return res.data as unknown as RepoStats;
    },
    enabled: !!repoId,
  });

  // 4. Regenerate Mutation
  const regenerateMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.POST("/api/v1/repos/{repo_id}/overview/regenerate", {
        params: { path: { repo_id: repoId! } },
      });
      if (res.error) throw new Error("Regeneration failed");
      return res.data;
    },
    onSuccess: () => {
      toast.success("Overview regenerated successfully");
      queryClient.invalidateQueries({ queryKey: ["repo-overview", repoId] });
    },
    onError: (err) => {
      toast.error(`Regeneration error: ${err.message}`);
    },
  });

  if (repoLoading || overviewLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[450px] text-center">
        <RefreshCw className="size-7 text-emerald-400 animate-spin mb-3" />
        <h3 className="text-base font-medium text-white text-balance">Synthesizing Architecture Overview...</h3>
        <p className="text-xs text-[#71717a] max-w-sm mt-1 text-pretty">
          Extracting AST symbols, mapping dependencies, and generating verified reading paths.
        </p>
      </div>
    );
  }

  // Calculate languages breakdown percentages
  const languagesMap: Record<string, number> = stats?.languages || repo?.stats?.languages || {};
  const totalLangLoc = Object.values(languagesMap).reduce((a: number, b: number) => a + b, 0) || 1;
  const sortedLangs = Object.entries(languagesMap)
    .sort(([, a], [, b]) => (b as number) - (a as number))
    .map(([name, loc]) => ({
      name,
      loc: loc as number,
      pct: (((loc as number) / totalLangLoc) * 100).toFixed(1),
      color: LANGUAGE_COLORS[name.toLowerCase()] || "#10b981",
    }));

  // Group tech stack by category
  const techStack = overview?.tech_stack || [];
  const techByCategory: Record<string, TechStackItem[]> = {};
  for (const item of techStack) {
    const cat = item.category.toLowerCase();
    if (!techByCategory[cat]) techByCategory[cat] = [];
    techByCategory[cat].push(item);
  }

  // Sources map for citation lookup
  const sourcesMap = new Map<string, OverviewSourceItem>();
  if (overview?.sources) {
    for (const src of overview.sources) {
      sourcesMap.set(src.id, src);
    }
  }

  const renderCitationPill = (citationId: string) => {
    const src = sourcesMap.get(citationId);
    return (
      <button
        key={citationId}
        type="button"
        onClick={() => src && setActiveSource(src)}
        aria-label={`View citation source ${citationId}`}
        className="inline-flex items-center px-1.5 py-0.5 mx-1 my-0.5 rounded text-[11px] font-mono font-medium bg-[#1e1e24] text-emerald-300 border border-[#27272a] hover:border-emerald-500/60 hover:text-white transition-colors cursor-pointer"
        title={src ? `${src.path}:${src.start_line}-${src.end_line}` : citationId}
      >
        [{citationId}]
      </button>
    );
  };

  const totalFiles = stats?.total_files ?? repo?.stats?.files_indexed ?? 0;
  const totalLoc = stats?.total_loc ?? repo?.stats?.loc ?? 0;
  const totalSymbols = stats?.total_symbols ?? repo?.stats?.symbols ?? 0;
  const totalChunks = stats?.total_chunks ?? repo?.stats?.chunks ?? 0;
  const totalRedactions = stats?.total_redactions ?? repo?.stats?.redactions ?? 0;

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-16">
      {/* Surface Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-[#27272a]/60">
        <div className="flex items-center gap-3">
          <div className="size-9 rounded-lg bg-[#18181b] border border-[#27272a] flex items-center justify-center text-emerald-400">
            <Layers className="size-4" />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-lg font-semibold text-white text-balance">
                {repo?.display_name || "Repository Overview"}
              </h1>
              {overview?.commit_sha && (
                <span className="px-2 py-0.5 rounded font-mono text-[11px] tabular-nums bg-[#18181b] text-[#a1a1aa] border border-[#27272a]">
                  @{overview.commit_sha.slice(0, 7)}
                </span>
              )}
            </div>
            <p className="text-xs text-[#71717a] mt-0.5 text-pretty">
              Architectural tour, entry points, technology stack, and recommended onboarding reading order
            </p>
          </div>
        </div>

        {/* Header Action Button */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => regenerateMutation.mutate()}
            disabled={regenerateMutation.isPending || overviewRefetching}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium bg-[#18181b] border border-[#27272a] text-[#a1a1aa] hover:text-white hover:border-[#3f3f46] disabled:opacity-50 transition-colors cursor-pointer shadow-xs"
          >
            <RefreshCw
              className={`size-3.5 ${
                regenerateMutation.isPending || overviewRefetching ? "animate-spin text-emerald-400" : ""
              }`}
            />
            <span>Regenerate Summary</span>
          </button>
        </div>
      </div>

      {/* Architecture Metrics Rail */}
      <div className="rounded-xl bg-[#0f0f12] border border-[#27272a] p-4 divide-y divide-[#1e1e24] sm:divide-y-0 sm:divide-x sm:divide-[#1e1e24] grid grid-cols-2 sm:grid-cols-5 gap-3 sm:gap-0">
        <div className="px-3 sm:px-4 py-1.5">
          <span className="text-[11px] text-[#71717a] block font-medium">Indexed Files</span>
          <span className="text-base font-semibold font-mono text-white tabular-nums block mt-0.5">
            {totalFiles}
          </span>
          <span className="text-[10px] text-[#52525b] block font-mono tabular-nums">
            {stats?.file_counts_by_kind?.code ?? totalFiles} code, {stats?.file_counts_by_kind?.doc ?? 0} docs
          </span>
        </div>

        <div className="px-3 sm:px-4 py-1.5">
          <span className="text-[11px] text-[#71717a] block font-medium">Total Lines</span>
          <span className="text-base font-semibold font-mono text-white tabular-nums block mt-0.5">
            {totalLoc.toLocaleString()}
          </span>
          <span className="text-[10px] text-[#52525b] block">across repository</span>
        </div>

        <div className="px-3 sm:px-4 py-1.5">
          <span className="text-[11px] text-[#71717a] block font-medium">AST Symbols</span>
          <span className="text-base font-semibold font-mono text-emerald-400 tabular-nums block mt-0.5">
            {totalSymbols}
          </span>
          <span className="text-[10px] text-[#52525b] block">functions &amp; classes</span>
        </div>

        <div className="px-3 sm:px-4 py-1.5">
          <span className="text-[11px] text-[#71717a] block font-medium">Semantic Chunks</span>
          <span className="text-base font-semibold font-mono text-white tabular-nums block mt-0.5">
            {totalChunks}
          </span>
          <span className="text-[10px] text-[#52525b] block">indexed for retrieval</span>
        </div>

        <div className="px-3 sm:px-4 py-1.5">
          <span className="text-[11px] text-[#71717a] block font-medium">Secret Redaction</span>
          <span className="text-base font-semibold font-mono text-emerald-400 tabular-nums block mt-0.5 flex items-center gap-1.5">
            <ShieldCheck className="size-3.5 shrink-0" />
            <span>{totalRedactions === 0 ? "Clean" : `${totalRedactions} redacted`}</span>
          </span>
          <span className="text-[10px] text-[#52525b] block">zero secrets exposed</span>
        </div>
      </div>

      {/* Language Proportion Bar */}
      {sortedLangs.length > 0 && (
        <div className="p-3.5 rounded-xl bg-[#0f0f12] border border-[#27272a] space-y-2.5">
          <div className="flex items-center justify-between text-xs text-[#a1a1aa]">
            <span className="flex items-center gap-1.5 font-medium text-white">
              <Code2 className="size-3.5 text-emerald-400" />
              <span>Language Distribution</span>
            </span>
            <span className="font-mono text-[11px] text-[#71717a] tabular-nums">
              {totalLoc.toLocaleString()} LOC
            </span>
          </div>

          <div className="h-2 w-full bg-[#18181b] rounded-full overflow-hidden flex">
            {sortedLangs.map((lang) => (
              <div
                key={lang.name}
                style={{ width: `${lang.pct}%`, backgroundColor: lang.color }}
                className="h-full transition-all"
                title={`${lang.name}: ${lang.pct}% (${lang.loc.toLocaleString()} LOC)`}
              />
            ))}
          </div>

          <div className="flex flex-wrap gap-3 pt-0.5">
            {sortedLangs.map((lang) => (
              <div key={lang.name} className="flex items-center gap-1.5 text-xs">
                <span
                  className="size-2 rounded-full shrink-0"
                  style={{ backgroundColor: lang.color }}
                />
                <span className="text-[#e4e4e7] font-medium">{lang.name}</span>
                <span className="text-[#71717a] font-mono text-[11px] tabular-nums">{lang.pct}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Suggested Inquiries Prompt Ribbon */}
      {overview?.suggested_questions && overview.suggested_questions.length > 0 && (
        <div className="p-3.5 rounded-xl bg-[#111113] border border-[#27272a] space-y-2">
          <div className="flex items-center gap-1.5 text-xs font-medium text-white">
            <Sparkles className="size-3.5 text-emerald-400" />
            <span>Explore with Agentic QA</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {overview.suggested_questions.map((question, i) => (
              <button
                key={i}
                type="button"
                onClick={() =>
                  navigate(
                    `/app/repos/${repoId}/chat?prompt=${encodeURIComponent(question)}`
                  )
                }
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#18181b] border border-[#27272a] text-xs text-[#d4d4d8] hover:text-white hover:border-emerald-500/60 hover:bg-[#1e1e24] transition-colors cursor-pointer text-left group"
              >
                <span>{question}</span>
                <ArrowRight className="size-3 text-[#71717a] group-hover:text-emerald-400 shrink-0 transition-transform group-hover:translate-x-0.5" />
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Main Architectural Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols): Markdown Architecture & Reading Roadmap */}
        <div className="lg:col-span-2 space-y-6">
          {/* Architecture Tour */}
          <div className="p-6 rounded-xl bg-[#0f0f12] border border-[#27272a] space-y-4">
            <div className="flex items-center justify-between border-b border-[#27272a]/80 pb-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-white text-balance">
                <BookOpen className="size-4 text-emerald-400" />
                <span>Architecture &amp; System Tour</span>
              </div>
              {overview?.updated_at && (
                <div className="flex items-center gap-1.5 text-[11px] text-[#71717a] font-mono tabular-nums">
                  <Calendar className="size-3" />
                  <span>{new Date(overview.updated_at).toLocaleDateString()}</span>
                </div>
              )}
            </div>

            {/* Markdown Text Body */}
            <div className="prose prose-invert prose-sm max-w-none prose-headings:font-semibold prose-headings:text-white prose-p:text-[#d4d4d8] prose-p:leading-relaxed prose-p:text-pretty prose-code:font-mono prose-code:text-emerald-300 prose-code:bg-[#18181b] prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:border prose-code:border-[#27272a] prose-li:text-[#d4d4d8] prose-strong:text-white">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeSanitize]}
                components={{
                  p({ children }) {
                    return (
                      <p className="mb-4 text-pretty">
                        {React.Children.map(children, (child) => {
                          if (typeof child === "string") {
                            const parts = child.split(/(\[S\d+\])/g);
                            return parts.map((part) => {
                              const match = part.match(/^\[(S\d+)\]$/);
                              if (match) {
                                return renderCitationPill(match[1]);
                              }
                              return part;
                            });
                          }
                          return child;
                        })}
                      </p>
                    );
                  },
                  li({ children }) {
                    return (
                      <li className="mb-1 text-pretty">
                        {React.Children.map(children, (child) => {
                          if (typeof child === "string") {
                            const parts = child.split(/(\[S\d+\])/g);
                            return parts.map((part) => {
                              const match = part.match(/^\[(S\d+)\]$/);
                              if (match) {
                                return renderCitationPill(match[1]);
                              }
                              return part;
                            });
                          }
                          return child;
                        })}
                      </li>
                    );
                  },
                }}
              >
                {overview?.markdown || "No architectural summary generated yet."}
              </ReactMarkdown>
            </div>
          </div>

          {/* Sequential Reading Roadmap */}
          {overview?.reading_order && overview.reading_order.length > 0 && (
            <div className="p-6 rounded-xl bg-[#0f0f12] border border-[#27272a] space-y-4">
              <div className="flex items-center justify-between border-b border-[#27272a]/80 pb-3">
                <div className="flex items-center gap-2 text-sm font-semibold text-white text-balance">
                  <Compass className="size-4 text-emerald-400" />
                  <span>Onboarding Reading Order</span>
                </div>
                <span className="text-[11px] text-[#71717a] font-mono tabular-nums">
                  {overview.reading_order.length} sequential milestones
                </span>
              </div>

              <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-px before:bg-[#27272a]">
                {overview.reading_order.map((step) => (
                  <div key={step.step} className="relative group">
                    {/* Node Dot */}
                    <div className="absolute -left-6 top-1 size-5 rounded-full bg-[#18181b] border border-[#3f3f46] text-emerald-300 flex items-center justify-center text-[10px] font-mono font-bold group-hover:border-emerald-500 group-hover:text-white transition-colors tabular-nums">
                      {step.step}
                    </div>

                    <div className="p-3 rounded-lg bg-[#111113] border border-[#27272a] hover:border-[#3f3f46] transition-colors">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Link
                          to={`/app/repos/${repoId}/explorer?file=${encodeURIComponent(step.path)}`}
                          className="font-mono text-xs font-semibold text-white hover:text-emerald-400 transition-colors flex items-center gap-1 truncate"
                        >
                          <span>{step.path}</span>
                          <ExternalLink className="size-3 shrink-0 opacity-50" />
                        </Link>
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-[#18181b] text-[#a1a1aa] border border-[#27272a]">
                          {step.category.replace("_", " ")}
                        </span>
                      </div>
                      <p className="text-xs text-[#71717a] mt-1 leading-relaxed text-pretty">
                        {step.reason}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column (1 Col): Technology Stack & Entry Points */}
        <div className="space-y-6">
          {/* Tech Stack */}
          <div className="p-5 rounded-xl bg-[#0f0f12] border border-[#27272a] space-y-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-white border-b border-[#27272a]/80 pb-3 text-balance">
              <Boxes className="size-4 text-emerald-400" />
              <span>Technology Stack</span>
            </div>

            {Object.keys(techByCategory).length === 0 ? (
              <p className="text-xs text-[#71717a] text-pretty">No technology stack detected.</p>
            ) : (
              <div className="space-y-3.5">
                {Object.entries(techByCategory).map(([cat, items]) => (
                  <div key={cat} className="space-y-1.5">
                    <span className="text-[10px] text-[#71717a] font-semibold block font-mono">
                      {cat}
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {items.map((tech) => (
                        <div
                          key={tech.name}
                          className="px-2 py-1 rounded-md bg-[#18181b] border border-[#27272a] text-xs text-[#e4e4e7] flex items-center gap-1.5"
                          title={tech.evidence ? `Evidence: ${tech.evidence}` : tech.name}
                        >
                          <span className="size-1.5 rounded-full bg-emerald-500" />
                          <span>{tech.name}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Application Entry Points */}
          <div className="p-5 rounded-xl bg-[#0f0f12] border border-[#27272a] space-y-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-white border-b border-[#27272a]/80 pb-3 text-balance">
              <Terminal className="size-4 text-teal-400" />
              <span>Application Entry Points</span>
            </div>

            {!overview?.entry_points || overview.entry_points.length === 0 ? (
              <p className="text-xs text-[#71717a] text-pretty">No explicit entry points identified.</p>
            ) : (
              <div className="space-y-2.5">
                {overview.entry_points.map((ep, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-[#111113] border border-[#27272a] space-y-1.5 hover:border-[#3f3f46] transition-colors"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <Link
                        to={`/app/repos/${repoId}/explorer?file=${encodeURIComponent(ep.path)}#L${ep.line}`}
                        className="font-mono text-xs font-semibold text-white hover:text-emerald-400 transition-colors truncate flex items-center gap-1"
                      >
                        <span className="truncate">{ep.path}</span>
                        <span className="text-[10px] text-[#71717a] tabular-nums">:{ep.line}</span>
                        <ExternalLink className="size-3 shrink-0 opacity-50" />
                      </Link>
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-[#18181b] border border-[#27272a] text-emerald-300 shrink-0">
                        {ep.kind.replace("_", " ")}
                      </span>
                    </div>
                    <p className="text-[11px] text-[#71717a] leading-relaxed text-pretty">
                      {ep.description}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Interactive Citation Snippet Drawer Modal */}
      {activeSource && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="relative w-full max-w-2xl bg-[#111113] border border-[#27272a] rounded-xl shadow-2xl p-5 text-white animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-start justify-between pb-3 border-b border-[#27272a]">
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                    [{activeSource.id}]
                  </span>
                  <span className="font-mono text-sm font-medium text-white">
                    {activeSource.path}
                  </span>
                </div>
                <span className="text-xs text-[#71717a] font-mono block mt-1 tabular-nums">
                  Lines {activeSource.start_line}–{activeSource.end_line}
                  {activeSource.symbol ? ` · Symbol: ${activeSource.symbol}` : ""}
                </span>
              </div>
              <button
                onClick={() => setActiveSource(null)}
                aria-label="Close citation details"
                className="text-[#71717a] hover:text-white transition-colors p-1 rounded-md"
              >
                <X className="size-5" />
              </button>
            </div>

            <div className="my-4 max-h-[350px] overflow-y-auto rounded-lg bg-[#09090b] border border-[#27272a] p-3">
              {activeSource.snippet ? (
                <pre className="font-mono text-xs text-[#d4d4d8] leading-relaxed whitespace-pre-wrap">
                  {activeSource.snippet}
                </pre>
              ) : (
                <p className="text-xs text-[#71717a] italic">
                  Snippet content mapped from AST symbol table.
                </p>
              )}
            </div>

            <div className="flex items-center justify-between pt-2">
              <Link
                to={`/app/repos/${repoId}/explorer?file=${encodeURIComponent(activeSource.path)}#L${activeSource.start_line}`}
                onClick={() => setActiveSource(null)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-600 text-white hover:bg-emerald-500 transition-colors shadow-xs"
              >
                <FileText className="size-3.5" />
                <span>Open in Explorer</span>
              </Link>
              <button
                onClick={() => setActiveSource(null)}
                className="px-3 py-1.5 rounded-lg text-xs font-medium bg-[#18181b] border border-[#27272a] text-[#a1a1aa] hover:text-white transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
