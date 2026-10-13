import React, { useState, useEffect } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router";
import {
  FolderGit2,
  BarChart3,
  Settings,
  ShieldAlert,
  Search,
  Moon,
  Sun,
  LogOut,
  Menu,
  X,
  Layers,
  MessageSquare,
  FileCode,
  Network,
  GitPullRequest,
  ChevronRight,
} from "lucide-react";
import { useAuthStore } from "../../stores/authStore";
import { useThemeStore } from "../../stores/themeStore";
import { authFetch } from "../../api/client";
import { CommandPalette } from "./CommandPalette";

export const AppLayout: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, setUser, logout } = useAuthStore();
  const { theme, setTheme } = useThemeStore();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);

  // Extract repoId if currently within a repository surface
  const repoMatch = location.pathname.match(/\/app\/repos\/([^/]+)/);
  const currentRepoId = repoMatch ? repoMatch[1] : null;

  // Global Ctrl+K / Cmd+K Command Palette listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    // Restore session if user state is uninitialized
    if (!user) {
      authFetch("/api/v1/auth/me")
        .then(async (res) => {
          if (res.ok) {
            const data = await res.json();
            setUser(data);
          } else if (res.status === 401) {
            logout();
            navigate("/login");
          }
        })
        .catch(() => {});
    }
  }, [user, setUser, logout, navigate]);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const toggleTheme = () => {
    setTheme(theme === "dark" ? "light" : "dark");
  };

  const navItems = [
    { label: "Repositories", path: "/app", icon: FolderGit2 },
    { label: "Evaluation", path: "/app/evaluation", icon: BarChart3 },
    { label: "Settings", path: "/app/settings", icon: Settings },
  ];

  if (user?.role === "admin") {
    navItems.push({ label: "Administration", path: "/app/admin", icon: ShieldAlert });
  }

  const repoNavTabs = currentRepoId
    ? [
        { label: "Overview", path: `/app/repos/${currentRepoId}/overview`, icon: Layers },
        { label: "Chat", path: `/app/repos/${currentRepoId}/chat`, icon: MessageSquare },
        { label: "Explorer", path: `/app/repos/${currentRepoId}/explorer`, icon: FileCode },
        { label: "Graph", path: `/app/repos/${currentRepoId}/graph`, icon: Network },
        { label: "Search", path: `/app/repos/${currentRepoId}/search`, icon: Search },
        { label: "Reviews", path: `/app/repos/${currentRepoId}/reviews`, icon: GitPullRequest },
      ]
    : [];

  return (
    <div className="min-h-dvh bg-zinc-50 text-zinc-900 flex font-sans antialiased">
      {/* Sidebar - Desktop */}
      <aside className="hidden md:flex w-64 border-r border-zinc-200 bg-white flex-col justify-between shrink-0 shadow-xs">
        <div>
          {/* Brand Logo Header */}
          <div className="h-20 border-b border-zinc-200 px-5 flex items-center justify-between">
            <Link to="/app" className="flex items-center gap-3.5 group">
              <img
                src="/logo-icon.png"
                alt="RepoGPT Logo"
                className="size-12 object-contain drop-shadow-sm transition-transform group-hover:scale-105 shrink-0"
              />
              <div>
                <span className="font-bold text-lg tracking-tight text-zinc-950 block leading-tight">
                  RepoGPT
                </span>
                <span className="text-[11px] text-zinc-500 font-mono block">Code Intelligence</span>
              </div>
            </Link>
          </div>

          {/* Primary Navigation Links */}
          <nav className="p-3 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive =
                item.path === "/app"
                  ? location.pathname === "/app"
                  : location.pathname.startsWith(item.path);

              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? "bg-emerald-50 text-emerald-900 border border-emerald-200/80 shadow-xs font-semibold"
                      : "text-zinc-600 hover:bg-zinc-100/70 hover:text-zinc-900"
                  }`}
                >
                  <Icon className={`size-4 ${isActive ? "text-emerald-600" : "text-zinc-400"}`} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* User Profile & Sign Out Footer */}
        <div className="p-3 border-t border-zinc-200 bg-zinc-50/50">
          <div className="flex items-center justify-between p-2 rounded-lg bg-white border border-zinc-200 shadow-xs">
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="size-7 rounded-full bg-zinc-100 border border-zinc-300 flex items-center justify-center text-xs font-semibold text-zinc-700 shrink-0">
                {user?.name ? user.name[0].toUpperCase() : "U"}
              </div>
              <div className="truncate">
                <p className="text-xs font-medium text-zinc-900 truncate leading-tight">
                  {user?.name || "Developer"}
                </p>
                <p className="text-[10px] text-zinc-500 truncate font-mono">
                  {user?.email || "user@repogpt.local"}
                </p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              title="Sign Out"
              aria-label="Sign out"
              className="p-1.5 rounded-md text-zinc-400 hover:text-zinc-900 hover:bg-zinc-100 transition-colors cursor-pointer"
            >
              <LogOut className="size-3.5" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Header */}
        <header className="h-16 border-b border-zinc-200 bg-white/90 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-40">
          <div className="flex items-center gap-4 min-w-0">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="Toggle mobile navigation"
              className="md:hidden p-2 rounded-lg text-zinc-600 hover:text-zinc-950 hover:bg-zinc-100"
            >
              {mobileMenuOpen ? <X className="size-5" /> : <Menu className="size-5" />}
            </button>

            {/* Mobile Brand Logo */}
            <Link to="/app" className="md:hidden flex items-center gap-2.5 shrink-0">
              <img src="/logo-icon.png" alt="RepoGPT Logo" className="size-8 object-contain drop-shadow-sm" />
              <span className="font-bold text-base text-zinc-950">RepoGPT</span>
            </Link>

            {/* Breadcrumb / Context */}
            {currentRepoId && (
              <div className="flex items-center gap-2 text-xs shrink-0">
                <Link to="/app" className="text-zinc-500 hover:text-zinc-900 transition-colors">
                  Repositories
                </Link>
                <ChevronRight className="size-3.5 text-zinc-400" />
                <span className="font-mono text-zinc-950 font-medium truncate max-w-[150px] sm:max-w-none">
                  {currentRepoId}
                </span>
              </div>
            )}

            {/* Command Palette / Search Trigger Button */}
            <button
              type="button"
              onClick={() => setCommandPaletteOpen(true)}
              aria-label="Search repository, symbol, file (Ctrl K)"
              className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg border border-zinc-200 bg-zinc-50 hover:bg-zinc-100 hover:border-zinc-300 text-xs text-zinc-500 hover:text-zinc-900 transition-all cursor-pointer shadow-xs group"
            >
              <Search className="size-3.5 text-zinc-400 group-hover:text-emerald-600 transition-colors" />
              <span>Search repository, symbol, file...</span>
              <kbd className="ml-2 font-mono bg-white group-hover:bg-zinc-50 border border-zinc-200 px-1.5 py-0.5 rounded text-[10px] text-zinc-600 shadow-xs transition-colors">
                Ctrl K
              </kbd>
            </button>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            {/* Mobile Search Button */}
            <button
              type="button"
              onClick={() => setCommandPaletteOpen(true)}
              aria-label="Search repository, symbol, file"
              className="sm:hidden p-2 rounded-lg border border-zinc-200 bg-zinc-50 text-zinc-600 hover:text-zinc-950 hover:border-zinc-300 transition-colors cursor-pointer"
            >
              <Search className="size-4" />
            </button>

            {/* Engine Status Indicator Pill */}
            <div className="hidden lg:flex items-center gap-2 px-2.5 py-1 rounded-full bg-zinc-100 border border-zinc-200 text-xs text-zinc-700">
              <span className="size-1.5 rounded-full bg-emerald-600" />
              <span className="font-mono text-[11px] font-medium">Verified AST &amp; BM25</span>
            </div>

            {/* Theme Toggle */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg border border-zinc-200 bg-zinc-50 text-zinc-600 hover:text-zinc-950 hover:bg-zinc-100 hover:border-zinc-300 transition-colors cursor-pointer shadow-xs"
              title="Toggle Theme"
              aria-label="Toggle color theme"
            >
              {theme === "dark" ? <Sun className="size-4 text-amber-500" /> : <Moon className="size-4 text-zinc-700" />}
            </button>
          </div>
        </header>

        {/* Repository Context Sub-Navigation Tabs */}
        {currentRepoId && (
          <div className="border-b border-zinc-200 bg-white px-6 overflow-x-auto scrollbar-none flex gap-1">
            {repoNavTabs.map((tab) => {
              const TabIcon = tab.icon;
              const isActive =
                location.pathname === tab.path || location.pathname.startsWith(`${tab.path}/`);
              return (
                <Link
                  key={tab.path}
                  to={tab.path}
                  className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium border-b-2 transition-all whitespace-nowrap ${
                    isActive
                      ? "border-emerald-600 text-emerald-800 bg-emerald-50/70 font-semibold"
                      : "border-transparent text-zinc-600 hover:text-zinc-950 hover:border-zinc-300"
                  }`}
                >
                  <TabIcon className={`size-3.5 ${isActive ? "text-emerald-600" : "text-zinc-400"}`} />
                  <span>{tab.label}</span>
                </Link>
              );
            })}
          </div>
        )}

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="md:hidden border-b border-zinc-200 bg-white p-4 space-y-3 shadow-md">
            <div className="flex items-center gap-3 px-2 py-1 border-b border-zinc-200 pb-3 mb-2">
              <img src="/logo-icon.png" alt="RepoGPT Logo" className="size-10 object-contain drop-shadow-sm" />
              <div>
                <span className="font-bold text-base text-zinc-950 block leading-tight">RepoGPT</span>
                <span className="text-[11px] text-zinc-500 font-mono block">Code Intelligence</span>
              </div>
            </div>
            <nav className="space-y-1">
              {navItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-zinc-600 hover:bg-zinc-100 hover:text-zinc-950"
                >
                  <item.icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </Link>
              ))}
            </nav>
          </div>
        )}

        {/* Main Content Area */}
        {(() => {
          const isWorkbenchView = Boolean(
            location.pathname.match(/\/app\/repos\/[^/]+\/(chat|explorer|graph)(\/.*)?$/)
          );
          return (
            <main
              className={`flex-1 ${
                isWorkbenchView
                  ? "min-h-0 flex flex-col overflow-hidden"
                  : "p-6 md:p-8 overflow-y-auto"
              }`}
            >
              <Outlet />
            </main>
          );
        })()}

        {/* Command Palette Modal */}
        <CommandPalette
          isOpen={commandPaletteOpen}
          onClose={() => setCommandPaletteOpen(false)}
          currentRepoId={currentRepoId}
        />
      </div>
    </div>
  );
};
