import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router";
import {
  User,
  Github,
  Shield,
  Activity,
  KeyRound,
  Eye,
  EyeOff,
  CheckCircle2,
  AlertCircle,
  Loader2,
  LogOut,
  Trash2,
  Save,
  Check,
  RefreshCw,
} from "lucide-react";
import { useAuthStore } from "../../stores/authStore";
import { getAccessToken, getCsrfTokenFromCookie } from "../../api/client";

interface UserProfile {
  id: string;
  email: string;
  name: string;
  avatar_url?: string;
  role: string;
  is_active: boolean;
  github?: {
    id?: number;
    login?: string;
    avatar_url?: string;
  };
  created_at?: string;
}

interface QuotaItem {
  current: number;
  limit: number;
  reset_at?: string;
}

interface UsageData {
  quotas: {
    questions?: QuotaItem;
    ingestions?: QuotaItem;
    reviews?: QuotaItem;
    tokens?: QuotaItem;
  };
}

export const SettingsPage: React.FC = () => {
  const navigate = useNavigate();
  const { user: authUser, setUser, logout } = useAuthStore();
  const [activeTab, setActiveTab] = useState<"profile" | "github" | "security" | "usage">("profile");

  // Profile State
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [profileName, setProfileName] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [profileMessage, setProfileMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // GitHub State
  const [githubPat, setGithubPat] = useState("");
  const [showPat, setShowPat] = useState(false);
  const [isTestingPat, setIsTestingPat] = useState(false);
  const [isSavingPat, setIsSavingPat] = useState(false);
  const [isRevokingPat, setIsRevokingPat] = useState(false);
  const [githubMessage, setGithubMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Security State
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [isLoggingOutAll, setIsLoggingOutAll] = useState(false);
  const [securityMessage, setSecurityMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Usage State
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [isLoadingUsage, setIsLoadingUsage] = useState(false);

  // Initial Fetch
  useEffect(() => {
    fetchProfile();
    fetchUsage();
  }, []);

  const fetchProfile = async () => {
    try {
      const token = getAccessToken();
      const res = await fetch("/api/v1/users/me", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data: UserProfile = await res.json();
        setProfile(data);
        setProfileName(data.name || "");
        setAvatarUrl(data.avatar_url || "");
        if (authUser) {
          setUser({
            ...authUser,
            name: data.name,
            role: data.role as "user" | "admin",
            github: data.github,
          });
        }
      }
    } catch {
      // Fallback to local auth store
    }
  };

  const fetchUsage = async () => {
    setIsLoadingUsage(true);
    try {
      const token = getAccessToken();
      const res = await fetch("/api/v1/users/me/usage", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data: UsageData = await res.json();
        setUsage(data);
      }
    } catch {
      // Keep silent
    } finally {
      setIsLoadingUsage(false);
    }
  };

  // Handle Profile Update
  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingProfile(true);
    setProfileMessage(null);
    try {
      const token = getAccessToken();
      const res = await fetch("/api/v1/users/me", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ name: profileName, avatar_url: avatarUrl || null }),
      });
      if (res.ok) {
        const updated = await res.json();
        setProfile(updated);
        setProfileMessage({ type: "success", text: "Profile updated successfully!" });
      } else {
        const err = await res.json();
        setProfileMessage({ type: "error", text: err.error?.message || "Failed to update profile." });
      }
    } catch {
      setProfileMessage({ type: "error", text: "Network error while saving profile." });
    } finally {
      setIsSavingProfile(false);
    }
  };

  // Handle GitHub PAT Test
  const handleTestPat = async () => {
    setIsTestingPat(true);
    setGithubMessage(null);
    try {
      const token = getAccessToken();
      const res = await fetch("/api/v1/users/me/github-token/test", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ token: githubPat || undefined }),
      });
      const data = await res.json();
      if (res.ok && data.valid) {
        setGithubMessage({
          type: "success",
          text: `Valid GitHub token! Authenticated as @${data.login || "user"}.`,
        });
      } else {
        setGithubMessage({
          type: "error",
          text: data.message || "Invalid GitHub token or insufficient permissions.",
        });
      }
    } catch {
      setGithubMessage({ type: "error", text: "Failed to connect to GitHub validation endpoint." });
    } finally {
      setIsTestingPat(false);
    }
  };

  // Handle GitHub PAT Save
  const handleSavePat = async () => {
    if (!githubPat.trim()) {
      setGithubMessage({ type: "error", text: "Please enter a personal access token." });
      return;
    }
    setIsSavingPat(true);
    setGithubMessage(null);
    try {
      const token = getAccessToken();
      const res = await fetch("/api/v1/users/me/github-token", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ token: githubPat }),
      });
      if (res.ok) {
        setGithubMessage({ type: "success", text: "GitHub PAT encrypted and saved successfully!" });
        setGithubPat("");
        await fetchProfile();
      } else {
        const err = await res.json();
        setGithubMessage({ type: "error", text: err.error?.message || "Failed to save token." });
      }
    } catch {
      setGithubMessage({ type: "error", text: "Network error saving GitHub token." });
    } finally {
      setIsSavingPat(false);
    }
  };

  // Handle GitHub PAT Revocation
  const handleRevokePat = async () => {
    if (!window.confirm("Are you sure you want to revoke your stored GitHub token?")) return;
    setIsRevokingPat(true);
    setGithubMessage(null);
    try {
      const token = getAccessToken();
      const res = await fetch("/api/v1/users/me/github-token", {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setGithubMessage({ type: "success", text: "GitHub access token revoked." });
        await fetchProfile();
      } else {
        setGithubMessage({ type: "error", text: "Failed to revoke token." });
      }
    } catch {
      setGithubMessage({ type: "error", text: "Network error revoking token." });
    } finally {
      setIsRevokingPat(false);
    }
  };

  // Handle Password Change
  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setSecurityMessage(null);

    if (newPassword.length < 12) {
      setSecurityMessage({ type: "error", text: "New password must be at least 12 characters long." });
      return;
    }
    if (newPassword !== confirmPassword) {
      setSecurityMessage({ type: "error", text: "New passwords do not match." });
      return;
    }

    setIsChangingPassword(true);
    try {
      const token = getAccessToken();
      const res = await fetch("/api/v1/users/me/password", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });
      if (res.ok) {
        setSecurityMessage({ type: "success", text: "Password changed successfully! Other sessions revoked." });
        setCurrentPassword("");
        setNewPassword("");
        setConfirmPassword("");
      } else {
        const err = await res.json();
        setSecurityMessage({ type: "error", text: err.error?.message || "Failed to update password." });
      }
    } catch {
      setSecurityMessage({ type: "error", text: "Network error changing password." });
    } finally {
      setIsChangingPassword(false);
    }
  };

  // Handle Logout All Devices
  const handleLogoutAll = async () => {
    if (!window.confirm("Are you sure you want to log out of all active devices?")) return;
    setIsLoggingOutAll(true);
    try {
      const token = getAccessToken();
      const csrfToken = getCsrfTokenFromCookie() || "";
      await fetch("/api/v1/auth/logout-all", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "X-CSRF-Token": csrfToken,
        },
      });
      logout();
      navigate("/login");
    } catch {
      logout();
      navigate("/login");
    } finally {
      setIsLoggingOutAll(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white text-balance">Account & System Settings</h1>
        <p className="text-sm text-[#a1a1aa] mt-1 text-pretty">
          Manage your personal details, GitHub PAT integration, security credentials, and view daily usage quotas.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#27272a] gap-2">
        <button
          onClick={() => setActiveTab("profile")}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px cursor-pointer ${
            activeTab === "profile"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-[#a1a1aa] hover:text-white"
          }`}
        >
          <User className="size-4" />
          Profile
        </button>
        <button
          onClick={() => setActiveTab("github")}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px cursor-pointer ${
            activeTab === "github"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-[#a1a1aa] hover:text-white"
          }`}
        >
          <Github className="size-4" />
          GitHub Integration
        </button>
        <button
          onClick={() => setActiveTab("security")}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px cursor-pointer ${
            activeTab === "security"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-[#a1a1aa] hover:text-white"
          }`}
        >
          <Shield className="size-4" />
          Security
        </button>
        <button
          onClick={() => setActiveTab("usage")}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px cursor-pointer ${
            activeTab === "usage"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-[#a1a1aa] hover:text-white"
          }`}
        >
          <Activity className="size-4" />
          Usage & Quotas
        </button>
      </div>

      {/* Tab 1: Profile */}
      {activeTab === "profile" && (
        <div className="bg-[#18181b] border border-[#27272a] rounded-xl p-6 shadow-sm space-y-6">
          <div>
            <h2 className="text-lg font-semibold text-white text-balance">Public Profile</h2>
            <p className="text-sm text-[#71717a] text-pretty">Manage how your name and identity appear across RepoGPT.</p>
          </div>

          {profileMessage && (
            <div
              className={`p-3 rounded-lg flex items-center gap-2 text-sm ${
                profileMessage.type === "success"
                  ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"
                  : "bg-red-500/10 border border-red-500/30 text-red-400"
              }`}
            >
              {profileMessage.type === "success" ? <CheckCircle2 className="size-4" /> : <AlertCircle className="size-4" />}
              {profileMessage.text}
            </div>
          )}

          <form onSubmit={handleSaveProfile} className="space-y-4 max-w-xl">
            <div>
              <label className="block text-xs font-semibold uppercase text-[#a1a1aa] mb-1">
                Full Name
              </label>
              <input
                type="text"
                value={profileName}
                onChange={(e) => setProfileName(e.target.value)}
                placeholder="Ada Lovelace"
                className="w-full bg-[#09090b] border border-[#27272a] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-[#a1a1aa] mb-1">
                Email Address
              </label>
              <input
                type="text"
                disabled
                value={profile?.email || authUser?.email || ""}
                className="w-full bg-[#09090b]/50 border border-[#27272a]/50 rounded-lg px-3 py-2 text-[#71717a] text-sm cursor-not-allowed"
              />
              <span className="text-[11px] text-[#71717a]">Email cannot be changed directly.</span>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-[#a1a1aa] mb-1">
                Avatar URL
              </label>
              <input
                type="url"
                value={avatarUrl}
                onChange={(e) => setAvatarUrl(e.target.value)}
                placeholder="https://example.com/avatar.png"
                className="w-full bg-[#09090b] border border-[#27272a] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div className="pt-2 flex items-center gap-4">
              <button
                type="submit"
                disabled={isSavingProfile}
                className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 cursor-pointer"
              >
                {isSavingProfile ? <Loader2 className="size-4 animate-spin" /> : <Save className="size-4" />}
                Save Profile
              </button>
              {profile?.created_at && (
                <span className="text-xs text-[#71717a] tabular-nums">
                  Member since {new Date(profile.created_at).toLocaleDateString()}
                </span>
              )}
            </div>
          </form>
        </div>
      )}

      {/* Tab 2: GitHub Integration */}
      {activeTab === "github" && (
        <div className="bg-[#18181b] border border-[#27272a] rounded-xl p-6 shadow-sm space-y-6">
          <div>
            <h2 className="text-lg font-semibold text-white text-balance">GitHub Integration & Personal Access Token</h2>
            <p className="text-sm text-[#71717a] text-pretty">
              RepoGPT connects to GitHub using a Personal Access Token (classic or fine-grained) to clone private
              repositories and publish intelligent pull request reviews.
            </p>
          </div>

          {/* Scopes Reminder Banner */}
          <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-4 flex items-start gap-3 text-sm text-emerald-200">
            <Github className="size-5 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-white">Required Permissions</p>
              <p className="text-xs text-emerald-300/80 mt-0.5 text-pretty">
                Ensure your Personal Access Token includes <code className="bg-emerald-500/20 px-1.5 py-0.5 rounded text-white font-mono text-[11px]">repo</code> (Full repository read/write access) and <code className="bg-emerald-500/20 px-1.5 py-0.5 rounded text-white font-mono text-[11px]">read:user</code> (Account profile identity) scopes.
              </p>
            </div>
          </div>

          {githubMessage && (
            <div
              className={`p-3 rounded-lg flex items-center gap-2 text-sm ${
                githubMessage.type === "success"
                  ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"
                  : "bg-red-500/10 border border-red-500/30 text-red-400"
              }`}
            >
              {githubMessage.type === "success" ? <CheckCircle2 className="size-4" /> : <AlertCircle className="size-4" />}
              {githubMessage.text}
            </div>
          )}

          {/* Current Status */}
          <div className="flex items-center justify-between p-4 bg-[#09090b] rounded-lg border border-[#27272a]">
            <div className="flex items-center gap-3">
              <div className="size-10 rounded-full bg-[#27272a] flex items-center justify-center text-white">
                <Github className="size-5" />
              </div>
              <div>
                <p className="text-sm font-medium text-white">
                  {profile?.github?.login ? (
                    <>Connected as <span className="text-emerald-400">@{profile.github.login}</span></>
                  ) : (
                    "No GitHub Account Connected"
                  )}
                </p>
                <p className="text-xs text-[#71717a]">
                  {profile?.github?.login ? "Tokens are encrypted using AES-128 Fernet at rest." : "Add a PAT below to enable repository syncing."}
                </p>
              </div>
            </div>
            {profile?.github?.login && (
              <button
                onClick={handleRevokePat}
                disabled={isRevokingPat}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 rounded-lg text-xs font-medium transition-colors cursor-pointer"
              >
                {isRevokingPat ? <Loader2 className="size-3.5 animate-spin" /> : <Trash2 className="size-3.5" />}
                Revoke Token
              </button>
            )}
          </div>

          {/* PAT Input */}
          <div className="space-y-4 max-w-xl">
            <div>
              <label className="block text-xs font-semibold uppercase text-[#a1a1aa] mb-1">
                Personal Access Token (PAT)
              </label>
              <div className="relative">
                <input
                  type={showPat ? "text" : "password"}
                  value={githubPat}
                  onChange={(e) => setGithubPat(e.target.value)}
                  placeholder="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                  className="w-full bg-[#09090b] border border-[#27272a] rounded-lg pl-3 pr-10 py-2 text-white text-sm font-mono focus:outline-none focus:border-emerald-500"
                />
                <button
                  type="button"
                  aria-label={showPat ? "Hide personal access token" : "Show personal access token"}
                  onClick={() => setShowPat(!showPat)}
                  className="absolute right-3 top-2.5 text-[#71717a] hover:text-white transition-colors cursor-pointer"
                >
                  {showPat ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleSavePat}
                disabled={isSavingPat || !githubPat}
                className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 cursor-pointer"
              >
                {isSavingPat ? <Loader2 className="size-4 animate-spin" /> : <Save className="size-4" />}
                Save & Encrypt
              </button>
              <button
                type="button"
                onClick={handleTestPat}
                disabled={isTestingPat}
                className="inline-flex items-center gap-2 px-4 py-2 bg-[#27272a] hover:bg-[#3f3f46] text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 cursor-pointer"
              >
                {isTestingPat ? <Loader2 className="size-4 animate-spin" /> : <Check className="size-4" />}
                Test Connection
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Security */}
      {activeTab === "security" && (
        <div className="bg-[#18181b] border border-[#27272a] rounded-xl p-6 shadow-sm space-y-8">
          {/* Change Password Form */}
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-semibold text-white text-balance">Password & Authentication</h2>
              <p className="text-sm text-[#71717a] text-pretty">
                Update your password. Changing your password will automatically invalidate all other active sessions.
              </p>
            </div>

            {securityMessage && (
              <div
                className={`p-3 rounded-lg flex items-center gap-2 text-sm ${
                  securityMessage.type === "success"
                    ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"
                    : "bg-red-500/10 border border-red-500/30 text-red-400"
                }`}
              >
                {securityMessage.type === "success" ? <CheckCircle2 className="size-4" /> : <AlertCircle className="size-4" />}
                {securityMessage.text}
              </div>
            )}

            <form onSubmit={handleChangePassword} className="space-y-4 max-w-xl">
              <div>
                <label className="block text-xs font-semibold uppercase text-[#a1a1aa] mb-1">
                  Current Password
                </label>
                <input
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  className="w-full bg-[#09090b] border border-[#27272a] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-[#a1a1aa] mb-1">
                  New Password (min 12 chars)
                </label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full bg-[#09090b] border border-[#27272a] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-[#a1a1aa] mb-1">
                  Confirm New Password
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full bg-[#09090b] border border-[#27272a] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={isChangingPassword}
                className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 cursor-pointer"
              >
                {isChangingPassword ? <Loader2 className="size-4 animate-spin" /> : <KeyRound className="size-4" />}
                Update Password
              </button>
            </form>
          </div>

          <hr className="border-[#27272a]" />

          {/* Active Sessions */}
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold text-white text-balance">Active Sessions</h2>
              <p className="text-sm text-[#71717a] text-pretty">
                You are currently signed in from this browser. If you notice any suspicious activity, immediately revoke
                all device sessions.
              </p>
            </div>

            <div className="flex items-center justify-between p-4 bg-[#09090b] rounded-lg border border-[#27272a]">
              <div>
                <p className="text-sm font-medium text-white">Current Browser Session</p>
                <p className="text-xs text-emerald-400">Active now • Automatic rotating refresh family</p>
              </div>
              <button
                onClick={handleLogoutAll}
                disabled={isLoggingOutAll}
                className="inline-flex items-center gap-1.5 px-3 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 rounded-lg text-xs font-semibold transition-colors disabled:opacity-50 cursor-pointer"
              >
                {isLoggingOutAll ? <Loader2 className="size-3.5 animate-spin" /> : <LogOut className="size-3.5" />}
                Log Out of All Devices
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Usage & Quotas */}
      {activeTab === "usage" && (
        <div className="bg-[#18181b] border border-[#27272a] rounded-xl p-6 shadow-sm space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-white text-balance">Daily Quotas & Usage</h2>
              <p className="text-sm text-[#71717a] text-pretty">
                All quotas reset daily at midnight UTC (00:00 UTC).
              </p>
            </div>
            <button
              onClick={fetchUsage}
              disabled={isLoadingUsage}
              aria-label="Refresh daily usage"
              className="p-2 text-[#a1a1aa] hover:text-white rounded-lg hover:bg-[#27272a] transition-colors cursor-pointer"
            >
              <RefreshCw className={`size-4 ${isLoadingUsage ? "animate-spin" : ""}`} />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Questions Quota */}
            <QuotaCard
              title="Questions Asked"
              current={usage?.quotas?.questions?.current ?? 0}
              limit={usage?.quotas?.questions?.limit ?? 100}
              unit="queries"
            />

            {/* Ingestions Quota */}
            <QuotaCard
              title="Repository Ingestions"
              current={usage?.quotas?.ingestions?.current ?? 0}
              limit={usage?.quotas?.ingestions?.limit ?? 10}
              unit="repos"
            />

            {/* PR Reviews Quota */}
            <QuotaCard
              title="Pull Request Reviews"
              current={usage?.quotas?.reviews?.current ?? 0}
              limit={usage?.quotas?.reviews?.limit ?? 20}
              unit="reviews"
            />

            {/* Token Quota */}
            <QuotaCard
              title="Daily LLM Token Usage"
              current={usage?.quotas?.tokens?.current ?? 0}
              limit={usage?.quotas?.tokens?.limit ?? 2000000}
              unit="tokens"
            />
          </div>
        </div>
      )}
    </div>
  );
};

interface QuotaCardProps {
  title: string;
  current: number;
  limit: number;
  unit: string;
}

const QuotaCard: React.FC<QuotaCardProps> = ({ title, current, limit, unit }) => {
  const percentage = Math.min(100, Math.round((current / (limit || 1)) * 100));

  return (
    <div className="bg-[#09090b] border border-[#27272a] rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-white">{title}</span>
        <span className="text-xs text-[#a1a1aa] font-mono tabular-nums">
          {current.toLocaleString()} / {limit.toLocaleString()} {unit}
        </span>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-[#27272a] rounded-full h-2 overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${
            percentage >= 90 ? "bg-red-500" : percentage >= 75 ? "bg-amber-500" : "bg-emerald-500"
          }`}
          style={{ width: `${percentage}%` }}
        />
      </div>

      <div className="flex justify-between items-center text-[11px] text-[#71717a]">
        <span className="tabular-nums">{percentage}% utilized</span>
        <span>Resets at 00:00 UTC</span>
      </div>
    </div>
  );
};
