import React from "react";
import { Link } from "react-router";
import {
  CheckCircle,
  Code2,
  FileSearch,
  GitPullRequest,
  Layers,
  Network,
  Sparkles,
} from "lucide-react";

export const LandingPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#09090b] text-[#fafafa] flex flex-col font-sans selection:bg-[#6366f1] selection:text-white">
      {/* Top Navigation */}
      <header className="border-b border-[#27272a] bg-[#111113]/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#6366f1] flex items-center justify-center font-bold text-white shadow-lg shadow-[#6366f1]/20">
              <Code2 className="w-5 h-5" />
            </div>
            <span className="font-bold text-xl tracking-tight">RepoGPT</span>
          </div>

          <nav className="flex items-center gap-6">
            <a
              href="#features"
              className="text-sm text-[#a1a1aa] hover:text-white transition-colors"
            >
              Features
            </a>
            <a
              href="#how-it-works"
              className="text-sm text-[#a1a1aa] hover:text-white transition-colors"
            >
              How it Works
            </a>
            <Link
              to="/login"
              className="text-sm font-medium text-[#a1a1aa] hover:text-white transition-colors"
            >
              Sign In
            </Link>
            <Link
              to="/register"
              className="text-sm font-medium bg-[#6366f1] hover:bg-[#818cf8] text-white px-4 py-2 rounded-md transition-all shadow-sm"
            >
              Get Started
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative pt-20 pb-16 px-6 max-w-7xl mx-auto text-center flex-1 flex flex-col items-center justify-center overflow-hidden">
        {/* Subtle Green Ambient Glow */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[640px] h-[320px] bg-gradient-to-b from-emerald-500/15 via-teal-500/5 to-transparent blur-3xl pointer-events-none -z-10" />

        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[#27272a] bg-[#111113] text-xs text-[#a1a1aa] mb-8">
          <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
          <span>Agentic AI System for Codebase Understanding & Review</span>
        </div>

        <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight max-w-4xl leading-tight">
          Understand Any Complex Codebase in Seconds,{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-300 to-emerald-400">
            With Exact Citations
          </span>
        </h1>

        <p className="mt-6 text-lg text-[#a1a1aa] max-w-2xl">
          RepoGPT parses your repository with tree-sitter AST, constructs hybrid vector + BM25 +
          dependency graph indices, and explains architecture, logic, and call chains with verifiable
          inline citations.
        </p>

        <div className="mt-8 flex flex-wrap gap-4 justify-center">
          <Link
            to="/register"
            className="bg-[#6366f1] hover:bg-[#818cf8] text-white font-medium px-6 py-3 rounded-lg transition-all shadow-lg shadow-[#6366f1]/25 flex items-center gap-2"
          >
            Start Exploring Code
            <Sparkles className="w-4 h-4" />
          </Link>
          <Link
            to="/login"
            className="border border-[#27272a] bg-[#111113] hover:bg-[#18181b] text-white font-medium px-6 py-3 rounded-lg transition-all"
          >
            Live Demo
          </Link>
        </div>

        {/* Illustrative Product Preview - TaskFlow Sample */}
        <div className="mt-16 w-full max-w-4xl border border-[#27272a] rounded-xl bg-[#111113] shadow-2xl overflow-hidden text-left">
          <div className="h-10 border-b border-[#27272a] bg-[#0c0c0e] px-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-[#ef4444]/60" />
              <div className="w-3 h-3 rounded-full bg-[#f59e0b]/60" />
              <div className="w-3 h-3 rounded-full bg-[#22c55e]/60" />
              <span className="ml-2 text-xs text-[#a1a1aa] font-mono">
                TaskFlow / backend/app/auth/security.py
              </span>
            </div>
            <div className="text-xs text-[#a1a1aa] bg-[#27272a] px-2 py-0.5 rounded font-mono">
              Hybrid + Rerank
            </div>
          </div>

          <div className="p-6 space-y-4">
            <div className="flex items-start gap-3">
              <div className="w-7 h-7 rounded bg-[#27272a] flex items-center justify-center text-xs text-[#a1a1aa] font-mono shrink-0">
                You
              </div>
              <p className="text-sm text-[#fafafa] pt-1">
                Where is the JWT access token created and how is its expiry handled?
              </p>
            </div>

            <div className="flex items-start gap-3 pt-2">
              <div className="w-7 h-7 rounded bg-[#6366f1] flex items-center justify-center text-xs text-white font-bold shrink-0">
                AI
              </div>
              <div className="text-sm text-[#a1a1aa] space-y-2 leading-relaxed">
                <p>
                  The JWT access token is generated inside{" "}
                  <code className="text-white bg-[#27272a] px-1.5 py-0.5 rounded font-mono text-xs">
                    create_access_token()
                  </code>{" "}
                  located in{" "}
                  <span className="inline-flex items-center gap-1 text-[#6366f1] bg-[#6366f1]/10 px-1.5 py-0.5 rounded text-xs font-mono border border-[#6366f1]/20">
                    [S1] backend/app/auth/security.py:28-42
                  </span>
                  .
                </p>
                <p>
                  It encodes the subject claims (user ID and role), assigns a random{" "}
                  <code className="text-white bg-[#27272a] px-1.5 py-0.5 rounded font-mono text-xs">
                    jti
                  </code>
                  , and computes expiry from{" "}
                  <code className="text-white bg-[#27272a] px-1.5 py-0.5 rounded font-mono text-xs">
                    JWT_ACCESS_TTL_MINUTES
                  </code>{" "}
                  <span className="inline-flex items-center gap-1 text-[#6366f1] bg-[#6366f1]/10 px-1.5 py-0.5 rounded text-xs font-mono border border-[#6366f1]/20">
                    [S2] backend/app/config.py:18
                  </span>
                  .
                </p>
                <div className="pt-2 flex items-center gap-3 text-xs">
                  <span className="text-[#22c55e] font-medium flex items-center gap-1">
                    <CheckCircle className="w-3.5 h-3.5" /> High Confidence (0.94)
                  </span>
                  <span className="text-[#71717a]">·</span>
                  <span className="text-[#a1a1aa]">Latency: 480ms</span>
                  <span className="text-[#71717a]">·</span>
                  <span className="text-[#a1a1aa]">Evidence: 2 verified sources</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 4 Core Features (§13.4) */}
      <section id="features" className="py-20 border-t border-[#27272a] bg-[#111113]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-3xl font-bold tracking-tight">Built for Deep Code Intelligence</h2>
            <p className="mt-3 text-[#a1a1aa]">
              Everything you need to onboard onto multi-language repositories and review incoming PRs.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="p-6 rounded-xl border border-[#27272a] bg-[#09090b] hover:border-[#6366f1]/50 transition-all">
              <div className="w-10 h-10 rounded-lg bg-[#6366f1]/10 text-[#6366f1] flex items-center justify-center mb-4">
                <FileSearch className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-lg text-white mb-2">Ask with Citations</h3>
              <p className="text-sm text-[#a1a1aa] leading-relaxed">
                Agentic LangGraph workflow retrieves code via RRF fusion and verifies each claim with
                exact line-level citations.
              </p>
            </div>

            <div className="p-6 rounded-xl border border-[#27272a] bg-[#09090b] hover:border-[#6366f1]/50 transition-all">
              <div className="w-10 h-10 rounded-lg bg-[#38bdf8]/10 text-[#38bdf8] flex items-center justify-center mb-4">
                <Network className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-lg text-white mb-2">Visualise Architecture</h3>
              <p className="text-sm text-[#a1a1aa] leading-relaxed">
                Interactive dependency graphs with PageRank importance, cycle detection, and directory
                collapsing via ELK and React Flow.
              </p>
            </div>

            <div className="p-6 rounded-xl border border-[#27272a] bg-[#09090b] hover:border-[#6366f1]/50 transition-all">
              <div className="w-10 h-10 rounded-lg bg-[#22c55e]/10 text-[#22c55e] flex items-center justify-center mb-4">
                <Layers className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-lg text-white mb-2">Measure IR Quality</h3>
              <p className="text-sm text-[#a1a1aa] leading-relaxed">
                Built-in evaluation dashboard benchmarking Precision@k, Recall@k, MRR, nDCG, latency,
                and confidence calibration.
              </p>
            </div>

            <div className="p-6 rounded-xl border border-[#27272a] bg-[#09090b] hover:border-[#6366f1]/50 transition-all">
              <div className="w-10 h-10 rounded-lg bg-[#f59e0b]/10 text-[#f59e0b] flex items-center justify-center mb-4">
                <GitPullRequest className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-lg text-white mb-2">Review Pull Requests</h3>
              <p className="text-sm text-[#a1a1aa] leading-relaxed">
                Context-aware code review mapping diff hunks to AST symbols, static analysis, and
                human verification workflows.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works (§13.4) */}
      <section id="how-it-works" className="py-20 border-t border-[#27272a] bg-[#09090b]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-3xl font-bold tracking-tight">How RepoGPT Works</h2>
            <p className="mt-3 text-[#a1a1aa]">From repository URL to full codebase mastery in four steps.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div className="flex flex-col items-center text-center">
              <div className="w-12 h-12 rounded-full border border-[#27272a] bg-[#111113] text-[#6366f1] font-bold flex items-center justify-center mb-4 text-base">
                1
              </div>
              <h4 className="font-semibold text-white mb-2">Safe Ingest & Extract</h4>
              <p className="text-sm text-[#a1a1aa]">
                Ingest via GitHub URL or ZIP. Filter binaries, apply gitignore, and redact secrets before indexing.
              </p>
            </div>

            <div className="flex flex-col items-center text-center">
              <div className="w-12 h-12 rounded-full border border-[#27272a] bg-[#111113] text-[#6366f1] font-bold flex items-center justify-center mb-4 text-base">
                2
              </div>
              <h4 className="font-semibold text-white mb-2">AST & Multi-Index</h4>
              <p className="text-sm text-[#a1a1aa]">
                Parse Tier-1 languages with tree-sitter. Index into vector embeddings, BM25, and NetworkX graphs.
              </p>
            </div>

            <div className="flex flex-col items-center text-center">
              <div className="w-12 h-12 rounded-full border border-[#27272a] bg-[#111113] text-[#6366f1] font-bold flex items-center justify-center mb-4 text-base">
                3
              </div>
              <h4 className="font-semibold text-white mb-2">Agentic Retrieval</h4>
              <p className="text-sm text-[#a1a1aa]">
                Route natural language questions, fuse candidates with RRF, expand along the graph, and rerank.
              </p>
            </div>

            <div className="flex flex-col items-center text-center">
              <div className="w-12 h-12 rounded-full border border-[#27272a] bg-[#111113] text-[#6366f1] font-bold flex items-center justify-center mb-4 text-base">
                4
              </div>
              <h4 className="font-semibold text-white mb-2">Verified Answers</h4>
              <p className="text-sm text-[#a1a1aa]">
                Generate streaming responses citing exact files and line ranges with computed confidence scores.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer with UPES Credits (§13.4 & §19) */}
      <footer className="border-t border-[#27272a] bg-[#0c0c0e] py-12 mt-auto">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="text-center md:text-left">
            <div className="flex items-center justify-center md:justify-start gap-2 mb-2">
              <Code2 className="w-5 h-5 text-[#6366f1]" />
              <span className="font-bold text-white tracking-tight">RepoGPT</span>
            </div>
            <p className="text-xs text-[#a1a1aa]">
              Major Project · B.Tech CSE (Data Science) · School of Computer Science
            </p>
            <p className="text-xs text-[#71717a] mt-1">
              University of Petroleum and Energy Studies (UPES), Dehradun
            </p>
          </div>

          <div className="text-center md:text-right text-xs text-[#a1a1aa] space-y-1">
            <p>
              <strong className="text-white">Team:</strong> Harsh Sinha (SAP 500120229) &amp; Anshuman Patel (SAP 500122770)
            </p>
            <p>
              <strong className="text-white">Project Guide:</strong> Dr. Archana Kumari
            </p>
            <p className="text-[#71717a] pt-1">Released under the MIT License · 2026</p>
          </div>
        </div>
      </footer>
    </div>
  );
};
