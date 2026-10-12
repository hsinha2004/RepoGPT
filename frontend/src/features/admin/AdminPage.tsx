import { useState, useEffect } from "react";
import {
  ShieldAlert,
  Users,
  Activity,
  Server,
  FileText,
  Search,
  KeyRound,
  RotateCcw,
  CheckCircle2,
  X,
  RefreshCw,
  FolderGit2,
  Cpu,
} from "lucide-react";
import { getAccessToken } from "../../api/client";

interface AdminUser {
  id: string;
  email: string;
  name: string;
  role: "user" | "admin";
  is_active: boolean;
  created_at: string;
  last_login_at?: string | null;
}

interface AdminJob {
  id: string;
  type: string;
  repo_id: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  stage: string;
  progress: number;
  message: string;
  error?: string | null;
  created_at: string;
}

interface AdminStats {
  total_users: number;
  total_repositories: number;
  total_jobs: number;
  system_status: string;
  llm_provider: string;
  vector_store: string;
}

interface AuditLog {
  _id: string;
  actor_id: string;
  action: string;
  target_type: string;
  target_id: string;
  ip?: string;
  created_at: string;
  metadata?: Record<string, unknown>;
}

export const AdminPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"users" | "jobs" | "stats" | "audit">("users");

  // State
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [jobs, setJobs] = useState<AdminJob[]>([]);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Filters & Modals
  const [userSearch, setUserSearch] = useState("");
  const [jobStatusFilter, setJobStatusFilter] = useState("all");
  const [auditActionFilter, setAuditActionFilter] = useState("all");
  const [resetPasswordUserId, setResetPasswordUserId] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [isResetting, setIsResetting] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchActiveTabData();
  }, [activeTab]);

  const fetchActiveTabData = async () => {
    setIsLoading(true);
    setSuccessMessage(null);
    const token = getAccessToken();
    const headers = {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };

    try {
      if (activeTab === "users") {
        const res = await fetch("/api/v1/admin/users", { headers });
        if (res.ok) setUsers(await res.json());
      } else if (activeTab === "jobs") {
        const res = await fetch("/api/v1/admin/jobs", { headers });
        if (res.ok) setJobs(await res.json());
      } else if (activeTab === "stats") {
        const res = await fetch("/api/v1/admin/stats", { headers });
        if (res.ok) setStats(await res.json());
      } else if (activeTab === "audit") {
        const res = await fetch("/api/v1/admin/audit-logs", { headers });
        if (res.ok) setAuditLogs(await res.json());
      }
    } catch {
      // Handle fetch error
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleUserActive = async (user: AdminUser) => {
    try {
      const token = getAccessToken();
      const res = await fetch(`/api/v1/admin/users/${user.id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ is_active: !user.is_active }),
      });
      if (res.ok) {
        setUsers((prev) =>
          prev.map((u) => (u.id === user.id ? { ...u, is_active: !u.is_active } : u))
        );
      }
    } catch {
      alert("Failed to update user status.");
    }
  };

  const handleToggleUserRole = async (user: AdminUser) => {
    const nextRole = user.role === "admin" ? "user" : "admin";
    try {
      const token = getAccessToken();
      const res = await fetch(`/api/v1/admin/users/${user.id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ role: nextRole }),
      });
      if (res.ok) {
        setUsers((prev) =>
          prev.map((u) => (u.id === user.id ? { ...u, role: nextRole } : u))
        );
      }
    } catch {
      alert("Failed to update user role.");
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resetPasswordUserId || !newPassword) return;
    setIsResetting(true);
    try {
      const token = getAccessToken();
      const res = await fetch(`/api/v1/admin/users/${resetPasswordUserId}/reset-password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ new_password: newPassword }),
      });
      if (res.ok) {
        setResetPasswordUserId(null);
        setNewPassword("");
        setSuccessMessage("Password reset successfully. User must change on next login.");
      } else {
        alert("Failed to reset password.");
      }
    } catch {
      alert("Failed to reset password.");
    } finally {
      setIsResetting(false);
    }
  };

  const handleRetryJob = async (jobId: string) => {
    try {
      const token = getAccessToken();
      const res = await fetch(`/api/v1/admin/jobs/${jobId}/retry`, {
        method: "POST",
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (res.ok) {
        fetchActiveTabData();
      }
    } catch {
      alert("Failed to retry job.");
    }
  };

  const filteredUsers = users.filter(
    (u) =>
      u.email.toLowerCase().includes(userSearch.toLowerCase()) ||
      u.name.toLowerCase().includes(userSearch.toLowerCase())
  );

  const filteredJobs = jobs.filter((j) => {
    if (jobStatusFilter === "all") return true;
    return j.status === jobStatusFilter;
  });

  const filteredAuditLogs = auditLogs.filter((l) => {
    if (auditActionFilter === "all") return true;
    return l.action.toLowerCase().includes(auditActionFilter.toLowerCase());
  });

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-[#27272a]">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="size-8 rounded-lg bg-rose-500/10 text-rose-400 flex items-center justify-center font-bold">
              <ShieldAlert className="size-5" />
            </div>
            <h1 className="text-xl font-bold text-white text-balance">Administration Panel</h1>
          </div>
          <p className="text-xs text-zinc-400 mt-1 text-pretty">
            System administration, user access control, background jobs, and compliance audit logs (§11.15, §12).
          </p>
        </div>

        <button
          onClick={fetchActiveTabData}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-[#18181b] hover:bg-zinc-800 border border-[#27272a] rounded-lg text-xs font-medium text-zinc-300 transition-colors cursor-pointer"
        >
          <RefreshCw className={`size-3.5 ${isLoading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {successMessage && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-xs text-emerald-400 flex items-center gap-2">
          <CheckCircle2 className="size-4 shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-[#27272a]">
        <button
          onClick={() => setActiveTab("users")}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px cursor-pointer ${
            activeTab === "users"
              ? "border-emerald-500 text-white"
              : "border-transparent text-zinc-400 hover:text-zinc-200"
          }`}
        >
          <Users className="size-4" />
          Users & Access
        </button>

        <button
          onClick={() => setActiveTab("jobs")}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px cursor-pointer ${
            activeTab === "jobs"
              ? "border-emerald-500 text-white"
              : "border-transparent text-zinc-400 hover:text-zinc-200"
          }`}
        >
          <Activity className="size-4" />
          Background Jobs
        </button>

        <button
          onClick={() => setActiveTab("stats")}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px cursor-pointer ${
            activeTab === "stats"
              ? "border-emerald-500 text-white"
              : "border-transparent text-zinc-400 hover:text-zinc-200"
          }`}
        >
          <Server className="size-4" />
          System Telemetry
        </button>

        <button
          onClick={() => setActiveTab("audit")}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px cursor-pointer ${
            activeTab === "audit"
              ? "border-emerald-500 text-white"
              : "border-transparent text-zinc-400 hover:text-zinc-200"
          }`}
        >
          <FileText className="size-4" />
          Security Audit Logs
        </button>
      </div>

      {/* TAB 1: USERS */}
      {activeTab === "users" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="relative w-72">
              <Search className="size-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
              <input
                type="text"
                placeholder="Search by name or email..."
                value={userSearch}
                onChange={(e) => setUserSearch(e.target.value)}
                className="w-full bg-[#18181b] border border-[#27272a] rounded-lg pl-8 pr-3 py-1.5 text-xs text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-emerald-500"
              />
            </div>
            <span className="text-xs text-zinc-400 tabular-nums">{filteredUsers.length} registered accounts</span>
          </div>

          <div className="border border-[#27272a] rounded-xl bg-[#111113] overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#18181b] border-b border-[#27272a] text-zinc-400 uppercase font-mono text-[11px]">
                <tr>
                  <th className="py-2.5 px-4">User</th>
                  <th className="py-2.5 px-4">Role</th>
                  <th className="py-2.5 px-4">Status</th>
                  <th className="py-2.5 px-4">Created</th>
                  <th className="py-2.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#27272a]">
                {filteredUsers.map((u) => (
                  <tr key={u.id} className="hover:bg-zinc-800/30">
                    <td className="py-2.5 px-4">
                      <div className="font-medium text-white">{u.name}</div>
                      <div className="text-[11px] font-mono text-zinc-400">{u.email}</div>
                    </td>
                    <td className="py-2.5 px-4">
                      <button
                        onClick={() => handleToggleUserRole(u)}
                        title="Click to toggle role"
                        className={`px-2 py-0.5 rounded-full text-[10px] font-mono uppercase font-semibold border cursor-pointer ${
                          u.role === "admin"
                            ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                            : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                        }`}
                      >
                        {u.role}
                      </button>
                    </td>
                    <td className="py-2.5 px-4">
                      <button
                        onClick={() => handleToggleUserActive(u)}
                        title="Click to toggle status"
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border cursor-pointer ${
                          u.is_active
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                            : "bg-zinc-800 text-zinc-500 border-zinc-700"
                        }`}
                      >
                        {u.is_active ? "Active" : "Disabled"}
                      </button>
                    </td>
                    <td className="py-2.5 px-4 font-mono text-zinc-400 tabular-nums">
                      {new Date(u.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-2.5 px-4 text-right space-x-2">
                      <button
                        onClick={() => {
                          setResetPasswordUserId(u.id);
                          setNewPassword("");
                        }}
                        className="p-1 rounded bg-[#18181b] hover:bg-zinc-800 text-zinc-300 hover:text-white border border-[#27272a] text-xs inline-flex items-center gap-1 px-2 py-1 cursor-pointer"
                      >
                        <KeyRound className="size-3.5 text-amber-400" />
                        Reset Pass
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: JOBS */}
      {activeTab === "jobs" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <select
              value={jobStatusFilter}
              onChange={(e) => setJobStatusFilter(e.target.value)}
              className="bg-[#18181b] border border-[#27272a] rounded-lg px-2.5 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-emerald-500"
            >
              <option value="all">All Job Statuses</option>
              <option value="queued">Queued</option>
              <option value="running">Running</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </select>
            <span className="text-xs text-zinc-400 tabular-nums">{filteredJobs.length} jobs</span>
          </div>

          <div className="border border-[#27272a] rounded-xl bg-[#111113] overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#18181b] border-b border-[#27272a] text-zinc-400 uppercase font-mono text-[11px]">
                <tr>
                  <th className="py-2.5 px-4">Job Type</th>
                  <th className="py-2.5 px-4">Status</th>
                  <th className="py-2.5 px-4">Progress / Stage</th>
                  <th className="py-2.5 px-4">Message</th>
                  <th className="py-2.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#27272a]">
                {filteredJobs.map((j) => (
                  <tr key={j.id} className="hover:bg-zinc-800/30">
                    <td className="py-2.5 px-4 font-mono text-white">{j.type}</td>
                    <td className="py-2.5 px-4">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-mono uppercase ${
                          j.status === "completed"
                            ? "bg-emerald-500/10 text-emerald-400"
                            : j.status === "running"
                            ? "bg-emerald-500/10 text-emerald-400 animate-pulse"
                            : j.status === "failed"
                            ? "bg-red-500/10 text-red-400"
                            : "bg-zinc-800 text-zinc-400"
                        }`}
                      >
                        {j.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-4 font-mono text-zinc-300 tabular-nums">
                      {j.progress}% • {j.stage}
                    </td>
                    <td className="py-2.5 px-4 text-zinc-400 max-w-xs truncate">{j.message}</td>
                    <td className="py-2.5 px-4 text-right">
                      {j.status === "failed" && (
                        <button
                          onClick={() => handleRetryJob(j.id)}
                          className="inline-flex items-center gap-1 px-2 py-1 rounded bg-[#18181b] hover:bg-zinc-800 text-zinc-300 hover:text-white border border-[#27272a] text-xs cursor-pointer"
                        >
                          <RotateCcw className="size-3.5 text-emerald-400" />
                          Retry
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: STATS */}
      {activeTab === "stats" && stats && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-[#111113] border border-[#27272a] rounded-xl p-5 space-y-2">
            <div className="text-xs text-zinc-400 flex items-center justify-between">
              <span>Total Accounts</span>
              <Users className="size-4 text-emerald-400" />
            </div>
            <div className="text-3xl font-bold text-white tabular-nums">{stats.total_users}</div>
            <p className="text-[11px] text-zinc-500">Registered users in database</p>
          </div>

          <div className="bg-[#111113] border border-[#27272a] rounded-xl p-5 space-y-2">
            <div className="text-xs text-zinc-400 flex items-center justify-between">
              <span>Repositories</span>
              <FolderGit2 className="size-4 text-emerald-400" />
            </div>
            <div className="text-3xl font-bold text-white tabular-nums">{stats.total_repositories}</div>
            <p className="text-[11px] text-zinc-500">Indexed codebases</p>
          </div>

          <div className="bg-[#111113] border border-[#27272a] rounded-xl p-5 space-y-2">
            <div className="text-xs text-zinc-400 flex items-center justify-between">
              <span>Background Tasks</span>
              <Cpu className="size-4 text-amber-400" />
            </div>
            <div className="text-3xl font-bold text-white tabular-nums">{stats.total_jobs}</div>
            <p className="text-[11px] text-zinc-500">Ingestion and sync jobs</p>
          </div>
        </div>
      )}

      {/* TAB 4: AUDIT LOGS */}
      {activeTab === "audit" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <select
              value={auditActionFilter}
              onChange={(e) => setAuditActionFilter(e.target.value)}
              className="bg-[#18181b] border border-[#27272a] rounded-lg px-2.5 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-emerald-500"
            >
              <option value="all">All Audit Actions</option>
              <option value="login">Login</option>
              <option value="admin">Admin Operations</option>
              <option value="repo">Repo Lifecycle</option>
            </select>
            <span className="text-xs text-zinc-400 tabular-nums">{filteredAuditLogs.length} audit entries</span>
          </div>

          <div className="border border-[#27272a] rounded-xl bg-[#111113] overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#18181b] border-b border-[#27272a] text-zinc-400 uppercase font-mono text-[11px]">
                <tr>
                  <th className="py-2.5 px-4">Action</th>
                  <th className="py-2.5 px-4">Actor ID</th>
                  <th className="py-2.5 px-4">Target Type / ID</th>
                  <th className="py-2.5 px-4">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#27272a]">
                {filteredAuditLogs.map((log) => (
                  <tr key={log._id} className="hover:bg-zinc-800/30">
                    <td className="py-2.5 px-4 font-mono font-semibold text-emerald-400">
                      {log.action}
                    </td>
                    <td className="py-2.5 px-4 font-mono text-zinc-300">{log.actor_id}</td>
                    <td className="py-2.5 px-4 font-mono text-zinc-400">
                      {log.target_type}:{log.target_id}
                    </td>
                    <td className="py-2.5 px-4 font-mono text-zinc-500 tabular-nums">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Reset Password Modal */}
      {resetPasswordUserId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-[#111113] border border-[#27272a] rounded-xl max-w-sm w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-[#27272a]">
              <h3 className="text-sm font-semibold text-white">Reset Account Password</h3>
              <button
                type="button"
                onClick={() => setResetPasswordUserId(null)}
                aria-label="Close dialog"
                className="text-zinc-400 hover:text-white cursor-pointer"
              >
                <X className="size-4" />
              </button>
            </div>
            <form onSubmit={handleResetPassword} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">
                  New Password (min 8 chars)
                </label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  minLength={8}
                  required
                  placeholder="Enter temporary password..."
                  className="w-full bg-[#18181b] border border-[#27272a] rounded-lg px-3 py-1.5 text-xs text-zinc-100 focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setResetPasswordUserId(null)}
                  className="px-3 py-1.5 text-xs text-zinc-400 hover:text-white cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isResetting || newPassword.length < 8}
                  className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium transition-colors cursor-pointer"
                >
                  {isResetting ? "Resetting..." : "Save Password"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
