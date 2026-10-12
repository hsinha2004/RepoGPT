import React, { useState, useEffect } from "react";
import { Link } from "react-router";
import {
  FolderGit2,
  Plus,
  Search,
  ExternalLink,
  MessageSquare,
  FileCode,
  Network,
  GitBranch,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Clock,
  Layers,
} from "lucide-react";
import { authFetch } from "../../api/client";
import { AddRepoDialog } from "./AddRepoDialog";
import { IngestionStepper } from "./IngestionStepper";

export interface RepositoryItem {
  id: string;
  display_name: string;
  description: string;
  source: {
    type: string;
    url?: string;
    owner?: string;
    name?: string;
    ref?: string;
  };
  commit_sha?: string;
  status: "queued" | "processing" | "ready" | "failed" | "syncing";
  status_message: string;
  stats: {
    files_total: number;
    files_indexed: number;
    files_skipped: number;
    loc: number;
    symbols: number;
    chunks: number;
    languages: Record<string, number>;
    redactions: number;
  };
  last_indexed_at?: string;
  created_at: string;
}

export const DashboardPage: React.FC = () => {
  const [repos, setRepos] = useState<RepositoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [activeJob, setActiveJob] = useState<{ jobId: string; repoId: string } | null>(null);

  useEffect(() => {
    fetchRepositories();
  }, []);

  const fetchRepositories = async () => {
    setIsLoading(true);
    try {
      const res = await authFetch("/api/v1/repos");
      if (res.ok) {
        const data = await res.json();
        setRepos(data.items || []);
      }
    } catch {
      // Offline fallback
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (repoId: string, displayName: string) => {
    if (!window.confirm(`Are you sure you want to permanently delete '${displayName}'?`)) return;
    try {
      const res = await authFetch(`/api/v1/repos/${repoId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        setRepos((prev) => prev.filter((r) => r.id !== repoId));
      }
    } catch {
      alert("Failed to delete repository.");
    }
  };

  const handleJobStarted = (jobId: string, repoId: string) => {
    setActiveJob({ jobId, repoId });
    fetchRepositories();
  };

  const filteredRepos = repos.filter(
    (r) =>
      r.display_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (r.description && r.description.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Top action row */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white text-balance">Repositories</h1>
          <p className="text-sm text-[#a1a1aa] mt-1 text-pretty">
            Manage ingested codebases, explore architecture and symbol graphs, and run intelligent code reviews.
          </p>
        </div>

        <button
          onClick={() => setIsAddDialogOpen(true)}
          className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-xs self-start sm:self-auto cursor-pointer"
        >
          <Plus className="size-4" />
          <span>Add Repository</span>
        </button>
      </div>

      {/* Search and summary bar */}
      <div className="flex flex-col sm:flex-row items-center gap-4">
        <div className="relative flex-1 w-full">
          <Search className="size-4 absolute left-3 top-3 text-[#71717a]" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search repositories by name, language, or description..."
            className="w-full bg-[#18181b] border border-[#27272a] rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-[#71717a] focus:outline-none focus:border-emerald-500 transition-colors"
          />
        </div>
      </div>

      {/* Repositories Grid */}
      {isLoading ? (
        <div className="p-12 text-center text-[#71717a]">
          <Loader2 className="size-8 animate-spin mx-auto text-emerald-400 mb-2" />
          <p className="text-sm">Loading repositories...</p>
        </div>
      ) : filteredRepos.length === 0 ? (
        <div className="p-12 text-center bg-[#18181b]/50 border border-dashed border-[#27272a] rounded-xl space-y-3">
          <FolderGit2 className="size-10 text-[#71717a] mx-auto" />
          <h3 className="text-base font-semibold text-white text-balance">No repositories found</h3>
          <p className="text-xs text-[#a1a1aa] max-w-sm mx-auto text-pretty">
            {searchTerm
              ? "No repositories match your search criteria."
              : "Get started by ingesting a public GitHub repository or uploading a ZIP file."}
          </p>
          {!searchTerm && (
            <button
              onClick={() => setIsAddDialogOpen(true)}
              className="inline-flex items-center gap-2 px-3 py-1.5 bg-emerald-600 text-white text-xs font-medium rounded-lg hover:bg-emerald-500 transition-colors cursor-pointer"
            >
              <Plus className="size-3.5" />
              Add Repository
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredRepos.map((repo) => {
            const languages = Object.keys(repo.stats?.languages || {});
            return (
              <div
                key={repo.id}
                className="bg-[#18181b] border border-[#27272a] hover:border-[#3f3f46] rounded-xl p-5 flex flex-col justify-between transition-colors group shadow-xs"
              >
                <div>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <FolderGit2 className="size-5 text-emerald-400" />
                      <h3 className="text-base font-semibold text-white group-hover:text-emerald-400 transition-colors text-balance">
                        {repo.display_name}
                      </h3>
                    </div>

                    {/* Status Badge */}
                    <StatusBadge status={repo.status} />
                  </div>

                  <p className="text-xs text-[#a1a1aa] mt-2 line-clamp-2 min-h-[32px] text-pretty">
                    {repo.description || repo.status_message || "No description provided."}
                  </p>

                  {/* Ref & SHA badge */}
                  <div className="flex items-center gap-3 mt-3 text-xs text-[#71717a]">
                    <div className="flex items-center gap-1 font-mono">
                      <GitBranch className="size-3.5 text-[#a1a1aa]" />
                      <span>{repo.source?.ref || "main"}</span>
                    </div>
                    {repo.commit_sha && (
                      <span className="font-mono bg-[#27272a] px-1.5 py-0.5 rounded text-[11px] text-[#a1a1aa] tabular-nums">
                        @{repo.commit_sha.slice(0, 7)}
                      </span>
                    )}
                    <span className="text-[11px] font-mono">
                      {repo.source?.type === "github" ? "GitHub" : "ZIP Upload"}
                    </span>
                  </div>

                  {/* Inline Stats Summary */}
                  <div className="flex items-center gap-3 mt-4 text-xs text-[#a1a1aa] font-mono tabular-nums">
                    <span>
                      <strong className="text-white font-semibold">{repo.stats?.files_indexed ?? 0}</strong> files
                    </span>
                    <span className="text-[#3f3f46]">·</span>
                    <span>
                      <strong className="text-white font-semibold">
                        {repo.stats?.loc ? repo.stats.loc.toLocaleString() : 0}
                      </strong> LOC
                    </span>
                    <span className="text-[#3f3f46]">·</span>
                    <span className="text-emerald-400">
                      {repo.stats?.redactions === 0 ? "0 secrets" : `${repo.stats?.redactions} redacted`}
                    </span>
                  </div>

                  {/* Languages Tags */}
                  {languages.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-3">
                      {languages.slice(0, 4).map((lang) => (
                        <span
                          key={lang}
                          className="px-2 py-0.5 bg-[#18181b] border border-[#27272a] rounded-md text-[10px] font-mono text-[#d4d4d8]"
                        >
                          {lang}
                        </span>
                      ))}
                      {languages.length > 4 && (
                        <span className="text-[10px] text-[#71717a] font-mono self-center tabular-nums">
                          +{languages.length - 4}
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Card Footer Actions */}
                <div className="flex items-center justify-between pt-4 mt-4 border-t border-[#27272a]">
                  <div className="flex items-center gap-2">
                    <Link
                      to={`/app/repos/${repo.id}/overview`}
                      className="p-1.5 text-[#a1a1aa] hover:text-white hover:bg-[#27272a] rounded-lg transition-colors"
                      title="Overview"
                      aria-label="Repository overview"
                    >
                      <Layers className="size-4" />
                    </Link>
                    <Link
                      to={`/app/repos/${repo.id}/chat`}
                      className="p-1.5 text-[#a1a1aa] hover:text-white hover:bg-[#27272a] rounded-lg transition-colors"
                      title="Chat"
                      aria-label="Repository chat"
                    >
                      <MessageSquare className="size-4" />
                    </Link>
                    <Link
                      to={`/app/repos/${repo.id}/explorer`}
                      className="p-1.5 text-[#a1a1aa] hover:text-white hover:bg-[#27272a] rounded-lg transition-colors"
                      title="Code Explorer"
                      aria-label="Code explorer"
                    >
                      <FileCode className="size-4" />
                    </Link>
                    <Link
                      to={`/app/repos/${repo.id}/search`}
                      className="p-1.5 text-[#a1a1aa] hover:text-white hover:bg-[#27272a] rounded-lg transition-colors"
                      title="Search Playground"
                      aria-label="Code search playground"
                    >
                      <Search className="size-4" />
                    </Link>
                    <Link
                      to={`/app/repos/${repo.id}/graph`}
                      className="p-1.5 text-[#a1a1aa] hover:text-white hover:bg-[#27272a] rounded-lg transition-colors"
                      title="Dependency Graph"
                      aria-label="Dependency graph"
                    >
                      <Network className="size-4" />
                    </Link>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleDelete(repo.id, repo.display_name)}
                      className="p-1.5 text-[#71717a] hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors cursor-pointer"
                      title="Delete Repository"
                      aria-label={`Delete repository ${repo.display_name}`}
                    >
                      <Trash2 className="size-4" />
                    </button>
                    <Link
                      to={`/app/repos/${repo.id}/overview`}
                      className="inline-flex items-center gap-1 px-3 py-1 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 rounded-lg text-xs font-semibold transition-colors"
                    >
                      Open
                      <ExternalLink className="size-3" />
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add Repository Modal */}
      <AddRepoDialog
        isOpen={isAddDialogOpen}
        onClose={() => setIsAddDialogOpen(false)}
        onJobStarted={handleJobStarted}
      />

      {/* Live Ingestion Stepper Modal */}
      {activeJob && (
        <IngestionStepper
          jobId={activeJob.jobId}
          repoId={activeJob.repoId}
          isOpen={!!activeJob}
          onClose={() => {
            setActiveJob(null);
            fetchRepositories();
          }}
        />
      )}
    </div>
  );
};

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  switch (status) {
    case "ready":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
          <CheckCircle2 className="size-3" />
          Ready
        </span>
      );
    case "processing":
    case "syncing":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-teal-500/10 text-teal-400 border border-teal-500/30">
          <Loader2 className="size-3 animate-spin" />
          Processing
        </span>
      );
    case "queued":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
          <Clock className="size-3" />
          Queued
        </span>
      );
    case "failed":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-red-500/10 text-red-400 border border-red-500/30">
          <AlertCircle className="size-3" />
          Failed
        </span>
      );
    default:
      return null;
  }
};
