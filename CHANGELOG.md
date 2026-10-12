# Changelog

All notable changes to RepoGPT will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-12

### Added
- **Complete Major Project Release**: Full end-to-end implementation across all 12 milestones (M0–M12).
- **Ingestion & Processing (M2, M3)**:
  - Tarball and ZIP safe extraction with path traversal and zip bomb defense.
  - Multi-language AST parsing using tree-sitter across 5 tier-1 languages (Python, TypeScript, JavaScript, Go, Rust).
  - High-entropy secret detection and redaction engine.
  - Code-aware AST chunker (max 500 tokens, 50-token overlap).
- **Multi-Modal Indexing & Retrieval (M4, M5)**:
  - Dense vector embeddings via FastEmbed (`jina-embeddings-v2-base-code`) and dual stores (ChromaDB & FAISS).
  - Sparse lexical indexing via `bm25s` with camelCase/snake_case token splitting.
  - Reciprocal Rank Fusion (RRF $k=60$) and Cross-Encoder reranking (`ms-marco-MiniLM-L-6-v2`).
  - Adaptive heuristic and LLM-powered query intent router.
- **Agentic QA & Chat (M6)**:
  - Multi-step LangGraph state graph with sufficiency checks, query reformulation, and streamed SSE generation.
  - Inline `[S#]` citations verified against actual retrieved line boundaries.
  - Calibrated 10-bin confidence score and interactive evidence inspection.
- **Architecture Overview & Dependency Graph (M7)**:
  - Automated tech stack identification, entry points detection, and reading order generator.
  - Interactive `@xyflow/react` and `elkjs` dependency graph with cycle detection and PageRank centrality.
- **Evaluation Suite (M8)**:
  - Mathematical metrics engine computing Hit@k, MRR, nDCG@k, Brier score, ECE, and latency percentiles.
  - Built-in benchmarks for TaskFlow (30Q) and psf/requests (15Q).
  - Interactive evaluation dashboard with pre-flight estimation, strategy comparison charts, and CSV/MD export.
- **Hardening & Security Gate (M9)**:
  - Scoped anti-enumeration tests verifying 33 routes against ID probing attacks (§7.5, §11.7).
  - Content sanitization with `rehype-sanitize` and multi-vector XSS testing.
  - Full admin dashboard for user management, audit logs, and worker telemetry.
  - Code splitting and lazy loading reducing initial bundle size to 409 kB.
- **Phase 2 Context-Aware PR Review (M10)**:
  - Unified diff parser and in-memory patch application on base snapshots.
  - Context retrieval mapping modified symbols, callers, and related test files.
  - Isolated Ruff static analysis (E9/F/B/S) mapped to changed lines.
  - LangGraph review state graph with executive risk scoring and finding deduplication.
  - Human triage UI (Accept, Reject, Edit) and GitHub COMMENT review publishing.
  - 100% recall benchmark across 6 seeded vulnerability and performance patches.
  - GitHub PR webhook endpoint with constant-time HMAC-SHA256 signature verification.
- **Production Delivery & Operations (M11)**:
  - Multi-stage Dockerfiles with non-root user `app:app` (UID 10001).
  - Caddy automatic TLS reverse proxy with strict security headers (CSP, HSTS).
  - Production Compose with resource limits, read-only root filesystems, and JSON log rotation.
  - Local LLM profile (`ollama`) and Monitoring profile (`prometheus` + `grafana` with pre-configured dashboard).
  - Idempotent Ubuntu 24.04 EC2 host bootstrap, zero-downtime deployment, daily backup with 7-day retention, and restore drill scripts.
- **Documentation & Report Assets (M12)**:
  - Complete documentation suite (`architecture.md`, `api.md`, `deployment.md`, `evaluation.md`, `development.md`, `user-guide.md`, `references.md`).
  - 10 Mermaid report diagrams and benchmark results.

## [0.1.0] - 2026-10-11
### Added
- Monorepo layout and development tooling.
- Core settings configuration with Pydantic Settings and strict validation.
- Standardized error handling envelope and custom `AppError` hierarchy.
- Structured logging with `structlog` and automatic secret scrubbing.
- Cryptographic primitives: Argon2id password hashing, JWT access tokens, Fernet secret encryption.
- PyMongo native async integration with idempotent MongoDB index creation.
- Redis client connection pool and sliding-window rate limiting.
- Healthcheck endpoints `/live` and `/ready`.
- Docker Compose configurations for base, dev, and production.
- Production Caddy reverse proxy setup with strict Content Security Policy.
- React 19 + Vite frontend shell with Tailwind CSS v4, dark theme tokens, landing page, and dashboard.
- GitHub Actions CI/CD workflows for testing, security audits, and EC2 deployment.
