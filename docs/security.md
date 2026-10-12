# RepoGPT — Security Architecture & Threat Model

**Document Version:** 1.0.0 (Phase 1 Gate — Hardening)  
**Specification References:** `docs/SPEC.md` §11, §12, §20  
**Authors:** Harsh Sinha, Anshuman Patel  
**Supervisor:** Dr. Archana Kumari  

---

## 1. Executive Summary & Security Philosophy

RepoGPT processes untrusted, third-party codebases, parses source files into ASTs, indexes symbols and chunks, and routes natural-language prompts to Large Language Models. Because an application processing arbitrary user source code is uniquely vulnerable to malicious payloads (zip-bombs, path traversal, prompt injection, and remote code execution), RepoGPT operates under a **Zero-Trust, Zero-Code-Execution** architectural model:

1. **Never Execute Code from Ingested Repositories:** Code from user repositories is never compiled, executed, tested, or dynamically imported. Tree-sitter performs purely static AST parsing in unprivileged container environments.
2. **Anti-Enumeration by Default:** Authorization failures on scoped resources return `404 Not Found` rather than `403 Forbidden` to prevent malicious attackers from probing the existence of private repositories, conversations, or jobs.
3. **Defense-in-Depth for Untrusted Text:** Multi-tier defenses guard against prompt injection, cross-site scripting (XSS), secret leaks, and server-side request forgery (SSRF).
4. **Local-First Privacy Option:** Full offline operation via `LLM_PROVIDER=ollama` or deterministic `fake` providers with ONNX `FastEmbed` ensures that source code never leaves the host environment.

---

## 2. STRIDE Threat Model

The following STRIDE matrix details the threat profile of RepoGPT, the associated attack vectors, and the technical countermeasures implemented across the architecture.

| Threat Category | Attack Vector / Scenario | Impact | Implemented Countermeasure | Verification |
|---|---|---|---|---|
| **Spoofing** | Forged JWT access tokens or spoofed user identity | Unauthorized access to user account and private repositories | Asymmetric/HMAC HMAC-SHA256 signature verification (`JWT_SECRET` $\ge 64$ bytes), 15-minute access token TTL, argon2id password hashing, constant-time token comparison. | `test_auth_service.py` |
| **Spoofing** | GitHub Webhook forgery (`POST /api/v1/webhooks/github`) | Triggering unauthorized ingestion, re-indexing, or fake reviews | Cryptographic HMAC-SHA256 signature verification using `GITHUB_WEBHOOK_SECRET` before parsing payload. Delivery ID deduplication in Redis. | `test_auth_api.py`, `deps.py` |
| **Spoofing** | Replaying stolen refresh tokens | Persistent unauthorized session hijacking | Rotating refresh token families. Detection of refresh token reuse instantly revokes the entire family across all sessions. | `test_auth_service.py` |
| **Tampering** | Path Traversal / Zip Slip in repository archive extraction (`../../etc/passwd`) | Overwriting critical system files or planting backdoors | Strict canonical path verification in `extract_archive_safely()`. Rejection of relative paths (`..`), absolute paths, drive letters (`C:`), symlinks, hardlinks, and device nodes. | `test_archive_security.py` |
| **Tampering** | Prompt Injection via ingested repository files (e.g. comments, docstrings, README) | Hijacking LLM instructions to leak secrets, bypass guardrails, or hallucinate findings | Strict instruction hierarchy in system prompts. User content isolated inside `<source>` delimiters with delimiter escaping (`</source>` replaced). Non-side-effecting QA agent. Inline citations verified against retrieved chunks. | `test_llm_providers.py`, `test_citations_and_confidence.py` |
| **Tampering** | Cross-Site Request Forgery (CSRF) on state-modifying requests | Unauthorized account updates or repo deletions via victim's browser | Double-submit CSRF cookie pattern (`rg_csrf`), `SameSite=Strict`, `HttpOnly` on session refresh cookies. | `test_auth_api.py` |
| **Repudiation** | User denies performing sensitive action (repo deletion, role change, review publish) | Inability to audit security incidents or maintain compliance | Comprehensive structured audit log (`audit_events` collection) recording timestamps, IP hashes, user IDs, actions, and resource IDs with offline fallback. | `audit.py`, `test_auth_service.py` |
| **Information Disclosure** | Insecure Direct Object References (IDOR) on `{repo_id}`, `{conversation_id}`, `{job_id}` | Attacker enumerates or accesses private repositories or conversations | Strict repository membership check in `require_repo_access()`. Unauthorized requests return `404 Not Found` (Anti-Enumeration). | `test_authz_enumeration.py` |
| **Information Disclosure** | Stored hardcoded secrets (API keys, PEM certificates, tokens) in source code | Exposure of secrets in vector store, search results, or LLM context | Automated secret redaction pipeline stage using high-entropy detectors and table-driven patterns (AWS, GitHub, Stripe, OpenAI, Slack, PEM, connection strings). Replaced with `[REDACTED_SECRET:type]` preserving line offsets. | `test_redaction.py` |
| **Information Disclosure** | Cross-Site Scripting (XSS) via rendered Markdown or code snippets in Chat / Overview | Execution of arbitrary JavaScript in user browser; cookie/token theft | `react-markdown` strictly filtered with `rehype-sanitize`. External links enforced with `rel="noopener noreferrer nofollow"`. `javascript:`, `data:`, and `vbscript:` URLs stripped. Code syntax highlighted safely via text output. | `xss.test.tsx` |
| **Information Disclosure** | Server-Side Request Forgery (SSRF) via repository clone URLs | Probing internal networks, AWS metadata service (`169.254.169.254`), or private services | Strict regex validation (`https://github.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+`). Requests routed exclusively to fixed `GITHUB_API_URL`. Redirects restricted to `codeload.github.com`. LLM base URLs configured exclusively via environment. | `test_github_fetcher.py` |
| **Denial of Service** | Decompression bombs ("Zip Bombs") or multi-gigabyte archives | Disk exhaustion, memory exhaustion, worker crash | Strict thresholds: max upload 100MB, max uncompressed 600MB, max compression ratio 100:1, max 30,000 archive entries. Stream-level counting during extraction. | `test_archive_security.py` |
| **Denial of Service** | Brute-force credential guessing | Account takeover | 10 consecutive failed login attempts trigger automated 15-minute account lockout. Generic error messages prevent user enumeration. | `test_auth_service.py` |
| **Denial of Service** | API flooding or LLM credit depletion | Service unavailability and high operational costs | Redis sliding-window rate limiting (`120 req/min` for API, `20 req/min` for search, `10 req/min` for LLM). User daily quotas tracked per organization. | `test_rate_limiter.py` |
| **Elevation of Privilege** | Normal user executing admin endpoints (`/admin/users`, `/admin/jobs/retry`) | Administrative takeover | RBAC middleware enforcing `require_role("admin")`. Normal users denied with `403 Forbidden` on admin APIs. | `test_authz_enumeration.py` |
| **Elevation of Privilege** | Container escape from worker parsing untrusted code | Compromise of host system | Containers run as unprivileged non-root user (UID `10001`), `cap_drop: [ALL]`, `no-new-privileges: true`, read-only root filesystems where possible, memory/CPU limits. | `docker-compose.yml`, `docker-compose.prod.yml` |

---

## 3. Controls Checklist (§11)

The following checklist tracks implementation and enforcement of all mandatory security controls specified in §11:

- [x] **1. Input Validation:** Pydantic v2 models validate every request body and query parameter with explicit constraints (string lengths, enum choices, regex). Request body size limits enforced at Caddy proxy (100MB upload, 10MB default) and ASGI middleware.
- [x] **2. SSRF Defenses:** Strict GitHub repository URL regex (`^https://github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)/?$`). All outbound GitHub REST calls use hardcoded `GITHUB_API_URL`. HTTP redirects permitted only to `codeload.github.com`. LLM/embedding base URLs come strictly from server environment configuration.
- [x] **3. Archive Safety:** Multi-layered defense in `extract_archive_safely()` against directory traversal (`..`), path escaping, absolute paths, drive letters, symlinks, device nodes, and zip-bombs (>100:1 compression ratio).
- [x] **4. Zero Code Execution:** Strict adherence to specification Rule 10: Ingested repositories are parsed statically via tree-sitter. Code is never built, installed, or imported into the runtime environment.
- [x] **5. Secret Redaction:** Table-driven secret detectors (AWS, GitHub, GitLab, Slack, Google, Stripe, OpenAI, Anthropic, Twilio, SendGrid, PEM blocks, connection strings, and generic high-entropy strings $\ge 3.5$) redact credentials before files are indexed, embedded, stored, or passed to LLMs.
- [x] **6. Authentication & Session Security:** Argon2id password hashing with unique salts, short-lived 15-minute access tokens, cryptographically secure rotating refresh tokens with family theft detection, `HttpOnly` `SameSite=Strict` cookies, double-submit CSRF tokens, 10-attempt lockout, and constant-time token comparison.
- [x] **7. Authorization & Anti-Enumeration:** Strict role-based repository scoping. Denials on private or non-existent resources return `404 Not Found`. Dynamic test `test_authz_enumeration.py` automatically discovers and validates all scoped routes in the application.
- [x] **8. Secrets at Rest:** Personal Access Tokens (PATs) encrypted using Fernet (AES-128-CBC + HMAC-SHA256). Refresh tokens hashed with SHA-256 before database storage. No secrets logged or emitted in API responses or bundle artifacts.
- [x] **9. Prompt-Injection Defenses:** Strict instruction hierarchy separating system instructions from untrusted repository snippets. Untrusted code encapsulated within `<source>` blocks with delimiter escaping (`</source>`). QA agent has no destructive or state-modifying tools. Inline citations validated against retrieved sources.
- [x] **10. XSS Prevention:** Markdown rendered with `react-markdown` sanitized via `rehype-sanitize`. External hyperlinks receive `rel="noopener noreferrer nofollow"` and `target="_blank"`. Pseudo-protocols (`javascript:`, `data:`, `vbscript:`) stripped. Code rendered via text Shiki highlighter. Verified by `xss.test.tsx`.
- [x] **11. HTTP Security Headers:** Strict headers configured in proxy and middleware:
  ```http
  Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://avatars.githubusercontent.com; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self' https://github.com; object-src 'none'
  Strict-Transport-Security: max-age=31536000; includeSubDomains
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  ```
- [x] **12. CORS Policy:** Strict same-origin policy in production (Caddy handles reverse proxying). Explicit `CORS_ORIGINS` whitelist in development with credentials and explicit method controls.
- [x] **13. Rate Limiting & Webhook Verification:** Redis sliding-window limiters protect all public routes. GitHub webhooks require HMAC-SHA256 signature verification prior to JSON parsing.
- [x] **14. API Documentation Protection:** Swagger UI (`/api/docs`) and OpenAPI schema (`/api/openapi.json`) disabled in production unless requester holds the `admin` role.
- [x] **15. Comprehensive Audit Logging:** Events logged for registration, authentication successes/failures, lockouts, token family revocations, PAT updates, repo creations/deletions, member modifications, and admin overrides.
- [x] **16. Cascading Data Deletion:** Deleting a repository atomically purges all MongoDB documents (repositories, files, symbols, chunks, jobs), vector collections in Chroma/FAISS, disk snapshots, and BM25 search indices. Verified in `test_sync_and_deletion.py`.
- [x] **17. Supply Chain & Vulnerability Scanning:** CI workflows incorporate `pip-audit`, `npm audit --audit-level=high`, Bandit static analysis, gitleaks secret detection, and Trivy container vulnerability scanning.
- [x] **18. Container Hardening:** Multi-stage builds, non-root users (`UID 10001`), `cap_drop: [ALL]`, `security_opt: ["no-new-privileges:true"]`, `read_only: true` root filesystems, resource memory/CPU caps, and database network isolation.
- [x] **19. Privacy & Local-First Mode:** Complete offline capability via `LLM_PROVIDER=ollama` or deterministic `FakeProvider` and local ONNX FastEmbed models where no source code ever leaves the local environment.

---

## 4. Privacy & Data Handling Disclosures

RepoGPT handles source code with explicit data boundary transparency:
- **Cloud LLM Providers (OpenAI, Anthropic, Gemini, Groq, OpenRouter):** When configured with cloud provider keys, retrieved source snippets and user queries are transmitted over encrypted HTTPS to provider APIs. Note that free-tier API accounts may be subject to provider telemetry or data logging per their respective terms of service.
- **Enterprise / Offline Local Mode:** Setting `LLM_PROVIDER=ollama` (or `fake`) and `EMBEDDING_PROVIDER=fastembed` ensures that 100% of parsing, embedding, vector search, and answer generation executes entirely on the local machine with zero network egress.
- **User Interface Transparency:** The "Add Repository" dialog prominently displays the active provider (e.g., *"Code snippets will be processed via: Gemini API"* or *"Code snippets processed locally: Ollama"*).

---

## 5. Security Contacts & Vulnerability Disclosure

Security reports are handled with high priority according to the policy in `SECURITY.md`.
Please report security issues directly to the development team:
- **Lead Maintainer:** Harsh Sinha (`security@repogpt.local`)
- **Core Maintainer:** Anshuman Patel
- **Faculty Guide:** Dr. Archana Kumari, Department of Computer Science, UPES

We pledge to acknowledge reports within 48 hours and provide remediation patches within 7 business days.
