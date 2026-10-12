import React from "react";
import { GitPullRequest, ShieldAlert, Sparkles, CheckCircle2, Lock } from "lucide-react";

export const CodeReviewTab: React.FC = () => {
  return (
    <div className="py-12 max-w-2xl mx-auto text-center space-y-6">
      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
        <Sparkles className="w-3.5 h-3.5" />
        Phase 2 Feature • Coming in Milestone 10
      </div>

      <div className="space-y-2">
        <h2 className="text-xl font-bold text-white tracking-tight">
          Automated Code Review Benchmarking
        </h2>
        <p className="text-sm text-zinc-400 max-w-lg mx-auto">
          Evaluate PR review precision, rule violation recall, security vulnerability detection,
          and false-positive rates against curated PR review benchmark fixtures (§15, §20).
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-left pt-4">
        <div className="p-4 rounded-xl bg-[#111113] border border-[#27272a] space-y-2">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center font-bold">
            <GitPullRequest className="w-4 h-4" />
          </div>
          <div className="text-xs font-semibold text-white">Diff Chunking Benchmark</div>
          <p className="text-[11px] text-zinc-400">
            Validates hunks parsing and AST-context retrieval under strict limits.
          </p>
        </div>

        <div className="p-4 rounded-xl bg-[#111113] border border-[#27272a] space-y-2">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center font-bold">
            <CheckCircle2 className="w-4 h-4" />
          </div>
          <div className="text-xs font-semibold text-white">Precision & Recall @ Rule</div>
          <p className="text-[11px] text-zinc-400">
            Measures rule detection accuracy across style, bugs, and performance violations.
          </p>
        </div>

        <div className="p-4 rounded-xl bg-[#111113] border border-[#27272a] space-y-2">
          <div className="w-8 h-8 rounded-lg bg-rose-500/10 text-rose-400 flex items-center justify-center font-bold">
            <ShieldAlert className="w-4 h-4" />
          </div>
          <div className="text-xs font-semibold text-white">Security Vulnerabilities</div>
          <p className="text-[11px] text-zinc-400">
            Tests detection of OWASP Top 10 flaws, hardcoded credentials, and unsafe calls.
          </p>
        </div>
      </div>

      <div className="inline-flex items-center gap-2 text-xs text-zinc-500 pt-4">
        <Lock className="w-3.5 h-3.5" />
        This module will activate automatically upon beginning Milestone 10 implementation.
      </div>
    </div>
  );
};
