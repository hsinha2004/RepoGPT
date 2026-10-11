import React, { useState } from "react";
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
} from "lucide-react";

export const DashboardPage: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState("");

  // Sample initial state for TaskFlow fixture repo
  const repos = [
    {
      id: "repo_taskflow_01",
      name: "TaskFlow",
      source: "upload",
      ref: "main",
      sha: "a3f81e2",
      status: "ready",
      stats: {
        files: 35,
        loc: 2840,
        symbols: 142,
        chunks: 260,
      },
      lastIndexed: "Just now",
      description: "Multi-language task management service with FastAPI, React, Go worker, and Java reporter.",
    },
  ];

  const filteredRepos = repos.filter((r) =>
    r.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Top action row */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Repositories</h1>
          <p className="text-sm text-[#a1a1aa] mt-1">
            Manage indexed repositories, explore architectures, and run AI code reviews.
          </p>
        </div>

        <button
          onClick={() => {}}
          className="inline-flex items-center gap-2 bg-[#6366f1] hover:bg-[#818cf8] text-white px-4 py-2 rounded-lg text-sm font-medium transition-all shadow-md shadow-[#6366f1]/20 self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>Add Repository</span>
        </button>
      </div>

      {/* Filter and search */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-[#71717a] absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Filter repositories..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[#111113] border border-[#27272a] rounded-lg pl-9 pr-3 py-1.5 text-sm text-white placeholder-[#71717a] outline-none focus:border-[#6366f1]"
          />
        </div>
      </div>

      {/* Repositories grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filteredRepos.map((repo) => (
          <div
            key={repo.id}
            className="border border-[#27272a] bg-[#111113] hover:border-[#6366f1]/50 rounded-xl p-5 flex flex-col justify-between transition-all group"
          >
            <div>
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="flex items-center gap-2.5">
                  <div className="w-9 h-9 rounded-lg bg-[#27272a] flex items-center justify-center text-[#fafafa] font-bold">
                    <FolderGit2 className="w-5 h-5 text-[#6366f1]" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white group-hover:text-[#818cf8] transition-colors">
                      {repo.name}
                    </h3>
                    <div className="flex items-center gap-1.5 text-xs text-[#a1a1aa]">
                      <GitBranch className="w-3 h-3" />
                      <span>{repo.ref}</span>
                      <span>·</span>
                      <span className="font-mono">{repo.sha}</span>
                    </div>
                  </div>
                </div>

                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-[#22c55e]/10 text-[#22c55e] border border-[#22c55e]/20">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#22c55e]" />
                  Ready
                </span>
              </div>

              <p className="text-xs text-[#a1a1aa] mt-3 line-clamp-2 leading-relaxed">
                {repo.description}
              </p>

              {/* Stats Bar */}
              <div className="grid grid-cols-4 gap-2 mt-4 pt-4 border-t border-[#27272a] text-center text-xs">
                <div>
                  <div className="font-semibold text-white">{repo.stats.files}</div>
                  <div className="text-[10px] text-[#71717a]">Files</div>
                </div>
                <div>
                  <div className="font-semibold text-white">{repo.stats.loc}</div>
                  <div className="text-[10px] text-[#71717a]">LOC</div>
                </div>
                <div>
                  <div className="font-semibold text-white">{repo.stats.symbols}</div>
                  <div className="text-[10px] text-[#71717a]">Symbols</div>
                </div>
                <div>
                  <div className="font-semibold text-white">{repo.stats.chunks}</div>
                  <div className="text-[10px] text-[#71717a]">Chunks</div>
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="flex items-center justify-between gap-2 mt-5 pt-3 border-t border-[#27272a]/60">
              <Link
                to={`/app/repos/${repo.id}/overview`}
                className="inline-flex items-center gap-1.5 text-xs text-[#6366f1] hover:text-[#818cf8] font-medium"
              >
                <span>Overview</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </Link>

              <div className="flex items-center gap-1">
                <Link
                  to={`/app/repos/${repo.id}/chat`}
                  className="p-1.5 rounded-md hover:bg-[#27272a] text-[#a1a1aa] hover:text-white transition-colors"
                  title="Ask Chat"
                >
                  <MessageSquare className="w-4 h-4" />
                </Link>
                <Link
                  to={`/app/repos/${repo.id}/explorer`}
                  className="p-1.5 rounded-md hover:bg-[#27272a] text-[#a1a1aa] hover:text-white transition-colors"
                  title="Explorer"
                >
                  <FileCode className="w-4 h-4" />
                </Link>
                <Link
                  to={`/app/repos/${repo.id}/graph`}
                  className="p-1.5 rounded-md hover:bg-[#27272a] text-[#a1a1aa] hover:text-white transition-colors"
                  title="Graph"
                >
                  <Network className="w-4 h-4" />
                </Link>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
