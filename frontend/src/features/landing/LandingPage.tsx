import React, { useState, useEffect } from "react";
import { Link } from "react-router";
import {
  CheckCircle,
  FileSearch,
  GitPullRequest,
  Layers,
  Network,
  Sparkles,
  Play,
  X,
} from "lucide-react";
import { motion, AnimatePresence, useScroll, useSpring } from "motion/react";

export const LandingPage: React.FC = () => {
  const [isDemoOpen, setIsDemoOpen] = useState(false);
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, {
    stiffness: 100,
    damping: 30,
    restDelta: 0.001,
  });

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setIsDemoOpen(false);
      }
    };
    if (isDemoOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isDemoOpen]);

  return (
    <div className="min-h-dvh bg-[#fafafa] text-zinc-900 flex flex-col font-sans selection:bg-emerald-500/20 selection:text-emerald-900">
      {/* Top Scroll Progress Bar */}
      <motion.div
        style={{ scaleX }}
        className="fixed top-0 left-0 right-0 h-1 bg-gradient-to-r from-emerald-600 via-teal-500 to-emerald-400 origin-left z-[100]"
      />

      {/* Top Navigation */}
      <header className="border-b border-zinc-200/80 bg-white/85 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3.5">
            <img src="/logo-icon.png" alt="RepoGPT Logo" className="size-11 object-contain drop-shadow-sm" />
            <span className="font-extrabold text-2xl tracking-tight text-zinc-950">RepoGPT</span>
          </div>

          <nav className="flex items-center gap-6">
            <a
              href="#features"
              className="text-sm text-zinc-600 hover:text-zinc-950 transition-colors"
            >
              Features
            </a>
            <a
              href="#how-it-works"
              className="text-sm text-zinc-600 hover:text-zinc-950 transition-colors"
            >
              How it Works
            </a>
            <button
              type="button"
              id="top-nav-demo-btn"
              data-testid="top-nav-demo-btn"
              onClick={() => setIsDemoOpen(true)}
              className="text-sm text-zinc-600 hover:text-zinc-950 transition-colors flex items-center gap-1.5 cursor-pointer font-medium"
            >
              <Play className="size-3.5 text-emerald-600 fill-emerald-600/20" />
              Demo
            </button>
            <Link
              to="/login"
              className="text-sm font-medium text-zinc-600 hover:text-zinc-950 transition-colors"
            >
              Sign In
            </Link>
            <Link
              to="/register"
              className="text-sm font-medium bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-md transition-all shadow-sm shadow-emerald-600/15 cursor-pointer"
            >
              Get Started
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative pt-16 pb-16 px-6 max-w-7xl mx-auto text-center flex-1 flex flex-col items-center justify-center overflow-hidden">
        {/* Subtle Green Ambient Glow */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[640px] h-[320px] bg-gradient-to-b from-emerald-500/10 via-teal-500/5 to-transparent blur-3xl pointer-events-none -z-10" />

        {/* Hero Logo Emblem */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9, y: 24 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
          className="mb-8 flex justify-center"
        >
          <div className="relative group flex flex-col items-center gap-2">
            <div className="absolute -inset-4 bg-gradient-to-r from-emerald-500/15 via-teal-500/10 to-blue-500/15 rounded-3xl blur-2xl opacity-75 group-hover:opacity-100 transition-opacity" />
            <img
              src="/logo-icon.png"
              alt="RepoGPT Official Logo"
              className="relative h-28 md:h-36 object-contain drop-shadow-[0_10px_25px_rgba(0,0,0,0.1)] transition-transform duration-300 group-hover:scale-105"
            />
            <span className="relative font-extrabold text-3xl md:text-5xl tracking-tight text-zinc-950 font-sans">
              Repo<span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-600 via-teal-600 to-emerald-600">GPT</span>
            </span>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-emerald-200 bg-emerald-50 text-xs text-emerald-800 mb-8 font-medium shadow-xs"
        >
          <Sparkles className="size-3.5 text-emerald-600" />
          <span>Agentic AI System for Codebase Understanding & Review</span>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
          className="text-4xl md:text-6xl font-extrabold tracking-tight max-w-4xl leading-tight text-balance text-zinc-950"
        >
          Understand Any Complex Codebase in Seconds,{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-600 via-teal-600 to-emerald-600">
            With Exact Citations
          </span>
        </motion.h1>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.4, ease: [0.16, 1, 0.3, 1] }}
          className="mt-8 flex flex-wrap gap-4 justify-center"
        >
          <Link
            to="/register"
            className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-6 py-3 rounded-lg transition-all shadow-md shadow-emerald-600/20 flex items-center gap-2 cursor-pointer"
          >
            Start Exploring Code
            <Sparkles className="w-4 h-4" />
          </Link>
          <button
            type="button"
            id="hero-view-demo-btn"
            data-testid="hero-view-demo-btn"
            onClick={() => setIsDemoOpen(true)}
            className="border border-zinc-200 bg-white hover:bg-zinc-50 hover:border-emerald-500/50 text-zinc-900 font-medium px-6 py-3 rounded-lg transition-all cursor-pointer flex items-center gap-2.5 group shadow-xs"
          >
            <Play className="w-4 h-4 text-emerald-600 group-hover:scale-110 transition-transform fill-emerald-600/20" />
            <span>View Demo</span>
          </button>
        </motion.div>

        {/* Illustrative Product Preview - TaskFlow Sample */}
        <motion.div
          initial={{ opacity: 0, y: 40, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.8, delay: 0.5, ease: [0.16, 1, 0.3, 1] }}
          whileHover={{ y: -4, transition: { duration: 0.2 } }}
          className="mt-16 w-full max-w-4xl border border-zinc-200 rounded-xl bg-white shadow-xl shadow-zinc-200/50 overflow-hidden text-left"
        >
          <div className="h-10 border-b border-zinc-200 bg-zinc-50 px-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-[#ef4444]" />
              <div className="w-3 h-3 rounded-full bg-[#f59e0b]" />
              <div className="w-3 h-3 rounded-full bg-[#22c55e]" />
              <span className="ml-2 text-xs text-zinc-600 font-mono font-medium">
                TaskFlow / backend/app/auth/security.py
              </span>
            </div>
            <div className="flex items-center gap-2.5">
              <button
                type="button"
                id="preview-watch-demo-btn"
                data-testid="preview-watch-demo-btn"
                onClick={() => setIsDemoOpen(true)}
                className="hidden sm:flex items-center gap-1.5 text-xs text-emerald-700 hover:text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 px-2.5 py-1 rounded font-medium transition-colors cursor-pointer"
              >
                <Play className="size-3 fill-emerald-600/30 text-emerald-600" />
                Watch Demo
              </button>
              <div className="text-xs text-zinc-600 bg-zinc-200/80 px-2 py-0.5 rounded font-mono">
                Hybrid + Rerank
              </div>
            </div>
          </div>

          <div className="p-6 space-y-4">
            <div className="flex items-start gap-3">
              <div className="w-7 h-7 rounded bg-zinc-200 flex items-center justify-center text-xs text-zinc-700 font-mono font-medium shrink-0">
                You
              </div>
              <p className="text-sm text-zinc-900 pt-1 font-medium">
                Where is the JWT access token created and how is its expiry handled?
              </p>
            </div>

            <div className="flex items-start gap-3 pt-2">
              <div className="w-7 h-7 rounded bg-emerald-600 flex items-center justify-center text-xs text-white font-bold shrink-0">
                AI
              </div>
              <div className="text-sm text-zinc-700 space-y-2 leading-relaxed">
                <p>
                  The JWT access token is generated inside{" "}
                  <code className="text-zinc-900 bg-zinc-100 border border-zinc-200 px-1.5 py-0.5 rounded font-mono text-xs">
                    create_access_token()
                  </code>{" "}
                  located in{" "}
                  <span className="inline-flex items-center gap-1 text-emerald-800 bg-emerald-50 px-1.5 py-0.5 rounded text-xs font-mono border border-emerald-200 font-medium">
                    [S1] backend/app/auth/security.py:28-42
                  </span>
                  .
                </p>
                <p>
                  It encodes the subject claims (user ID and role), assigns a random{" "}
                  <code className="text-zinc-900 bg-zinc-100 border border-zinc-200 px-1.5 py-0.5 rounded font-mono text-xs">
                    jti
                  </code>
                  , and computes expiry from{" "}
                  <code className="text-zinc-900 bg-zinc-100 border border-zinc-200 px-1.5 py-0.5 rounded font-mono text-xs">
                    JWT_ACCESS_TTL_MINUTES
                  </code>{" "}
                  <span className="inline-flex items-center gap-1 text-emerald-800 bg-emerald-50 px-1.5 py-0.5 rounded text-xs font-mono border border-emerald-200 font-medium">
                    [S2] backend/app/config.py:18
                  </span>
                  .
                </p>
                <div className="pt-2 flex items-center gap-3 text-xs">
                  <span className="text-emerald-700 font-semibold flex items-center gap-1">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-600" /> High Confidence (0.94)
                  </span>
                  <span className="text-zinc-300">·</span>
                  <span className="text-zinc-600">Latency: 480ms</span>
                  <span className="text-zinc-300">·</span>
                  <span className="text-zinc-600">Evidence: 2 verified sources</span>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </section>

      {/* 4 Core Features (§13.4) */}
      <section id="features" className="py-20 border-t border-zinc-200 bg-white">
        <div className="max-w-7xl mx-auto px-6">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.6 }}
            className="text-center max-w-2xl mx-auto mb-16"
          >
            <h2 className="text-3xl font-bold tracking-tight text-zinc-950 text-balance">
              Built for Deep Code Intelligence
            </h2>
            <p className="mt-3 text-zinc-600 text-pretty">
              Everything you need to onboard onto multi-language repositories and review incoming PRs.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <motion.div
              initial={{ opacity: 0, y: 35 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.5, delay: 0.05 }}
              whileHover={{ y: -6, transition: { duration: 0.2 } }}
              className="p-6 rounded-xl border border-zinc-200 bg-zinc-50/60 hover:bg-white hover:border-emerald-500/50 hover:shadow-lg hover:shadow-emerald-600/5 transition-all"
            >
              <div className="size-10 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center mb-4">
                <FileSearch className="size-5" />
              </div>
              <h3 className="font-semibold text-lg text-zinc-950 mb-2">Ask with Citations</h3>
              <p className="text-sm text-zinc-600 leading-relaxed text-pretty">
                Agentic LangGraph workflow retrieves code via RRF fusion and verifies each claim with
                exact line-level citations.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 35 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.5, delay: 0.15 }}
              whileHover={{ y: -6, transition: { duration: 0.2 } }}
              className="p-6 rounded-xl border border-zinc-200 bg-zinc-50/60 hover:bg-white hover:border-teal-500/50 hover:shadow-lg hover:shadow-teal-600/5 transition-all"
            >
              <div className="size-10 rounded-lg bg-teal-100 text-teal-700 flex items-center justify-center mb-4">
                <Network className="size-5" />
              </div>
              <h3 className="font-semibold text-lg text-zinc-950 mb-2">Visualise Architecture</h3>
              <p className="text-sm text-zinc-600 leading-relaxed text-pretty">
                Interactive dependency graphs with PageRank importance, cycle detection, and directory
                collapsing via ELK and React Flow.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 35 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.5, delay: 0.25 }}
              whileHover={{ y: -6, transition: { duration: 0.2 } }}
              className="p-6 rounded-xl border border-zinc-200 bg-zinc-50/60 hover:bg-white hover:border-emerald-500/50 hover:shadow-lg hover:shadow-emerald-600/5 transition-all"
            >
              <div className="size-10 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center mb-4">
                <Layers className="size-5" />
              </div>
              <h3 className="font-semibold text-lg text-zinc-950 mb-2">Measure IR Quality</h3>
              <p className="text-sm text-zinc-600 leading-relaxed text-pretty">
                Built-in evaluation dashboard benchmarking Precision@k, Recall@k, MRR, nDCG, latency,
                and confidence calibration.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 35 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.5, delay: 0.35 }}
              whileHover={{ y: -6, transition: { duration: 0.2 } }}
              className="p-6 rounded-xl border border-zinc-200 bg-zinc-50/60 hover:bg-white hover:border-amber-500/50 hover:shadow-lg hover:shadow-amber-600/5 transition-all"
            >
              <div className="size-10 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center mb-4">
                <GitPullRequest className="size-5" />
              </div>
              <h3 className="font-semibold text-lg text-zinc-950 mb-2">Review Pull Requests</h3>
              <p className="text-sm text-zinc-600 leading-relaxed text-pretty">
                Context-aware code review mapping diff hunks to AST symbols, static analysis, and
                human verification workflows.
              </p>
            </motion.div>
          </div>
        </div>
      </section>

      {/* How It Works (§13.4) */}
      <section id="how-it-works" className="py-20 border-t border-zinc-200 bg-zinc-50/50">
        <div className="max-w-7xl mx-auto px-6">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.6 }}
            className="text-center max-w-2xl mx-auto mb-16"
          >
            <h2 className="text-3xl font-bold tracking-tight text-zinc-950 text-balance">
              How RepoGPT Works
            </h2>
            <p className="mt-3 text-zinc-600 text-pretty">
              From repository URL to full codebase mastery in four steps.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <motion.div
              initial={{ opacity: 0, y: 30, scale: 0.95 }}
              whileInView={{ opacity: 1, y: 0, scale: 1 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.5, delay: 0.08 }}
              whileHover={{ scale: 1.03, transition: { duration: 0.2 } }}
              className="flex flex-col items-center text-center p-5 rounded-xl bg-white border border-zinc-200/80 shadow-xs hover:border-emerald-300 transition-colors group"
            >
              <div className="size-12 rounded-full border border-emerald-600/30 bg-emerald-50 text-emerald-700 font-bold flex items-center justify-center mb-4 text-base group-hover:bg-emerald-600 group-hover:text-white transition-colors tabular-nums">
                1
              </div>
              <h4 className="font-semibold text-zinc-950 mb-2">Safe Ingest & Extract</h4>
              <p className="text-sm text-zinc-600 text-pretty">
                Ingest via GitHub URL or ZIP. Filter binaries, apply gitignore, and redact secrets before indexing.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 30, scale: 0.95 }}
              whileInView={{ opacity: 1, y: 0, scale: 1 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.5, delay: 0.16 }}
              whileHover={{ scale: 1.03, transition: { duration: 0.2 } }}
              className="flex flex-col items-center text-center p-5 rounded-xl bg-white border border-zinc-200/80 shadow-xs hover:border-emerald-300 transition-colors group"
            >
              <div className="size-12 rounded-full border border-emerald-600/30 bg-emerald-50 text-emerald-700 font-bold flex items-center justify-center mb-4 text-base group-hover:bg-emerald-600 group-hover:text-white transition-colors tabular-nums">
                2
              </div>
              <h4 className="font-semibold text-zinc-950 mb-2">AST & Multi-Index</h4>
              <p className="text-sm text-zinc-600 text-pretty">
                Parse Tier-1 languages with tree-sitter. Index into vector embeddings, BM25, and NetworkX graphs.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 30, scale: 0.95 }}
              whileInView={{ opacity: 1, y: 0, scale: 1 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.5, delay: 0.24 }}
              whileHover={{ scale: 1.03, transition: { duration: 0.2 } }}
              className="flex flex-col items-center text-center p-5 rounded-xl bg-white border border-zinc-200/80 shadow-xs hover:border-emerald-300 transition-colors group"
            >
              <div className="size-12 rounded-full border border-emerald-600/30 bg-emerald-50 text-emerald-700 font-bold flex items-center justify-center mb-4 text-base group-hover:bg-emerald-600 group-hover:text-white transition-colors tabular-nums">
                3
              </div>
              <h4 className="font-semibold text-zinc-950 mb-2">Agentic Retrieval</h4>
              <p className="text-sm text-zinc-600 text-pretty">
                Route natural language questions, fuse candidates with RRF, expand along the graph, and rerank.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 30, scale: 0.95 }}
              whileInView={{ opacity: 1, y: 0, scale: 1 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.5, delay: 0.32 }}
              whileHover={{ scale: 1.03, transition: { duration: 0.2 } }}
              className="flex flex-col items-center text-center p-5 rounded-xl bg-white border border-zinc-200/80 shadow-xs hover:border-emerald-300 transition-colors group"
            >
              <div className="size-12 rounded-full border border-emerald-600/30 bg-emerald-50 text-emerald-700 font-bold flex items-center justify-center mb-4 text-base group-hover:bg-emerald-600 group-hover:text-white transition-colors tabular-nums">
                4
              </div>
              <h4 className="font-semibold text-zinc-950 mb-2">Verified Answers</h4>
              <p className="text-sm text-zinc-600 text-pretty">
                Generate streaming responses citing exact files and line ranges with computed confidence scores.
              </p>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Footer with UPES Credits (§13.4 & §19) */}
      <motion.footer
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.7 }}
        className="border-t border-zinc-200 bg-white py-12 mt-auto"
      >
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="text-center md:text-left">
            <div className="flex items-center justify-center md:justify-start gap-2.5 mb-2">
              <img src="/logo-icon.png" alt="RepoGPT Logo" className="size-5 object-contain" />
              <span className="font-bold text-zinc-950 tracking-tight">RepoGPT</span>
            </div>
            <p className="text-xs text-zinc-600">
              Major Project · B.Tech CSE (Data Science) · School of Computer Science
            </p>
            <p className="text-xs text-zinc-500 mt-1">
              University of Petroleum and Energy Studies (UPES), Dehradun
            </p>
          </div>

          <div className="text-center md:text-right text-xs text-zinc-600 space-y-1">
            <p>
              <strong className="text-zinc-950">Team:</strong> Harsh Sinha (SAP 500120229) &amp; Anshuman Patel (SAP 500122770)
            </p>
            <p>
              <strong className="text-zinc-950">Project Guide:</strong> Dr. Archana Kumari
            </p>
            <p className="text-zinc-500 pt-1">Released under the MIT License · 2026</p>
          </div>
        </div>
      </motion.footer>

      {/* Product Demo Video Modal Dialog */}
      <AnimatePresence>
        {isDemoOpen && (
          <motion.div
            id="demo-video-modal"
            data-testid="demo-video-modal"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            role="dialog"
            aria-modal="true"
            aria-label="RepoGPT Product Demo Video"
            className="fixed inset-0 z-[200] bg-black/60 backdrop-blur-md flex items-center justify-center p-4 md:p-8"
            onClick={(e) => {
              if (e.target === e.currentTarget) {
                setIsDemoOpen(false);
              }
            }}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 15 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 15 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
              className="relative w-full max-w-5xl rounded-2xl border border-zinc-200 bg-white shadow-2xl overflow-hidden flex flex-col"
            >
              {/* Modal Header */}
              <div className="h-14 border-b border-zinc-200 bg-zinc-50 px-5 flex items-center justify-between shrink-0">
                <div className="flex items-center gap-2.5">
                  <span className="size-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="font-semibold text-sm text-zinc-950">
                    RepoGPT Product Walkthrough &amp; Demo
                  </span>
                  <span className="hidden sm:inline text-xs text-zinc-500 font-mono border-l border-zinc-200 pl-2.5">
                    Feature Overview Video
                  </span>
                </div>
                <button
                  type="button"
                  id="close-demo-modal-btn"
                  data-testid="close-demo-modal-btn"
                  onClick={() => setIsDemoOpen(false)}
                  className="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-900 hover:bg-zinc-200 transition-colors cursor-pointer"
                  aria-label="Close demo video"
                >
                  <X className="size-5" />
                </button>
              </div>

              {/* Video Player */}
              <div className="relative w-full aspect-video bg-black flex items-center justify-center overflow-hidden">
                <video
                  id="demo-video-player"
                  data-testid="demo-video-player"
                  src="/demo.mp4"
                  controls
                  autoPlay
                  playsInline
                  className="w-full h-full object-contain"
                >
                  Your browser does not support HTML5 video.
                </video>
              </div>

              {/* Modal Footer */}
              <div className="px-5 py-3 border-t border-zinc-200 bg-zinc-50 flex items-center justify-between text-xs text-zinc-600">
                <span className="text-zinc-500">
                  Press{" "}
                  <kbd className="font-mono bg-white border border-zinc-300 px-1.5 py-0.5 rounded text-[10px] text-zinc-700 shadow-xs">
                    ESC
                  </kbd>{" "}
                  or click outside to close
                </span>
                <div className="flex items-center gap-3">
                  <Link
                    to="/register"
                    onClick={() => setIsDemoOpen(false)}
                    className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-3.5 py-1.5 rounded-md transition-all shadow-sm shadow-emerald-600/15 flex items-center gap-1.5 cursor-pointer"
                  >
                    Get Started Free
                    <Sparkles className="size-3.5" />
                  </Link>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
