import React, { useState } from "react";
import {
  Github,
  Upload,
  X,
  Loader2,
  AlertCircle,
  FileCode2,
} from "lucide-react";
import { authFetch } from "../../api/client";

interface AddRepoDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onJobStarted: (jobId: string, repoId: string) => void;
}

export const AddRepoDialog: React.FC<AddRepoDialogProps> = ({ isOpen, onClose, onJobStarted }) => {
  const [tab, setTab] = useState<"github" | "upload">("github");
  const [githubUrl, setGithubUrl] = useState("");
  const [githubRef, setGithubRef] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadDisplayName, setUploadDisplayName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleGitHubSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!githubUrl.trim()) return;

    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      const res = await authFetch("/api/v1/repos", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url: githubUrl.trim(),
          ref: githubRef.trim() || undefined,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        if (res.status === 401) {
          setErrorMessage("Authentication session expired. Please sign in again.");
        } else {
          setErrorMessage(data.error?.message || "Failed to add GitHub repository.");
        }
        return;
      }

      onJobStarted(data.job_id, data.repository.id);
      onClose();
    } catch {
      setErrorMessage("Network error connecting to RepoGPT API.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setErrorMessage("Please select a ZIP file to upload.");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      if (uploadDisplayName.trim()) {
        formData.append("display_name", uploadDisplayName.trim());
      }

      const res = await authFetch("/api/v1/repos/upload", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) {
        if (res.status === 401) {
          setErrorMessage("Authentication session expired. Please sign in again.");
        } else {
          setErrorMessage(data.error?.message || "Failed to upload repository ZIP.");
        }
        return;
      }

      onJobStarted(data.job_id, data.repository.id);
      onClose();
    } catch {
      setErrorMessage("Network error uploading archive.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-lg bg-[#18181b] border border-[#27272a] rounded-xl shadow-2xl p-6 text-white animate-in fade-in zoom-in-95 duration-150">
        <button
          onClick={onClose}
          aria-label="Close dialog"
          className="absolute right-4 top-4 text-[#71717a] hover:text-white transition-colors cursor-pointer"
        >
          <X className="size-5" />
        </button>

        <h2 className="text-xl font-bold mb-1 text-balance">Add Repository to RepoGPT</h2>
        <p className="text-sm text-[#a1a1aa] mb-6 text-pretty">
          Ingest a GitHub repository or upload a local ZIP archive to enable agentic search, graph visualization, and code review.
        </p>

        {/* Tabs */}
        <div className="flex border-b border-[#27272a] gap-2 mb-6">
          <button
            onClick={() => { setTab("github"); setErrorMessage(null); }}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px cursor-pointer ${
              tab === "github"
                ? "border-emerald-500 text-emerald-400"
                : "border-transparent text-[#a1a1aa] hover:text-white"
            }`}
          >
            <Github className="size-4" />
            GitHub URL
          </button>
          <button
            onClick={() => { setTab("upload"); setErrorMessage(null); }}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px cursor-pointer ${
              tab === "upload"
                ? "border-emerald-500 text-emerald-400"
                : "border-transparent text-[#a1a1aa] hover:text-white"
            }`}
          >
            <Upload className="size-4" />
            Upload ZIP
          </button>
        </div>

        {errorMessage && (
          <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm flex items-center gap-2 text-pretty">
            <AlertCircle className="size-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Tab 1: GitHub URL */}
        {tab === "github" ? (
          <form onSubmit={handleGitHubSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase text-[#a1a1aa] mb-1 font-mono">
                GitHub Repository URL or Shorthand
              </label>
              <input
                type="text"
                placeholder="https://github.com/fastapi/fastapi or owner/repo"
                value={githubUrl}
                onChange={(e) => setGithubUrl(e.target.value)}
                required
                className="w-full bg-[#09090b] border border-[#27272a] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500 font-mono"
              />
              <span className="text-[11px] text-[#71717a] mt-1 block text-pretty">
                Public repositories clone automatically. Private repositories require a GitHub PAT configured in Settings.
              </span>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-[#a1a1aa] mb-1 font-mono">
                Branch, Tag, or Commit SHA (Optional)
              </label>
              <input
                type="text"
                placeholder="main (defaults to repository default branch)"
                value={githubRef}
                onChange={(e) => setGithubRef(e.target.value)}
                className="w-full bg-[#09090b] border border-[#27272a] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500 font-mono"
              />
            </div>

            <div className="pt-2 flex justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 bg-[#27272a] hover:bg-[#3f3f46] text-white text-sm font-medium rounded-lg transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting || !githubUrl.trim()}
                className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 cursor-pointer shadow-xs"
              >
                {isSubmitting ? <Loader2 className="size-4 animate-spin" /> : <Github className="size-4" />}
                Ingest Repository
              </button>
            </div>
          </form>
        ) : (
          /* Tab 2: Upload ZIP */
          <form onSubmit={handleUploadSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase text-[#a1a1aa] mb-1 font-mono">
                Select ZIP Archive
              </label>
              <div className="border-2 border-dashed border-[#27272a] hover:border-emerald-500/50 rounded-lg p-6 text-center transition-colors">
                <input
                  type="file"
                  accept=".zip,application/zip"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  className="hidden"
                  id="zip-upload-input"
                />
                <label htmlFor="zip-upload-input" className="cursor-pointer flex flex-col items-center">
                  <FileCode2 className="size-8 text-emerald-400 mb-2" />
                  <span className="text-sm font-medium text-white text-balance">
                    {selectedFile ? selectedFile.name : "Click to select a .zip codebase archive"}
                  </span>
                  <span className="text-xs text-[#71717a] mt-1 tabular-nums">
                    {selectedFile
                      ? `${(selectedFile.size / (1024 * 1024)).toFixed(1)} MB`
                      : "Maximum size: 100 MB. Magic bytes verified."}
                  </span>
                </label>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-[#a1a1aa] mb-1 font-mono">
                Display Name (Optional)
              </label>
              <input
                type="text"
                placeholder="My Project"
                value={uploadDisplayName}
                onChange={(e) => setUploadDisplayName(e.target.value)}
                className="w-full bg-[#09090b] border border-[#27272a] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500 font-mono"
              />
            </div>

            <div className="pt-2 flex justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 bg-[#27272a] hover:bg-[#3f3f46] text-white text-sm font-medium rounded-lg transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting || !selectedFile}
                className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 cursor-pointer shadow-xs"
              >
                {isSubmitting ? <Loader2 className="size-4 animate-spin" /> : <Upload className="size-4" />}
                Upload & Ingest
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
