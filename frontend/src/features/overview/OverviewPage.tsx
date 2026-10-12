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
  Sparkles,
  RefreshCw,
  FileCode,
  Code2,
  Boxes,
  Compass,
  ShieldCheck,
  HelpCircle,
  ExternalLink,
  BookOpen,
  Terminal,
  Calendar,
  X,
  FileText,
  MessageSquare,
  Network,
  GitPullRequest,
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
      <div className="flex flex-col items-center justify-center min-h-[500px] text-center">
        <RefreshCw className="w-8 h-8 text-[#6366f1] animate-spin mb-4" />
        <h3 className="text-lg font-semibold text-white">Analyzing Codebase Architecture...</h3>
        <p className="text-sm text-[#71717a] max-w-sm mt-1">
          Generating dependency graphs, identifying entry points, and summarizing system architecture.
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
      color: LANGUAGE_COLORS[name.toLowerCase()] || "#6366f1",
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
        className="inline-flex items-center px-1.5 py-0.5 mx-1 my-0.5 rounded text-[11px] font-mono font-medium bg-[#6366f1]/20 text-[#a5b4fc] border border-[#6366f1]/40 hover:bg-[#6366f1]/30 hover:border-[#6366f1] transition-all cursor-pointer"
        title={src ? `${src.path}:${src.start_line}-${src.end_line}` : citationId}
      >
        [{citationId}]
      </button>
    );
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16">
      {/* Sub-navigation bar between repository features */}
      <div className="flex items-center justify-between border-b border-[#27272a] pb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#6366f1]/15 border border-[#6366f1]/30 flex items-center justify-center text-[#818cf8]">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-white">
                {repo?.display_name || "Repository"}
              </h1>
              {overview?.commit_sha && (
                <span className="px-2 py-0.5 rounded font-mono text-[11px] bg-[#27272a] text-[#a1a1aa] border border-[#3f3f46]">
                  @{overview.commit_sha.slice(0, 7)}
                </span>
              )}
            </div>
            <p className="text-xs text-[#71717a]">
              Architectural summary, key dependencies, and onboarding reading guide
            </p>
          </div>
        </div>

        {/* Feature quick links & regenerate */}
        <div className="flex items-center gap-2">
          <Link
            to={`/app/repos/${repoId}/chat`}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[#18181b] border border-[#27272a] text-[#a1a1aa] hover:text-white hover:border-[#6366f1]/50 transition-colors"
          >
            <MessageSquare className="w-3.5 h-3.5 text-[#818cf8]" />
            <span>Chat</span>
          </Link>
          <Link
            to={`/app/repos/${repoId}/explorer`}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[#18181b] border border-[#27272a] text-[#a1a1aa] hover:text-white hover:border-[#6366f1]/50 transition-colors"
          >
            <FileCode className="w-3.5 h-3.5 text-[#10b981]" />
            <span>Explorer</span>
          </Link>
          <Link
            to={`/app/repos/${repoId}/graph`}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[#18181b] border border-[#27272a] text-[#a1a1aa] hover:text-white hover:border-[#6366f1]/50 transition-colors"
          >
            <Network className="w-3.5 h-3.5 text-[#f59e0b]" />
            <span>Graph</span>
          </Link>
          <Link
            to={`/app/repos/${repoId}/reviews`}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[#18181b] border border-[#27272a] text-[#a1a1aa] hover:text-white hover:border-[#6366f1]/50 transition-colors"
          >
            <GitPullRequest className="w-3.5 h-3.5 text-[#ec4899]" />
            <span>Reviews</span>
          </Link>

          <button
            onClick={() => regenerateMutation.mutate()}
            disabled={regenerateMutation.isPending || overviewRefetching}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[#6366f1] text-white hover:bg-[#4f46e5] disabled:opacity-50 transition-all shadow-sm cursor-pointer"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 ${
                regenerateMutation.isPending || overviewRefetching ? "animate-spin" : ""
              }`}
            />
            <span>Regenerate</span>
          </button>
        </div>
      </div>

      {/* Language Breakdown Bar */}
      {sortedLangs.length > 0 && (
        <div className="p-4 rounded-xl bg-[#111113] border border-[#27272a] space-y-3">
          <div className="flex items-center justify-between text-xs font-medium text-[#a1a1aa]">
            <span className="flex items-center gap-1.5">
              <Code2 className="w-4 h-4 text-[#818cf8]" />
              Languages Breakdown
            </span>
            <span className="font-mono text-[11px] text-[#71717a]">
              {(stats?.total_loc || repo?.stats?.loc || 0).toLocaleString()} Total Lines
            </span>
          </div>

          {/* Bar segments */}
          <div className="h-2.5 w-full bg-[#18181b] rounded-full overflow-hidden flex">
            {sortedLangs.map((lang) => (
              <div
                key={lang.name}
                style={{ width: `${lang.pct}%`, backgroundColor: lang.color }}
                className="h-full first:rounded-l-full last:rounded-r-full transition-all"
                title={`${lang.name}: ${lang.pct}% (${lang.loc.toLocaleString()} LOC)`}
              />
            ))}
          </div>

          {/* Legend */}
          <div className="flex flex-wrap gap-4 pt-1">
            {sortedLangs.map((lang) => (
              <div key={lang.name} className="flex items-center gap-1.5 text-xs">
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: lang.color }}
                />
                <span className="text-white font-medium">{lang.name}</span>
                <span className="text-[#71717a] font-mono text-[11px]">{lang.pct}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick Stats Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <div className="p-4 rounded-xl bg-[#111113] border border-[#27272a]">
          <span className="text-xs text-[#71717a] block">Indexed Files</span>
          <span className="text-xl font-bold font-mono text-white mt-1 block">
            {stats?.total_files ?? repo?.stats?.files_indexed ?? 0}
          </span>
          <span className="text-[11px] text-[#52525b] mt-1 block">
            {stats?.file_counts_by_kind?.code ?? 0} code, {stats?.file_counts_by_kind?.doc ?? 0} docs
          </span>
        </div>

        <div className="p-4 rounded-xl bg-[#111113] border border-[#27272a]">
          <span className="text-xs text-[#71717a] block">Total LOC</span>
          <span className="text-xl font-bold font-mono text-white mt-1 block">
            {(stats?.total_loc ?? repo?.stats?.loc ?? 0).toLocaleString()}
          </span>
          <span className="text-[11px] text-[#52525b] mt-1 block">across codebase</span>
        </div>

        <div className="p-4 rounded-xl bg-[#111113] border border-[#27272a]">
          <span className="text-xs text-[#71717a] block">AST Symbols</span>
          <span className="text-xl font-bold font-mono text-[#818cf8] mt-1 block">
            {(stats?.total_symbols ?? repo?.stats?.symbols ?? 0).toLocaleString()}
          </span>
          <span className="text-[11px] text-[#52525b] mt-1 block">functions &amp; classes</span>
        </div>

        <div className="p-4 rounded-xl bg-[#111113] border border-[#27272a]">
          <span className="text-xs text-[#71717a] block">Semantic Chunks</span>
          <span className="text-xl font-bold font-mono text-[#10b981] mt-1 block">
            {(stats?.total_chunks ?? repo?.stats?.chunks ?? 0).toLocaleString()}
          </span>
          <span className="text-[11px] text-[#52525b] mt-1 block">indexed for retrieval</span>
        </div>

        <div className="p-4 rounded-xl bg-[#111113] border border-[#27272a]">
          <span className="text-xs text-[#71717a] block">Redacted Secrets</span>
          <span className="text-xl font-bold font-mono text-[#f59e0b] mt-1 block">
            {stats?.total_redactions ?? repo?.stats?.redactions ?? 0}
          </span>
          <span className="text-[11px] text-[#10b981] flex items-center gap-1 mt-1">
            <ShieldCheck className="w-3 h-3" /> Zero secrets exposed
          </span>
        </div>
      </div>

      {/* Suggested Onboarding Questions */}
      {overview?.suggested_questions && overview.suggested_questions.length > 0 && (
        <div className="p-5 rounded-xl bg-gradient-to-r from-[#6366f1]/10 via-[#111113] to-[#111113] border border-[#6366f1]/20 space-y-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-white">
            <Sparkles className="w-4 h-4 text-[#818cf8]" />
            <span>Suggested Onboarding Questions</span>
          </div>
          <p className="text-xs text-[#a1a1aa]">
            Click any question to start an interactive deep-dive in Chat with citation grounding:
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-1">
            {overview.suggested_questions.map((question, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() =>
                  navigate(`/app/repos/${repoId}/chat?q=${encodeURIComponent(question)}`)
                }
                className="flex items-start gap-2.5 p-3 rounded-lg bg-[#09090b]/80 border border-[#27272a] text-left hover:border-[#6366f1]/60 hover:bg-[#18181b] transition-all group cursor-pointer"
              >
                <HelpCircle className="w-4 h-4 text-[#6366f1] shrink-0 mt-0.5 group-hover:text-[#818cf8] transition-colors" />
                <span className="text-xs text-[#e4e4e7] group-hover:text-white leading-relaxed">
                  {question}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Main Grid: Architecture Overview Narrative & Side Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left 2 Cols: Markdown Narrative */}
        <div className="lg:col-span-2 space-y-6">
          <div className="p-6 rounded-xl bg-[#111113] border border-[#27272a] space-y-4">
            <div className="flex items-center justify-between border-b border-[#27272a] pb-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-white">
                <BookOpen className="w-4 h-4 text-[#818cf8]" />
                <span>Architecture &amp; System Tour</span>
              </div>
              {overview?.updated_at && (
                <div className="flex items-center gap-1.5 text-[11px] text-[#71717a]">
                  <Calendar className="w-3.5 h-3.5" />
                  <span>{new Date(overview.updated_at).toLocaleDateString()}</span>
                </div>
              )}
            </div>

            {/* Markdown Body */}
            <div className="prose prose-invert prose-sm max-w-none prose-headings:font-semibold prose-headings:tracking-tight prose-headings:text-white prose-p:text-[#d4d4d8] prose-p:leading-relaxed prose-code:font-mono prose-code:text-[#c7d2fe] prose-code:bg-[#18181b] prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:border prose-code:border-[#27272a] prose-li:text-[#d4d4d8] prose-strong:text-white">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeSanitize]}
                components={{
                  // Enhance text nodes to turn [S#] citations into interactive pills
                  p({ children }) {
                    return (
                      <p className="mb-4">
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
                      <li className="mb-1">
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
                {overview?.markdown || "No overview generated yet."}
              </ReactMarkdown>
            </div>
          </div>

          {/* Reading Order Progression Section */}
          {overview?.reading_order && overview.reading_order.length > 0 && (
            <div className="p-6 rounded-xl bg-[#111113] border border-[#27272a] space-y-4">
              <div className="flex items-center justify-between border-b border-[#27272a] pb-3">
                <div className="flex items-center gap-2 text-sm font-semibold text-white">
                  <Compass className="w-4 h-4 text-[#10b981]" />
                  <span>Recommended Reading Order</span>
                </div>
                <span className="text-[11px] text-[#71717a]">
                  {overview.reading_order.length} sequential milestones
                </span>
              </div>

              <p className="text-xs text-[#a1a1aa]">
                Study this repository following an architectural progression from high-level documentation down to critical leaf services:
              </p>

              <div className="space-y-2.5 pt-2">
                {overview.reading_order.map((step) => (
                  <div
                    key={step.step}
                    className="flex items-start gap-3 p-3 rounded-lg bg-[#09090b] border border-[#27272a] hover:border-[#3f3f46] transition-colors"
                  >
                    <div className="w-6 h-6 rounded-full bg-[#27272a] text-[#c7d2fe] flex items-center justify-center text-xs font-mono font-bold shrink-0 mt-0.5">
                      {step.step}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Link
                          to={`/app/repos/${repoId}/explorer?file=${encodeURIComponent(step.path)}`}
                          className="font-mono text-xs font-medium text-white hover:text-[#818cf8] transition-colors flex items-center gap-1 truncate"
                        >
                          <span>{step.path}</span>
                          <ExternalLink className="w-3 h-3 shrink-0 opacity-60" />
                        </Link>
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider bg-[#18181b] text-[#a1a1aa] border border-[#27272a]">
                          {step.category.replace("_", " ")}
                        </span>
                      </div>
                      <p className="text-xs text-[#71717a] mt-1 leading-relaxed">
                        {step.reason}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right 1 Col: Tech Stack & Entry Points */}
        <div className="space-y-6">
          {/* Tech Stack Card */}
          <div className="p-5 rounded-xl bg-[#111113] border border-[#27272a] space-y-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-white border-b border-[#27272a] pb-3">
              <Boxes className="w-4 h-4 text-[#f59e0b]" />
              <span>Technology Stack</span>
            </div>

            {Object.keys(techByCategory).length === 0 ? (
              <p className="text-xs text-[#71717a]">No technology stack detected.</p>
            ) : (
              <div className="space-y-3.5">
                {Object.entries(techByCategory).map(([cat, items]) => (
                  <div key={cat} className="space-y-1.5">
                    <span className="text-[10px] uppercase tracking-wider text-[#71717a] font-semibold block">
                      {cat}
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {items.map((tech) => (
                        <div
                          key={tech.name}
                          className="px-2 py-1 rounded-md bg-[#18181b] border border-[#27272a] text-xs text-[#e4e4e7] flex items-center gap-1.5"
                          title={tech.evidence ? `Evidence: ${tech.evidence}` : tech.name}
                        >
                          <span className="w-1.5 h-1.5 rounded-full bg-[#6366f1]" />
                          <span>{tech.name}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Entry Points Card */}
          <div className="p-5 rounded-xl bg-[#111113] border border-[#27272a] space-y-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-white border-b border-[#27272a] pb-3">
              <Terminal className="w-4 h-4 text-[#ec4899]" />
              <span>Application Entry Points</span>
            </div>

            {(!overview?.entry_points || overview.entry_points.length === 0) ? (
              <p className="text-xs text-[#71717a]">No explicit entry points identified.</p>
            ) : (
              <div className="space-y-2.5">
                {overview.entry_points.map((ep, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-[#09090b] border border-[#27272a] space-y-1"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <Link
                        to={`/app/repos/${repoId}/explorer?file=${encodeURIComponent(ep.path)}#L${ep.line}`}
                        className="font-mono text-xs font-medium text-white hover:text-[#818cf8] transition-colors truncate flex items-center gap-1"
                      >
                        <span className="truncate">{ep.path}</span>
                        <ExternalLink className="w-3 h-3 shrink-0 opacity-60" />
                      </Link>
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider bg-[#ec4899]/15 text-[#f472b6] border border-[#ec4899]/30 shrink-0">
                        {ep.kind.replace("_", " ")}
                      </span>
                    </div>
                    <p className="text-xs text-[#71717a]">{ep.description}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Sources Explorer List */}
          {overview?.sources && overview.sources.length > 0 && (
            <div className="p-5 rounded-xl bg-[#111113] border border-[#27272a] space-y-3">
              <div className="flex items-center justify-between border-b border-[#27272a] pb-3">
                <div className="flex items-center gap-2 text-sm font-semibold text-white">
                  <FileText className="w-4 h-4 text-[#a1a1aa]" />
                  <span>Grounding Sources</span>
                </div>
                <span className="font-mono text-xs text-[#71717a]">
                  {overview.sources.length} sources
                </span>
              </div>
              <div className="space-y-1.5 max-h-64 overflow-y-auto pr-1">
                {overview.sources.map((src) => (
                  <button
                    key={src.id}
                    type="button"
                    onClick={() => setActiveSource(src)}
                    className="w-full flex items-center justify-between p-2 rounded-lg bg-[#09090b] border border-[#27272a] text-left hover:border-[#6366f1]/50 transition-colors cursor-pointer"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="px-1 py-0.5 rounded font-mono text-[10px] bg-[#6366f1]/20 text-[#a5b4fc] border border-[#6366f1]/40 shrink-0">
                        {src.id}
                      </span>
                      <span className="font-mono text-xs text-[#d4d4d8] truncate">{src.path}</span>
                    </div>
                    <span className="font-mono text-[10px] text-[#71717a] shrink-0 ml-2">
                      L{src.start_line}-{src.end_line}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Source Detail Modal Drawer */}
      {activeSource && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-2xl bg-[#111113] border border-[#27272a] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
            <div className="p-4 border-b border-[#27272a] flex items-center justify-between bg-[#18181b]">
              <div className="flex items-center gap-2.5">
                <span className="px-2 py-0.5 rounded font-mono text-xs font-semibold bg-[#6366f1]/20 text-[#a5b4fc] border border-[#6366f1]/40">
                  {activeSource.id}
                </span>
                <div>
                  <h3 className="font-mono text-sm font-medium text-white">{activeSource.path}</h3>
                  <span className="text-[11px] text-[#71717a]">
                    Lines {activeSource.start_line} – {activeSource.end_line}
                    {activeSource.symbol ? ` • Symbol: ${activeSource.symbol}` : ""}
                  </span>
                </div>
              </div>
              <button
                onClick={() => setActiveSource(null)}
                className="p-1 rounded-lg text-[#a1a1aa] hover:text-white hover:bg-[#27272a] transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 overflow-y-auto flex-1 bg-[#09090b]">
              <pre className="font-mono text-xs text-[#d4d4d8] leading-relaxed whitespace-pre-wrap p-3 rounded-lg bg-[#111113] border border-[#27272a]">
                {activeSource.snippet || "No snippet available for this source."}
              </pre>
            </div>

            <div className="p-4 border-t border-[#27272a] flex items-center justify-between bg-[#18181b]">
              <span className="text-xs text-[#71717a]">Verified grounding source</span>
              <div className="flex items-center gap-2">
                <Link
                  to={`/app/repos/${repoId}/explorer?file=${encodeURIComponent(
                    activeSource.path
                  )}#L${activeSource.start_line}-L${activeSource.end_line}`}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[#6366f1] text-white hover:bg-[#4f46e5] transition-colors"
                >
                  <span>Open in Explorer</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
