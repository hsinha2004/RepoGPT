import React, { useState } from "react";
import {
  FileCode2,
  Upload,
  Search,
  Trash2,
  Eye,
  Play,
  AlertCircle,
  X,
  FileCheck,
} from "lucide-react";
import { Benchmark } from "./types";
import { getAccessToken } from "../../api/client";

interface BenchmarksTabProps {
  benchmarks: Benchmark[];
  isLoading: boolean;
  onRefresh: () => void;
  onSelectRunBenchmark: (benchmark: Benchmark) => void;
}

export const BenchmarksTab: React.FC<BenchmarksTabProps> = ({
  benchmarks,
  isLoading,
  onRefresh,
  onSelectRunBenchmark,
}) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [viewBenchmark, setViewBenchmark] = useState<Benchmark | null>(null);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  const filtered = benchmarks.filter(
    (b) =>
      b.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      b.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      setUploadError("Please select a .yaml file to upload.");
      return;
    }
    setIsUploading(true);
    setUploadError(null);

    try {
      const formData = new FormData();
      formData.append("file", uploadFile);

      const token = getAccessToken();
      const res = await fetch("/api/v1/eval/benchmarks", {
        method: "POST",
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.message || `Upload failed (${res.status})`);
      }

      setIsUploadOpen(false);
      setUploadFile(null);
      onRefresh();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to upload benchmark";
      setUploadError(msg);
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (benchmarkId: string) => {
    try {
      const token = getAccessToken();
      const res = await fetch(`/api/v1/eval/benchmarks/${benchmarkId}`, {
        method: "DELETE",
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.message || "Failed to delete benchmark");
      }

      setDeleteConfirmId(null);
      onRefresh();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Error deleting benchmark");
    }
  };

  const getCategoryColor = (cat: string) => {
    switch (cat.toLowerCase()) {
      case "locate":
        return "bg-blue-500/10 text-blue-400 border-blue-500/20";
      case "explain":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "flow":
        return "bg-purple-500/10 text-purple-400 border-purple-500/20";
      case "architecture":
        return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      case "dependency":
        return "bg-cyan-500/10 text-cyan-400 border-cyan-500/20";
      case "config":
        return "bg-rose-500/10 text-rose-400 border-rose-500/20";
      default:
        return "bg-zinc-500/10 text-zinc-400 border-zinc-500/20";
    }
  };

  return (
    <div className="space-y-6">
      {/* Header controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="relative w-full sm:w-80">
          <Search className="size-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
          <input
            type="text"
            placeholder="Search benchmarks..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-white border border-zinc-200 rounded-lg pl-9 pr-4 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:outline-none focus:border-emerald-500 shadow-xs transition-colors"
          />
        </div>

        <button
          onClick={() => {
            setIsUploadOpen(true);
            setUploadError(null);
          }}
          className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-medium transition-colors shadow-xs cursor-pointer"
        >
          <Upload className="size-4" />
          Upload Custom Benchmark
        </button>
      </div>

      {/* Benchmarks Grid */}
      {isLoading ? (
        <div className="py-16 text-center text-zinc-500">Loading benchmark suites...</div>
      ) : filtered.length === 0 ? (
        <div className="py-16 text-center border border-dashed border-zinc-200 rounded-xl bg-white shadow-xs">
          <FileCode2 className="size-10 text-zinc-400 mx-auto mb-3" />
          <p className="text-zinc-900 font-medium">No benchmarks found</p>
          <p className="text-xs text-zinc-500 mt-1 text-pretty">
            Try adjusting your search query or upload a custom YAML suite.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((b) => (
            <div
              key={b.id}
              className="bg-white border border-zinc-200 hover:border-zinc-300 rounded-xl p-5 flex flex-col justify-between transition-colors shadow-xs"
            >
              <div>
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div>
                    <h3 className="text-base font-semibold text-zinc-900 text-balance">{b.name}</h3>
                    <p className="text-xs text-zinc-500 mt-0.5 line-clamp-2 text-pretty">
                      {b.description || "Comprehensive evaluation benchmark suite."}
                    </p>
                  </div>
                  {b.is_builtin ? (
                    <span className="shrink-0 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                      Built-in
                    </span>
                  ) : (
                    <span className="shrink-0 px-2 py-0.5 rounded-full text-[11px] font-medium bg-zinc-100 text-zinc-700 border border-zinc-200">
                      Custom
                    </span>
                  )}
                </div>

                <div className="space-y-1.5 py-3 border-y border-zinc-200 text-xs text-zinc-500">
                  <div className="flex items-center justify-between">
                    <span>Target Repository:</span>
                    <span className="font-mono text-zinc-800">
                      {b.repo?.path || b.repo?.url || "Sample Repo"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Questions:</span>
                    <span className="font-medium text-zinc-900 tabular-nums">{b.question_count} verified Qs</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between gap-2 mt-4 pt-2">
                <button
                  onClick={() => setViewBenchmark(b)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white hover:bg-zinc-50 border border-zinc-200 text-xs font-medium text-zinc-700 transition-colors cursor-pointer shadow-xs"
                >
                  <Eye className="size-3.5" />
                  View Questions
                </button>

                <div className="flex items-center gap-1.5">
                  {!b.is_builtin && (
                    <button
                      onClick={() => setDeleteConfirmId(b.id)}
                      aria-label="Delete benchmark suite"
                      className="p-1.5 text-zinc-400 hover:text-rose-600 hover:bg-rose-50 rounded-md transition-colors cursor-pointer"
                    >
                      <Trash2 className="size-4" />
                    </button>
                  )}
                  <button
                    onClick={() => onSelectRunBenchmark(b)}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md text-xs font-medium transition-colors cursor-pointer shadow-xs"
                  >
                    <Play className="size-3.5 fill-current" />
                    Run Eval
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Benchmark Question Viewer Drawer/Modal */}
      {viewBenchmark && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-white border border-zinc-200 rounded-xl max-w-3xl w-full max-h-[85vh] flex flex-col shadow-2xl">
            <div className="px-6 py-4 border-b border-zinc-200 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-zinc-900">{viewBenchmark.name}</h3>
                <p className="text-xs text-zinc-500">
                  {viewBenchmark.question_count} questions • Target:{" "}
                  {viewBenchmark.repo?.path || "Sample Repo"}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setViewBenchmark(null)}
                aria-label="Close dialog"
                className="text-zinc-400 hover:text-zinc-600 p-1 rounded-md transition-colors cursor-pointer"
              >
                <X className="size-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-3 divide-y divide-zinc-200">
              {viewBenchmark.questions?.map((q, idx) => (
                <div key={q.id || idx} className="pt-3 first:pt-0">
                  <div className="flex items-start justify-between gap-3 mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs px-1.5 py-0.5 rounded bg-zinc-100 border border-zinc-200 text-zinc-600 tabular-nums">
                        {q.id || `q${idx + 1}`}
                      </span>
                      <span
                        className={`text-[11px] font-medium px-2 py-0.5 rounded-full border ${getCategoryColor(
                          q.category
                        )}`}
                      >
                        {q.category}
                      </span>
                    </div>
                    <span className="text-[11px] text-zinc-500">
                      Expected Intent: {q.expected_intent}
                    </span>
                  </div>
                  <p className="text-sm font-medium text-zinc-900">{q.question}</p>
                  <div className="mt-2 flex flex-wrap gap-1.5 text-xs">
                    {q.expected_files?.map((f) => (
                      <span
                        key={f}
                        className="font-mono text-[11px] px-2 py-0.5 bg-zinc-100 rounded text-zinc-700 border border-zinc-200"
                      >
                        {f}
                      </span>
                    ))}
                    {q.expected_symbols?.map((sym) => (
                      <span
                        key={sym}
                        className="font-mono text-[11px] px-2 py-0.5 bg-emerald-50 text-emerald-700 rounded border border-emerald-200"
                      >
                        sym: {sym}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div className="px-6 py-3 border-t border-zinc-200 flex justify-end">
              <button
                type="button"
                onClick={() => {
                  const b = viewBenchmark;
                  setViewBenchmark(null);
                  onSelectRunBenchmark(b);
                }}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-medium transition-colors cursor-pointer shadow-xs"
              >
                Run Evaluation With This Benchmark
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Upload Benchmark Modal */}
      {isUploadOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-white border border-zinc-200 rounded-xl max-w-lg w-full p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-200 mb-4">
              <h3 className="text-base font-semibold text-zinc-900">Upload Benchmark YAML</h3>
              <button
                type="button"
                onClick={() => setIsUploadOpen(false)}
                aria-label="Close dialog"
                className="text-zinc-400 hover:text-zinc-600 cursor-pointer"
              >
                <X className="size-5" />
              </button>
            </div>

            <form onSubmit={handleUploadSubmit} className="space-y-4">
              <div className="border-2 border-dashed border-zinc-200 hover:border-emerald-500 rounded-xl p-6 text-center cursor-pointer transition-colors bg-zinc-50/50">
                <input
                  type="file"
                  id="benchmark-file"
                  accept=".yaml,.yml"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files?.[0]) {
                      setUploadFile(e.target.files[0]);
                      setUploadError(null);
                    }
                  }}
                />
                <label htmlFor="benchmark-file" className="cursor-pointer">
                  {uploadFile ? (
                    <div className="flex flex-col items-center">
                      <FileCheck className="size-8 text-emerald-600 mb-2" />
                      <p className="text-sm font-medium text-zinc-900">{uploadFile.name}</p>
                      <p className="text-xs text-zinc-500 mt-1 tabular-nums">
                        {(uploadFile.size / 1024).toFixed(1)} KB • Ready to upload
                      </p>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center">
                      <Upload className="size-8 text-zinc-400 mb-2" />
                      <p className="text-sm font-medium text-zinc-800">Click to choose benchmark YAML</p>
                      <p className="text-xs text-zinc-500 mt-1">
                        Must contain name, repo, and questions array.
                      </p>
                    </div>
                  )}
                </label>
              </div>

              {uploadError && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg flex items-center gap-2 text-xs text-rose-700">
                  <AlertCircle className="size-4 shrink-0" />
                  <span>{uploadError}</span>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsUploadOpen(false)}
                  className="px-4 py-2 rounded-lg text-sm font-medium text-zinc-600 hover:text-zinc-900 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!uploadFile || isUploading}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors cursor-pointer shadow-xs"
                >
                  {isUploading ? "Uploading..." : "Upload & Validate"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirmId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-white border border-zinc-200 rounded-xl max-w-sm w-full p-6 shadow-2xl">
            <h3 className="text-base font-semibold text-zinc-900 text-balance">Delete Benchmark</h3>
            <p className="text-xs text-zinc-500 mt-2 text-pretty">
              Are you sure you want to delete this custom benchmark suite? This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3 mt-6">
              <button
                type="button"
                onClick={() => setDeleteConfirmId(null)}
                className="px-3 py-1.5 text-xs font-medium text-zinc-600 hover:text-zinc-900 cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => handleDelete(deleteConfirmId)}
                className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-md text-xs font-medium transition-colors cursor-pointer shadow-xs"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
