import React from "react";
import {
  FileCode,
  ShieldCheck,
  ShieldAlert,
  MessageSquare,
} from "lucide-react";
import { useNavigate } from "react-router";

interface FileInfoHeaderProps {
  repoId: string;
  path: string;
  language: string;
  loc: number;
  sizeBytes: number;
  redactionCount: number;
  imports: string[];
}

export const FileInfoHeader: React.FC<FileInfoHeaderProps> = ({
  repoId,
  path,
  language,
  loc,
  sizeBytes,
  redactionCount,
  imports,
}) => {
  const navigate = useNavigate();

  const handleAskAboutFile = () => {
    navigate(`/app/repos/${repoId}/chat?file=${encodeURIComponent(path)}`);
  };

  return (
    <div className="flex flex-col gap-2 p-3 bg-[#141416] border-b border-zinc-800">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileCode className="size-4 text-emerald-400" />
          <h2 className="font-mono text-sm font-semibold text-zinc-100 text-balance">{path}</h2>
        </div>

        <button
          onClick={handleAskAboutFile}
          className="flex items-center gap-1.5 px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs transition-colors font-medium cursor-pointer"
        >
          <MessageSquare className="size-3.5" />
          <span>Ask about this file</span>
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-400">
        <span className="px-2 py-0.5 bg-zinc-800/80 rounded text-zinc-300 capitalize font-mono text-[11px]">
          {language}
        </span>
        <span>·</span>
        <span className="tabular-nums font-mono">{loc.toLocaleString()} LOC</span>
        <span>·</span>
        <span className="tabular-nums font-mono">{(sizeBytes / 1024).toFixed(1)} KB</span>

        <span>·</span>
        {redactionCount > 0 ? (
          <span className="flex items-center gap-1 px-2 py-0.5 bg-amber-950/60 text-amber-300 border border-amber-800/60 rounded text-[11px] tabular-nums font-mono">
            <ShieldAlert className="size-3 text-amber-400" />
            <span>{redactionCount} secret{redactionCount === 1 ? "" : "s"} redacted</span>
          </span>
        ) : (
          <span className="flex items-center gap-1 text-[11px] text-zinc-500">
            <ShieldCheck className="size-3 text-emerald-500" />
            <span>0 secrets redacted</span>
          </span>
        )}

        {imports.length > 0 && (
          <div className="flex items-center gap-1 ml-auto overflow-hidden max-w-[40%]">
            <span className="text-zinc-500 text-[11px] shrink-0">Imports:</span>
            <div className="flex items-center gap-1 overflow-x-auto custom-scrollbar">
              {imports.slice(0, 5).map((imp) => (
                <span
                  key={imp}
                  className="px-1.5 py-0.2 bg-zinc-800 text-zinc-400 rounded text-[10px] font-mono shrink-0"
                >
                  {imp}
                </span>
              ))}
              {imports.length > 5 && (
                <span className="text-[10px] text-zinc-500 shrink-0">
                  +{imports.length - 5} more
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
