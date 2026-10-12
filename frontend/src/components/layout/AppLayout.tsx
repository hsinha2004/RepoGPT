import React, { useState, useEffect } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router";
import {
  Code2,
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

export const AppLayout: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, setUser, logout } = useAuthStore();
  const { theme, setTheme } = useThemeStore();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Extract repoId if currently within a repository surface
  const repoMatch = location.pathname.match(/\/app\/repos\/([^/]+)/);
  const currentRepoId = repoMatch ? repoMatch[1] : null;

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
        { label: "Reviews", path: `/app/repos/${currentRepoId}/reviews`, icon: GitPullRequest },
      ]
    : [];

  return (
    <div className="min-h-screen bg-[#09090b] text-[#fafafa] flex font-sans antialiased">
      {/* Sidebar - Desktop */}
      <aside className="hidden md:flex w-64 border-r border-[#27272a] bg-[#0c0c0e] flex-col justify-between shrink-0">
        <div>
          {/* Brand Logo Header */}
          <div className="h-16 border-b border-[#27272a] px-5 flex items-center justify-between">
            <Link to="/app" className="flex items-center gap-3 group">
              <div className="w-8 h-8 rounded-lg bg-[#6366f1] flex items-center justify-center font-bold text-white shadow-sm transition-transform group-hover:scale-105">
                <Code2 className="w-4 h-4" />
              </div>
              <div>
                <span className="font-semibold text-base tracking-tight text-white block leading-tight">
                  RepoGPT
                </span>
                <span className="text-[10px] text-[#71717a] font-mono block">Code Intelligence</span>
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
                      ? "bg-[#18181b] text-white border border-[#27272a] shadow-xs"
                      : "text-[#a1a1aa] hover:bg-[#141417] hover:text-white"
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? "text-[#818cf8]" : "text-[#71717a]"}`} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* User Profile & Sign Out Footer */}
        <div className="p-3 border-t border-[#27272a] bg-[#09090b]">
          <div className="flex items-center justify-between p-2 rounded-lg bg-[#111113] border border-[#27272a]">
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-7 h-7 rounded-full bg-[#27272a] border border-[#3f3f46] flex items-center justify-center text-xs font-semibold text-white shrink-0">
                {user?.name ? user.name[0].toUpperCase() : "U"}
              </div>
              <div className="truncate">
                <p className="text-xs font-medium text-white truncate leading-tight">
                  {user?.name || "Developer"}
                </p>
                <p className="text-[10px] text-[#71717a] truncate font-mono">
                  {user?.email || "user@repogpt.local"}
                </p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              title="Sign Out"
              className="p-1.5 rounded-md text-[#71717a] hover:text-white hover:bg-[#27272a] transition-colors cursor-pointer"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Header */}
        <header className="h-16 border-b border-[#27272a] bg-[#0c0c0e]/90 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-40">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-lg text-[#a1a1aa] hover:text-white hover:bg-[#27272a]"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>

            {/* Breadcrumb / Context */}
            {currentRepoId ? (
              <div className="flex items-center gap-2 text-xs">
                <Link to="/app" className="text-[#71717a] hover:text-white transition-colors">
                  Repositories
                </Link>
                <ChevronRight className="w-3.5 h-3.5 text-[#52525b]" />
                <span className="font-mono text-white font-medium truncate max-w-[200px] sm:max-w-none">
                  {currentRepoId}
                </span>
              </div>
            ) : (
              <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[#27272a] bg-[#111113] text-xs text-[#71717a]">
                <Search className="w-3.5 h-3.5" />
                <span>Search repository, symbol, file...</span>
                <kbd className="ml-2 font-mono bg-[#18181b] border border-[#27272a] px-1.5 py-0.5 rounded text-[10px] text-[#a1a1aa]">
                  Ctrl K
                </kbd>
              </div>
            )}
          </div>

          <div className="flex items-center gap-3">
            {/* Engine Status Indicator Pill */}
            <div className="hidden lg:flex items-center gap-2 px-2.5 py-1 rounded-full bg-[#18181b] border border-[#27272a] text-xs text-[#a1a1aa]">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              <span className="font-mono text-[11px]">Verified AST &amp; BM25</span>
            </div>

            {/* Theme Toggle */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg border border-[#27272a] bg-[#111113] text-[#a1a1aa] hover:text-white hover:border-[#3f3f46] transition-colors cursor-pointer"
              title="Toggle Theme"
            >
              {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
          </div>
        </header>

        {/* Repository Context Sub-Navigation Tabs */}
        {currentRepoId && (
          <div className="border-b border-[#27272a] bg-[#111113]/50 px-6 overflow-x-auto scrollbar-none flex gap-1">
            {repoNavTabs.map((tab) => {
              const TabIcon = tab.icon;
              const isActive = location.pathname === tab.path;
              return (
                <Link
                  key={tab.path}
                  to={tab.path}
                  className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium border-b-2 transition-all whitespace-nowrap ${
                    isActive
                      ? "border-[#6366f1] text-white bg-[#18181b]/50"
                      : "border-transparent text-[#a1a1aa] hover:text-white hover:border-[#3f3f46]"
                  }`}
                >
                  <TabIcon className={`w-3.5 h-3.5 ${isActive ? "text-[#818cf8]" : "text-[#71717a]"}`} />
                  <span>{tab.label}</span>
                </Link>
              );
            })}
          </div>
        )}

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="md:hidden border-b border-[#27272a] bg-[#111113] p-4 space-y-2">
            <nav className="space-y-1">
              {navItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-[#a1a1aa] hover:bg-[#18181b] hover:text-white"
                >
                  <item.icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </Link>
              ))}
            </nav>
          </div>
        )}

        {/* Main Content Area */}
        <main className="flex-1 p-6 md:p-8 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
