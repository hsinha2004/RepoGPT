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

- [ ] **M4: Indexing**
  - Scope: Embedding providers (fastembed, API, fake), embedding cache, Chroma + FAISS stores, BM25 index, incremental sync, deletion cleanup.
  - Exit criteria: TaskFlow fully indexed (`ready`); sync re-embeds only changed files (test); deletion test passes.
  - Status: Pending
  - Verification:
  - Known issues: None

- [ ] **M5: Retrieval & router**
  - Scope: Keyword, vector, hybrid RRF, reranker, symbol lookup, graph expansion hook, summary scope, context builder, heuristic + LLM router; `/search` endpoint; frontend Search playground.
  - Exit criteria: Integration: expected file in top-5 for >= 80% of TaskFlow questions (hybrid); router table tests pass.
  - Status: Pending
  - Verification:
  - Known issues: None

- [ ] **M6: Agentic QA & chat**
  - Scope: LLM provider layer (Anthropic, OpenAI-compatible presets, fake), limiter, pricing, prompts, LangGraph QA graph, SSE streaming, citations, grounding, confidence, conversations, cache, feedback, export; frontend Chat with evidence panel, trace, confidence, stop/regenerate.
  - Exit criteria: SSE integration test passes; with a real provider key, answers cite correct TaskFlow files; offline mode works with no key.
  - Status: Pending
  - Verification:
  - Known issues: None

- [ ] **M7: Graph, analysis & overview**
  - Scope: Import resolvers, heuristic calls, NetworkX metrics, directory aggregation, tech stack, entry points, reading order, overview (LLM + heuristic); frontend Overview and Graph pages.
  - Exit criteria: Graph of TaskFlow shows frontend -> API -> service -> repository -> db chain; overview lists correct stack and entry points.
  - Status: Pending
  - Verification:
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
