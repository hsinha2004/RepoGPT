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
  top_dir?: string;
  top_directory?: string;
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
  node_count?: number;
  edge_count?: number;
  total_nodes?: number;
  total_edges?: number;
  nodes: GraphNodeData[];
  edges: GraphEdgeData[];
  cycles: string[][];
  orphans?: string[];
  orphan_count?: number;
}

const DIR_COLORS: Record<string, { bg: string; border: string; text: string; dot: string }> = {
  backend: { bg: "bg-emerald-50", border: "border-emerald-300", text: "text-emerald-800", dot: "bg-emerald-600" },
  app: { bg: "bg-emerald-50", border: "border-emerald-300", text: "text-emerald-800", dot: "bg-emerald-600" },
  frontend: { bg: "bg-teal-50", border: "border-teal-300", text: "text-teal-800", dot: "bg-teal-600" },
  src: { bg: "bg-cyan-50", border: "border-cyan-300", text: "text-cyan-800", dot: "bg-cyan-600" },
  services: { bg: "bg-emerald-50", border: "border-emerald-300", text: "text-emerald-800", dot: "bg-emerald-600" },
  api: { bg: "bg-teal-50", border: "border-teal-300", text: "text-teal-800", dot: "bg-teal-600" },
  db: { bg: "bg-amber-50", border: "border-amber-300", text: "text-amber-800", dot: "bg-amber-600" },
  models: { bg: "bg-emerald-50", border: "border-emerald-300", text: "text-emerald-800", dot: "bg-emerald-600" },
  tests: { bg: "bg-teal-50", border: "border-teal-300", text: "text-teal-800", dot: "bg-teal-600" },
  default: { bg: "bg-white", border: "border-zinc-300", text: "text-zinc-800", dot: "bg-zinc-500" },
  external: { bg: "bg-zinc-100", border: "border-dashed border-zinc-400", text: "text-zinc-600", dot: "bg-zinc-500" },
};

function getDirColor(topDir?: string | null, isExternal?: boolean) {
  if (isExternal) return DIR_COLORS.external;
  const key = (topDir || "").toLowerCase();
  return DIR_COLORS[key] || DIR_COLORS.default;
}

// Custom Node Component
const CustomGraphNode: React.FC<{ data: GraphNodeData }> = ({ data }) => {
  const dirName = data.top_directory || data.top_dir || "root";
  const colors = getDirColor(dirName, data.is_external);

  return (
    <div
      className={`px-3 py-2 rounded-xl border backdrop-blur-md transition-colors min-w-[200px] max-w-[280px] shadow-sm ${
        colors.bg
      } ${colors.border} ${
        data.isSelected ? "ring-2 ring-emerald-500 border-transparent shadow-emerald-500/20" : ""
      } ${data.in_cycle ? "ring-2 ring-rose-500" : ""}`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!size-2 !bg-emerald-600 !border-none"
      />

      <div className="flex items-center justify-between gap-1.5 mb-1">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className={`size-2 rounded-full shrink-0 ${colors.dot}`} />
          <span className="text-[10px] uppercase font-mono font-semibold text-zinc-500 truncate">
            {data.is_external ? "External" : dirName}
          </span>
        </div>

        {data.in_cycle && (
          <span className="px-1.5 py-0.2 rounded text-[9px] font-bold uppercase bg-rose-50 text-rose-700 border border-rose-200">
            Cycle
          </span>
        )}
      </div>

      <div className="font-mono text-xs font-semibold text-zinc-900 truncate" title={data.id}>
        {data.label}
      </div>

      <div className="flex items-center justify-between mt-2 pt-1.5 border-t border-zinc-200 text-[10px] font-mono text-zinc-600 tabular-nums">
        <div className="flex items-center gap-2">
          <span title={`Fan-in (imported by ${data.fan_in} files)`}>↓{data.fan_in}</span>
          <span title={`Fan-out (imports ${data.fan_out} files)`}>↑{data.fan_out}</span>
        </div>
        <span className="text-emerald-700 font-semibold" title="PageRank centrality">
          PR {(data.pagerank * 100).toFixed(1)}%
        </span>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className="!size-2 !bg-emerald-600 !border-none"
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

    if (filteredNodes.length === 0) {
      setNodes([]);
      setEdges([]);
      setIsLayouting(false);
      return;
    }

    setIsLayouting(true);

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
              stroke: inCycle ? "#e11d48" : isCall ? "#0d9488" : "#059669",
              strokeWidth: inCycle ? 2.5 : isCall ? 1.5 : 2,
              strokeDasharray: isCall ? "4 4" : undefined,
              opacity: 0.8,
            },
            markerEnd: {
              type: MarkerType.ArrowClosed,
              width: 14,
              height: 14,
              color: inCycle ? "#e11d48" : isCall ? "#0d9488" : "#059669",
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
  }, [graphData, searchQuery]);

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
    <div className="flex flex-col flex-1 min-h-0 relative overflow-hidden bg-zinc-50">
      {/* Top Controls Toolbar */}
      <div className="px-6 py-3 border-b border-zinc-200 bg-white/95 backdrop-blur z-20 flex flex-wrap items-center justify-between gap-4 shadow-xs">
        {/* Left: View Level & Search */}
        <div className="flex items-center gap-3">
          <div className="flex items-center p-0.5 rounded-lg bg-zinc-100 border border-zinc-200">
            <button
              onClick={() => setLevel("file")}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors cursor-pointer ${
                level === "file"
                  ? "bg-white text-zinc-900 shadow-xs"
                  : "text-zinc-600 hover:text-zinc-900"
              }`}
            >
              File Level
            </button>
            <button
              onClick={() => setLevel("directory")}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors cursor-pointer ${
                level === "directory"
                  ? "bg-white text-zinc-900 shadow-xs"
                  : "text-zinc-600 hover:text-zinc-900"
              }`}
            >
              Directory Level
            </button>
          </div>

          {/* Search within graph */}
          <div className="relative">
            <Search className="size-3.5 text-zinc-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Filter graph nodes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 pr-3 py-1 text-xs bg-white border border-zinc-200 rounded-lg text-zinc-900 placeholder-zinc-400 focus:outline-none focus:border-emerald-500 w-48 font-mono shadow-xs"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                aria-label="Clear filter query"
                className="absolute right-2.5 top-2 text-zinc-400 hover:text-zinc-700 cursor-pointer"
              >
                <X className="size-3" />
              </button>
            )}
          </div>
        </div>

        {/* Center: Graph Stats */}
        <div className="flex items-center gap-4 text-xs font-mono text-zinc-600 tabular-nums">
          <div className="flex items-center gap-1.5">
            <span className="size-2 rounded-full bg-emerald-600" />
            <span>
              {graphData?.total_nodes ?? graphData?.node_count ?? graphData?.nodes?.length ?? 0}{" "}
              Nodes
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="size-2 rounded-full bg-teal-600" />
            <span>
              {graphData?.total_edges ?? graphData?.edge_count ?? graphData?.edges?.length ?? 0}{" "}
              Edges
            </span>
          </div>
          {graphData?.cycles && graphData.cycles.length > 0 && (
            <div className="flex items-center gap-1.5 text-rose-600 font-semibold">
              <AlertTriangle className="size-3.5" />
              <span>{graphData.cycles.length} Cycles</span>
            </div>
          )}
        </div>

        {/* Right: Toggles & Depth */}
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5 text-xs text-zinc-600 cursor-pointer">
            <input
              type="checkbox"
              checked={includeCalls}
              onChange={(e) => setIncludeCalls(e.target.checked)}
              className="rounded bg-white border-zinc-300 text-emerald-600 focus:ring-0"
            />
            <span>Heuristic Calls</span>
          </label>

          <label className="flex items-center gap-1.5 text-xs text-zinc-600 cursor-pointer">
            <input
              type="checkbox"
              checked={includeExternal}
              onChange={(e) => setIncludeExternal(e.target.checked)}
              className="rounded bg-white border-zinc-300 text-emerald-600 focus:ring-0"
            />
            <span>External pkgs</span>
          </label>

          {/* Depth selector */}
          <div className="flex items-center gap-1.5 text-xs text-zinc-600">
            <Sliders className="size-3" />
            <span>Depth:</span>
            <select
              value={depth}
              onChange={(e) => setDepth(Number(e.target.value))}
              className="bg-white border border-zinc-200 rounded px-2 py-0.5 text-xs text-zinc-800 focus:outline-none shadow-xs cursor-pointer"
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
              className="flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100 transition-colors cursor-pointer"
            >
              <span>Focus: {focus.split("/").pop()}</span>
              <X className="size-3" />
            </button>
          )}

          <button
            onClick={() => refetch()}
            className="p-1.5 rounded-lg border border-zinc-200 bg-white text-zinc-600 hover:text-zinc-900 transition-colors cursor-pointer shadow-xs"
            title="Refresh graph"
            aria-label="Refresh graph layout"
          >
            <RefreshCw className={`size-3.5 ${isLoading || isLayouting ? "animate-spin text-emerald-600" : ""}`} />
          </button>
        </div>
      </div>

      {/* Main Canvas Area */}
      <div className="flex-1 relative w-full h-full">
        {isLoading || isLayouting ? (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-white/80 backdrop-blur-xs">
            <RefreshCw className="size-8 text-emerald-600 animate-spin mb-3" />
            <p className="text-sm font-medium text-zinc-900 text-balance">Computing Graph Layout (ELK)...</p>
            <p className="text-xs text-zinc-500 mt-1 text-pretty">Hierarchical dependency routing &amp; cycles</p>
          </div>
        ) : null}

        {!isLoading && !isLayouting && nodes.length === 0 && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-zinc-50 text-center p-6">
            <div className="size-10 rounded-xl bg-white border border-zinc-200 flex items-center justify-center text-zinc-400 mb-3 shadow-xs">
              <FileCode className="size-5 text-emerald-600" />
            </div>
            <h3 className="text-sm font-semibold text-zinc-900 text-balance">No Dependency Connections Found</h3>
            <p className="text-xs text-zinc-500 max-w-sm mt-1 text-pretty">
              {searchQuery
                ? `No nodes match filter "${searchQuery}".`
                : "This repository contains standalone files without internal imports. Check \"External pkgs\" above to visualize external library dependencies."}
            </p>
          </div>
        )}

        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          fitView
          attributionPosition="bottom-left"
          className="bg-zinc-50"
        >
          <Background color="#cbd5e1" gap={20} size={1} variant={BackgroundVariant.Dots} />
          <Controls className="!bg-white !border-zinc-200 !fill-zinc-700 shadow-xs" />
          <MiniMap
            nodeColor={(node) => {
              const data = node.data as unknown as GraphNodeData;
              if (data?.in_cycle) return "#e11d48";
              if (data?.is_external) return "#94a3b8";
              return "#059669";
            }}
            className="!bg-white !border-zinc-200 !rounded-xl overflow-hidden shadow-xs"
          />
        </ReactFlow>

        {/* Side Inspector Drawer */}
        {selectedNode && (
          <div className="absolute right-4 top-4 bottom-4 w-96 bg-white/95 border border-zinc-200 rounded-2xl shadow-xl backdrop-blur-md z-30 flex flex-col overflow-hidden animate-in slide-in-from-right-4 duration-200">
            {/* Drawer Header */}
            <div className="p-4 border-b border-zinc-200 flex items-start justify-between bg-zinc-50">
              <div className="min-w-0 pr-2">
                <div className="flex items-center gap-1.5 mb-1">
                  <span
                    className={`size-2 rounded-full ${
                      getDirColor(selectedNode.top_dir, selectedNode.is_external).dot
                    }`}
                  />
                  <span className="text-[10px] uppercase font-mono font-semibold text-zinc-500">
                    {selectedNode.is_external ? "External" : selectedNode.top_dir || "root"}
                  </span>
                </div>
                <h3 className="font-mono text-sm font-bold text-zinc-900 truncate" title={selectedNode.id}>
                  {selectedNode.id}
                </h3>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                aria-label="Close module details"
                className="p-1 rounded-lg text-zinc-400 hover:text-zinc-700 hover:bg-zinc-200 transition-colors cursor-pointer"
              >
                <X className="size-4" />
              </button>
            </div>

            {/* Metrics Grid */}
            <div className="p-4 border-b border-zinc-200 grid grid-cols-3 gap-2 bg-zinc-50/50 text-center">
              <div className="p-2 rounded-lg bg-white border border-zinc-200 shadow-xs">
                <span className="text-[10px] text-zinc-500 block">PageRank</span>
                <span className="font-mono text-xs font-bold text-emerald-600 tabular-nums">
                  {(selectedNode.pagerank * 100).toFixed(2)}%
                </span>
              </div>
              <div className="p-2 rounded-lg bg-white border border-zinc-200 shadow-xs">
                <span className="text-[10px] text-zinc-500 block">Fan-In</span>
                <span className="font-mono text-xs font-bold text-teal-600 tabular-nums">
                  {selectedNode.fan_in}
                </span>
              </div>
              <div className="p-2 rounded-lg bg-white border border-zinc-200 shadow-xs">
                <span className="text-[10px] text-zinc-500 block">Fan-Out</span>
                <span className="font-mono text-xs font-bold text-amber-600 tabular-nums">
                  {selectedNode.fan_out}
                </span>
              </div>
            </div>

            {/* Cycle Warning */}
            {selectedNode.in_cycle && (
              <div className="m-4 p-3 rounded-lg bg-rose-50 border border-rose-200 flex items-start gap-2.5 text-xs text-rose-700">
                <AlertTriangle className="size-4 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold block">Circular Dependency Warning</span>
                  <span className="text-[11px] text-rose-600 text-pretty">
                    This module participates in one or more import cycles. Refactor dependencies to decouple.
                  </span>
                </div>
              </div>
            )}

            {/* Incoming & Outgoing Dependencies Lists */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* Incoming: Imported By */}
              <div>
                <span className="text-xs font-semibold text-zinc-900 block mb-2 flex items-center gap-1.5">
                  <ArrowRight className="size-3.5 text-teal-600 rotate-180" />
                  <span className="tabular-nums">Imported By ({incomingDependencies.length})</span>
                </span>
                {incomingDependencies.length === 0 ? (
                  <p className="text-[11px] text-zinc-400 italic">No incoming imports (entry point or leaf)</p>
                ) : (
                  <div className="space-y-1">
                    {incomingDependencies.map((dep, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          const n = graphData?.nodes.find((item) => item.id === dep.source);
                          if (n) setSelectedNode(n);
                        }}
                        className="w-full text-left p-1.5 rounded bg-white border border-zinc-200 hover:border-emerald-400 text-xs font-mono text-zinc-800 truncate flex items-center justify-between cursor-pointer shadow-xs"
                      >
                        <span className="truncate">{dep.source}</span>
                        {dep.heuristic && (
                          <span className="text-[9px] text-teal-600 uppercase font-bold shrink-0 ml-1">
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
                <span className="text-xs font-semibold text-zinc-900 block mb-2 flex items-center gap-1.5">
                  <ArrowRight className="size-3.5 text-amber-600" />
                  <span className="tabular-nums">Imports ({outgoingDependencies.length})</span>
                </span>
                {outgoingDependencies.length === 0 ? (
                  <p className="text-[11px] text-zinc-400 italic">No outgoing imports (leaf dependency)</p>
                ) : (
                  <div className="space-y-1">
                    {outgoingDependencies.map((dep, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          const n = graphData?.nodes.find((item) => item.id === dep.target);
                          if (n) setSelectedNode(n);
                        }}
                        className="w-full text-left p-1.5 rounded bg-white border border-zinc-200 hover:border-emerald-400 text-xs font-mono text-zinc-800 truncate flex items-center justify-between cursor-pointer shadow-xs"
                      >
                        <span className="truncate">{dep.target}</span>
                        {dep.heuristic && (
                          <span className="text-[9px] text-teal-600 uppercase font-bold shrink-0 ml-1">
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
            <div className="p-4 border-t border-zinc-200 bg-zinc-50 flex flex-col gap-2">
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => {
                    setFocus(selectedNode.id);
                  }}
                  className="flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-white border border-zinc-200 text-zinc-800 hover:bg-zinc-100 transition-colors cursor-pointer shadow-xs"
                >
                  <Eye className="size-3.5 text-emerald-600" />
                  <span>Focus in Graph</span>
                </button>

                {!selectedNode.is_external && (
                  <Link
                    to={`/app/repos/${repoId}/explorer?file=${encodeURIComponent(selectedNode.id)}`}
                    className="flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-white border border-zinc-200 text-zinc-800 hover:bg-zinc-100 transition-colors shadow-xs"
                  >
                    <FileCode className="size-3.5 text-teal-600" />
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
                className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 transition-colors shadow-xs cursor-pointer"
              >
                <MessageSquare className="size-3.5" />
                <span>Ask RepoGPT About This Module</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
