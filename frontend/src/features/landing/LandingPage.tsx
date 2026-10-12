import React from "react";
import { Link } from "react-router";
import {
  CheckCircle,
  FileSearch,
  GitPullRequest,
  Layers,
  Network,
  Sparkles,
} from "lucide-react";
import { motion, useScroll, useSpring } from "motion/react";

export const LandingPage: React.FC = () => {
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, {
    stiffness: 100,
    damping: 30,
    restDelta: 0.001,
  });

  return (
    <div className="min-h-dvh bg-[#09090b] text-[#fafafa] flex flex-col font-sans selection:bg-emerald-500 selection:text-white">
      {/* Top Scroll Progress Bar */}
      <motion.div
        style={{ scaleX }}
        className="fixed top-0 left-0 right-0 h-1 bg-gradient-to-r from-emerald-500 via-teal-400 to-emerald-300 origin-left z-[100]"
      />

      {/* Top Navigation */}
      <header className="border-b border-[#27272a] bg-[#111113]/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3.5">
            <img src="/logo-icon.png" alt="RepoGPT Logo" className="size-11 object-contain drop-shadow" />
            <span className="font-extrabold text-2xl tracking-tight text-white">RepoGPT</span>
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
              className="text-sm font-medium bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-md transition-all shadow-sm cursor-pointer"
            >
              Get Started
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative pt-16 pb-16 px-6 max-w-7xl mx-auto text-center flex-1 flex flex-col items-center justify-center overflow-hidden">
        {/* Subtle Green Ambient Glow */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[640px] h-[320px] bg-gradient-to-b from-emerald-500/15 via-teal-500/5 to-transparent blur-3xl pointer-events-none -z-10" />

        {/* Hero Logo Emblem */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9, y: 24 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
          className="mb-6 flex justify-center"
        >
          <div className="relative group">
            <div className="absolute -inset-4 bg-gradient-to-r from-emerald-500/25 via-teal-500/20 to-blue-500/25 rounded-3xl blur-2xl opacity-75 group-hover:opacity-100 transition-opacity" />
            <img
              src="/logo.png"
              alt="RepoGPT Official Logo"
              className="relative h-36 md:h-44 object-contain drop-shadow-[0_15px_35px_rgba(0,0,0,0.6)] transition-transform duration-300 group-hover:scale-105"
            />
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-[#27272a] bg-[#111113] text-xs text-[#a1a1aa] mb-8"
        >
          <Sparkles className="size-3.5 text-emerald-400" />
          <span>Agentic AI System for Codebase Understanding & Review</span>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
          className="text-4xl md:text-6xl font-extrabold tracking-tight max-w-4xl leading-tight text-balance"
        >
          Understand Any Complex Codebase in Seconds,{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-300 to-emerald-400">
            With Exact Citations
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
          className="mt-6 text-lg text-[#a1a1aa] max-w-2xl text-pretty"
        >
          RepoGPT parses your repository with tree-sitter AST, constructs hybrid vector + BM25 +
          dependency graph indices, and explains architecture, logic, and call chains with verifiable
          inline citations.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.4, ease: [0.16, 1, 0.3, 1] }}
          className="mt-8 flex flex-wrap gap-4 justify-center"
        >
          <Link
            to="/register"
            className="bg-emerald-600 hover:bg-emerald-500 text-white font-medium px-6 py-3 rounded-lg transition-all shadow-lg shadow-emerald-500/20 flex items-center gap-2 cursor-pointer"
          >
            Start Exploring Code
            <Sparkles className="w-4 h-4" />
          </Link>
          <Link
            to="/login"
            className="border border-[#27272a] bg-[#111113] hover:bg-[#18181b] text-white font-medium px-6 py-3 rounded-lg transition-all cursor-pointer"
          >
            Live Demo
          </Link>
        </motion.div>

        {/* Illustrative Product Preview - TaskFlow Sample */}
        <motion.div
          initial={{ opacity: 0, y: 40, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.8, delay: 0.5, ease: [0.16, 1, 0.3, 1] }}
          whileHover={{ y: -4, transition: { duration: 0.2 } }}
          className="mt-16 w-full max-w-4xl border border-[#27272a] rounded-xl bg-[#111113] shadow-2xl overflow-hidden text-left"
        >
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
              <div className="w-7 h-7 rounded bg-emerald-600 flex items-center justify-center text-xs text-white font-bold shrink-0">
                AI
              </div>
              <div className="text-sm text-[#a1a1aa] space-y-2 leading-relaxed">
                <p>
                  The JWT access token is generated inside{" "}
                  <code className="text-white bg-[#27272a] px-1.5 py-0.5 rounded font-mono text-xs">
                    create_access_token()
                  </code>{" "}
                  located in{" "}
                  <span className="inline-flex items-center gap-1 text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded text-xs font-mono border border-emerald-500/20">
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
                  <span className="inline-flex items-center gap-1 text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded text-xs font-mono border border-emerald-500/20">
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
        </motion.div>
      </section>

      {/* 4 Core Features (§13.4) */}
      <section id="features" className="py-20 border-t border-[#27272a] bg-[#111113]">
        <div className="max-w-7xl mx-auto px-6">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.6 }}
            className="text-center max-w-2xl mx-auto mb-16"
          >
            <h2 className="text-3xl font-bold tracking-tight text-white text-balance">
              Built for Deep Code Intelligence
            </h2>
            <p className="mt-3 text-[#a1a1aa] text-pretty">
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
              className="p-6 rounded-xl border border-[#27272a] bg-[#09090b] hover:border-emerald-500/50 hover:shadow-lg hover:shadow-emerald-500/5 transition-all"
            >
              <div className="size-10 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center mb-4">
                <FileSearch className="size-5" />
              </div>
              <h3 className="font-semibold text-lg text-white mb-2">Ask with Citations</h3>
              <p className="text-sm text-[#a1a1aa] leading-relaxed text-pretty">
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
              className="p-6 rounded-xl border border-[#27272a] bg-[#09090b] hover:border-teal-500/50 hover:shadow-lg hover:shadow-teal-500/5 transition-all"
            >
              <div className="size-10 rounded-lg bg-teal-500/10 text-teal-400 flex items-center justify-center mb-4">
                <Network className="size-5" />
              </div>
              <h3 className="font-semibold text-lg text-white mb-2">Visualise Architecture</h3>
              <p className="text-sm text-[#a1a1aa] leading-relaxed text-pretty">
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
              className="p-6 rounded-xl border border-[#27272a] bg-[#09090b] hover:border-emerald-500/50 hover:shadow-lg hover:shadow-emerald-500/5 transition-all"
            >
              <div className="size-10 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center mb-4">
                <Layers className="size-5" />
              </div>
              <h3 className="font-semibold text-lg text-white mb-2">Measure IR Quality</h3>
              <p className="text-sm text-[#a1a1aa] leading-relaxed text-pretty">
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
              className="p-6 rounded-xl border border-[#27272a] bg-[#09090b] hover:border-amber-500/50 hover:shadow-lg hover:shadow-amber-500/5 transition-all"
            >
              <div className="size-10 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center mb-4">
                <GitPullRequest className="size-5" />
              </div>
              <h3 className="font-semibold text-lg text-white mb-2">Review Pull Requests</h3>
              <p className="text-sm text-[#a1a1aa] leading-relaxed text-pretty">
                Context-aware code review mapping diff hunks to AST symbols, static analysis, and
                human verification workflows.
              </p>
            </motion.div>
          </div>
        </div>
      </section>

      {/* How It Works (§13.4) */}
      <section id="how-it-works" className="py-20 border-t border-[#27272a] bg-[#09090b]">
        <div className="max-w-7xl mx-auto px-6">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.6 }}
            className="text-center max-w-2xl mx-auto mb-16"
          >
            <h2 className="text-3xl font-bold tracking-tight text-white text-balance">
              How RepoGPT Works
            </h2>
            <p className="mt-3 text-[#a1a1aa] text-pretty">
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
              className="flex flex-col items-center text-center p-4 rounded-xl hover:bg-[#111113]/50 transition-colors group"
            >
              <div className="size-12 rounded-full border border-emerald-500/30 bg-[#111113] text-emerald-400 font-bold flex items-center justify-center mb-4 text-base group-hover:bg-emerald-500 group-hover:text-white transition-colors tabular-nums">
                1
              </div>
              <h4 className="font-semibold text-white mb-2">Safe Ingest & Extract</h4>
              <p className="text-sm text-[#a1a1aa] text-pretty">
                Ingest via GitHub URL or ZIP. Filter binaries, apply gitignore, and redact secrets before indexing.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 30, scale: 0.95 }}
              whileInView={{ opacity: 1, y: 0, scale: 1 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.5, delay: 0.16 }}
              whileHover={{ scale: 1.03, transition: { duration: 0.2 } }}
              className="flex flex-col items-center text-center p-4 rounded-xl hover:bg-[#111113]/50 transition-colors group"
            >
              <div className="size-12 rounded-full border border-emerald-500/30 bg-[#111113] text-emerald-400 font-bold flex items-center justify-center mb-4 text-base group-hover:bg-emerald-500 group-hover:text-white transition-colors tabular-nums">
                2
              </div>
              <h4 className="font-semibold text-white mb-2">AST & Multi-Index</h4>
              <p className="text-sm text-[#a1a1aa] text-pretty">
                Parse Tier-1 languages with tree-sitter. Index into vector embeddings, BM25, and NetworkX graphs.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 30, scale: 0.95 }}
              whileInView={{ opacity: 1, y: 0, scale: 1 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.5, delay: 0.24 }}
              whileHover={{ scale: 1.03, transition: { duration: 0.2 } }}
              className="flex flex-col items-center text-center p-4 rounded-xl hover:bg-[#111113]/50 transition-colors group"
            >
              <div className="size-12 rounded-full border border-emerald-500/30 bg-[#111113] text-emerald-400 font-bold flex items-center justify-center mb-4 text-base group-hover:bg-emerald-500 group-hover:text-white transition-colors tabular-nums">
                3
              </div>
              <h4 className="font-semibold text-white mb-2">Agentic Retrieval</h4>
              <p className="text-sm text-[#a1a1aa] text-pretty">
                Route natural language questions, fuse candidates with RRF, expand along the graph, and rerank.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 30, scale: 0.95 }}
              whileInView={{ opacity: 1, y: 0, scale: 1 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.5, delay: 0.32 }}
              whileHover={{ scale: 1.03, transition: { duration: 0.2 } }}
              className="flex flex-col items-center text-center p-4 rounded-xl hover:bg-[#111113]/50 transition-colors group"
            >
              <div className="size-12 rounded-full border border-emerald-500/30 bg-[#111113] text-emerald-400 font-bold flex items-center justify-center mb-4 text-base group-hover:bg-emerald-500 group-hover:text-white transition-colors tabular-nums">
                4
              </div>
              <h4 className="font-semibold text-white mb-2">Verified Answers</h4>
              <p className="text-sm text-[#a1a1aa] text-pretty">
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
        className="border-t border-[#27272a] bg-[#0c0c0e] py-12 mt-auto"
      >
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="text-center md:text-left">
            <div className="flex items-center justify-center md:justify-start gap-2.5 mb-2">
              <img src="/logo-icon.png" alt="RepoGPT Logo" className="size-5 object-contain" />
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
      </motion.footer>
    </div>
  );
};
