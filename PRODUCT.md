# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Software Engineers & Tech Leads**: Developers onboarding to unfamiliar, legacy, or large-scale multi-language codebases who need to quickly build a clear mental model of the architecture and safely conduct pull request reviews.
- **Academic Researchers & Project Evaluators**: Computer science researchers studying information retrieval (IR), retrieval-augmented generation (RAG), and deterministic AST-assisted code comprehension.

## Product Purpose

RepoGPT is an agentic AI system for codebase understanding, developer onboarding, and intelligent code review. It ingests source code repositories, extracts AST symbol tables, generates dependency graphs with PageRank metrics and cycle detection, and provides natural language code exploration with verified inline citations down to exact file paths and line ranges. Success means reducing developer repository onboarding from days to minutes with zero hallucinated code references.

## Positioning

Interactive architectural visualization (dependency graphs, PageRank, cycles) coupled directly with agentic QA and verified inline citations. Unlike generic code assistants that rely solely on token window dumping or naive vector search, RepoGPT enforces deterministic AST parsing, automated secret redaction, hybrid BM25 + vector retrieval, and calibrated confidence scores linked to exact code locations.

## Operating Context

- **Usage Scene**: Web browser single-page application operated alongside local IDEs, terminal workflows, and GitHub PR reviews.
- **Data Ingestion**: Public and private GitHub repositories, or local ZIP archives.
- **Language Support**: Tier-1 AST extraction for Python, TypeScript, JavaScript, Java, and Go via tree-sitter, with resilient fallback chunking for all standard file formats.
- **Workflow**: Repository Ingestion -> Architecture & Tech Stack Tour -> Interactive Dependency Graph Exploration -> Verified Natural Language Code QA -> PR Diff Review.

## Capabilities and Constraints

- **Capabilities**:
  - Deterministic AST symbol and import extraction.
  - Multi-tier indexing: dual vector store abstraction (ChromaDB / FAISS) and code-aware BM25 keyword index (`bm25s`).
  - LangGraph stateful agentic QA with hybrid Reciprocal Rank Fusion (RRF) and cross-encoder reranking.
  - Interactive ELK-layered dependency graphs with PageRank centrality and cycle analysis.
  - Automated onboarding architecture synthesis (reading order, application entry points, tech stack detection).
  - Comprehensive IR evaluation suite (MRR, nDCG@k, Precision@k, Recall@k, ECE calibration).
- **Constraints**:
  - **Streamlined Simplicity**: Minimal cognitive load, clean layouts, and rapid visual scanning over dense, cluttered enterprise dashboards.
  - **Strict Secret Redaction**: High-entropy strings, API keys, tokens, and credentials are redacted prior to chunking, vector indexing, or LLM exposure.
  - **Deployment Self-Containment**: Fully containerized with Docker Compose (FastAPI backend, Celery worker, MongoDB 8, Redis 7, ChromaDB, React 19 SPA).

## Brand Commitments

- **Name**: RepoGPT
- **Tone & Voice**: Precise, calm, developer-friendly, and authoritative without marketing hype.
- **Visual Identity**: Modern dark-first theme, refined indigo accents (`#6366f1`), crisp monospace font accents for code identifiers, and high-density, legible typography.

## Evidence on Hand

- Verified, fully working local full-stack codebase (FastAPI + Celery + MongoDB 8 + ChromaDB + React 19).
- Tested real-world repository ingestions (`hsinha2004/Sovereign-AI`) with complete AST symbol, chunk, and graph data.
- 192 automated unit and integration tests passing.
- Academic major project at UPES School of Computer Science (Team: Harsh Sinha & Anshuman Patel; Guide: Dr. Archana Kumari).

## Product Principles

1. **Grounding over Guesswork**: Every answer, summary, or review finding must be linked to verified inline citations (`[S#]`) with exact file and line ranges. If evidence is missing, state context insufficiency explicitly.
2. **Visual Architecture First**: Pair natural language explanations with visual structural mental models (dependency graphs, entry point flow, module layers) to accelerate comprehension.
3. **Streamlined Consumer-Grade Simplicity**: Prevent visual noise and cognitive fatigue. Prioritize immediate scanability, intuitive navigation, and clean information hierarchy.
4. **Zero-Trust Secret Protection**: Redact credentials, AWS keys, GitHub tokens, and private secrets deterministically before embedding or transmitting code to model providers.
5. **Transparency & Calibrated Confidence**: Always expose retrieval quality, citation validity, and confidence metrics so developers can trust what they read.

## Accessibility & Inclusion

- WCAG AA compliant contrast ratios for dark and light modes.
- Accessible, colorblind-friendly syntax highlighting themes.
- Full keyboard navigation for graph exploration, code inspection, and chat inputs.
