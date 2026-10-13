import React, { useState, useEffect, useRef, useMemo, useId } from "react";
import { useNavigate } from "react-router";
import {
  Search,
  FolderGit2,
  Layers,
  MessageSquare,
  FileCode,
  Network,
  GitPullRequest,
  BarChart3,
  Settings,
  ShieldAlert,
  Moon,
  Sun,
  ArrowRight,
  Code2,
} from "lucide-react";
import { authFetch } from "../../api/client";
import { useAuthStore } from "../../stores/authStore";
import { useThemeStore } from "../../stores/themeStore";

interface RepositoryItem {
  id: string;
  display_name: string;
  description?: string;
  status: string;
}

interface PaletteAction {
  id: string;
  title: string;
  subtitle?: string;
  category: "search" | "repository" | "repo_views" | "navigation" | "theme";
  icon: React.ElementType;
  badge?: string;
  onSelect: () => void;
}

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  currentRepoId?: string | null;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  currentRepoId,
}) => {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { theme, setTheme } = useThemeStore();
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [repos, setRepos] = useState<RepositoryItem[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const titleId = useId();

  // Load repositories for search
  useEffect(() => {
    if (!isOpen) return;

    let isMounted = true;
    authFetch("/api/v1/repos")
      .then(async (res) => {
        if (res.ok) {
          const data = await res.json();
          if (isMounted) {
            setRepos(data.items || []);
          }
        }
      })
      .catch(() => {});

    return () => {
      isMounted = false;
    };
  }, [isOpen]);

  // Reset query and selection whenever palette is opened
  useEffect(() => {
    if (isOpen) {
      setQuery("");
      setSelectedIndex(0);
      setTimeout(() => {
        inputRef.current?.focus();
      }, 50);
    }
  }, [isOpen]);

  // Compute available actions based on context and search query
  const actions = useMemo<PaletteAction[]>(() => {
    const list: PaletteAction[] = [];
    const trimmed = query.trim().toLowerCase();

    // 1. If user typed a search query, provide instant Code Search actions
    if (trimmed) {
      if (currentRepoId) {
        list.push({
          id: `search-curr-${currentRepoId}`,
          title: `Search codebase for "${query.trim()}"`,
          subtitle: `Query current repository symbols, files, and semantics`,
          category: "search",
          icon: Code2,
          badge: "Current Repo",
          onSelect: () => {
            navigate(`/app/repos/${currentRepoId}/search?q=${encodeURIComponent(query.trim())}`);
            onClose();
          },
        });
      } else if (repos.length > 0) {
        const targetRepo = repos[0];
        list.push({
          id: `search-first-${targetRepo.id}`,
          title: `Search code in ${targetRepo.display_name} for "${query.trim()}"`,
          subtitle: `Query symbols, files, and semantics`,
          category: "search",
          icon: Code2,
          badge: targetRepo.display_name,
          onSelect: () => {
            navigate(`/app/repos/${targetRepo.id}/search?q=${encodeURIComponent(query.trim())}`);
            onClose();
          },
        });
      }
    }

    // 2. Current Repository Navigation Views
    if (currentRepoId) {
      const currentRepoObj = repos.find((r) => r.id === currentRepoId);
      const repoLabel = currentRepoObj?.display_name || currentRepoId;

      const repoViews: Array<{
        title: string;
        path: string;
        icon: React.ElementType;
        sub: string;
      }> = [
        {
          title: `Chat & Ask AI`,
          path: `/app/repos/${currentRepoId}/chat`,
          icon: MessageSquare,
          sub: `Ask questions about ${repoLabel}`,
        },
        {
          title: `Overview & Architecture`,
          path: `/app/repos/${currentRepoId}/overview`,
          icon: Layers,
          sub: `High-level architecture and ingestion status`,
        },
        {
          title: `Codebase Explorer`,
          path: `/app/repos/${currentRepoId}/explorer`,
          icon: FileCode,
          sub: `Browse files, symbols, and syntax trees`,
        },
        {
          title: `Dependency Graph`,
          path: `/app/repos/${currentRepoId}/graph`,
          icon: Network,
          sub: `Explore module and package dependencies`,
        },
        {
          title: `Search Code & Symbols`,
          path: `/app/repos/${currentRepoId}/search`,
          icon: Search,
          sub: `Hybrid BM25 and vector retrieval`,
        },
        {
          title: `Code Reviews`,
          path: `/app/repos/${currentRepoId}/reviews`,
          icon: GitPullRequest,
          sub: `Automated PR and diff code reviews`,
        },
      ];

      for (const view of repoViews) {
        if (!trimmed || view.title.toLowerCase().includes(trimmed) || view.sub.toLowerCase().includes(trimmed)) {
          list.push({
            id: `repo-view-${view.path}`,
            title: view.title,
            subtitle: view.sub,
            category: "repo_views",
            icon: view.icon,
            badge: "Repo View",
            onSelect: () => {
              navigate(view.path);
              onClose();
            },
          });
        }
      }
    }

    // 3. Repositories
    const matchingRepos = repos.filter(
      (r) =>
        !trimmed ||
        r.display_name.toLowerCase().includes(trimmed) ||
        r.id.toLowerCase().includes(trimmed) ||
        (r.description && r.description.toLowerCase().includes(trimmed))
    );

    for (const r of matchingRepos.slice(0, 6)) {
      list.push({
        id: `repo-${r.id}`,
        title: r.display_name,
        subtitle: r.description || `Repository ID: ${r.id}`,
        category: "repository",
        icon: FolderGit2,
        badge: r.status,
        onSelect: () => {
          navigate(`/app/repos/${r.id}/overview`);
          onClose();
        },
      });
    }

    // 4. Global App Navigation
    const navItems = [
      {
        title: "All Repositories",
        path: "/app",
        icon: FolderGit2,
        sub: "Dashboard and repository management",
      },
      {
        title: "Evaluation Benchmark",
        path: "/app/evaluation",
        icon: BarChart3,
        sub: "Recall, precision, and latency evaluation",
      },
      {
        title: "Settings & LLM Config",
        path: "/app/settings",
        icon: Settings,
        sub: "API keys, models, and provider preferences",
      },
    ];

    if (user?.role === "admin") {
      navItems.push({
        title: "Administration",
        path: "/app/admin",
        icon: ShieldAlert,
        sub: "System telemetry and administrative control",
      });
    }

    for (const item of navItems) {
      if (!trimmed || item.title.toLowerCase().includes(trimmed) || item.sub.toLowerCase().includes(trimmed)) {
        list.push({
          id: `nav-${item.path}`,
          title: item.title,
          subtitle: item.sub,
          category: "navigation",
          icon: item.icon,
          onSelect: () => {
            navigate(item.path);
            onClose();
          },
        });
      }
    }

    // 5. Theme Toggle Action
    if (!trimmed || "theme dark light mode".includes(trimmed)) {
      list.push({
        id: "theme-toggle",
        title: `Switch to ${theme === "dark" ? "Light" : "Dark"} Theme`,
        subtitle: `Currently using ${theme} theme`,
        category: "theme",
        icon: theme === "dark" ? Sun : Moon,
        onSelect: () => {
          setTheme(theme === "dark" ? "light" : "dark");
          onClose();
        },
      });
    }

    return list;
  }, [query, currentRepoId, repos, user?.role, theme, setTheme, navigate, onClose]);

  // Reset selectedIndex if it goes out of bounds
  useEffect(() => {
    if (selectedIndex >= actions.length) {
      setSelectedIndex(Math.max(0, actions.length - 1));
    }
  }, [actions.length, selectedIndex]);

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % Math.max(1, actions.length));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + actions.length) % Math.max(1, actions.length));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (actions[selectedIndex]) {
        actions[selectedIndex].onSelect();
      }
    } else if (e.key === "Escape") {
      e.preventDefault();
      onClose();
    }
  };

  // Auto-scroll the active option into view
  useEffect(() => {
    if (!listRef.current) return;
    const activeEl = listRef.current.querySelector<HTMLElement>("[data-active='true']");
    if (activeEl) {
      activeEl.scrollIntoView({ block: "nearest" });
    }
  }, [selectedIndex]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-start justify-center pt-[10vh] px-4 animate-in fade-in duration-150"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      <div
        className="w-full max-w-2xl rounded-2xl border border-zinc-200 bg-white shadow-2xl shadow-zinc-400/25 flex flex-col overflow-hidden text-zinc-900 animate-in zoom-in-95 duration-150"
        onKeyDown={handleKeyDown}
      >
        <span id={titleId} className="sr-only">Command Palette</span>
        {/* Search Input Bar */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-zinc-200 bg-zinc-50">
          <Search className="size-5 text-emerald-600 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            placeholder="Type a command, search repository, symbol, file..."
            className="flex-1 bg-transparent text-sm text-zinc-950 placeholder-zinc-400 outline-none"
            aria-label="Search repository, symbol, file or command"
          />
          <kbd className="font-mono text-[10px] bg-white text-zinc-600 border border-zinc-200 px-1.5 py-0.5 rounded shadow-xs shrink-0">
            ESC
          </kbd>
        </div>

        {/* Results List */}
        <div
          ref={listRef}
          className="max-h-[60vh] overflow-y-auto p-2 space-y-1 divide-y divide-zinc-100 scrollbar-thin"
        >
          {actions.length === 0 ? (
            <div className="py-12 text-center text-xs text-zinc-500">
              No results found for &ldquo;<span className="text-zinc-900 font-medium">{query}</span>&rdquo;
            </div>
          ) : (
            actions.map((action, idx) => {
              const Icon = action.icon;
              const isSelected = idx === selectedIndex;
              return (
                <button
                  key={action.id}
                  data-active={isSelected}
                  onClick={action.onSelect}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`w-full flex items-center justify-between gap-3 px-3.5 py-2.5 rounded-xl text-left transition-colors cursor-pointer ${
                    isSelected
                      ? "bg-emerald-50 text-emerald-950 border border-emerald-200"
                      : "text-zinc-600 hover:bg-zinc-100/80 hover:text-zinc-900 border border-transparent"
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className={`p-2 rounded-lg shrink-0 ${
                        isSelected
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-zinc-100 text-zinc-500"
                      }`}
                    >
                      <Icon className="size-4" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs font-medium text-zinc-950 flex items-center gap-2 truncate">
                        <span>{action.title}</span>
                        {action.badge && (
                          <span className="font-mono text-[9px] uppercase px-1.5 py-0.2 rounded bg-zinc-100 text-zinc-600 border border-zinc-200 shrink-0">
                            {action.badge}
                          </span>
                        )}
                      </div>
                      {action.subtitle && (
                        <div className="text-[11px] text-zinc-500 truncate mt-0.5">
                          {action.subtitle}
                        </div>
                      )}
                    </div>
                  </div>

                  <ArrowRight
                    className={`size-3.5 shrink-0 transition-transform ${
                      isSelected ? "text-emerald-600 translate-x-0.5" : "text-transparent"
                    }`}
                  />
                </button>
              );
            })
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="px-4 py-2 border-t border-zinc-200 bg-zinc-50 flex items-center justify-between text-[11px] text-zinc-500">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <kbd className="font-mono bg-white px-1 py-0.5 rounded border border-zinc-200 text-[10px] text-zinc-600 shadow-xs">
                ↑
              </kbd>
              <kbd className="font-mono bg-white px-1 py-0.5 rounded border border-zinc-200 text-[10px] text-zinc-600 shadow-xs">
                ↓
              </kbd>{" "}
              navigate
            </span>
            <span className="flex items-center gap-1">
              <kbd className="font-mono bg-white px-1 py-0.5 rounded border border-zinc-200 text-[10px] text-zinc-600 shadow-xs">
                ↵
              </kbd>{" "}
              select
            </span>
          </div>
          <div className="font-mono text-[10px] text-emerald-700 font-medium">RepoGPT Command Palette</div>
        </div>
      </div>
    </div>
  );
};
