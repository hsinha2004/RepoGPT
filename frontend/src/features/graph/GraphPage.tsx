import React, { useState, useEffect, useMemo, useCallback } from "react";
import { useParams, Link, useNavigate } from "react-router";
import { useQuery } from "@tanstack/react-query";
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
  MarkerType,
  Handle,
  Position,
  BackgroundVariant,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import ELK from "elkjs/lib/elk.bundled.js";
import { apiClient } from "../../api/client";
import {
  Search,
  Eye,
  ArrowRight,
  MessageSquare,
  FileCode,
  AlertTriangle,
  RefreshCw,
  X,
  Sliders,
} from "lucide-react";

const elk = new ELK();

interface GraphNodeData {
  id: string;
  label: string;
  pagerank: number;
  fan_in: number;
  fan_out: number;
  is_external: boolean;
  in_cycle: boolean;
  top_dir: string;
  loc?: number;
  language?: string;
  isSelected?: boolean;
}

interface GraphEdgeData {
  source: string;
  target: string;
  type: string;
  heuristic: boolean;
  symbol?: string | null;
  in_cycle?: boolean;
}

interface GraphApiResponse {
  level: "file" | "directory";
  node_count: number;
  edge_count: number;
  nodes: GraphNodeData[];
  edges: GraphEdgeData[];
  cycles: string[][];
  orphans: string[];
}

const DIR_COLORS: Record<string, { bg: string; border: string; text: string; dot: string }> = {
  backend: { bg: "bg-[#6366f1]/10", border: "border-[#6366f1]/40", text: "text-[#a5b4fc]", dot: "bg-[#6366f1]" },
  app: { bg: "bg-[#6366f1]/10", border: "border-[#6366f1]/40", text: "text-[#a5b4fc]", dot: "bg-[#6366f1]" },
  frontend: { bg: "bg-[#10b981]/10", border: "border-[#10b981]/40", text: "text-[#6ee7b7]", dot: "bg-[#10b981]" },
  src: { bg: "bg-[#06b6d4]/10", border: "border-[#06b6d4]/40", text: "text-[#67e8f9]", dot: "bg-[#06b6d4]" },
  services: { bg: "bg-[#8b5cf6]/10", border: "border-[#8b5cf6]/40", text: "text-[#c4b5fd]", dot: "bg-[#8b5cf6]" },
  api: { bg: "bg-[#3b82f6]/10", border: "border-[#3b82f6]/40", text: "text-[#93c5fd]", dot: "bg-[#3b82f6]" },
  db: { bg: "bg-[#f59e0b]/10", border: "border-[#f59e0b]/40", text: "text-[#fcd34d]", dot: "bg-[#f59e0b]" },
  models: { bg: "bg-[#ec4899]/10", border: "border-[#ec4899]/40", text: "text-[#f472b6]", dot: "bg-[#ec4899]" },
  tests: { bg: "bg-[#14b8a6]/10", border: "border-[#14b8a6]/40", text: "text-[#5eead4]", dot: "bg-[#14b8a6]" },
  default: { bg: "bg-[#27272a]/40", border: "border-[#3f3f46]", text: "text-[#e4e4e7]", dot: "bg-[#71717a]" },
  external: { bg: "bg-[#18181b]", border: "border-dashed border-[#52525b]", text: "text-[#a1a1aa]", dot: "bg-[#a1a1aa]" },
};

function getDirColor(topDir: string, isExternal: boolean) {
  if (isExternal) return DIR_COLORS.external;
  const key = topDir.toLowerCase();
  return DIR_COLORS[key] || DIR_COLORS.default;
}

// Custom Node Component
const CustomGraphNode: React.FC<{ data: GraphNodeData }> = ({ data }) => {
  const colors = getDirColor(data.top_dir, data.is_external);

  return (
    <div
      className={`px-3 py-2 rounded-xl border backdrop-blur-md transition-all duration-150 min-w-[200px] max-w-[280px] shadow-lg ${
        colors.bg
      } ${colors.border} ${
        data.isSelected ? "ring-2 ring-[#6366f1] border-transparent shadow-[#6366f1]/20" : ""
      } ${data.in_cycle ? "ring-2 ring-[#f43f5e]/80" : ""}`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!w-2 !h-2 !bg-[#6366f1] !border-none"
      />

      <div className="flex items-center justify-between gap-1.5 mb-1">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className={`w-2 h-2 rounded-full shrink-0 ${colors.dot}`} />
          <span className="text-[10px] uppercase font-mono font-semibold tracking-wider text-[#71717a] truncate">
            {data.is_external ? "External" : data.top_dir || "root"}
          </span>
        </div>

        {data.in_cycle && (
          <span className="px-1.5 py-0.2 rounded text-[9px] font-bold uppercase bg-[#f43f5e]/20 text-[#f43f5e] border border-[#f43f5e]/40">
            Cycle
          </span>
        )}
      </div>

      <div className="font-mono text-xs font-semibold text-white truncate" title={data.id}>
        {data.label}
      </div>

      <div className="flex items-center justify-between mt-2 pt-1.5 border-t border-[#27272a]/60 text-[10px] font-mono text-[#a1a1aa]">
        <div className="flex items-center gap-2">
          <span title={`Fan-in (imported by ${data.fan_in} files)`}>↓{data.fan_in}</span>
          <span title={`Fan-out (imports ${data.fan_out} files)`}>↑{data.fan_out}</span>
        </div>
        <span className="text-[#818cf8]" title="PageRank centrality">
          PR {(data.pagerank * 100).toFixed(1)}%
        </span>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className="!w-2 !h-2 !bg-[#6366f1] !border-none"
      />
    </div>
  );
};

const nodeTypes = {
  custom: CustomGraphNode,
};

export const GraphPage: React.FC = () => {
  const { repoId } = useParams<{ repoId: string }>();
  const navigate = useNavigate();

  // Filter & Query States
  const [level, setLevel] = useState<"file" | "directory">("file");
  const [depth, setDepth] = useState<number>(3);
  const [focus, setFocus] = useState<string>("");
  const [includeExternal, setIncludeExternal] = useState<boolean>(false);
  const [includeCalls, setIncludeCalls] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Selection & Inspector
  const [selectedNode, setSelectedNode] = useState<GraphNodeData | null>(null);

  // React Flow State
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [isLayouting, setIsLayouting] = useState<boolean>(false);

  // Fetch Graph API
  const { data: graphData, isLoading, refetch } = useQuery<GraphApiResponse>({
    queryKey: [
      "repo-graph",
      repoId,
      level,
      depth,
      focus,
      includeExternal,
      includeCalls,
    ],
    queryFn: async () => {
      const res = await apiClient.GET("/api/v1/repos/{repo_id}/graph", {
        params: {
          path: { repo_id: repoId! },
          query: {
            level,
            depth: depth || undefined,
            focus: focus || undefined,
            hops: 1,
            include_external: includeExternal,
            include_calls: includeCalls,
          },
        },
      });
      if (res.error) throw new Error("Failed to load graph");
      return res.data as unknown as GraphApiResponse;
    },
    enabled: !!repoId,
  });

  // Layout Computation with ELK
  useEffect(() => {
    if (!graphData) return;

    let isMounted = true;
    setIsLayouting(true);

    const rawNodes = graphData.nodes || [];
    const rawEdges = graphData.edges || [];

    // Filter by search query if set
    const filteredNodes = searchQuery
      ? rawNodes.filter(
          (n) =>
            n.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
            n.label.toLowerCase().includes(searchQuery.toLowerCase())
        )
      : rawNodes;

    const visibleNodeIds = new Set(filteredNodes.map((n) => n.id));

    const visibleEdges = rawEdges.filter(
      (e) => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target)
    );

    const elkChildren = filteredNodes.map((n) => ({
      id: n.id,
      width: 220,
      height: 76,
    }));

    const elkEdges = visibleEdges.map((e, idx) => ({
      id: `e-${e.source}-${e.target}-${idx}`,
      sources: [e.source],
      targets: [e.target],
    }));

    const elkGraph = {
      id: "root",
      layoutOptions: {
        "elk.algorithm": "layered",
        "elk.direction": "RIGHT",
        "elk.spacing.nodeNode": "50",
        "elk.layered.spacing.nodeNodeBetweenLayers": "80",
        "elk.edgeRouting": "SPLINES",
      },
      children: elkChildren,
      edges: elkEdges,
    };

    elk
      .layout(elkGraph)
      .then((layouted) => {
        if (!isMounted) return;

        const posMap = new Map<string, { x: number; y: number }>();
        for (const child of layouted.children || []) {
          posMap.set(child.id, { x: child.x || 0, y: child.y || 0 });
        }

        const flowNodes: Node[] = filteredNodes.map((n) => ({
          id: n.id,
          type: "custom",
          position: posMap.get(n.id) || { x: 0, y: 0 },
          data: {
            ...n,
            isSelected: selectedNode?.id === n.id,
          },
        }));

        const flowEdges: Edge[] = visibleEdges.map((e, idx) => {
          const isCall = e.heuristic;
          const inCycle = e.in_cycle;

          return {
            id: `e-${e.source}-${e.target}-${idx}`,
            source: e.source,
            target: e.target,
            animated: inCycle,
            style: {
              stroke: inCycle ? "#f43f5e" : isCall ? "#a855f7" : "#6366f1",
              strokeWidth: inCycle ? 2.5 : isCall ? 1.5 : 2,
              strokeDasharray: isCall ? "4 4" : undefined,
              opacity: 0.75,
            },
            markerEnd: {
              type: MarkerType.ArrowClosed,
              width: 14,
              height: 14,
              color: inCycle ? "#f43f5e" : isCall ? "#a855f7" : "#6366f1",
            },
            data: e as unknown as Record<string, unknown>,
          };
        });

        setNodes(flowNodes);
        setEdges(flowEdges);
        setIsLayouting(false);
      })
      .catch((err) => {
        console.error("ELK Layout error:", err);
        // Fallback: simple grid positioning
        const flowNodes: Node[] = filteredNodes.map((n, idx) => ({
          id: n.id,
          type: "custom",
          position: { x: (idx % 6) * 260, y: Math.floor(idx / 6) * 120 },
          data: {
            ...n,
            isSelected: selectedNode?.id === n.id,
          },
        }));
        setNodes(flowNodes);
        setIsLayouting(false);
      });

    return () => {
      isMounted = false;
    };
  }, [graphData, searchQuery, selectedNode]);

  // Handle Node Selection
  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      const nodeData = node.data as unknown as GraphNodeData;
      setSelectedNode(nodeData);
    },
    []
  );

  // Inspector dependencies
  const incomingDependencies = useMemo(() => {
    if (!selectedNode || !graphData?.edges) return [];
    return graphData.edges.filter((e) => e.target === selectedNode.id);
  }, [selectedNode, graphData]);

  const outgoingDependencies = useMemo(() => {
    if (!selectedNode || !graphData?.edges) return [];
    return graphData.edges.filter((e) => e.source === selectedNode.id);
  }, [selectedNode, graphData]);

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] -m-6 relative overflow-hidden bg-[#09090b]">
      {/* Top Controls Toolbar */}
      <div className="px-6 py-3 border-b border-[#27272a] bg-[#111113]/90 backdrop-blur z-20 flex flex-wrap items-center justify-between gap-4">
        {/* Left: View Level & Search */}
        <div className="flex items-center gap-3">
          <div className="flex items-center p-0.5 rounded-lg bg-[#18181b] border border-[#27272a]">
            <button
              onClick={() => setLevel("file")}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                level === "file"
                  ? "bg-[#6366f1] text-white shadow-sm"
                  : "text-[#a1a1aa] hover:text-white"
              }`}
            >
              File Level
            </button>
            <button
              onClick={() => setLevel("directory")}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                level === "directory"
                  ? "bg-[#6366f1] text-white shadow-sm"
                  : "text-[#a1a1aa] hover:text-white"
              }`}
            >
              Directory Level
            </button>
          </div>

          {/* Search within graph */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-[#71717a] absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Filter graph nodes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 pr-3 py-1 text-xs bg-[#18181b] border border-[#27272a] rounded-lg text-white placeholder-[#71717a] focus:outline-none focus:border-[#6366f1] w-48"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-2.5 top-2 text-[#71717a] hover:text-white"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>
        </div>

        {/* Center: Graph Stats */}
        <div className="flex items-center gap-4 text-xs font-mono text-[#a1a1aa]">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#6366f1]" />
            <span>{graphData?.node_count || 0} Nodes</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#10b981]" />
            <span>{graphData?.edge_count || 0} Edges</span>
          </div>
          {graphData?.cycles && graphData.cycles.length > 0 && (
            <div className="flex items-center gap-1.5 text-[#f43f5e] font-semibold">
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>{graphData.cycles.length} Cycles</span>
            </div>
          )}
        </div>

        {/* Right: Toggles & Depth */}
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5 text-xs text-[#a1a1aa] cursor-pointer">
            <input
              type="checkbox"
              checked={includeCalls}
              onChange={(e) => setIncludeCalls(e.target.checked)}
              className="rounded bg-[#18181b] border-[#27272a] text-[#6366f1] focus:ring-0"
            />
            <span>Heuristic Calls</span>
          </label>

          <label className="flex items-center gap-1.5 text-xs text-[#a1a1aa] cursor-pointer">
            <input
              type="checkbox"
              checked={includeExternal}
              onChange={(e) => setIncludeExternal(e.target.checked)}
              className="rounded bg-[#18181b] border-[#27272a] text-[#6366f1] focus:ring-0"
            />
            <span>External pkgs</span>
          </label>

          {/* Depth selector */}
          <div className="flex items-center gap-1.5 text-xs text-[#a1a1aa]">
            <Sliders className="w-3 h-3" />
            <span>Depth:</span>
            <select
              value={depth}
              onChange={(e) => setDepth(Number(e.target.value))}
              className="bg-[#18181b] border border-[#27272a] rounded px-2 py-0.5 text-xs text-white focus:outline-none"
            >
              <option value={1}>1</option>
              <option value={2}>2</option>
              <option value={3}>3</option>
              <option value={4}>4</option>
              <option value={5}>5</option>
            </select>
          </div>

          {focus && (
            <button
              onClick={() => setFocus("")}
              className="flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-[#27272a] text-[#c7d2fe] hover:bg-[#3f3f46] transition-colors"
            >
              <span>Focus: {focus.split("/").pop()}</span>
              <X className="w-3 h-3" />
            </button>
          )}

          <button
            onClick={() => refetch()}
            className="p-1.5 rounded-lg border border-[#27272a] bg-[#18181b] text-[#a1a1aa] hover:text-white transition-colors cursor-pointer"
            title="Refresh graph"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading || isLayouting ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Main Canvas Area */}
      <div className="flex-1 relative w-full h-full">
        {isLoading || isLayouting ? (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-[#09090b]/80 backdrop-blur-sm">
            <RefreshCw className="w-8 h-8 text-[#6366f1] animate-spin mb-3" />
            <p className="text-sm font-medium text-white">Computing Graph Layout (ELK)...</p>
            <p className="text-xs text-[#71717a] mt-1">Hierarchical dependency routing &amp; cycles</p>
          </div>
        ) : null}

        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          fitView
          attributionPosition="bottom-left"
          className="bg-[#09090b]"
        >
          <Background color="#27272a" gap={20} size={1} variant={BackgroundVariant.Dots} />
          <Controls className="!bg-[#18181b] !border-[#27272a] !fill-white" />
          <MiniMap
            nodeColor={(node) => {
              const data = node.data as unknown as GraphNodeData;
              if (data?.in_cycle) return "#f43f5e";
              if (data?.is_external) return "#52525b";
              return "#6366f1";
            }}
            className="!bg-[#111113] !border-[#27272a] !rounded-xl overflow-hidden"
          />
        </ReactFlow>

        {/* Side Inspector Drawer */}
        {selectedNode && (
          <div className="absolute right-4 top-4 bottom-4 w-96 bg-[#111113]/95 border border-[#27272a] rounded-2xl shadow-2xl backdrop-blur-md z-30 flex flex-col overflow-hidden animate-in slide-in-from-right-4 duration-200">
            {/* Drawer Header */}
            <div className="p-4 border-b border-[#27272a] flex items-start justify-between bg-[#18181b]">
              <div className="min-w-0 pr-2">
                <div className="flex items-center gap-1.5 mb-1">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      getDirColor(selectedNode.top_dir, selectedNode.is_external).dot
                    }`}
                  />
                  <span className="text-[10px] uppercase font-mono font-semibold text-[#71717a]">
                    {selectedNode.is_external ? "External" : selectedNode.top_dir}
                  </span>
                </div>
                <h3 className="font-mono text-sm font-bold text-white truncate" title={selectedNode.id}>
                  {selectedNode.id}
                </h3>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="p-1 rounded-lg text-[#71717a] hover:text-white hover:bg-[#27272a] transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Metrics Grid */}
            <div className="p-4 border-b border-[#27272a] grid grid-cols-3 gap-2 bg-[#09090b] text-center">
              <div className="p-2 rounded-lg bg-[#111113] border border-[#27272a]">
                <span className="text-[10px] text-[#71717a] block">PageRank</span>
                <span className="font-mono text-xs font-bold text-[#818cf8]">
                  {(selectedNode.pagerank * 100).toFixed(2)}%
                </span>
              </div>
              <div className="p-2 rounded-lg bg-[#111113] border border-[#27272a]">
                <span className="text-[10px] text-[#71717a] block">Fan-In</span>
                <span className="font-mono text-xs font-bold text-[#10b981]">
                  {selectedNode.fan_in}
                </span>
              </div>
              <div className="p-2 rounded-lg bg-[#111113] border border-[#27272a]">
                <span className="text-[10px] text-[#71717a] block">Fan-Out</span>
                <span className="font-mono text-xs font-bold text-[#f59e0b]">
                  {selectedNode.fan_out}
                </span>
              </div>
            </div>

            {/* Cycle Warning */}
            {selectedNode.in_cycle && (
              <div className="m-4 p-3 rounded-lg bg-[#f43f5e]/10 border border-[#f43f5e]/30 flex items-start gap-2.5 text-xs text-[#f43f5e]">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold block">Circular Dependency Warning</span>
                  <span className="text-[11px] text-[#fca5a5]">
                    This module participates in one or more import cycles. Refactor dependencies to decouple.
                  </span>
                </div>
              </div>
            )}

            {/* Incoming & Outgoing Dependencies Lists */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* Incoming: Imported By */}
              <div>
                <span className="text-xs font-semibold text-white block mb-2 flex items-center gap-1.5">
                  <ArrowRight className="w-3.5 h-3.5 text-[#10b981] rotate-180" />
                  Imported By ({incomingDependencies.length})
                </span>
                {incomingDependencies.length === 0 ? (
                  <p className="text-[11px] text-[#71717a] italic">No incoming imports (entry point or leaf)</p>
                ) : (
                  <div className="space-y-1">
                    {incomingDependencies.map((dep, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          const n = graphData?.nodes.find((item) => item.id === dep.source);
                          if (n) setSelectedNode(n);
                        }}
                        className="w-full text-left p-1.5 rounded bg-[#18181b] border border-[#27272a] hover:border-[#6366f1]/50 text-xs font-mono text-[#d4d4d8] truncate flex items-center justify-between cursor-pointer"
                      >
                        <span className="truncate">{dep.source}</span>
                        {dep.heuristic && (
                          <span className="text-[9px] text-[#a855f7] uppercase font-bold shrink-0 ml-1">
                            Call
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Outgoing: Imports */}
              <div>
                <span className="text-xs font-semibold text-white block mb-2 flex items-center gap-1.5">
                  <ArrowRight className="w-3.5 h-3.5 text-[#f59e0b]" />
                  Imports ({outgoingDependencies.length})
                </span>
                {outgoingDependencies.length === 0 ? (
                  <p className="text-[11px] text-[#71717a] italic">No outgoing imports (leaf dependency)</p>
                ) : (
                  <div className="space-y-1">
                    {outgoingDependencies.map((dep, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          const n = graphData?.nodes.find((item) => item.id === dep.target);
                          if (n) setSelectedNode(n);
                        }}
                        className="w-full text-left p-1.5 rounded bg-[#18181b] border border-[#27272a] hover:border-[#6366f1]/50 text-xs font-mono text-[#d4d4d8] truncate flex items-center justify-between cursor-pointer"
                      >
                        <span className="truncate">{dep.target}</span>
                        {dep.heuristic && (
                          <span className="text-[9px] text-[#a855f7] uppercase font-bold shrink-0 ml-1">
                            Call
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Drawer Actions Footer */}
            <div className="p-4 border-t border-[#27272a] bg-[#18181b] flex flex-col gap-2">
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => {
                    setFocus(selectedNode.id);
                  }}
                  className="flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[#27272a] text-white hover:bg-[#3f3f46] transition-colors cursor-pointer"
                >
                  <Eye className="w-3.5 h-3.5 text-[#818cf8]" />
                  <span>Focus in Graph</span>
                </button>

                {!selectedNode.is_external && (
                  <Link
                    to={`/app/repos/${repoId}/explorer?file=${encodeURIComponent(selectedNode.id)}`}
                    className="flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[#27272a] text-white hover:bg-[#3f3f46] transition-colors"
                  >
                    <FileCode className="w-3.5 h-3.5 text-[#10b981]" />
                    <span>View in Explorer</span>
                  </Link>
                )}
              </div>

              <button
                onClick={() =>
                  navigate(
                    `/app/repos/${repoId}/chat?q=${encodeURIComponent(
                      `Explain the architecture, role, and incoming dependencies of module ${selectedNode.id}`
                    )}`
                  )
                }
                className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold bg-[#6366f1] text-white hover:bg-[#4f46e5] transition-colors shadow-sm cursor-pointer"
              >
                <MessageSquare className="w-3.5 h-3.5" />
                <span>Ask RepoGPT About This Module</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
