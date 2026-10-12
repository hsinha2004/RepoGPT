# RepoGPT — Build Progress & Milestone Checklist

Tracks implementation progress across all 13 milestones (§20 of `docs/SPEC.md`).
Updated at the completion of each milestone with status, verification details, and known issues.

---

## Milestone Checklist

- [x] **M0: Foundation**
  - Scope: Monorepo layout, tooling (uv, ruff, mypy, pytest, Vite/TS/ESLint/Prettier/Vitest), pre-commit, `.env.example` + `generate_secrets.py`, Settings with validation, Compose base + dev (all services healthy), app factory, health endpoints, error envelope, logging, request IDs, CI skeleton, Makefile, `docs/SPEC.md`, `PROGRESS.md`, `DECISIONS.md`.
  - Exit criteria: `make setup && make dev` -> all containers healthy; `/api/v1/health/ready` all green; frontend shell loads; workflow files pass actionlint, and every CI job's commands pass locally.
  - Status: Completed (Verified)
  - Verification:
    - Backend: `ruff check` (0 errors), `ruff format --check` (clean), `mypy backend/app` (0 issues), `pytest backend/tests/unit` (15 passed).
    - Frontend: `npm run typecheck` (tsc clean), `npm test` (vitest 1 passed), `npm run build` (vite bundle 138kB gzip, clean).
    - Scripts: `python scripts/generate_secrets.py` and `python scripts/export_openapi.py` verified; OpenAPI contract exported to `frontend/src/api/openapi.json` and types generated via `openapi-typescript`.
  - Known issues: None

- [x] **M1: Auth & security baseline**
  - Scope: Users, sessions, Argon2, JWT, refresh rotation + reuse detection, CSRF, lockout, rate limiter, quotas scaffolding, admin seeding, PAT storage, GitHub OAuth, audit log, security headers middleware; frontend landing, login/register, app shell, theme, command-palette shell, auth refresh logic, settings (profile/password/PAT/sessions).
  - Exit criteria: Auth unit + integration tests pass; manual flow works in browser; tokens never in localStorage.
  - Status: Completed (Verified)
  - Verification:
    - Backend: `pytest backend/tests` (19 passed, 0 warnings); `ruff check` (0 errors); `ruff format` (clean); `mypy backend/app` (0 issues in 26 files).
    - Auth & Security: Argon2id password hashing, constant-time compare, opaque token generation with SHA-256 storage, Fernet AES-128 PAT encryption/decryption, token family theft/reuse detection revokes entire family, 10 consecutive failed attempts triggers 15-minute lockout.
    - Frontend: `npm run typecheck` (tsc clean), `npm test` (vitest clean), `npm run build` (vite bundle built in 3.45s), `SettingsPage` implemented with Profile, GitHub PAT integration with show/hide toggle + test connection + revocation, Password change, Log out all devices, and Daily Quotas & Usage display.
  - Known issues: None

- [x] **M2: Ingestion & jobs**
  - Scope: GitHub fetcher, ZIP upload, safe extraction, filters, snapshots, Celery app/runtime, jobs + SSE progress + cancel, repo CRUD + members, TaskFlow fixture repo; frontend dashboard, add-repo dialog, progress stepper, repo settings/members.
  - Exit criteria: Fixture ZIP and a public GitHub repo ingest through "filtering" with live progress; malicious-archive tests pass.
  - Status: Completed (Verified)
  - Verification:
    - TaskFlow Fixture: Created complete 37-file multi-language fixture repo (`eval/fixtures/sample-repo/`) with FastAPI backend, React 19 TS frontend, Go background reminder worker, Java reporting CLI, Docker compose, and configurations.
    - Security Defenses: Safe archive extraction rejecting path traversals (`..`), absolute paths, drive letters, symlinks/hardlinks, device files, and zip-bombs (> 100:1 compression ratio). Strict GitHub URL regexes preventing SSRF.
    - Filtering & Classification: Default ignores, gitignore (pathspec), binary detection (NUL byte / decode fallback), minified/generated heuristics, language and kind (`code`/`doc`/`config`/`test`) detection.
    - Celery & Jobs: Celery worker app (`app/jobs/celery_app.py`) on Redis DB 0 with JSON serializer, isolated async runtime (`app/jobs/runtime.py`) binding fresh PyMongo and Redis connections per task, per-repo concurrency lock `lock:repo:{id}`.
    - Server-Sent Events: SSE endpoint `/api/v1/jobs/{id}/events` streaming live progress updates via Redis pub/sub.
    - Testing & Gates: 34 pytest tests passing (`test_archive_security.py`, `test_filter.py`, `test_github_fetcher.py`, `test_ingestion_pipeline.py`); `ruff check` (0 errors); `ruff format` (clean); `mypy backend/app` (0 issues in 41 files); frontend `npm run typecheck` (clean); `npm test` (clean); `npm run build` (vite bundle built).
  - Known issues: None

- [x] **M3: Parsing, redaction, chunking**
  - Scope: ParserRegistry, five tier-1 extractors, tier-2 + docs + config, redaction, chunker with headers, symbols, file cards, dir summaries; frontend Explorer (tree, viewer, outline, deep links, file info).
  - Exit criteria: Extractor/redaction/chunker tests pass; Explorer browses TaskFlow with symbols and highlighted line deep links.
  - Status: Completed (Verified)
  - Verification:
    - Secret Redaction: Table-driven detectors (AWS, GitHub, GitLab, Slack, Google API, Stripe, OpenAI/Anthropic, SendGrid, Twilio, JWTs, PEM blocks, connection strings, and generic high-entropy assignments >= 3.5). 17/17 tests passing with line count preservation and dynamically generated fake secrets.
    - AST Extractors: `ParserRegistry` with tree-sitter tier-1 extractors for Python, JavaScript, TypeScript/TSX, Java, Go, Docs (Markdown), Config (Dockerfile, Makefile, JSON, YAML) and line-window fallback. 8/8 tests passing.
    - Code Chunking: `CodeChunker` using tiktoken `cl100k_base` producing symbol chunks, large symbol splitting (>800 tokens to <=512 token parts with 3-line overlap), class skeletons, module headers, deterministic file cards, directory summaries, contextual headers prepended to `embed_text`, and delimiter escaping (`</source>`). 5/5 tests passing.
    - Ingestion Pipeline: Integrated stages 4 (parsing 15%), 5 (redacting 5%), and 6 (chunking 5%). End-to-end integration test on 37-file TaskFlow fixture repo extracted > 200 LOC, symbols, and chunks into MongoDB `symbols` and `chunks` collections.
    - Frontend Explorer: Responsive 3-pane Explorer implemented (`FileTree`, `FileInfoHeader`, `CodeViewer`, `SymbolOutline`) with virtualized tree, language badges, skipped file tooltips, line numbers, `#L10-L40` deep links, permalink copying, symbol jump-to-line, and "Ask about file / selection" chat actions.
    - Quality Gates: All 64 pytest tests passed; `mypy backend/app` clean (0 issues in 60 source files); `ruff check` and `ruff format` passed; frontend `npm run typecheck` passed (clean); `npm test` passed; `npm run build` passed (vite bundle built in 3.80s).
  - Known issues: None

- [x] **M4: Indexing**
  - Scope: Embedding providers (fastembed, API, fake), embedding cache, Chroma + FAISS stores, BM25 index, incremental sync, deletion cleanup.
  - Exit criteria: TaskFlow fully indexed (`ready`); sync re-embeds only changed files (test); deletion test passes.
  - Status: Completed (Verified)
  - Verification:
    - Embedding Subsystem: `EmbeddingProvider` abstract base with `FastEmbedProvider` (BAAI/bge-small-en-v1.5, 384 dimensions), `APIEmbeddingProvider` (OpenAI / voyage / Ollama compatible), and `FakeEmbeddingProvider` (deterministic unit-normalized hashing). In-memory + optional Redis `EmbeddingCache` keyed by model and text SHA-256 with 7-day TTL.
    - Vector Stores: `VectorStore` interface supporting cosine similarity search, metadata filtering, chunk deduplication, and persistence. Implemented `ChromaVectorStore` (persistent SQLite/WAL collection) and `FAISSVectorStore` (IndexFlatIP with L2 normalized vectors and index/pickle persistence). Factory dynamically loads configured store.
    - Keyword Search (BM25): Code-aware tokenizer with camelCase/PascalCase/snake_case/kebab-case splitting, digits separation, common stop words filtering, and 2x path boosting for file path tokens in chunk headers. High-performance `BM25Index` wrapping `bm25s` with persistence and thread-safe LRU cache (`BM25IndexManager`).
    - Incremental Sync: `IncrementalSyncService` diffs file content hashes against previous snapshot, deletes stale chunks/symbols from MongoDB and vector/BM25 indices, parses/redacts/chunks only added/modified files, leverages embedding cache to avoid re-computing existing chunk embeddings, updates indices, and atomically transitions repo state to `ready`.
    - Repo Deletion: `RepoDeletionService` purges MongoDB repository, files, symbols, chunks, jobs, snapshots, vector store collections, and BM25 index directory on disk.
    - Quality Gates: All 77 pytest tests passed (`test_embeddings.py`, `test_vector_stores.py`, `test_bm25_tokenizer.py`, `test_sync_and_deletion.py`, `test_ingestion_pipeline.py`); `ruff check` (0 errors); `ruff format` (clean); `mypy backend/app` (0 issues in 78 source files); frontend `npm run typecheck` (clean); `npm test` (clean); `npm run build` (vite production bundle clean).
  - Known issues: None

- [x] **M5: Retrieval & router**
  - Scope: Keyword, vector, hybrid RRF, reranker, symbol lookup, graph expansion hook, summary scope, context builder, heuristic + LLM router; `/search` endpoint; frontend Search playground.
  - Exit criteria: Integration: expected file in top-5 for >= 80% of TaskFlow questions (hybrid); router table tests pass.
  - Status: Complete
  - Verification: 56/56 heuristic router test cases passed; 3/3 reranker tests passed; 3/3 RRF fusion tests passed; 5/5 context builder tests passed; 4/4 search endpoint tests passed; TaskFlow benchmark Hit@5 achieved 90.0% (27/30) exceeding the >= 80% exit criterion; frontend Search playground implemented and verified; `mypy app` (97 files clean), `ruff check/format` clean, `tsc -b && vite build` succeeded.
  - Known issues: None


- [x] **M6: Agentic QA & chat**
  - Scope: LLM provider layer (Anthropic, OpenAI-compatible presets, fake), limiter, pricing, prompts, LangGraph QA graph, SSE streaming, citations, grounding, confidence, conversations, cache, feedback, export; frontend Chat with evidence panel, trace, confidence, stop/regenerate.
  - Exit criteria: SSE integration test passes; with a real provider key, answers cite correct TaskFlow files; offline mode works with no key.
  - Status: Completed (Verified)
  - Verification:
    - LLM Provider Subsystem: Protocol `LLMProvider`, `AnthropicProvider`, `OpenAICompatibleProvider` (covers OpenAI, Gemini, Groq, OpenRouter, Ollama), `FakeProvider` with deterministic routing, extractive answer synthesis, and grounding check. Structured output parsing and repair loop, model pricing calculator per 1M tokens with override support, Redis sliding window rate limiter (`llm:rpm:{provider}`) and concurrency semaphore. 6/6 tests passing in `test_llm_providers.py`.
    - Citations & Confidence: Verified regex extraction of `[S#]`, cross-validation against candidate chunks, stripping of ungrounded citations, and calibrated confidence score calculation ($0.35R + 0.20C + 0.15K + 0.30G$) with insufficient evidence score capping $\le 0.35$. 5/5 tests passing in `test_citations_and_confidence.py`.
    - LangGraph State Machine: 10-node QA graph (`contextualize` -> `route` -> `retrieve` -> `graph_expand` -> `rerank` -> `assess` ↺ `reformulate` -> `generate` -> `verify` -> `finalize`) with conditional loop edges and state tracking. 2/2 tests passing in `test_qa_graph.py`.
    - SSE Streaming & API Endpoints: Endpoints for conversation CRUD, Markdown export, SSE message streaming (`text/event-stream` delivering `meta`, `status`, `route`, `sources`, `token`, `citations`, `confidence`, `done`, `error`), and message feedback. 2/2 integration tests passing in `test_chat_sse.py`.
    - Frontend Chat UI: Full 3-pane layout (`ChatPage.tsx`) with conversation list, search filter, message thread, markdown/code rendering, inline citation chips, status spinner, feedback modal, strategy selector, and Evidence panel with Sources, Trace, and Confidence tabs. 4/4 Vitest tests passing.
    - Quality Gates: All 164 backend pytest tests passing; `mypy backend/app` clean across 122 source files; `ruff check` and `ruff format` clean; frontend `tsc -b && vite build` built cleanly; zero-key offline mode fully functional.
  - Known issues: None

- [x] **M7: Graph, analysis & overview**
  - Scope: Import resolvers, heuristic calls, NetworkX metrics, directory aggregation, tech stack, entry points, reading order, overview (LLM + heuristic); frontend Overview and Graph pages.
  - Exit criteria: Graph of TaskFlow shows frontend -> API -> service -> repository -> db chain; overview lists correct stack and entry points.
  - Status: Completed (Verified)
  - Verification:
    - Multi-Language Import Resolvers: Language-specific import resolvers in `app/services/graph/resolvers/` for Python (relative `.`/`..`, package roots, `.py`/`__init__.py`), JavaScript/TypeScript (relative, `@/` / `~/` aliases, `index.ts`/`tsx` extensions), Java (fully qualified package/class names and wildcard packages), and Go (standard library detection, `go.mod` module path matching, package directories). 5/5 unit tests passing in `test_resolvers.py`.
    - Graph Builder & NetworkX Analysis: `GraphBuilder` constructing import and call dependency edges (`imports`, `calls`). `GraphAnalyzer` computing PageRank centrality, in-degree/out-degree (fan-in / fan-out), orphan detection, simple cycle detection ($\le 50$), weakly connected components, ego-graph focus subgraphs, and directory-level rollup aggregation. 5/5 unit tests passing in `test_graph_analysis.py`.
    - Architectural Detection & Analysis: `TechStackDetector` identifying frameworks, libraries, databases, and runtimes across 8 categories with manifest evidence; `EntryPointDetector` detecting CLI, API server, background worker, script, and app factories; `ReadingOrderGenerator` producing topologically and centrality-sorted onboarding reading path.
    - Onboarding Overview Service: `OverviewService` synthesizing structured markdown architectural narratives with verified inline `[S#]` citations, 6–8 repo-specific suggested questions, and zero-key deterministic heuristic fallback.
    - Pipeline & Incremental Sync: Integrated Stage 9 (`graph`, 90 -> 95%) and Stage 10 (`overview`, 95 -> 100%) into `IngestionPipeline` and `IncrementalSyncService` with snapshot file metrics bulk persistence.
    - API Endpoints: Fully typed OpenAPI endpoints mounted at `GET /api/v1/repos/{id}/overview`, `POST /api/v1/repos/{id}/overview/regenerate`, `GET /api/v1/repos/{id}/graph`, and `GET /api/v1/repos/{id}/stats`. Integration verified in `test_graph_overview.py`.
    - Frontend Architecture & Visual Graph: Interactive `OverviewPage.tsx` with dynamic `[S#]` citations, tech stack chips, language breakdown bar, stat counters, entry points table, suggested questions, and regenerator button; interactive `GraphPage.tsx` with `@xyflow/react`, `elkjs` hierarchical auto-layout, directory cluster filtering, centrality metrics, cycle warnings, and detail inspection drawer. 6/6 Vitest tests passing in `overview.test.ts` and `graph.test.ts`.
    - Quality Gates: All 175 backend pytest tests passing (100%); `ruff check` and `ruff format` 100% clean; `mypy backend/app` clean across 137 source files; frontend `tsc -b` and `vite build` passing with 0 errors.
  - Known issues: None

- [ ] **M8: Evaluation**
  - Scope: Benchmark schema/upload, built-in benchmarks (TaskFlow 30 Q, requests 15 Q), metrics, runner job + CLI, exports, `eval-report`, live metrics; frontend Evaluation pages (all tabs except Code review).
  - Exit criteria: Eval run on TaskFlow completes for all 5 strategies; charts render; CSV/MD export works; slow eval thresholds met.
  - Status: Pending
  - Verification:
  - Known issues: None

- [ ] **M9: Phase 1 gate — hardening**
  - Scope: Authz enumeration test, full security checklist (§11) review, XSS tests, E2E suite, performance pass (bundle size, lazy loading, query indexes), accessibility pass, admin pages, docs for Phase 1, screenshots.
  - Exit criteria: All tests + E2E green; security checklist items each verified and ticked in PROGRESS.md; Phase 1 usable end to end with `FEATURE_PR_REVIEW=false`.
  - Status: Pending
  - Verification:
  - Known issues: None

- [ ] **M10: Phase 2 — PR review**
  - Scope: GitHub PR fetcher, diff upload, diff parser, symbol mapper, context retrieval, static analysis, review LangGraph, validation, findings workflow, export, publish, webhook, seeded patches + review evaluation; frontend Reviews pages + Code review eval tab.
  - Exit criteria: All 6 seeded patches reviewed via diff upload; detection recall reported; publish tested against mocked GitHub API; webhook HMAC tests pass.
  - Status: Pending
  - Verification:
  - Known issues: None

- [ ] **M11: Production & delivery**
  - Scope: Prod Compose, Caddy image/Caddyfile, hardening flags, monitoring profile, Ollama profile, CI security + deploy workflows, EC2 bootstrap/deploy/backup/restore scripts, Dependabot.
  - Exit criteria: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up` works locally on `:80` with security headers verified by `curl -I`; images run as non-root; Trivy clean of fixable CRITICALs.
  - Status: Pending
  - Verification:
  - Known issues: None

- [ ] **M12: Finalisation**
  - Scope: Complete all docs (§19) and report assets, README screenshots, `make eval-report` results committed, Definition of Done (§21), self-audit (§22).
  - Exit criteria: Every DoD item ticked with evidence.
  - Status: Pending
  - Verification:
  - Known issues: None
