import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import {
  CheckCircle2,
  AlertCircle,
  Loader2,
  ArrowRight,
  StopCircle,
  X,
  FileCode,
  ShieldCheck,
  Filter,
} from "lucide-react";
import { streamSSE } from "../../api/sse";
import { getAccessToken } from "../../api/client";

interface IngestionStepperProps {
  jobId: string;
  repoId: string;
  isOpen: boolean;
  onClose: () => void;
}

interface JobProgressEvent {
  job_id: string;
  repo_id: string;
  stage: string;
  progress: number;
  message: string;
  counters?: {
    files_scanned?: number;
    files_kept?: number;
    files_skipped?: number;
    loc?: number;
  };
  warnings?: string[];
  status: string;
}

export const IngestionStepper: React.FC<IngestionStepperProps> = ({
  jobId,
  repoId,
  isOpen,
  onClose,
}) => {
  const navigate = useNavigate();
  const [currentStage, setCurrentStage] = useState<string>("fetching");
  const [progressPercent, setProgressPercent] = useState<number>(5);
  const [statusMessage, setStatusMessage] = useState<string>("Initializing ingestion pipeline...");
  const [counters, setCounters] = useState<JobProgressEvent["counters"]>({});
  const [warnings, setWarnings] = useState<string[]>([]);
  const [jobStatus, setJobStatus] = useState<string>("running");
  const [isCancelling, setIsCancelling] = useState<boolean>(false);

  useEffect(() => {
    if (!isOpen || !jobId) return;

    const controller = new AbortController();

    streamSSE({
      url: `/api/v1/jobs/${jobId}/events`,
      signal: controller.signal,
      onEvent: (event) => {
        if (event.event === "progress" && event.data) {
          const payload = event.data as JobProgressEvent;
          setCurrentStage(payload.stage || "processing");
          setProgressPercent(payload.progress || 0);
          if (payload.message) setStatusMessage(payload.message);
          if (payload.counters) setCounters(payload.counters);
          if (payload.warnings && payload.warnings.length > 0) {
            setWarnings((prev) => Array.from(new Set([...prev, ...payload.warnings!])));
          }
          if (payload.status) setJobStatus(payload.status);
        }
      },
      onError: (err) => {
        console.error("SSE stream error:", err);
      },
    });

    return () => {
      controller.abort();
    };
  }, [isOpen, jobId]);

  if (!isOpen) return null;

  const handleCancel = async () => {
    setIsCancelling(true);
    try {
      const token = getAccessToken();
      await fetch(`/api/v1/jobs/${jobId}/cancel`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      // Ignored
    } finally {
      setIsCancelling(false);
    }
  };

  const handleGoToRepo = () => {
    onClose();
    navigate(`/app/repos/${repoId}/overview`);
  };

  const stagesList = [
    { key: "fetching", label: "Fetching Codebase", icon: FileCode },
    { key: "extracting", label: "Safe Extraction", icon: ShieldCheck },
    { key: "filtering", label: "Filtering & Analysis", icon: Filter },
    { key: "complete", label: "Ready", icon: CheckCircle2 },
  ];

  const getStageState = (stageKey: string) => {
    const stageOrder = ["fetching", "extracting", "filtering", "complete"];
    const currentIndex = stageOrder.indexOf(currentStage === "finished" ? "complete" : currentStage);
    const targetIndex = stageOrder.indexOf(stageKey);

    if (jobStatus === "failed") return "error";
    if (jobStatus === "succeeded" || targetIndex < currentIndex) return "completed";
    if (targetIndex === currentIndex) return "active";
    return "pending";
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-xl bg-[#18181b] border border-[#27272a] rounded-xl shadow-2xl p-6 text-white animate-in fade-in zoom-in-95 duration-150 space-y-6">
        <button
          onClick={onClose}
          aria-label="Close ingestion progress"
          className="absolute right-4 top-4 text-[#71717a] hover:text-white transition-colors cursor-pointer"
        >
          <X className="size-5" />
        </button>

        <div>
          <h2 className="text-xl font-bold text-balance">Repository Ingestion Progress</h2>
          <p className="text-xs text-[#a1a1aa] mt-1 font-mono tabular-nums">Job ID: {jobId}</p>
        </div>

        {/* Stepper Steps */}
        <div className="grid grid-cols-4 gap-2">
          {stagesList.map((step) => {
            const state = getStageState(step.key);
            const Icon = step.icon;
            return (
              <div
                key={step.key}
                className={`p-3 rounded-lg border text-center transition-colors ${
                  state === "active"
                    ? "bg-emerald-500/15 border-emerald-500 text-white shadow-xs"
                    : state === "completed"
                    ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                    : state === "error"
                    ? "bg-red-500/10 border-red-500/30 text-red-400"
                    : "bg-[#09090b] border-[#27272a] text-[#71717a]"
                }`}
              >
                <div className="flex justify-center mb-1">
                  {state === "active" ? (
                    <Loader2 className="size-5 animate-spin text-emerald-400" />
                  ) : (
                    <Icon className="size-5" />
                  )}
                </div>
                <span className="text-[11px] font-medium block leading-tight">{step.label}</span>
              </div>
            );
          })}
        </div>

        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-xs">
            <span className="text-[#a1a1aa]">{statusMessage}</span>
            <span className="font-mono font-semibold text-white tabular-nums">{progressPercent}%</span>
          </div>
          <div className="w-full bg-[#27272a] rounded-full h-2.5 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                jobStatus === "failed"
                  ? "bg-red-500"
                  : jobStatus === "succeeded"
                  ? "bg-emerald-500"
                  : "bg-gradient-to-r from-emerald-500 to-teal-400"
              }`}
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* Metrics Counters */}
        {counters && Object.keys(counters).length > 0 && (
          <div className="grid grid-cols-4 gap-3 p-3 bg-[#09090b] rounded-lg border border-[#27272a] text-center">
            <div>
              <span className="text-[10px] text-[#71717a] font-mono block">Scanned</span>
              <span className="text-sm font-mono font-semibold text-white tabular-nums">
                {counters.files_scanned ?? 0}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-[#71717a] font-mono block">Indexed</span>
              <span className="text-sm font-mono font-semibold text-emerald-400 tabular-nums">
                {counters.files_kept ?? 0}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-[#71717a] font-mono block">Skipped</span>
              <span className="text-sm font-mono font-semibold text-amber-400 tabular-nums">
                {counters.files_skipped ?? 0}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-[#71717a] font-mono block">Lines</span>
              <span className="text-sm font-mono font-semibold text-white tabular-nums">
                {counters.loc ? counters.loc.toLocaleString() : 0}
              </span>
            </div>
          </div>
        )}

        {/* Warnings */}
        {warnings.length > 0 && (
          <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg text-amber-300 text-xs space-y-1">
            <div className="flex items-center gap-1.5 font-semibold">
              <AlertCircle className="size-4" />
              <span>Ingestion Notices</span>
            </div>
            {warnings.map((w, idx) => (
              <p key={idx} className="text-[#fde68a] pl-5 text-pretty">
                • {w}
              </p>
            ))}
          </div>
        )}

        {/* Footer Actions */}
        <div className="flex items-center justify-between pt-2">
          {jobStatus === "running" && (
            <button
              onClick={handleCancel}
              disabled={isCancelling}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs text-red-400 hover:text-red-300 border border-red-500/30 hover:bg-red-500/10 rounded-lg transition-colors cursor-pointer"
            >
              <StopCircle className="size-4" />
              {isCancelling ? "Cancelling..." : "Cancel Ingestion"}
            </button>
          )}

          <div className="ml-auto flex items-center gap-3">
            {jobStatus === "succeeded" ? (
              <button
                onClick={handleGoToRepo}
                className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition-colors shadow-xs cursor-pointer"
              >
                Explore Repository
                <ArrowRight className="size-4" />
              </button>
            ) : (
              <button
                onClick={onClose}
                className="px-4 py-2 bg-[#27272a] hover:bg-[#3f3f46] text-white text-sm font-medium rounded-lg transition-colors cursor-pointer"
              >
                {jobStatus === "failed" ? "Close" : "Run in Background"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
