import React, { useState, useEffect, useRef } from "react";
import { useParams, useNavigate, Link } from "react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../../api/client";
import { streamSSE } from "../../api/sse";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";
import { toast } from "sonner";
import {
  MessageSquare,
  Plus,
  Send,
  Square,
  RotateCw,
  Copy,
  ThumbsUp,
  ThumbsDown,
  Download,
  Trash2,
  Edit2,
  ChevronRight,
  Sparkles,
  Layers,
  ExternalLink,
  ShieldAlert,
  SlidersHorizontal,
  Search,
  Activity,
  AlertTriangle,
  Clock,
  Compass,
} from "lucide-react";

type StrategyOption = "auto" | "keyword" | "vector" | "hybrid" | "hybrid_rerank";

interface CitationUI {
  source_id: string;
  path: string;
  start_line: number;
  end_line: number;
  symbol?: string | null;
}

interface SourceUI {
  id: string;
  path: string;
  start_line: number;
  end_line: number;
  symbol?: string | null;
  language?: string;
  chunk_type?: string;
  snippet: string;
  scores?: {
    rrf?: number;
    rerank?: number | null;
  };
}

interface ConfidenceUI {
  score: number;
  label: "High" | "Medium" | "Low" | "N/A";
  factors: {
    r: number;
    c: number;
    k: number;
    g?: number | null;
  };
  insufficient?: boolean;
}

interface RouteUI {
  intent: string;
  strategy: string;
  weights: { bm25: number; vector: number };
  enrich: { symbol_lookup: boolean; graph_expand: boolean; summary_scope: boolean };
  identifiers: string[];
  search_queries: string[];
  reason: string;
}

interface MessageUI {
  id: string;
  conversation_id: string;
  user_id: string;
  role: "user" | "assistant";
  content: string;
  status: "complete" | "stopped" | "error";
  route?: RouteUI | null;
  sources?: SourceUI[];
  citations?: CitationUI[];
  confidence?: ConfidenceUI | null;
  usage?: { prompt_tokens?: number; completion_tokens?: number; cost_usd?: number | null } | null;
  latency_ms?: Record<string, number>;
  trace?: Record<string, unknown>;
  cached?: boolean;
  feedback?: { rating: "up" | "down"; comment?: string | null; at: string } | null;
  created_at: string;
}

interface ConversationUI {
  id: string;
  repo_id: string;
  user_id: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

const SAMPLE_QUESTIONS = [
  "Where is authentication and JWT creation implemented?",
  "How does a request flow from the API to the database?",
  "What are the main models and database repositories?",
  "How is configuration and Docker deployment structured?",
];

export const chatMarkdownComponents = {
  code({ className, children, ...props }: any) {
    return (
      <code
        className="rounded bg-[#18181b] px-1 py-0.5 font-mono text-[11px] text-[#e4e4e7]"
        {...props}
      >
        {children}
      </code>
    );
  },
  a({ href, children, ...props }: any) {
    const isSafe =
      href &&
      (href.startsWith("https://") ||
        href.startsWith("http://") ||
        href.startsWith("/") ||
        href.startsWith("#"));
    if (!isSafe) {
      return <span>{children}</span>;
    }
    const isExternal = href.startsWith("http://") || href.startsWith("https://");
    return (
      <a
        href={href}
        target={isExternal ? "_blank" : undefined}
        rel={isExternal ? "noopener noreferrer nofollow" : undefined}
        className="text-[#6366f1] underline hover:text-[#818cf8]"
        {...props}
      >
        {children}
      </a>
    );
  },
};

export const ChatPage: React.FC = () => {
  const { repoId, conversationId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [inputMessage, setInputMessage] = useState("");
  const [selectedStrategy, setSelectedStrategy] = useState<StrategyOption>("auto");
  const [searchFilter, setSearchFilter] = useState("");
  const [isEvidenceOpen, setIsEvidenceOpen] = useState(true);
  const [evidenceTab, setEvidenceTab] = useState<"sources" | "trace" | "confidence">("sources");

  // Streaming State
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingStatus, setStreamingStatus] = useState<string | null>(null);
  const [streamingContent, setStreamingContent] = useState("");
  const [streamingSources, setStreamingSources] = useState<SourceUI[]>([]);
  const [streamingRoute, setStreamingRoute] = useState<RouteUI | null>(null);
  const [streamingCitations, setStreamingCitations] = useState<CitationUI[]>([]);
  const [streamingConfidence, setStreamingConfidence] = useState<ConfidenceUI | null>(null);
  const [streamingTimings, setStreamingTimings] = useState<Record<string, number>>({});
  const abortControllerRef = useRef<AbortController | null>(null);

  // Active message selected for inspection in Evidence panel
  const [activeMessageId, setActiveMessageId] = useState<string | null>(null);

  // Rename modal state
  const [editingConvId, setEditingConvId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");

  // Feedback modal state
  const [feedbackMsgId, setFeedbackMsgId] = useState<string | null>(null);
  const [feedbackRating, setFeedbackRating] = useState<"up" | "down">("up");
  const [feedbackComment, setFeedbackComment] = useState("");

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  // 1. Fetch conversations for this repository
  const { data: convsData, isLoading: isLoadingConvs } = useQuery({
    queryKey: ["conversations", repoId],
    queryFn: async () => {
      if (!repoId) return { items: [] };
      const res = await apiClient.GET("/api/v1/repos/{repo_id}/conversations", {
        params: { path: { repo_id: repoId } },
      });
      if (res.error) throw new Error("Failed to load conversations");
      return res.data as { items: ConversationUI[] };
    },
    enabled: !!repoId,
  });

  const conversations = convsData?.items || [];

  // If no conversationId is set, redirect to the most recent conversation if one exists
  useEffect(() => {
    if (!conversationId && conversations.length > 0 && repoId) {
      navigate(`/app/repos/${repoId}/chat/${conversations[0].id}`, { replace: true });
    }
  }, [conversationId, conversations, navigate, repoId]);

  // 2. Fetch active conversation detail and messages
  const { data: activeConvDetail, isLoading: isLoadingMessages } = useQuery({
    queryKey: ["conversation", conversationId],
    queryFn: async () => {
      if (!conversationId) return null;
      const res = await apiClient.GET("/api/v1/conversations/{conversation_id}", {
        params: { path: { conversation_id: conversationId } },
      });
      if (res.error) throw new Error("Failed to load conversation");
      return res.data as { conversation: ConversationUI; messages: MessageUI[] };
    },
    enabled: !!conversationId,
  });

  const messages = activeConvDetail?.messages || [];

  // Auto-scroll to bottom when messages update or streaming
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent, streamingStatus]);

  // 3. Create conversation mutation
  const createConvMutation = useMutation({
    mutationFn: async (title?: string) => {
      if (!repoId) throw new Error("Repository ID is required");
      const res = await apiClient.POST("/api/v1/repos/{repo_id}/conversations", {
        params: { path: { repo_id: repoId } },
        body: { title: title || "New Conversation" },
      });
      if (res.error) throw new Error("Failed to create conversation");
      return res.data as ConversationUI;
    },
    onSuccess: (newConv) => {
      queryClient.invalidateQueries({ queryKey: ["conversations", repoId] });
      navigate(`/app/repos/${repoId}/chat/${newConv.id}`);
      toast.success("New conversation started");
    },
    onError: (err) => {
      toast.error(`Failed to create conversation: ${err.message}`);
    },
  });

  // 4. Rename conversation mutation
  const renameConvMutation = useMutation({
    mutationFn: async ({ id, title }: { id: string; title: string }) => {
      const res = await apiClient.PATCH("/api/v1/conversations/{conversation_id}", {
        params: { path: { conversation_id: id } },
        body: { title },
      });
      if (res.error) throw new Error("Failed to rename conversation");
      return res.data as ConversationUI;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conversations", repoId] });
      queryClient.invalidateQueries({ queryKey: ["conversation", conversationId] });
      setEditingConvId(null);
      toast.success("Conversation renamed");
    },
    onError: (err) => {
      toast.error(`Rename failed: ${err.message}`);
    },
  });

  // 5. Delete conversation mutation
  const deleteConvMutation = useMutation({
    mutationFn: async (id: string) => {
      const res = await apiClient.DELETE("/api/v1/conversations/{conversation_id}", {
        params: { path: { conversation_id: id } },
      });
      if (res.error) throw new Error("Failed to delete conversation");
      return id;
    },
    onSuccess: (deletedId) => {
      queryClient.invalidateQueries({ queryKey: ["conversations", repoId] });
      toast.success("Conversation deleted");
      if (conversationId === deletedId) {
        navigate(`/app/repos/${repoId}/chat`);
      }
    },
    onError: (err) => {
      toast.error(`Delete failed: ${err.message}`);
    },
  });

  // 6. Submit feedback mutation
  const feedbackMutation = useMutation({
    mutationFn: async ({
      msgId,
      rating,
      comment,
    }: {
      msgId: string;
      rating: "up" | "down";
      comment?: string;
    }) => {
      const res = await apiClient.POST("/api/v1/messages/{message_id}/feedback", {
        params: { path: { message_id: msgId } },
        body: {
          rating,
          comment: comment || null,
        },
      });
      if (res.error) throw new Error("Failed to submit feedback");
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conversation", conversationId] });
      setFeedbackMsgId(null);
      setFeedbackComment("");
      toast.success("Feedback submitted. Thank you!");
    },
    onError: (err) => {
      toast.error(`Feedback failed: ${err.message}`);
    },
  });

  // 7. Export conversation handler
  const handleExport = async (cId: string) => {
    try {
      const res = await apiClient.GET("/api/v1/conversations/{conversation_id}/export", {
        params: { path: { conversation_id: cId } },
      });
      if (res.error) throw new Error("Failed to export conversation");
      const exportData = res.data as { markdown: string; filename: string };
      const blob = new Blob([exportData.markdown], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = exportData.filename;
      link.click();
      URL.revokeObjectURL(url);
      toast.success("Conversation exported as Markdown");
    } catch (e: any) {
      toast.error(`Export failed: ${e.message}`);
    }
  };

  // 8. Stream Message Sender
  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend ?? inputMessage).trim();
    if (!text || isStreaming) return;

    let targetConvId = conversationId;
    if (!targetConvId) {
      try {
        const newConv = await createConvMutation.mutateAsync("New Conversation");
        targetConvId = newConv.id;
      } catch {
        return;
      }
    }

    setInputMessage("");
    setIsStreaming(true);
    setStreamingContent("");
    setStreamingStatus("Contextualizing question...");
    setStreamingSources([]);
    setStreamingRoute(null);
    setStreamingCitations([]);
    setStreamingConfidence(null);
    setStreamingTimings({});

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      await streamSSE({
        url: `/api/v1/conversations/${targetConvId}/messages`,
        method: "POST",
        body: {
          content: text,
          strategy: selectedStrategy,
        },
        signal: controller.signal,
        onEvent: (event) => {
          if (event.event === "meta") {
            // Meta event with message IDs
          } else if (event.event === "status") {
            const data = typeof event.data === "string" ? JSON.parse(event.data) : event.data;
            setStreamingStatus(data.detail || data.stage);
          } else if (event.event === "route") {
            const data = typeof event.data === "string" ? JSON.parse(event.data) : event.data;
            setStreamingRoute(data);
          } else if (event.event === "sources") {
            const data = typeof event.data === "string" ? JSON.parse(event.data) : event.data;
            setStreamingSources(data || []);
          } else if (event.event === "token") {
            const data = typeof event.data === "string" ? JSON.parse(event.data) : event.data;
            setStreamingContent((prev) => prev + (data.text || ""));
          } else if (event.event === "citations") {
            const data = typeof event.data === "string" ? JSON.parse(event.data) : event.data;
            setStreamingCitations(data.valid || []);
          } else if (event.event === "confidence") {
            const data = typeof event.data === "string" ? JSON.parse(event.data) : event.data;
            setStreamingConfidence(data);
          } else if (event.event === "done") {
            const data = typeof event.data === "string" ? JSON.parse(event.data) : event.data;
            setStreamingTimings(data.latency_ms || {});
            setIsStreaming(false);
            setStreamingStatus(null);
            queryClient.invalidateQueries({ queryKey: ["conversation", targetConvId] });
            queryClient.invalidateQueries({ queryKey: ["conversations", repoId] });
          } else if (event.event === "error") {
            const data = typeof event.data === "string" ? JSON.parse(event.data) : event.data;
            toast.error(data.message || "An error occurred during generation");
            setIsStreaming(false);
            setStreamingStatus(null);
          }
        },
        onError: (err) => {
          if (err.name !== "AbortError") {
            toast.error(`Stream error: ${err.message}`);
          }
          setIsStreaming(false);
          setStreamingStatus(null);
        },
        onDone: () => {
          setIsStreaming(false);
          setStreamingStatus(null);
          queryClient.invalidateQueries({ queryKey: ["conversation", targetConvId] });
        },
      });
    } catch (e: any) {
      if (e.name !== "AbortError") {
        toast.error(`Message error: ${e.message}`);
      }
      setIsStreaming(false);
      setStreamingStatus(null);
    }
  };

  const handleStopStreaming = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsStreaming(false);
      setStreamingStatus(null);
      toast.info("Generation stopped");
      queryClient.invalidateQueries({ queryKey: ["conversation", conversationId] });
    }
  };

  // Inspect message in Evidence panel
  const activeMessage =
    (messages as MessageUI[]).find((m: MessageUI) => m.id === activeMessageId) ||
    (messages as MessageUI[])[messages.length - 1];
  const displayedSources = isStreaming ? streamingSources : activeMessage?.sources || [];
  const displayedRoute = isStreaming ? streamingRoute : activeMessage?.route || null;
  const displayedConfidence = isStreaming
    ? streamingConfidence
    : activeMessage?.confidence || null;
  const displayedTimings = isStreaming ? streamingTimings : activeMessage?.latency_ms || {};

  const filteredConversations = (conversations as ConversationUI[]).filter((c: ConversationUI) =>
    c.title.toLowerCase().includes(searchFilter.toLowerCase())
  );

  return (
    <div className="flex h-[calc(100vh-4rem)] w-full overflow-hidden bg-[#09090b] text-[#fafafa]">
      {/* ======================================================== */}
      {/* 1. LEFT PANE: CONVERSATION LIST (Sidebar)              */}
      {/* ======================================================== */}
      <aside className="flex w-72 flex-col border-r border-[#27272a] bg-[#111113]">
        {/* Header & New Chat button */}
        <div className="flex flex-col gap-3 p-3 border-b border-[#27272a]">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-[#a1a1aa]">
              Conversations
            </h2>
            <button
              onClick={() => createConvMutation.mutate("New Conversation")}
              disabled={createConvMutation.isPending}
              className="flex items-center gap-1.5 rounded-md bg-[#6366f1] px-2.5 py-1 text-xs font-medium text-white transition-colors hover:bg-[#818cf8]"
            >
              <Plus className="h-3.5 w-3.5" />
              New Chat
            </button>
          </div>

          {/* Search bar */}
          <div className="relative">
            <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-[#71717a]" />
            <input
              type="text"
              placeholder="Search conversations..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              className="w-full rounded-md border border-[#27272a] bg-[#18181b] py-1.5 pl-8 pr-3 text-xs text-[#fafafa] placeholder-[#71717a] focus:border-[#6366f1] focus:outline-none"
            />
          </div>
        </div>

        {/* Scrollable List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {isLoadingConvs ? (
            <div className="p-4 text-center text-xs text-[#71717a]">Loading chats...</div>
          ) : filteredConversations.length === 0 ? (
            <div className="p-6 text-center text-xs text-[#71717a]">
              No conversations found. Click "New Chat" to begin!
            </div>
          ) : (
            filteredConversations.map((c: ConversationUI) => {
              const isActive = c.id === conversationId;
              return (
                <div
                  key={c.id}
                  onClick={() => navigate(`/app/repos/${repoId}/chat/${c.id}`)}
                  className={`group relative flex cursor-pointer items-center justify-between rounded-lg px-3 py-2 text-xs transition-all ${
                    isActive
                      ? "bg-[#27272a] font-medium text-[#fafafa] shadow-sm"
                      : "text-[#a1a1aa] hover:bg-[#18181b] hover:text-[#fafafa]"
                  }`}
                >
                  <div className="flex items-center gap-2 overflow-hidden pr-6">
                    <MessageSquare
                      className={`h-3.5 w-3.5 shrink-0 ${
                        isActive ? "text-[#6366f1]" : "text-[#71717a]"
                      }`}
                    />
                    {editingConvId === c.id ? (
                      <input
                        type="text"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            renameConvMutation.mutate({ id: c.id, title: editTitle });
                          } else if (e.key === "Escape") {
                            setEditingConvId(null);
                          }
                        }}
                        autoFocus
                        onClick={(e) => e.stopPropagation()}
                        className="w-full rounded bg-[#09090b] px-1.5 py-0.5 text-xs text-white border border-[#6366f1] outline-none"
                      />
                    ) : (
                      <span className="truncate">{c.title}</span>
                    )}
                  </div>

                  {/* Actions on hover */}
                  <div className="absolute right-2 flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingConvId(c.id);
                        setEditTitle(c.title);
                      }}
                      title="Rename"
                      className="rounded p-1 text-[#71717a] hover:bg-[#27272a] hover:text-white"
                    >
                      <Edit2 className="h-3 w-3" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleExport(c.id);
                      }}
                      title="Export Markdown"
                      className="rounded p-1 text-[#71717a] hover:bg-[#27272a] hover:text-white"
                    >
                      <Download className="h-3 w-3" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirm("Delete this conversation?")) {
                          deleteConvMutation.mutate(c.id);
                        }
                      }}
                      title="Delete"
                      className="rounded p-1 text-[#71717a] hover:bg-[#27272a] hover:text-[#ef4444]"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </aside>

      {/* ======================================================== */}
      {/* 2. MIDDLE PANE: MESSAGE THREAD & COMPOSER               */}
      {/* ======================================================== */}
      <main className="flex flex-1 flex-col overflow-hidden bg-[#09090b]">
        {/* Top Header Bar */}
        <header className="flex h-12 items-center justify-between border-b border-[#27272a] px-4">
          <div className="flex items-center gap-2 overflow-hidden">
            <span className="text-xs font-semibold text-[#fafafa] truncate">
              {activeConvDetail?.conversation?.title || "RepoGPT Assistant"}
            </span>
            <span className="rounded bg-[#27272a] px-1.5 py-0.5 text-[10px] text-[#a1a1aa]">
              {messages.length} messages
            </span>
          </div>

          <div className="flex items-center gap-2">
            {/* Strategy selector dropdown */}
            <div className="flex items-center gap-1.5">
              <SlidersHorizontal className="h-3.5 w-3.5 text-[#a1a1aa]" />
              <select
                value={selectedStrategy}
                onChange={(e) => setSelectedStrategy(e.target.value as StrategyOption)}
                className="rounded-md border border-[#27272a] bg-[#18181b] px-2 py-1 text-xs text-[#fafafa] outline-none focus:border-[#6366f1]"
              >
                <option value="auto">Auto (Router)</option>
                <option value="hybrid_rerank">Hybrid + Rerank</option>
                <option value="hybrid">Hybrid (RRF)</option>
                <option value="vector">Vector Only</option>
                <option value="keyword">Keyword (BM25)</option>
              </select>
            </div>

            {/* Toggle Evidence panel button */}
            <button
              onClick={() => setIsEvidenceOpen(!isEvidenceOpen)}
              title={isEvidenceOpen ? "Hide Evidence Panel" : "Show Evidence Panel"}
              className={`flex items-center gap-1 rounded-md border border-[#27272a] px-2.5 py-1 text-xs transition-colors ${
                isEvidenceOpen
                  ? "bg-[#27272a] text-[#fafafa]"
                  : "bg-[#18181b] text-[#a1a1aa] hover:bg-[#27272a] hover:text-[#fafafa]"
              }`}
            >
              <Layers className="h-3.5 w-3.5" />
              <span>Evidence</span>
            </button>
          </div>
        </header>

        {/* Message Thread Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {isLoadingMessages ? (
            <div className="flex h-full items-center justify-center text-xs text-[#71717a]">
              Loading messages...
            </div>
          ) : messages.length === 0 && !isStreaming ? (
            /* Empty State with Suggested Questions */
            <div className="flex h-full flex-col items-center justify-center text-center p-6 max-w-xl mx-auto">
              <div className="mb-4 rounded-full bg-[#18181b] p-3 text-[#6366f1] ring-1 ring-[#27272a]">
                <Sparkles className="h-6 w-6" />
              </div>
              <h3 className="text-base font-semibold text-[#fafafa]">
                Ask RepoGPT about this Codebase
              </h3>
              <p className="mt-1.5 text-xs text-[#a1a1aa] leading-relaxed">
                RepoGPT uses an agentic RAG workflow with AST-aware code chunking, hybrid retrieval,
                and verifiable inline citations.
              </p>

              <div className="mt-6 w-full space-y-2">
                <span className="text-[11px] font-medium text-[#71717a] uppercase tracking-wider">
                  Suggested Questions
                </span>
                <div className="grid grid-cols-1 gap-2 pt-1">
                  {SAMPLE_QUESTIONS.map((q, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSendMessage(q)}
                      className="flex items-center justify-between rounded-lg border border-[#27272a] bg-[#111113] p-2.5 text-left text-xs text-[#fafafa] transition-all hover:border-[#6366f1] hover:bg-[#18181b]"
                    >
                      <span>{q}</span>
                      <ChevronRight className="h-3.5 w-3.5 text-[#71717a]" />
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            /* Render Existing Messages */
            (messages as MessageUI[]).map((m: MessageUI) => {
              const isAssistant = m.role === "assistant";
              return (
                <div
                  key={m.id}
                  onClick={() => isAssistant && setActiveMessageId(m.id)}
                  className={`flex flex-col gap-2 ${
                    isAssistant ? "items-start" : "items-end"
                  }`}
                >
                  {/* Sender Header */}
                  <div className="flex items-center gap-2 text-[11px] text-[#71717a]">
                    <span>{isAssistant ? "RepoGPT" : "You"}</span>
                    <span>•</span>
                    <span>{new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                    {isAssistant && m.cached && (
                      <span className="rounded bg-[#1e293b] px-1.5 py-0.2 text-[10px] text-[#38bdf8]">
                        Cached
                      </span>
                    )}
                  </div>

                  {/* Message Bubble */}
                  <div
                    className={`max-w-2xl rounded-xl px-4 py-3 text-xs leading-relaxed ${
                      isAssistant
                        ? "border border-[#27272a] bg-[#111113] text-[#fafafa] shadow-sm"
                        : "bg-[#6366f1] text-white"
                    }`}
                  >
                    {/* Metadata Header for Assistant */}
                    {isAssistant && (
                      <div className="mb-2 flex flex-wrap items-center gap-2 border-b border-[#27272a] pb-2 text-[10px]">
                        {/* Route Intent Badge */}
                        {m.route && (
                          <span
                            title={m.route.reason}
                            className="flex items-center gap-1 rounded bg-[#27272a] px-2 py-0.5 font-mono text-[#a1a1aa]"
                          >
                            <Compass className="h-3 w-3 text-[#6366f1]" />
                            {m.route.intent}
                          </span>
                        )}

                        {/* Confidence Badge */}
                        {m.confidence && (
                          <span
                            title={`Relevance: ${(m.confidence.factors.r * 100).toFixed(0)}% | Validity: ${(m.confidence.factors.c * 100).toFixed(0)}%`}
                            className={`flex items-center gap-1 rounded px-2 py-0.5 font-semibold ${
                              m.confidence.label === "High"
                                ? "bg-[#14532d]/40 text-[#22c55e]"
                                : m.confidence.label === "Medium"
                                ? "bg-[#78350f]/40 text-[#f59e0b]"
                                : m.confidence.label === "Low"
                                ? "bg-[#7f1d1d]/40 text-[#ef4444]"
                                : "bg-[#27272a] text-[#a1a1aa]"
                            }`}
                          >
                            <ShieldAlert className="h-3 w-3" />
                            {m.confidence.label} Confidence ({(m.confidence.score * 100).toFixed(0)}%)
                          </span>
                        )}

                        {/* Zero Citations Warning */}
                        {(!m.citations || m.citations.length === 0) &&
                          m.route?.intent !== "general" &&
                          m.route?.intent !== "out_of_scope" && (
                            <span className="flex items-center gap-1 text-[#f59e0b]">
                              <AlertTriangle className="h-3 w-3" />
                              No supporting citations
                            </span>
                          )}
                      </div>
                    )}

                    {/* Markdown Content */}
                    <div className="prose prose-invert prose-xs max-w-none">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        rehypePlugins={[rehypeSanitize]}
                        components={chatMarkdownComponents}
                      >
                        {m.content}
                      </ReactMarkdown>
                    </div>

                    {/* Assistant Action Bar */}
                    {isAssistant && (
                      <div className="mt-3 flex items-center justify-between border-t border-[#27272a] pt-2 text-[#71717a]">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(m.content);
                              toast.success("Answer copied to clipboard");
                            }}
                            title="Copy Answer"
                            className="rounded p-1 hover:bg-[#18181b] hover:text-white"
                          >
                            <Copy className="h-3 w-3" />
                          </button>
                          <button
                            onClick={() => handleSendMessage(messages[messages.indexOf(m) - 1]?.content || "")}
                            title="Regenerate"
                            className="rounded p-1 hover:bg-[#18181b] hover:text-white"
                          >
                            <RotateCw className="h-3 w-3" />
                          </button>
                        </div>

                        {/* Feedback buttons */}
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => {
                              setFeedbackMsgId(m.id);
                              setFeedbackRating("up");
                              feedbackMutation.mutate({ msgId: m.id, rating: "up" });
                            }}
                            className={`rounded p-1 hover:bg-[#18181b] ${
                              m.feedback?.rating === "up" ? "text-[#22c55e]" : "hover:text-white"
                            }`}
                          >
                            <ThumbsUp className="h-3 w-3" />
                          </button>
                          <button
                            onClick={() => {
                              setFeedbackMsgId(m.id);
                              setFeedbackRating("down");
                            }}
                            className={`rounded p-1 hover:bg-[#18181b] ${
                              m.feedback?.rating === "down" ? "text-[#ef4444]" : "hover:text-white"
                            }`}
                          >
                            <ThumbsDown className="h-3 w-3" />
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}

          {/* Active Streaming Message Bubble */}
          {isStreaming && (
            <div className="flex flex-col items-start gap-2">
              <div className="flex items-center gap-2 text-[11px] text-[#71717a]">
                <span>RepoGPT</span>
                <span>•</span>
                <span className="flex items-center gap-1 text-[#6366f1] animate-pulse">
                  <Activity className="h-3 w-3" />
                  {streamingStatus || "Processing..."}
                </span>
              </div>

              <div className="max-w-2xl rounded-xl border border-[#27272a] bg-[#111113] px-4 py-3 text-xs leading-relaxed text-[#fafafa] shadow-sm">
                {streamingRoute && (
                  <div className="mb-2 flex items-center gap-2 border-b border-[#27272a] pb-2 text-[10px]">
                    <span className="flex items-center gap-1 rounded bg-[#27272a] px-2 py-0.5 font-mono text-[#a1a1aa]">
                      <Compass className="h-3 w-3 text-[#6366f1]" />
                      {streamingRoute.intent}
                    </span>
                    <span className="text-[#71717a] truncate">{streamingRoute.reason}</span>
                  </div>
                )}

                <div className="prose prose-invert prose-xs max-w-none">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    rehypePlugins={[rehypeSanitize]}
                    components={chatMarkdownComponents}
                  >
                    {streamingContent || "Synthesizing answer..."}
                  </ReactMarkdown>
                </div>

                {streamingCitations.length > 0 && (
                  <div className="mt-3 flex flex-wrap items-center gap-1.5 border-t border-[#27272a] pt-2">
                    <span className="text-[10px] text-[#71717a]">Citations:</span>
                    {streamingCitations.map((c: CitationUI) => (
                      <span
                        key={c.source_id}
                        className="rounded bg-[#6366f1]/10 px-1.5 py-0.5 font-mono text-[10px] text-[#818cf8]"
                      >
                        [{c.source_id}] {c.path}:{c.start_line}-{c.end_line}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Composer Bar */}
        <div className="border-t border-[#27272a] bg-[#111113] p-3">
          <div className="relative flex flex-col rounded-xl border border-[#27272a] bg-[#18181b] focus-within:border-[#6366f1] transition-all">
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              placeholder="Ask a question about this repository... (Enter to send, Shift+Enter for newline)"
              rows={2}
              className="w-full resize-none bg-transparent p-3 text-xs text-[#fafafa] placeholder-[#71717a] focus:outline-none"
            />

            <div className="flex items-center justify-between border-t border-[#27272a]/60 px-3 py-2 text-[11px] text-[#71717a]">
              <span>Strategy: {selectedStrategy}</span>

              <div className="flex items-center gap-2">
                {isStreaming ? (
                  <button
                    onClick={handleStopStreaming}
                    className="flex items-center gap-1.5 rounded-md bg-[#ef4444] px-3 py-1 text-xs font-medium text-white transition-colors hover:bg-[#dc2626]"
                  >
                    <Square className="h-3 w-3 fill-white" />
                    Stop
                  </button>
                ) : (
                  <button
                    onClick={() => handleSendMessage()}
                    disabled={!inputMessage.trim()}
                    className="flex items-center gap-1.5 rounded-md bg-[#6366f1] px-3 py-1 text-xs font-medium text-white transition-colors hover:bg-[#818cf8] disabled:opacity-40 disabled:hover:bg-[#6366f1]"
                  >
                    <Send className="h-3 w-3" />
                    Send
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* ======================================================== */}
      {/* 3. RIGHT PANE: EVIDENCE PANEL (Sources, Trace, Confidence)*/}
      {/* ======================================================== */}
      {isEvidenceOpen && (
        <aside className="flex w-96 flex-col border-l border-[#27272a] bg-[#111113]">
          {/* Header & Tabs */}
          <div className="flex items-center justify-between border-b border-[#27272a] p-3">
            <div className="flex items-center gap-1 rounded-lg bg-[#18181b] p-0.5 text-xs">
              <button
                onClick={() => setEvidenceTab("sources")}
                className={`rounded-md px-2.5 py-1 font-medium transition-colors ${
                  evidenceTab === "sources"
                    ? "bg-[#27272a] text-[#fafafa]"
                    : "text-[#a1a1aa] hover:text-[#fafafa]"
                }`}
              >
                Sources ({displayedSources.length})
              </button>
              <button
                onClick={() => setEvidenceTab("trace")}
                className={`rounded-md px-2.5 py-1 font-medium transition-colors ${
                  evidenceTab === "trace"
                    ? "bg-[#27272a] text-[#fafafa]"
                    : "text-[#a1a1aa] hover:text-[#fafafa]"
                }`}
              >
                Trace
              </button>
              <button
                onClick={() => setEvidenceTab("confidence")}
                className={`rounded-md px-2.5 py-1 font-medium transition-colors ${
                  evidenceTab === "confidence"
                    ? "bg-[#27272a] text-[#fafafa]"
                    : "text-[#a1a1aa] hover:text-[#fafafa]"
                }`}
              >
                Confidence
              </button>
            </div>

            <button
              onClick={() => setIsEvidenceOpen(false)}
              className="rounded p-1 text-[#71717a] hover:bg-[#27272a] hover:text-white"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-y-auto p-3">
            {/* --- Tab 1: Sources --- */}
            {evidenceTab === "sources" && (
              <div className="space-y-3">
                {displayedSources.length === 0 ? (
                  <div className="p-6 text-center text-xs text-[#71717a]">
                    No sources retrieved yet. Ask a question to view citations and evidence.
                  </div>
                ) : (
                  displayedSources.map((s: SourceUI, idx: number) => (
                    <div
                      key={idx}
                      className="rounded-lg border border-[#27272a] bg-[#18181b] p-2.5 text-xs space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="rounded bg-[#6366f1]/20 px-1.5 py-0.5 font-mono text-[10px] font-bold text-[#818cf8]">
                          {s.id}
                        </span>
                        <Link
                          to={`/app/repos/${repoId}/explorer?path=${encodeURIComponent(
                            s.path
                          )}#L${s.start_line}-L${s.end_line}`}
                          className="flex items-center gap-1 text-[11px] text-[#6366f1] hover:underline"
                        >
                          Explorer <ExternalLink className="h-3 w-3" />
                        </Link>
                      </div>

                      <div className="text-[11px] text-[#fafafa] font-mono break-all">
                        {s.path}:{s.start_line}-{s.end_line}
                      </div>

                      {s.symbol && (
                        <div className="text-[10px] text-[#a1a1aa]">
                          Symbol: <code className="text-[#e4e4e7]">{s.symbol}</code>
                        </div>
                      )}

                      {/* Snippet box */}
                      <pre className="max-h-28 overflow-y-auto rounded bg-[#09090b] p-2 font-mono text-[10px] text-[#a1a1aa] whitespace-pre-wrap">
                        {s.snippet}
                      </pre>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* --- Tab 2: Trace --- */}
            {evidenceTab === "trace" && (
              <div className="space-y-4 text-xs">
                {displayedRoute ? (
                  <div className="rounded-lg border border-[#27272a] bg-[#18181b] p-3 space-y-2">
                    <div className="text-[11px] font-semibold text-[#a1a1aa] uppercase tracking-wider">
                      Query Route Decision
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[#71717a]">Intent:</span>
                      <span className="font-mono text-[#fafafa]">{displayedRoute.intent}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[#71717a]">Strategy:</span>
                      <span className="font-mono text-[#fafafa]">{displayedRoute.strategy}</span>
                    </div>
                    <div className="flex flex-col gap-1 pt-1 border-t border-[#27272a]">
                      <span className="text-[#71717a]">Rationale:</span>
                      <span className="text-[#a1a1aa] text-[11px] leading-relaxed">
                        {displayedRoute.reason}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="p-6 text-center text-xs text-[#71717a]">
                    No trace data available.
                  </div>
                )}

                {/* Timing Breakdown */}
                {Object.keys(displayedTimings).length > 0 && (
                  <div className="rounded-lg border border-[#27272a] bg-[#18181b] p-3 space-y-2">
                    <div className="text-[11px] font-semibold text-[#a1a1aa] uppercase tracking-wider flex items-center gap-1.5">
                      <Clock className="h-3.5 w-3.5" />
                      Latency Breakdown
                    </div>
                    {Object.entries(displayedTimings).map(([stage, ms]) => (
                      <div key={stage} className="flex items-center justify-between text-[11px]">
                        <span className="text-[#71717a] capitalize">{stage}:</span>
                        <span className="font-mono text-[#fafafa]">{String(ms)} ms</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* --- Tab 3: Confidence --- */}
            {evidenceTab === "confidence" && (
              <div className="space-y-4 text-xs">
                {displayedConfidence ? (
                  <div className="rounded-lg border border-[#27272a] bg-[#18181b] p-3 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-semibold uppercase text-[#a1a1aa]">
                        Overall Score
                      </span>
                      <span className="font-mono text-sm font-bold text-[#fafafa]">
                        {(displayedConfidence.score * 100).toFixed(0)}%
                      </span>
                    </div>

                    {/* Factors Breakdown Progress Bars */}
                    <div className="space-y-2 pt-2 border-t border-[#27272a]">
                      <div>
                        <div className="flex justify-between text-[10px] text-[#a1a1aa] mb-1">
                          <span>Retrieval Relevance (R - 35%)</span>
                          <span>{(displayedConfidence.factors.r * 100).toFixed(0)}%</span>
                        </div>
                        <div className="h-1.5 w-full bg-[#27272a] rounded-full overflow-hidden">
                          <div
                            className="h-full bg-[#6366f1]"
                            style={{ width: `${displayedConfidence.factors.r * 100}%` }}
                          />
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between text-[10px] text-[#a1a1aa] mb-1">
                          <span>Citation Validity (C - 20%)</span>
                          <span>{(displayedConfidence.factors.c * 100).toFixed(0)}%</span>
                        </div>
                        <div className="h-1.5 w-full bg-[#27272a] rounded-full overflow-hidden">
                          <div
                            className="h-full bg-[#22c55e]"
                            style={{ width: `${displayedConfidence.factors.c * 100}%` }}
                          />
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between text-[10px] text-[#a1a1aa] mb-1">
                          <span>Citation Coverage (K - 15%)</span>
                          <span>{(displayedConfidence.factors.k * 100).toFixed(0)}%</span>
                        </div>
                        <div className="h-1.5 w-full bg-[#27272a] rounded-full overflow-hidden">
                          <div
                            className="h-full bg-[#f59e0b]"
                            style={{ width: `${displayedConfidence.factors.k * 100}%` }}
                          />
                        </div>
                      </div>

                      {displayedConfidence.factors.g !== null && (
                        <div>
                          <div className="flex justify-between text-[10px] text-[#a1a1aa] mb-1">
                            <span>Grounding Verification (G - 30%)</span>
                            <span>{(displayedConfidence.factors.g! * 100).toFixed(0)}%</span>
                          </div>
                          <div className="h-1.5 w-full bg-[#27272a] rounded-full overflow-hidden">
                            <div
                              className="h-full bg-[#38bdf8]"
                              style={{ width: `${displayedConfidence.factors.g! * 100}%` }}
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="p-6 text-center text-xs text-[#71717a]">
                    No confidence evaluation available.
                  </div>
                )}
              </div>
            )}
          </div>
        </aside>
      )}

      {/* Feedback Dialog Modal */}
      {feedbackMsgId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-sm rounded-xl border border-[#27272a] bg-[#111113] p-4 text-xs space-y-3">
            <h4 className="font-semibold text-white">Provide Feedback</h4>
            <p className="text-[#a1a1aa]">
              Help improve RepoGPT by sharing why this answer was {feedbackRating === "up" ? "helpful" : "unhelpful"}.
            </p>

            <textarea
              value={feedbackComment}
              onChange={(e) => setFeedbackComment(e.target.value)}
              placeholder="Optional comment..."
              rows={3}
              className="w-full rounded-md border border-[#27272a] bg-[#18181b] p-2 text-xs text-white placeholder-[#71717a] focus:border-[#6366f1] focus:outline-none"
            />

            <div className="flex justify-end gap-2">
              <button
                onClick={() => setFeedbackMsgId(null)}
                className="rounded px-3 py-1.5 text-xs text-[#a1a1aa] hover:bg-[#27272a]"
              >
                Cancel
              </button>
              <button
                onClick={() =>
                  feedbackMutation.mutate({
                    msgId: feedbackMsgId,
                    rating: feedbackRating,
                    comment: feedbackComment,
                  })
                }
                className="rounded bg-[#6366f1] px-3 py-1.5 text-xs font-medium text-white hover:bg-[#818cf8]"
              >
                Submit Feedback
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
