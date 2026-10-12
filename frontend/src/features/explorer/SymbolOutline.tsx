import React, { useState } from "react";
import {
  Code2,
  Boxes,
  FunctionSquare,
  Sparkles,
  Layers,
  Search,
} from "lucide-react";

export interface SymbolItem {
  name: string;
  qualified_name: string;
  kind: string;
  signature: string;
  docstring?: string | null;
  start_line: number;
  end_line: number;
  parent?: string | null;
  language?: string;
  exported?: boolean;
}

interface SymbolOutlineProps {
  symbols: SymbolItem[];
  selectedSymbol: string | null;
  onSelectSymbol: (symbol: SymbolItem) => void;
}

function getSymbolIcon(kind: string) {
  const k = kind.toLowerCase();
  if (k === "class" || k === "interface" || k === "struct") {
    return <Boxes className="size-3.5 text-teal-400 shrink-0" />;
  }
  if (k === "function" || k === "method") {
    return <FunctionSquare className="size-3.5 text-emerald-400 shrink-0" />;
  }
  if (k === "component") {
    return <Sparkles className="size-3.5 text-emerald-300 shrink-0" />;
  }
  return <Code2 className="size-3.5 text-zinc-400 shrink-0" />;
}

export const SymbolOutline: React.FC<SymbolOutlineProps> = ({
  symbols,
  selectedSymbol,
  onSelectSymbol,
}) => {
  const [search, setSearch] = useState("");

  const filteredSymbols = symbols.filter(
    (s) =>
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.signature.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex flex-col h-full bg-[#111113] border-l border-zinc-800/80">
      <div className="p-2.5 border-b border-zinc-800/80 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-zinc-300">
            <Layers className="size-3.5 text-emerald-400" />
            <span>Outline ({symbols.length})</span>
          </div>
        </div>

        <div className="relative">
          <Search className="size-3.5 absolute left-2.5 top-2.5 text-zinc-400 pointer-events-none" />
          <input
            type="text"
            placeholder="Filter symbols..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-[#18181b] border border-zinc-800 text-zinc-200 text-xs rounded pl-8 pr-2.5 py-1.5 focus:outline-none focus:border-emerald-500 transition-colors font-mono"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto py-1 px-1 custom-scrollbar space-y-0.5">
        {filteredSymbols.length === 0 ? (
          <div className="p-4 text-center text-xs text-zinc-500 text-pretty">
            {symbols.length === 0 ? "No symbols found" : "No matching symbols"}
          </div>
        ) : (
          filteredSymbols.map((s) => {
            const isSelected = selectedSymbol === s.qualified_name;
            const isChild = Boolean(s.parent);

            return (
              <button
                key={`${s.qualified_name}-${s.start_line}`}
                onClick={() => onSelectSymbol(s)}
                className={`flex items-center gap-2 w-full text-left py-1.5 px-2 rounded text-xs transition-colors group cursor-pointer ${
                  isSelected
                    ? "bg-emerald-950/50 text-emerald-300 font-medium border-l-2 border-emerald-500"
                    : "hover:bg-zinc-800/40 text-zinc-300"
                } ${isChild ? "pl-5" : ""}`}
              >
                {getSymbolIcon(s.kind)}
                <div className="flex-1 min-w-0">
                  <div className="truncate font-mono text-[11px]">{s.name}</div>
                  <div className="text-[10px] text-zinc-500 truncate capitalize font-sans">
                    {s.kind}
                    {s.parent ? ` · in ${s.parent}` : ""}
                  </div>
                </div>
                <span className="text-[10px] text-zinc-500 font-mono shrink-0 tabular-nums">
                  :{s.start_line}
                </span>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
};
