import React, { useState } from "react";
import { useParams, Link } from "react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  GitPullRequest,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  Upload,
  RefreshCw,
  Download,
  Filter,
  Check,
  X,
  Edit2,
  ChevronRight,
  Sparkles,
  ArrowLeft,
  Send,
  Copy,
  Info,
  Clock,
} from "lucide-react";
import { apiClient, getAccessToken } from "../../api/client";

export interface FindingEvidence {
  source_id: string;
  path: string;
  start_line: number;
  end_line: number;
}

export interface ReviewFinding {
  id: string;
  path: string;
  start_line: number;
  end_line: number;
  side: "LEFT" | "RIGHT";
  category:
    | "bug"
    | "security"
    | "performance"
    | "error_handling"
    | "concurrency"
    | "api_contract"
    | "testing"
    | "maintainability"
    | "documentation";
  severity: "critical" | "high" | "medium" | "low" | "info";
  title: string;
  explanation: string;
  suggestion?: string | null;
  suggested_code?: string | null;
  evidence: FindingEvidence[];
  confidence: number;
  origin: "llm" | "static";
  status: "pending" | "accepted" | "rejected" | "edited";
  user_note?: string | null;
}

export interface ReviewStats {
  files_changed: number;
  lines_added: number;
  lines_deleted: number;
  findings_count: number;
  accepted_count: number;
  rejected_count: number;
}

export interface ReviewSource {
  type: "github" | "upload" | "webhook";
  pr_number?: number;
  pr_url?: string;
  base_sha?: string;
  head_sha?: string;
  patch_filename?: string;
}

export interface ReviewDoc {
  id: string;
  repo_id: string;
  user_id: string;
  source: ReviewSource;
  status: "pending" | "running" | "completed" | "failed";
  risk_level: "low" | "medium" | "high" | "critical";
  stats: ReviewStats;
  summary: string;
  file_walkthrough: Array<{
    path: string;
    added_lines: number;
    deleted_lines: number;
    findings_count: number;
  }>;
  findings: ReviewFinding[];
  general_comments: Array<{
    title: string;
    explanation: string;
    severity?: string;
  }>;
  published_to_github: boolean;
  github_review_id?: string | null;
  github_review_url?: string | null;
  error?: string | null;
  indexed_commit_mismatch: boolean;
  created_at: string;
  updated_at: string;
}

export const ReviewsPage: React.FC = () => {
  const { repoId } = useParams<{ repoId: string }>();
  const queryClient = useQueryClient();

  const [selectedReviewId, setSelectedReviewId] = useState<string | null>(null);
  const [triggerTab, setTriggerTab] = useState<"github" | "upload">("github");
  const [prUrl, setPrUrl] = useState("");
  const [patToken, setPatToken] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // Filters
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [fileFilter, setFileFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Edit Finding State
  const [editingFindingId, setEditingFindingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editExplanation, setEditExplanation] = useState("");
  const [editSuggestion, setEditSuggestion] = useState("");
  const [editSeverity, setEditSeverity] = useState<ReviewFinding["severity"]>("medium");
  const [editNote, setEditNote] = useState("");

  // Publish Modal State
  const [publishModalOpen, setPublishModalOpen] = useState(false);
  const [publishToken, setPublishToken] = useState("");
  const [copiedCodeId, setCopiedCodeId] = useState<string | null>(null);

  // 1. Fetch Repo Details
  useQuery({
    queryKey: ["repo", repoId],
    queryFn: async () => {
      const res = await apiClient.GET("/api/v1/repos/{repo_id}", {
        params: { path: { repo_id: repoId! } },
      });
      return res.data;
    },
    enabled: !!repoId,
  });

  // 2. Fetch Reviews List
  const {
    data: reviews = [],
    isLoading: listLoading,
    refetch: refetchReviews,
  } = useQuery<ReviewDoc[]>({
    queryKey: ["repo-reviews", repoId],
    queryFn: async () => {
      const res = await apiClient.GET("/api/v1/repos/{repo_id}/reviews", {
        params: { path: { repo_id: repoId! } },
      });
      if (res.error) throw new Error("Failed to load reviews");
      return (res.data as unknown as ReviewDoc[]) || [];
    },
    enabled: !!repoId,
  });

  // 3. Fetch Selected Review Details
  const {
    data: review,
    isLoading: reviewLoading,
  } = useQuery<ReviewDoc>({
    queryKey: ["review-detail", selectedReviewId],
    queryFn: async () => {
      const res = await apiClient.GET("/api/v1/reviews/{review_id}", {
        params: { path: { review_id: selectedReviewId! } },
      });
      if (res.error) throw new Error("Failed to load review details");
      return res.data as unknown as ReviewDoc;
    },
    enabled: !!selectedReviewId,
  });

  // Trigger Review from GitHub PR
  const prReviewMutation = useMutation({
    mutationFn: async () => {
      const token = getAccessToken();
      const res = await fetch(`/api/v1/repos/${repoId}/reviews`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ pr_url: prUrl }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Request failed" }));
        throw new Error(err.detail || "Failed to trigger PR review");
      }
      return (await res.json()) as ReviewDoc;
    },
    onSuccess: (newReview) => {
      queryClient.invalidateQueries({ queryKey: ["repo-reviews", repoId] });
      setSelectedReviewId(newReview.id);
      setPrUrl("");
    },
  });

  // Trigger Review from Diff Upload
  const uploadReviewMutation = useMutation({
    mutationFn: async () => {
      if (!selectedFile) throw new Error("Please select a .diff or .patch file");
      const formData = new FormData();
      formData.append("file", selectedFile);

      const token = getAccessToken();
      const res = await fetch(`/api/v1/repos/${repoId}/reviews`, {
        method: "POST",
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(err.detail || "Failed to trigger diff review");
      }
      return (await res.json()) as ReviewDoc;
    },
    onSuccess: (newReview) => {
      queryClient.invalidateQueries({ queryKey: ["repo-reviews", repoId] });
      setSelectedReviewId(newReview.id);
      setSelectedFile(null);
    },
  });

  // Update Finding Acceptance / Status / Content
  const updateFindingMutation = useMutation({
    mutationFn: async ({
      findingId,
      updates,
    }: {
      findingId: string;
      updates: Partial<ReviewFinding>;
    }) => {
      const res = await apiClient.PATCH("/api/v1/reviews/{review_id}/findings/{finding_id}", {
        params: { path: { review_id: selectedReviewId!, finding_id: findingId } },
        body: updates,
      });
      if (res.error) throw new Error("Failed to update finding");
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["review-detail", selectedReviewId] });
      queryClient.invalidateQueries({ queryKey: ["repo-reviews", repoId] });
      setEditingFindingId(null);
    },
  });

  // Publish to GitHub
  const publishMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.POST("/api/v1/reviews/{review_id}/publish", {
        params: { path: { review_id: selectedReviewId! } },
        body: { comments_only: true, include_general_summary: true, github_token: publishToken || undefined },
      });
      if (res.error) throw new Error("Failed to publish review to GitHub");
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["review-detail", selectedReviewId] });
      setPublishModalOpen(false);
    },
  });

  const handleStartEdit = (f: ReviewFinding) => {
    setEditingFindingId(f.id);
    setEditTitle(f.title);
    setEditExplanation(f.explanation);
    setEditSuggestion(f.suggestion || "");
    setEditSeverity(f.severity);
    setEditNote(f.user_note || "");
  };

  const handleSaveEdit = (findingId: string) => {
    updateFindingMutation.mutate({
      findingId,
      updates: {
        title: editTitle,
        explanation: editExplanation,
        suggestion: editSuggestion,
        severity: editSeverity,
        user_note: editNote,
        status: "edited",
      },
    });
  };

  const handleBulkAction = (action: "accepted" | "rejected") => {
    if (!review) return;
    review.findings
      .filter((f) => f.status === "pending")
      .forEach((f) => {
        updateFindingMutation.mutate({
          findingId: f.id,
          updates: { status: action },
        });
      });
  };

  const handleCopyCode = (id: string, code: string) => {
    navigator.clipboard.writeText(code);
    setCopiedCodeId(id);
    setTimeout(() => setCopiedCodeId(null), 2000);
  };

  // Filtered Findings
  const filteredFindings = (review?.findings || []).filter((f) => {
    if (severityFilter !== "all" && f.severity !== severityFilter) return false;
    if (categoryFilter !== "all" && f.category !== categoryFilter) return false;
    if (statusFilter !== "all" && f.status !== statusFilter) return false;
    if (fileFilter !== "all" && f.path !== fileFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const match =
        f.title.toLowerCase().includes(q) ||
        f.explanation.toLowerCase().includes(q) ||
        f.path.toLowerCase().includes(q);
      if (!match) return false;
    }
    return true;
  });

  // Unique files for dropdown
  const uniqueFiles = Array.from(new Set((review?.findings || []).map((f) => f.path)));

  const severityBadge = (severity: string) => {
    switch (severity) {
      case "critical":
        return "bg-rose-500/10 text-rose-400 border-rose-500/30";
      case "high":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30";
      case "medium":
        return "bg-yellow-500/10 text-yellow-400 border-yellow-500/30";
      case "low":
        return "bg-blue-500/10 text-blue-400 border-blue-500/30";
      default:
        return "bg-zinc-800 text-zinc-400 border-zinc-700";
    }
  };

  const statusBadge = (status: string) => {
    switch (status) {
      case "accepted":
        return "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
      case "rejected":
        return "bg-zinc-800 text-zinc-500 line-through border-zinc-700";
      case "edited":
        return "bg-indigo-500/15 text-indigo-400 border-indigo-500/30";
      default:
        return "bg-amber-500/10 text-amber-400 border-amber-500/20";
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-20">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#27272a] pb-4">
        <div className="flex items-center gap-3">
          <div className="size-9 rounded-lg bg-emerald-500/10 border border-emerald-500/25 flex items-center justify-center text-emerald-400">
            <GitPullRequest className="size-4" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-white text-balance">
              Pull Request & Code Reviews
            </h1>
            <p className="text-xs text-[#71717a] text-pretty">
              Context-aware pull request review, bug & security finding verification, and GitHub publishing.
            </p>
          </div>
        </div>
      </div>

      {/* Main Review View Toggle */}
      {!selectedReviewId ? (
        <div className="space-y-6">
          {/* Top Banner & Trigger Form */}
          <div className="p-6 rounded-2xl bg-[#111113] border border-[#27272a] space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#27272a] pb-4">
              <div>
                <h2 className="text-base font-semibold text-white flex items-center gap-2 text-balance">
                  <Sparkles className="size-4 text-emerald-400" />
                  Trigger Automated Pull Request Review
                </h2>
                <p className="text-xs text-zinc-400 text-pretty">
                  Analyze pull request changes against symbol graph, callers, and test conventions.
                </p>
              </div>

              {/* Tabs */}
              <div className="flex items-center p-1 rounded-xl bg-[#18181b] border border-[#27272a] self-start sm:self-auto">
                <button
                  type="button"
                  onClick={() => setTriggerTab("github")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                    triggerTab === "github"
                      ? "bg-emerald-600 text-white shadow-xs"
                      : "text-zinc-400 hover:text-white"
                  }`}
                >
                  GitHub PR URL
                </button>
                <button
                  type="button"
                  onClick={() => setTriggerTab("upload")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                    triggerTab === "upload"
                      ? "bg-emerald-600 text-white shadow-xs"
                      : "text-zinc-400 hover:text-white"
                  }`}
                >
                  Upload Diff / Patch
                </button>
              </div>
            </div>

            {triggerTab === "github" ? (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  if (prUrl) prReviewMutation.mutate();
                }}
                className="space-y-4"
              >
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div className="md:col-span-2 space-y-1.5">
                    <label className="text-xs font-medium text-zinc-300">
                      GitHub Pull Request URL
                    </label>
                    <input
                      type="url"
                      placeholder="https://github.com/owner/repository/pull/123"
                      value={prUrl}
                      onChange={(e) => setPrUrl(e.target.value)}
                      required
                      className="w-full px-3.5 py-2 rounded-xl bg-[#18181b] border border-[#27272a] text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-[#6366f1]"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-zinc-300">
                      GitHub PAT (Optional)
                    </label>
                    <input
                      type="password"
                      placeholder="ghp_... (default token if blank)"
                      value={patToken}
                      onChange={(e) => setPatToken(e.target.value)}
                      className="w-full px-3.5 py-2 rounded-xl bg-[#18181b] border border-[#27272a] text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-[#6366f1]"
                    />
                  </div>
                </div>

                {prReviewMutation.isError && (
                  <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 shrink-0" />
                    <span>{(prReviewMutation.error as Error).message}</span>
                  </div>
                )}

                <div className="flex items-center justify-between pt-2">
                  <div className="text-[11px] text-zinc-500 flex items-center gap-1.5">
                    <ShieldAlert className="w-3.5 h-3.5 text-indigo-400" />
                    Enforces diff line budgeting, static AST isolation, and finding validation.
                  </div>
                  <button
                    type="submit"
                    disabled={!prUrl || prReviewMutation.isPending}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-medium bg-[#6366f1] text-white hover:bg-[#4f46e5] disabled:opacity-50 transition-all shadow-md shadow-[#6366f1]/20 cursor-pointer"
                  >
                    {prReviewMutation.isPending ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Analyzing PR...</span>
                      </>
                    ) : (
                      <>
                        <Send className="w-3.5 h-3.5" />
                        <span>Start Review</span>
                      </>
                    )}
                  </button>
                </div>
              </form>
            ) : (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  if (selectedFile) uploadReviewMutation.mutate();
                }}
                className="space-y-4"
              >
                <div className="border-2 border-dashed border-[#27272a] hover:border-[#6366f1]/50 rounded-2xl p-6 text-center transition-all bg-[#18181b]/50">
                  <input
                    type="file"
                    id="patch-upload"
                    accept=".diff,.patch,text/plain"
                    onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                    className="hidden"
                  />
                  <label htmlFor="patch-upload" className="cursor-pointer space-y-2 block">
                    <div className="w-10 h-10 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center mx-auto">
                      <Upload className="w-5 h-5" />
                    </div>
                    <div className="text-sm font-medium text-white">
                      {selectedFile ? selectedFile.name : "Choose a .diff or .patch file"}
                    </div>
                    <p className="text-xs text-zinc-500">
                      {selectedFile
                        ? `${(selectedFile.size / 1024).toFixed(1)} KB selected`
                        : "Drag and drop unified diff patch file (up to 2 MB)"}
                    </p>
                  </label>
                </div>

                {uploadReviewMutation.isError && (
                  <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 shrink-0" />
                    <span>{(uploadReviewMutation.error as Error).message}</span>
                  </div>
                )}

                <div className="flex items-center justify-end pt-1">
                  <button
                    type="submit"
                    disabled={!selectedFile || uploadReviewMutation.isPending}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-medium bg-[#6366f1] text-white hover:bg-[#4f46e5] disabled:opacity-50 transition-all shadow-md shadow-[#6366f1]/20 cursor-pointer"
                  >
                    {uploadReviewMutation.isPending ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Parsing Patch...</span>
                      </>
                    ) : (
                      <>
                        <Upload className="w-3.5 h-3.5" />
                        <span>Upload & Review</span>
                      </>
                    )}
                  </button>
                </div>
              </form>
            )}
          </div>

          {/* Past Reviews List */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                <Clock className="w-4 h-4 text-zinc-400" />
                Previous Code Reviews ({reviews.length})
              </h2>
              <button
                type="button"
                onClick={() => refetchReviews()}
                className="text-xs text-zinc-400 hover:text-white flex items-center gap-1.5 transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Refresh</span>
              </button>
            </div>

            {listLoading ? (
              <div className="p-12 text-center text-xs text-zinc-500 flex items-center justify-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
                <span>Loading past reviews...</span>
              </div>
            ) : reviews.length === 0 ? (
              <div className="p-12 text-center rounded-2xl bg-[#111113] border border-[#27272a] space-y-2">
                <GitPullRequest className="w-8 h-8 text-zinc-600 mx-auto" />
                <div className="text-sm font-medium text-white">No reviews recorded yet</div>
                <p className="text-xs text-zinc-500 max-w-sm mx-auto">
                  Submit a GitHub PR URL or upload a patch above to trigger context-aware automated code review.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-2.5">
                {reviews.map((rev) => (
                  <div
                    key={rev.id}
                    onClick={() => setSelectedReviewId(rev.id)}
                    className="p-4 rounded-xl bg-[#111113] border border-[#27272a] hover:border-[#6366f1]/50 transition-all cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-3 group"
                  >
                    <div className="flex items-start sm:items-center gap-3">
                      <div
                        className={`w-9 h-9 rounded-lg flex items-center justify-center font-bold text-xs uppercase border ${
                          rev.risk_level === "critical"
                            ? "bg-rose-500/10 text-rose-400 border-rose-500/30"
                            : rev.risk_level === "high"
                            ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                            : rev.risk_level === "medium"
                            ? "bg-yellow-500/10 text-yellow-400 border-yellow-500/30"
                            : "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                        }`}
                      >
                        {rev.risk_level[0]}
                      </div>

                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-white group-hover:text-indigo-400 transition-colors">
                            {rev.source.type === "github"
                              ? `Pull Request #${rev.source.pr_number || ""}`
                              : rev.source.patch_filename || "Patch Diff"}
                          </span>

                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase border ${statusBadge(
                              rev.status
                            )}`}
                          >
                            {rev.status}
                          </span>

                          {rev.published_to_github && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              Published
                            </span>
                          )}

                          {rev.indexed_commit_mismatch && (
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20">
                              Commit Mismatch
                            </span>
                          )}
                        </div>

                        <div className="flex items-center gap-3 text-xs text-zinc-500">
                          <span>
                            {rev.stats.files_changed} files (+{rev.stats.lines_added} / -{rev.stats.lines_deleted})
                          </span>
                          <span>•</span>
                          <span className="text-zinc-300 font-medium">
                            {rev.stats.findings_count} findings ({rev.stats.accepted_count} accepted)
                          </span>
                          <span>•</span>
                          <span>{new Date(rev.created_at).toLocaleString()}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-end sm:self-center">
                      <span className="text-xs text-zinc-400 group-hover:text-white flex items-center gap-1 transition-colors">
                        View Findings <ChevronRight className="w-3.5 h-3.5" />
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Detailed Review Findings View */
        <div className="space-y-6">
          {/* Header Action Bar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#27272a] pb-4">
            <button
              type="button"
              onClick={() => setSelectedReviewId(null)}
              className="inline-flex items-center gap-2 text-xs font-medium text-zinc-400 hover:text-white transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to all reviews</span>
            </button>

            <div className="flex items-center gap-2">
              <a
                href={`/api/v1/reviews/${selectedReviewId}/export?format=markdown`}
                download
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[#18181b] border border-[#27272a] text-zinc-300 hover:text-white transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export Markdown</span>
              </a>

              <a
                href={`/api/v1/reviews/${selectedReviewId}/export?format=json`}
                download
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[#18181b] border border-[#27272a] text-zinc-300 hover:text-white transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export JSON</span>
              </a>

              {review?.source.type === "github" && (
                <button
                  type="button"
                  onClick={() => setPublishModalOpen(true)}
                  disabled={
                    review.published_to_github ||
                    (review.stats.accepted_count === 0 &&
                      !review.findings.some((f) => f.status === "accepted" || f.status === "edited"))
                  }
                  className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-[#6366f1] text-white hover:bg-[#4f46e5] disabled:opacity-50 transition-all shadow-sm cursor-pointer"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>
                    {review.published_to_github ? "Published on GitHub" : "Publish to GitHub"}
                  </span>
                </button>
              )}
            </div>
          </div>

          {reviewLoading || !review ? (
            <div className="p-16 text-center text-xs text-zinc-500 flex items-center justify-center gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
              <span>Loading review details...</span>
            </div>
          ) : (
            <>
              {/* Commit Mismatch Warning */}
              {review.indexed_commit_mismatch && (
                <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300 flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                    <span>
                      <strong>Indexed commit mismatch:</strong> The base commit of this pull request differs from the repository snapshot currently indexed in RepoGPT. Context citations may reference shifted lines.
                    </span>
                  </div>
                  <Link
                    to={`/app/repos/${repoId}/overview`}
                    className="px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-amber-500/20 text-amber-200 hover:bg-amber-500/30 transition-colors whitespace-nowrap"
                  >
                    Sync Repository
                  </Link>
                </div>
              )}

              {/* Review Overview Card */}
              <div className="p-6 rounded-2xl bg-[#111113] border border-[#27272a] space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#27272a] pb-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2.5">
                      <h2 className="text-lg font-bold text-white">
                        {review.source.type === "github"
                          ? `PR Review #${review.source.pr_number || ""}`
                          : review.source.patch_filename || "Unified Patch Review"}
                      </h2>
                      {review.source.pr_url && (
                        <a
                          href={review.source.pr_url}
                          target="_blank"
                          rel="noopener noreferrer nofollow"
                          className="text-xs text-indigo-400 hover:underline flex items-center gap-1"
                        >
                          View on GitHub <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                    <p className="text-xs text-zinc-400">
                      Evaluated on {new Date(review.created_at).toLocaleString()}
                    </p>
                  </div>

                  {/* Badges and KPI stats */}
                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <div className="text-[10px] text-zinc-500 uppercase font-bold font-mono">
                        Risk Level
                      </div>
                      <span
                        className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-bold uppercase border font-mono ${severityBadge(
                          review.risk_level
                        )}`}
                      >
                        {review.risk_level}
                      </span>
                    </div>

                    <div className="h-8 w-px bg-[#27272a]" />

                    <div className="text-right">
                      <div className="text-[10px] text-zinc-500 uppercase font-bold font-mono">
                        Acceptance
                      </div>
                      <div className="text-xs font-semibold text-emerald-400 tabular-nums font-mono">
                        {review.stats.accepted_count} / {review.stats.findings_count}
                      </div>
                    </div>
                  </div>
                </div>

                {/* AI Summary */}
                {review.summary && (
                  <div className="space-y-1.5">
                    <h3 className="text-xs font-semibold text-zinc-300 uppercase font-mono text-balance">
                      Summary Narrative
                    </h3>
                    <div className="p-3.5 rounded-xl bg-[#18181b] border border-[#27272a] text-xs text-zinc-300 leading-relaxed whitespace-pre-line text-pretty">
                      {review.summary}
                    </div>
                  </div>
                )}

                {/* File Walkthrough */}
                {review.file_walkthrough.length > 0 && (
                  <div className="space-y-1.5">
                    <h3 className="text-xs font-semibold text-zinc-300 uppercase font-mono text-balance">
                      Changed Files Walkthrough ({review.file_walkthrough.length})
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                      {review.file_walkthrough.map((fw) => (
                        <div
                          key={fw.path}
                          className="p-2.5 rounded-lg bg-[#18181b] border border-[#27272a] text-xs flex items-center justify-between"
                        >
                          <span className="font-mono text-zinc-300 truncate mr-2" title={fw.path}>
                            {fw.path}
                          </span>
                          <div className="flex items-center gap-1.5 text-[11px] shrink-0 font-mono">
                            <span className="text-emerald-400">+{fw.added_lines}</span>
                            <span className="text-rose-400">-{fw.deleted_lines}</span>
                            {fw.findings_count > 0 && (
                              <span className="px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-400 font-sans font-semibold">
                                {fw.findings_count}
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Actionable Findings Toolbar */}
              <div className="space-y-3">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 p-3.5 rounded-xl bg-[#111113] border border-[#27272a]">
                  {/* Left Filters */}
                  <div className="flex flex-wrap items-center gap-2">
                    <div className="flex items-center gap-1 text-xs text-zinc-400 mr-1">
                      <Filter className="w-3.5 h-3.5" />
                      <span>Filters:</span>
                    </div>

                    <select
                      value={severityFilter}
                      onChange={(e) => setSeverityFilter(e.target.value)}
                      className="px-2.5 py-1 rounded-lg bg-[#18181b] border border-[#27272a] text-xs text-zinc-300 focus:outline-none"
                    >
                      <option value="all">All Severities</option>
                      <option value="critical">Critical</option>
                      <option value="high">High</option>
                      <option value="medium">Medium</option>
                      <option value="low">Low</option>
                      <option value="info">Info</option>
                    </select>

                    <select
                      value={statusFilter}
                      onChange={(e) => setStatusFilter(e.target.value)}
                      className="px-2.5 py-1 rounded-lg bg-[#18181b] border border-[#27272a] text-xs text-zinc-300 focus:outline-none"
                    >
                      <option value="all">All Statuses</option>
                      <option value="pending">Pending</option>
                      <option value="accepted">Accepted</option>
                      <option value="rejected">Rejected</option>
                      <option value="edited">Edited</option>
                    </select>

                    <select
                      value={categoryFilter}
                      onChange={(e) => setCategoryFilter(e.target.value)}
                      className="px-2.5 py-1 rounded-lg bg-[#18181b] border border-[#27272a] text-xs text-zinc-300 focus:outline-none"
                    >
                      <option value="all">All Categories</option>
                      <option value="security">Security</option>
                      <option value="bug">Bug</option>
                      <option value="performance">Performance</option>
                      <option value="concurrency">Concurrency</option>
                      <option value="api_contract">API Contract</option>
                      <option value="error_handling">Error Handling</option>
                      <option value="maintainability">Maintainability</option>
                    </select>

                    <select
                      value={fileFilter}
                      onChange={(e) => setFileFilter(e.target.value)}
                      className="px-2.5 py-1 rounded-lg bg-[#18181b] border border-[#27272a] text-xs text-zinc-300 focus:outline-none max-w-[160px] truncate"
                    >
                      <option value="all">All Files</option>
                      {uniqueFiles.map((f) => (
                        <option key={f} value={f}>
                          {f}
                        </option>
                      ))}
                    </select>

                    <input
                      type="text"
                      placeholder="Search findings..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="px-2.5 py-1 rounded-lg bg-[#18181b] border border-[#27272a] text-xs text-zinc-300 placeholder-zinc-500 focus:outline-none w-36"
                    />
                  </div>

                  {/* Bulk Actions */}
                  <div className="flex items-center gap-2 self-end md:self-auto">
                    <button
                      type="button"
                      onClick={() => handleBulkAction("accepted")}
                      className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20 transition-colors"
                    >
                      <Check className="w-3 h-3" />
                      <span>Accept All</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleBulkAction("rejected")}
                      className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium bg-rose-500/10 border border-rose-500/20 text-rose-400 hover:bg-rose-500/20 transition-colors"
                    >
                      <X className="w-3 h-3" />
                      <span>Reject All</span>
                    </button>
                  </div>
                </div>

                {/* Findings List */}
                {filteredFindings.length === 0 ? (
                  <div className="p-12 text-center rounded-2xl bg-[#111113] border border-[#27272a] space-y-2">
                    <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto" />
                    <div className="text-sm font-medium text-white">No findings matching filter</div>
                    <p className="text-xs text-zinc-500">
                      All issues in this filter view have been handled or none were detected.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {filteredFindings.map((f) => {
                      const isEditing = editingFindingId === f.id;

                      return (
                        <div
                          key={f.id}
                          className={`p-5 rounded-2xl border transition-all ${
                            f.status === "rejected"
                              ? "bg-[#111113]/50 border-[#27272a] opacity-60"
                              : f.status === "accepted" || f.status === "edited"
                              ? "bg-[#111113] border-emerald-500/30"
                              : "bg-[#111113] border-[#27272a]"
                          }`}
                        >
                          {/* Finding Header */}
                          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                            <div className="space-y-1.5 flex-1">
                              <div className="flex flex-wrap items-center gap-2">
                                <span
                                  className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${severityBadge(
                                    f.severity
                                  )}`}
                                >
                                  {f.severity}
                                </span>

                                <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-zinc-800 text-zinc-300 border border-zinc-700">
                                  {f.category}
                                </span>

                                <span
                                  className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${statusBadge(
                                    f.status
                                  )}`}
                                >
                                  {f.status}
                                </span>

                                <span className="font-mono text-xs text-indigo-400 font-medium">
                                  {f.path}:{f.start_line}
                                  {f.end_line > f.start_line ? `-${f.end_line}` : ""}
                                </span>

                                <span className="text-[11px] text-zinc-500">
                                  ({Math.round(f.confidence * 100)}% conf)
                                </span>

                                {f.origin === "static" && (
                                  <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-purple-500/10 text-purple-400 border border-purple-500/20">
                                    Static
                                  </span>
                                )}
                              </div>

                              {!isEditing ? (
                                <h4 className="text-sm font-semibold text-white pt-1">{f.title}</h4>
                              ) : (
                                <input
                                  type="text"
                                  value={editTitle}
                                  onChange={(e) => setEditTitle(e.target.value)}
                                  className="w-full px-3 py-1.5 rounded-lg bg-[#18181b] border border-[#27272a] text-sm text-white focus:outline-none"
                                />
                              )}
                            </div>

                            {/* Action Buttons */}
                            <div className="flex items-center gap-1.5 shrink-0">
                              {f.status !== "accepted" && (
                                <button
                                  type="button"
                                  onClick={() =>
                                    updateFindingMutation.mutate({
                                      findingId: f.id,
                                      updates: { status: "accepted" },
                                    })
                                  }
                                  title="Accept finding"
                                  className="p-1.5 rounded-lg text-emerald-400 hover:bg-emerald-500/20 border border-emerald-500/30 transition-colors"
                                >
                                  <Check className="w-4 h-4" />
                                </button>
                              )}

                              {f.status !== "rejected" && (
                                <button
                                  type="button"
                                  onClick={() =>
                                    updateFindingMutation.mutate({
                                      findingId: f.id,
                                      updates: { status: "rejected" },
                                    })
                                  }
                                  title="Reject finding"
                                  className="p-1.5 rounded-lg text-rose-400 hover:bg-rose-500/20 border border-rose-500/30 transition-colors"
                                >
                                  <X className="w-4 h-4" />
                                </button>
                              )}

                              {!isEditing ? (
                                <button
                                  type="button"
                                  onClick={() => handleStartEdit(f)}
                                  title="Edit finding"
                                  className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 border border-zinc-700 transition-colors"
                                >
                                  <Edit2 className="w-4 h-4" />
                                </button>
                              ) : (
                                <button
                                  type="button"
                                  onClick={() => handleSaveEdit(f.id)}
                                  title="Save edits"
                                  className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-[#6366f1] text-white hover:bg-[#4f46e5] transition-colors"
                                >
                                  Save
                                </button>
                              )}
                            </div>
                          </div>

                          {/* Body Content */}
                          <div className="pt-3 space-y-3 text-xs">
                            {!isEditing ? (
                              <p className="text-zinc-300 leading-relaxed whitespace-pre-line">
                                {f.explanation}
                              </p>
                            ) : (
                              <textarea
                                value={editExplanation}
                                onChange={(e) => setEditExplanation(e.target.value)}
                                rows={3}
                                className="w-full px-3 py-2 rounded-lg bg-[#18181b] border border-[#27272a] text-xs text-white focus:outline-none"
                              />
                            )}

                            {/* Suggestion & Code replacement */}
                            {f.suggestion && (
                              <div className="p-3 rounded-xl bg-[#18181b] border border-[#27272a] space-y-2">
                                <div className="text-[11px] font-semibold text-indigo-400 flex items-center gap-1.5">
                                  <Sparkles className="w-3.5 h-3.5" />
                                  <span>Suggested Remediation</span>
                                </div>
                                <p className="text-zinc-300">{f.suggestion}</p>

                                {f.suggested_code && (
                                  <div className="relative pt-1">
                                    <pre className="p-3 rounded-lg bg-[#09090b] text-emerald-300 font-mono text-[11px] overflow-x-auto border border-[#27272a]">
                                      <code>{f.suggested_code}</code>
                                    </pre>
                                    <button
                                      type="button"
                                      onClick={() => handleCopyCode(f.id, f.suggested_code!)}
                                      className="absolute top-3 right-3 p-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300 transition-colors"
                                      title="Copy suggested code"
                                    >
                                      {copiedCodeId === f.id ? (
                                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                                      ) : (
                                        <Copy className="w-3.5 h-3.5" />
                                      )}
                                    </button>
                                  </div>
                                )}
                              </div>
                            )}

                            {/* User Note */}
                            {f.user_note && !isEditing && (
                              <div className="text-[11px] text-zinc-400 italic">
                                <strong>Reviewer note:</strong> {f.user_note}
                              </div>
                            )}

                            {isEditing && (
                              <input
                                type="text"
                                placeholder="Add reviewer note (optional)..."
                                value={editNote}
                                onChange={(e) => setEditNote(e.target.value)}
                                className="w-full px-3 py-1.5 rounded-lg bg-[#18181b] border border-[#27272a] text-xs text-white focus:outline-none"
                              />
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* General Comments (Unanchored issues) */}
              {review.general_comments.length > 0 && (
                <div className="p-5 rounded-2xl bg-[#111113] border border-[#27272a] space-y-3">
                  <h3 className="text-xs font-semibold text-zinc-300 uppercase font-mono flex items-center gap-2 text-balance">
                    <Info className="size-4 text-teal-400" />
                    General PR Observations & Unanchored Comments ({review.general_comments.length})
                  </h3>
                  <div className="space-y-2">
                    {review.general_comments.map((gc, i) => (
                      <div key={i} className="p-3 rounded-xl bg-[#18181b] border border-[#27272a] space-y-1">
                        <div className="text-xs font-semibold text-white">{gc.title}</div>
                        <p className="text-xs text-zinc-400">{gc.explanation}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          {/* Publish Confirmation Modal */}
          {publishModalOpen && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
              <div className="w-full max-w-md rounded-2xl bg-[#111113] border border-[#27272a] p-6 space-y-5 shadow-2xl">
                <div className="flex items-center justify-between border-b border-[#27272a] pb-3">
                  <div className="flex items-center gap-2 text-white font-semibold text-base">
                    <Send className="w-4 h-4 text-indigo-400" />
                    <span>Publish Review to GitHub</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setPublishModalOpen(false)}
                    className="p-1 rounded-lg text-zinc-400 hover:text-white"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                <div className="space-y-3 text-xs text-zinc-300 leading-relaxed">
                  <p>
                    RepoGPT will post a <strong>COMMENT review</strong> to GitHub containing:
                  </p>
                  <ul className="list-disc pl-5 space-y-1 text-zinc-400">
                    <li>PR summary narrative</li>
                    <li>
                      <strong>
                        {review?.findings.filter((f) => f.status === "accepted" || f.status === "edited").length} accepted finding(s)
                      </strong>{" "}
                      anchored to lines with severity tags and suggested code blocks
                    </li>
                  </ul>
                  <div className="p-3 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-300">
                    <strong>Notice (§10.5):</strong> RepoGPT never approves or requests changes, and will never push or merge code.
                  </div>

                  <div className="space-y-1.5 pt-1">
                    <label className="text-xs font-medium text-zinc-300">
                      GitHub PAT with write:pull_request (optional)
                    </label>
                    <input
                      type="password"
                      placeholder="Use default server token if blank"
                      value={publishToken}
                      onChange={(e) => setPublishToken(e.target.value)}
                      className="w-full px-3 py-2 rounded-xl bg-[#18181b] border border-[#27272a] text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#6366f1]"
                    />
                  </div>
                </div>

                {publishMutation.isError && (
                  <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400">
                    {(publishMutation.error as Error).message}
                  </div>
                )}

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setPublishModalOpen(false)}
                    className="px-4 py-2 rounded-xl text-xs font-medium text-zinc-400 hover:text-white transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => publishMutation.mutate()}
                    disabled={publishMutation.isPending}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-[#6366f1] text-white hover:bg-[#4f46e5] disabled:opacity-50 transition-all shadow-md shadow-[#6366f1]/20 cursor-pointer"
                  >
                    {publishMutation.isPending ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Publishing...</span>
                      </>
                    ) : (
                      <>
                        <Send className="w-3.5 h-3.5" />
                        <span>Confirm & Publish</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
