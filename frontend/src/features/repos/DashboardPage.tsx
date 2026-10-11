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
import { getAccessToken } from "../../api/client";
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
      const token = getAccessToken();
      const res = await fetch("/api/v1/repos", {
        headers: { Authorization: `Bearer ${token}` },
      });
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
      const token = getAccessToken();
      const res = await fetch(`/api/v1/repos/${repoId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
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
          <h1 className="text-2xl font-bold tracking-tight text-white">Repositories</h1>
          <p className="text-sm text-[#a1a1aa] mt-1">
            Manage ingested codebases, explore architecture and symbol graphs, and run intelligent code reviews.
          </p>
        </div>

        <button
          onClick={() => setIsAddDialogOpen(true)}
          className="inline-flex items-center gap-2 bg-[#6366f1] hover:bg-[#4f46e5] text-white px-4 py-2 rounded-lg text-sm font-medium transition-all shadow-md shadow-[#6366f1]/20 self-start sm:self-auto cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>Add Repository</span>
        </button>
      </div>

      {/* Search and summary bar */}
      <div className="flex flex-col sm:flex-row items-center gap-4">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 absolute left-3 top-3 text-[#71717a]" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search repositories by name, language, or description..."
            className="w-full bg-[#18181b] border border-[#27272a] rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-[#71717a] focus:outline-none focus:border-[#6366f1] transition-colors"
          />
        </div>
      </div>

      {/* Repositories Grid */}
      {isLoading ? (
        <div className="p-12 text-center text-[#71717a]">
          <Loader2 className="w-8 h-8 animate-spin mx-auto text-[#6366f1] mb-2" />
          <p className="text-sm">Loading repositories...</p>
        </div>
      ) : filteredRepos.length === 0 ? (
        <div className="p-12 text-center bg-[#18181b]/50 border border-dashed border-[#27272a] rounded-xl space-y-3">
          <FolderGit2 className="w-10 h-10 text-[#71717a] mx-auto" />
          <h3 className="text-base font-semibold text-white">No repositories found</h3>
          <p className="text-xs text-[#a1a1aa] max-w-sm mx-auto">
            {searchTerm
              ? "No repositories match your search criteria."
              : "Get started by ingesting a public GitHub repository or uploading a ZIP file."}
          </p>
          {!searchTerm && (
            <button
              onClick={() => setIsAddDialogOpen(true)}
              className="inline-flex items-center gap-2 px-3 py-1.5 bg-[#6366f1] text-white text-xs font-medium rounded-lg hover:bg-[#4f46e5] transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
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
                className="bg-[#18181b] border border-[#27272a] hover:border-[#3f3f46] rounded-xl p-5 flex flex-col justify-between transition-all duration-200 group shadow-sm"
              >
                <div>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <FolderGit2 className="w-5 h-5 text-[#818cf8]" />
                      <h3 className="text-base font-semibold text-white group-hover:text-[#818cf8] transition-colors">
                        {repo.display_name}
                      </h3>
                    </div>

                    {/* Status Badge */}
                    <StatusBadge status={repo.status} />
                  </div>

                  <p className="text-xs text-[#a1a1aa] mt-2 line-clamp-2 min-h-[32px]">
                    {repo.description || repo.status_message || "No description provided."}
                  </p>

                  {/* Ref & SHA badge */}
                  <div className="flex items-center gap-3 mt-3 text-xs text-[#71717a]">
                    <div className="flex items-center gap-1 font-mono">
                      <GitBranch className="w-3.5 h-3.5 text-[#a1a1aa]" />
                      <span>{repo.source?.ref || "main"}</span>
                    </div>
                    {repo.commit_sha && (
                      <span className="font-mono bg-[#27272a] px-1.5 py-0.5 rounded text-[11px] text-[#a1a1aa]">
                        @{repo.commit_sha.slice(0, 7)}
                      </span>
                    )}
                    <span className="text-[11px] font-mono">
                      {repo.source?.type === "github" ? "GitHub" : "ZIP Upload"}
                    </span>
                  </div>

                  {/* Stats Bar */}
                  <div className="grid grid-cols-3 gap-2 mt-4 p-2 bg-[#09090b] rounded-lg border border-[#27272a] text-center">
                    <div>
                      <span className="text-[10px] text-[#71717a] uppercase tracking-wider block">Files</span>
                      <span className="text-xs font-mono font-semibold text-white">
                        {repo.stats?.files_indexed ?? 0}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] text-[#71717a] uppercase tracking-wider block">Lines</span>
                      <span className="text-xs font-mono font-semibold text-white">
                        {repo.stats?.loc ? repo.stats.loc.toLocaleString() : 0}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] text-[#71717a] uppercase tracking-wider block">Redactions</span>
                      <span className="text-xs font-mono font-semibold text-white">
                        {repo.stats?.redactions ?? 0}
                      </span>
                    </div>
                  </div>

                  {/* Languages Tags */}
                  {languages.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-3">
                      {languages.slice(0, 4).map((lang) => (
                        <span
                          key={lang}
                          className="px-2 py-0.5 bg-[#27272a] rounded-full text-[10px] font-medium text-[#c7d2fe]"
                        >
                          {lang}
                        </span>
                      ))}
                      {languages.length > 4 && (
                        <span className="text-[10px] text-[#71717a] self-center">
                          +{languages.length - 4} more
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
                    >
                      <Layers className="w-4 h-4" />
                    </Link>
                    <Link
                      to={`/app/repos/${repo.id}/chat`}
                      className="p-1.5 text-[#a1a1aa] hover:text-white hover:bg-[#27272a] rounded-lg transition-colors"
                      title="Chat"
                    >
                      <MessageSquare className="w-4 h-4" />
                    </Link>
                    <Link
                      to={`/app/repos/${repo.id}/explorer`}
                      className="p-1.5 text-[#a1a1aa] hover:text-white hover:bg-[#27272a] rounded-lg transition-colors"
                      title="Code Explorer"
                    >
                      <FileCode className="w-4 h-4" />
                    </Link>
                    <Link
                      to={`/app/repos/${repo.id}/search`}
                      className="p-1.5 text-[#a1a1aa] hover:text-white hover:bg-[#27272a] rounded-lg transition-colors"
                      title="Search Playground"
                    >
                      <Search className="w-4 h-4" />
                    </Link>
                    <Link
                      to={`/app/repos/${repo.id}/graph`}
                      className="p-1.5 text-[#a1a1aa] hover:text-white hover:bg-[#27272a] rounded-lg transition-colors"
                      title="Dependency Graph"
                    >
                      <Network className="w-4 h-4" />
                    </Link>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleDelete(repo.id, repo.display_name)}
                      className="p-1.5 text-[#71717a] hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                      title="Delete Repository"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                    <Link
                      to={`/app/repos/${repo.id}/overview`}
                      className="inline-flex items-center gap-1 px-3 py-1 bg-[#6366f1]/20 hover:bg-[#6366f1]/30 text-[#818cf8] border border-[#6366f1]/40 rounded-lg text-xs font-semibold transition-colors"
                    >
                      Open
                      <ExternalLink className="w-3 h-3" />
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
          <CheckCircle2 className="w-3 h-3" />
          Ready
        </span>
      );
    case "processing":
    case "syncing":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/30">
          <Loader2 className="w-3 h-3 animate-spin" />
          Processing
        </span>
      );
    case "queued":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
          <Clock className="w-3 h-3" />
          Queued
        </span>
      );
    case "failed":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-red-500/10 text-red-400 border border-red-500/30">
          <AlertCircle className="w-3 h-3" />
          Failed
        </span>
      );
    default:
      return null;
  }
};
