import React, { useEffect, useState, useMemo } from "react";
import { useParams, useNavigate, useLocation } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../../api/client";
import { FileTree, TreeFileItem } from "./FileTree";
import { CodeViewer } from "./CodeViewer";
import { SymbolOutline, SymbolItem } from "./SymbolOutline";
import { FileInfoHeader } from "./FileInfoHeader";
import { Loader2, FileCode, AlertCircle } from "lucide-react";

export const ExplorerPage: React.FC = () => {
  const { repoId } = useParams<{ repoId: string }>();
  const navigate = useNavigate();
  const location = useLocation();

  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [highlightRange, setHighlightRange] = useState<{ start: number; end: number } | null>(
    null
  );

  // Parse deep link hash e.g. #L10-L40 or #L15
  useEffect(() => {
    const hash = location.hash;
    if (hash && hash.startsWith("#L")) {
      const match = hash.slice(2).match(/^(\d+)(?:-L?(\d+))?$/);
      if (match) {
        const start = parseInt(match[1], 10);
        const end = match[2] ? parseInt(match[2], 10) : start;
        setHighlightRange({ start, end });
      }
    }
  }, [location.hash]);

  // Query parameter support: ?file=...
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const fileParam = params.get("file");
    if (fileParam && fileParam !== selectedPath) {
      setSelectedPath(fileParam);
    }
  }, [location.search, selectedPath]);

  // 1. Fetch Files list
  const {
    data: filesData,
    isLoading: filesLoading,
    error: filesError,
  } = useQuery({
    queryKey: ["repo-files", repoId],
    queryFn: async () => {
      if (!repoId) return [];
      const res = await apiClient.GET("/api/v1/repos/{repo_id}/files", {
        params: { path: { repo_id: repoId } },
      });
      if (res.error) throw new Error("Failed to load repository files");
      return res.data || [];
    },
    enabled: Boolean(repoId),
  });

  // 2. Fetch Skipped Files list
  const { data: skippedData } = useQuery({
    queryKey: ["repo-skipped-files", repoId],
    queryFn: async () => {
      if (!repoId) return [];
      const res = await apiClient.GET("/api/v1/repos/{repo_id}/skipped-files", {
        params: { path: { repo_id: repoId } },
      });
      if (res.error) return [];
      return res.data || [];
    },
    enabled: Boolean(repoId),
  });

  const treeFiles = useMemo<TreeFileItem[]>(() => {
    if (!filesData) return [];
    return filesData.map((f: any) => ({
      id: f.id,
      path: f.path,
      language: f.language,
      loc: f.loc,
      kind: f.kind,
      isSkipped: false,
    }));
  }, [filesData]);

  const treeSkipped = useMemo<TreeFileItem[]>(() => {
    if (!skippedData) return [];
    return skippedData.map((s: any) => ({
      path: s.path,
      isSkipped: true,
      skipReason: s.reason,
    }));
  }, [skippedData]);

  // Set default selected file if none selected
  useEffect(() => {
    if (!selectedPath && treeFiles.length > 0) {
      // Pick first non-empty file or README if present
      const readme = treeFiles.find((f) => f.path.toLowerCase().includes("readme"));
      setSelectedPath(readme ? readme.path : treeFiles[0].path);
    }
  }, [selectedPath, treeFiles]);

  // 3. Fetch File Detail
  const { data: fileDetail, isLoading: detailLoading } = useQuery({
    queryKey: ["file-detail", repoId, selectedPath],
    queryFn: async () => {
      if (!repoId || !selectedPath) return null;
      const res = await apiClient.GET("/api/v1/repos/{repo_id}/files/{file_path}", {
        params: {
          path: {
            repo_id: repoId,
            file_path: selectedPath,
          },
        },
      });
      if (res.error) throw new Error("Failed to load file details");
      return res.data;
    },
    enabled: Boolean(repoId && selectedPath),
  });

  const handleSelectFile = (path: string) => {
    setSelectedPath(path);
    setSelectedSymbol(null);
    setHighlightRange(null);
    navigate(`/app/repos/${repoId}/explorer?file=${encodeURIComponent(path)}`, {
      replace: true,
    });
  };

  const handleSelectSymbol = (symbol: SymbolItem) => {
    setSelectedSymbol(symbol.qualified_name);
    setHighlightRange({ start: symbol.start_line, end: symbol.end_line });
    const rangeHash =
      symbol.start_line === symbol.end_line
        ? `#L${symbol.start_line}`
        : `#L${symbol.start_line}-L${symbol.end_line}`;
    window.history.replaceState(null, "", rangeHash);
  };

  const handleAskAboutSelection = (start: number, end: number) => {
    if (!repoId || !selectedPath) return;
    navigate(
      `/app/repos/${repoId}/chat?file=${encodeURIComponent(
        selectedPath
      )}&lines=${start}-${end}`
    );
  };

  if (filesLoading) {
    return (
      <div className="flex flex-1 min-h-0 items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-zinc-400">
          <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
          <span className="text-sm">Loading repository tree...</span>
        </div>
      </div>
    );
  }

  if (filesError) {
    return (
      <div className="flex flex-1 min-h-0 items-center justify-center p-6">
        <div className="flex items-center gap-2 p-4 bg-red-950/40 border border-red-800 text-red-300 rounded text-sm">
          <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
          <span>Failed to load repository files. Please try again or check ingestion status.</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 min-h-0 flex overflow-hidden bg-[#0d0d0f]">
      {/* Left: File Tree Explorer (260px) */}
      <div className="w-64 shrink-0 h-full">
        <FileTree
          files={treeFiles}
          skippedFiles={treeSkipped}
          selectedPath={selectedPath}
          onSelectFile={handleSelectFile}
        />
      </div>

      {/* Center: File Info Header & Code Viewer */}
      <div className="flex-1 flex flex-col h-full min-w-0">
        {selectedPath && fileDetail ? (
          <>
            <FileInfoHeader
              repoId={repoId || ""}
              path={fileDetail.path}
              language={fileDetail.language}
              loc={fileDetail.loc}
              sizeBytes={fileDetail.size_bytes}
              redactionCount={fileDetail.redaction_count}
              imports={fileDetail.imports || []}
            />
            <div className="flex-1 min-h-0">
              <CodeViewer
                content={fileDetail.content}
                language={fileDetail.language}
                highlightRange={highlightRange}
                onSelectRange={setHighlightRange}
                onAskAboutSelection={handleAskAboutSelection}
              />
            </div>
          </>
        ) : detailLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-zinc-500 gap-2">
            <FileCode className="w-8 h-8 text-zinc-600" />
            <p className="text-xs">Select a file from the explorer tree to view its content</p>
          </div>
        )}
      </div>

      {/* Right: Symbol Outline (240px) */}
      {fileDetail && fileDetail.symbols && fileDetail.symbols.length > 0 && (
        <div className="w-64 shrink-0 h-full hidden lg:block">
          <SymbolOutline
            symbols={fileDetail.symbols}
            selectedSymbol={selectedSymbol}
            onSelectSymbol={handleSelectSymbol}
          />
        </div>
      )}
    </div>
  );
};
