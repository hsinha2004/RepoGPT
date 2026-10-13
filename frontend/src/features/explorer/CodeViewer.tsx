import React, { useEffect, useRef, useState } from "react";
import { Copy, Check, MessageSquareCode, Link2 } from "lucide-react";
import { toast } from "sonner";

interface CodeViewerProps {
  content: string;
  language: string;
  highlightRange: { start: number; end: number } | null;
  onSelectRange: (range: { start: number; end: number } | null) => void;
  onAskAboutSelection: (start: number, end: number) => void;
}

export const CodeViewer: React.FC<CodeViewerProps> = ({
  content,
  highlightRange,
  onSelectRange,
  onAskAboutSelection,
}) => {
  const [copied, setCopied] = useState(false);
  const lineRefs = useRef<Record<number, HTMLDivElement | null>>({});

  const lines = React.useMemo(() => content.split("\n"), [content]);

  // Scroll to highlightRange start when it changes
  useEffect(() => {
    if (highlightRange && highlightRange.start) {
      const el = lineRefs.current[highlightRange.start];
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }
  }, [highlightRange]);

  const handleLineClick = (lineNum: number, event: React.MouseEvent) => {
    if (event.shiftKey && highlightRange) {
      const start = Math.min(highlightRange.start, lineNum);
      const end = Math.max(highlightRange.end, lineNum);
      onSelectRange({ start, end });
    } else {
      if (
        highlightRange &&
        highlightRange.start === lineNum &&
        highlightRange.end === lineNum
      ) {
        onSelectRange(null);
      } else {
        onSelectRange({ start: lineNum, end: lineNum });
      }
    }
  };

  const copyPermalink = () => {
    let url = window.location.href.split("#")[0];
    if (highlightRange) {
      url +=
        highlightRange.start === highlightRange.end
          ? `#L${highlightRange.start}`
          : `#L${highlightRange.start}-L${highlightRange.end}`;
    }
    navigator.clipboard.writeText(url);
    toast.success("Permalink copied to clipboard");
  };

  const copyCode = () => {
    let textToCopy = content;
    if (highlightRange) {
      textToCopy = lines
        .slice(highlightRange.start - 1, highlightRange.end)
        .join("\n");
    }
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    toast.success("Code copied");
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex flex-col h-full bg-white font-mono text-xs select-text text-zinc-900">
      {/* Code Viewer Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-zinc-50 border-b border-zinc-200 text-zinc-600">
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-zinc-500 font-sans tabular-nums">
            {lines.length} lines · {content.length.toLocaleString()} bytes
          </span>
          {highlightRange && (
            <span className="text-[11px] text-emerald-800 font-sans bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 font-medium tabular-nums">
              Lines {highlightRange.start}
              {highlightRange.end !== highlightRange.start && `–${highlightRange.end}`} selected
            </span>
          )}
        </div>

        <div className="flex items-center gap-1.5">
          {highlightRange && (
            <button
              onClick={() =>
                onAskAboutSelection(highlightRange.start, highlightRange.end)
              }
              className="flex items-center gap-1 px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-xs transition-colors font-sans cursor-pointer shadow-xs"
            >
              <MessageSquareCode className="size-3.5" />
              <span>Ask about selection</span>
            </button>
          )}

          <button
            onClick={copyPermalink}
            title="Copy deep-link permalink"
            aria-label="Copy deep-link permalink"
            className="flex items-center gap-1 px-2 py-1 bg-white border border-zinc-200 hover:bg-zinc-100 text-zinc-700 rounded text-xs transition-colors font-sans cursor-pointer shadow-xs"
          >
            <Link2 className="size-3.5" />
            <span>Permalink</span>
          </button>

          <button
            onClick={copyCode}
            title="Copy content"
            aria-label="Copy code content"
            className="flex items-center gap-1 px-2 py-1 bg-white border border-zinc-200 hover:bg-zinc-100 text-zinc-700 rounded text-xs transition-colors font-sans cursor-pointer shadow-xs"
          >
            {copied ? (
              <Check className="size-3.5 text-emerald-600" />
            ) : (
              <Copy className="size-3.5" />
            )}
            <span>{copied ? "Copied" : "Copy"}</span>
          </button>
        </div>
      </div>

      {/* Code Text with Line Numbers */}
      <div className="flex-1 overflow-auto py-2 custom-scrollbar">
        <table className="w-full border-collapse">
          <tbody>
            {lines.map((line, index) => {
              const lineNum = index + 1;
              const isHighlighted =
                highlightRange &&
                lineNum >= highlightRange.start &&
                lineNum <= highlightRange.end;

              return (
                <tr
                  key={lineNum}
                  ref={(el) => {
                    lineRefs.current[lineNum] = el;
                  }}
                  className={`group transition-colors ${
                    isHighlighted
                      ? "bg-emerald-50/80 text-emerald-950"
                      : "hover:bg-zinc-50 text-zinc-800"
                  }`}
                >
                  {/* Line Number */}
                  <td
                    onClick={(e) => handleLineClick(lineNum, e)}
                    className={`py-0.5 px-3 select-none text-right cursor-pointer w-12 border-r border-zinc-200 text-[11px] font-mono tabular-nums ${
                      isHighlighted
                        ? "text-emerald-700 font-semibold bg-emerald-100/60"
                        : "text-zinc-400 group-hover:text-zinc-700"
                    }`}
                  >
                    {lineNum}
                  </td>

                  {/* Line Content */}
                  <td className="py-0.5 px-4 whitespace-pre font-mono leading-5 overflow-x-visible">
                    {line || " "}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
