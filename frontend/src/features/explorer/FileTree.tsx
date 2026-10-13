import React, { useState, useMemo } from "react";
import {
  Folder,
  FolderOpen,
  FileCode,
  FileText,
  FileCog,
  FileQuestion,
  ChevronRight,
  ChevronDown,
  Search,
  AlertCircle,
} from "lucide-react";

export interface TreeFileItem {
  id?: string;
  path: string;
  language?: string;
  loc?: number;
  kind?: string;
  isSkipped?: boolean;
  skipReason?: string;
}

interface TreeNode {
  name: string;
  path: string;
  isDir: boolean;
  children: Record<string, TreeNode>;
  fileItem?: TreeFileItem;
}

interface FileTreeProps {
  files: TreeFileItem[];
  skippedFiles: TreeFileItem[];
  selectedPath: string | null;
  onSelectFile: (path: string) => void;
}

function getFileIcon(lang?: string, isSkipped?: boolean) {
  if (isSkipped) return <AlertCircle className="size-4 text-amber-500 shrink-0" />;
  const l = (lang || "").toLowerCase();
  if (["python", "javascript", "typescript", "java", "go", "code"].includes(l)) {
    return <FileCode className="size-4 text-emerald-600 shrink-0" />;
  }
  if (["markdown", "doc", "docs"].includes(l)) {
    return <FileText className="size-4 text-teal-600 shrink-0" />;
  }
  if (["config", "json", "yaml"].includes(l)) {
    return <FileCog className="size-4 text-zinc-500 shrink-0" />;
  }
  return <FileQuestion className="size-4 text-zinc-400 shrink-0" />;
}

export const FileTree: React.FC<FileTreeProps> = ({
  files,
  skippedFiles,
  selectedPath,
  onSelectFile,
}) => {
  const [search, setSearch] = useState("");
  const [expandedDirs, setExpandedDirs] = useState<Record<string, boolean>>({
    "": true,
  });
  const [showSkipped, setShowSkipped] = useState(false);

  const toggleDir = (dirPath: string) => {
    setExpandedDirs((prev) => ({
      ...prev,
      [dirPath]: !prev[dirPath],
    }));
  };

  const treeRoot = useMemo(() => {
    const root: TreeNode = { name: "", path: "", isDir: true, children: {} };

    const allItems: TreeFileItem[] = [...files];
    if (showSkipped) {
      allItems.push(...skippedFiles);
    }

    const filtered = search
      ? allItems.filter((f) => f.path.toLowerCase().includes(search.toLowerCase()))
      : allItems;

    for (const item of filtered) {
      const parts = item.path.split("/");
      let current = root;

      for (let i = 0; i < parts.length; i++) {
        const part = parts[i];
        const isLast = i === parts.length - 1;
        const currentPath = parts.slice(0, i + 1).join("/");

        if (isLast) {
          current.children[part] = {
            name: part,
            path: item.path,
            isDir: false,
            children: {},
            fileItem: item,
          };
        } else {
          if (!current.children[part]) {
            current.children[part] = {
              name: part,
              path: currentPath,
              isDir: true,
              children: {},
            };
          }
          current = current.children[part];
        }
      }
    }

    return root;
  }, [files, skippedFiles, showSkipped, search]);

  const renderNode = (node: TreeNode, depth: number = 0) => {
    const isExpanded = expandedDirs[node.path] ?? (search ? true : depth < 2);

    if (node.isDir) {
      const sortedChildKeys = Object.keys(node.children).sort((a, b) => {
        const childA = node.children[a];
        const childB = node.children[b];
        if (childA.isDir && !childB.isDir) return -1;
        if (!childA.isDir && childB.isDir) return 1;
        return a.localeCompare(b);
      });

      return (
        <div key={node.path || "root"}>
          {node.path && (
            <button
              onClick={() => toggleDir(node.path)}
              className="flex items-center gap-1.5 w-full text-left py-1 px-2 rounded hover:bg-zinc-200/60 text-xs text-zinc-700 font-mono transition-colors cursor-pointer"
              style={{ paddingLeft: `${depth * 12 + 8}px` }}
            >
              {isExpanded ? (
                <ChevronDown className="size-3.5 text-zinc-400 shrink-0" />
              ) : (
                <ChevronRight className="size-3.5 text-zinc-400 shrink-0" />
              )}
              {isExpanded ? (
                <FolderOpen className="size-4 text-amber-500 shrink-0" />
              ) : (
                <Folder className="size-4 text-amber-500 shrink-0" />
              )}
              <span className="truncate">{node.name}</span>
            </button>
          )}
          {isExpanded && (
            <div>
              {sortedChildKeys.map((k) => renderNode(node.children[k], depth + (node.path ? 1 : 0)))}
            </div>
          )}
        </div>
      );
    }

    const isSelected = selectedPath === node.path;
    const isSkipped = node.fileItem?.isSkipped;

    return (
      <button
        key={node.path}
        disabled={isSkipped}
        onClick={() => onSelectFile(node.path)}
        title={isSkipped ? `Skipped: ${node.fileItem?.skipReason}` : node.path}
        className={`flex items-center gap-2 w-full text-left py-1 px-2 rounded text-xs font-mono transition-colors group cursor-pointer ${
          isSkipped
            ? "opacity-50 cursor-not-allowed text-zinc-400"
            : isSelected
              ? "bg-emerald-50 text-emerald-800 font-semibold border-l-2 border-emerald-600"
              : "hover:bg-zinc-100 text-zinc-600 hover:text-zinc-900"
        }`}
        style={{ paddingLeft: `${depth * 12 + 20}px` }}
      >
        {getFileIcon(node.fileItem?.language, isSkipped)}
        <span className="truncate flex-1">{node.name}</span>
        {node.fileItem?.loc ? (
          <span className="text-[10px] text-zinc-400 opacity-0 group-hover:opacity-100 transition-opacity tabular-nums">
            {node.fileItem.loc}L
          </span>
        ) : null}
      </button>
    );
  };

  return (
    <div className="flex flex-col h-full bg-zinc-50 border-r border-zinc-200">
      {/* Search Header */}
      <div className="p-2.5 border-b border-zinc-200 space-y-2">
        <div className="relative">
          <Search className="size-3.5 absolute left-2.5 top-2.5 text-zinc-400 pointer-events-none" />
          <input
            type="text"
            placeholder="Search files..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-white border border-zinc-200 text-zinc-900 text-xs rounded pl-8 pr-2.5 py-1.5 focus:outline-none focus:border-emerald-500 transition-colors font-mono shadow-xs"
          />
        </div>

        {skippedFiles.length > 0 && (
          <div className="flex items-center justify-between text-[11px] px-1 text-zinc-500">
            <span className="tabular-nums font-mono">{files.length} indexed files</span>
            <button
              onClick={() => setShowSkipped(!showSkipped)}
              className="hover:text-amber-600 transition-colors text-[10px] underline underline-offset-2 tabular-nums font-mono cursor-pointer"
            >
              {showSkipped ? "Hide skipped" : `+${skippedFiles.length} skipped`}
            </button>
          </div>
        )}
      </div>

      {/* Virtual/Nested Tree List */}
      <div className="flex-1 overflow-y-auto py-1 px-1 custom-scrollbar">
        {renderNode(treeRoot, 0)}
      </div>
    </div>
  );
};
