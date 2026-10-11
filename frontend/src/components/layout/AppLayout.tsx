import React, { useState } from "react";
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
  AlertTriangle,
} from "lucide-react";
import { useAuthStore } from "../../stores/authStore";
import { useThemeStore } from "../../stores/themeStore";

export const AppLayout: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const { theme, setTheme } = useThemeStore();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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

  return (
    <div className="min-h-screen bg-[#09090b] text-[#fafafa] flex font-sans">
      {/* Sidebar - Desktop */}
      <aside className="hidden md:flex w-64 border-r border-[#27272a] bg-[#111113] flex-col justify-between shrink-0">
        <div>
          {/* Logo & App Title */}
          <div className="h-16 border-b border-[#27272a] px-5 flex items-center justify-between">
            <Link to="/app" className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-[#6366f1] flex items-center justify-center font-bold text-white shadow-md shadow-[#6366f1]/20">
                <Code2 className="w-5 h-5" />
              </div>
              <span className="font-bold text-lg tracking-tight text-white">RepoGPT</span>
            </Link>
          </div>

          {/* Navigation Links */}
          <nav className="p-3 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path || (item.path !== "/app" && location.pathname.startsWith(item.path));
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-[#6366f1]/15 text-[#818cf8] border border-[#6366f1]/30"
                      : "text-[#a1a1aa] hover:bg-[#18181b] hover:text-white"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* User Card & Logout */}
        <div className="p-4 border-t border-[#27272a] bg-[#0c0c0e]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-8 h-8 rounded-full bg-[#27272a] flex items-center justify-center text-xs font-semibold text-white">
                {user?.name ? user.name[0].toUpperCase() : "U"}
              </div>
              <div className="truncate">
                <p className="text-xs font-medium text-white truncate">{user?.name || "Developer"}</p>
                <p className="text-[11px] text-[#71717a] truncate">{user?.email || "user@repogpt.local"}</p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              title="Sign Out"
              className="p-1.5 rounded-lg text-[#a1a1aa] hover:text-white hover:bg-[#27272a] transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Header */}
        <header className="h-16 border-b border-[#27272a] bg-[#111113]/80 backdrop-blur px-6 flex items-center justify-between sticky top-0 z-40">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-lg text-[#a1a1aa] hover:text-white hover:bg-[#27272a]"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>

            {/* Quick Command Palette trigger */}
            <button
              onClick={() => {}}
              className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[#27272a] bg-[#09090b] text-xs text-[#a1a1aa] hover:border-[#6366f1]/50 transition-all"
            >
              <Search className="w-3.5 h-3.5" />
              <span>Search repository, symbol, file...</span>
              <kbd className="ml-2 font-mono bg-[#18181b] border border-[#27272a] px-1.5 py-0.5 rounded text-[10px]">
                Ctrl K
              </kbd>
            </button>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg border border-[#27272a] bg-[#09090b] text-[#a1a1aa] hover:text-white hover:border-[#6366f1]/50 transition-colors"
              title="Toggle Theme"
            >
              {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
          </div>
        </header>

        {/* Global Banner for Offline Mode if applicable */}
        <div className="bg-[#f59e0b]/10 border-b border-[#f59e0b]/20 px-6 py-2 flex items-center justify-between text-xs text-[#f59e0b]">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>Running in local extractive mode with verified AST &amp; BM25 indexing.</span>
          </div>
          <span className="font-mono text-[10px] bg-[#f59e0b]/20 px-1.5 py-0.5 rounded">v0.1.0</span>
        </div>

        {/* Page Outlet */}
        <main className="flex-1 p-6 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
