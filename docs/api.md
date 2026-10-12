# RepoGPT — REST API & Server-Sent Events Reference

This document provides a narrative reference for the RepoGPT REST API (`/api/v1`) and Server-Sent Events (SSE) streaming protocols per §7 and §12 of the system specification.

---

## 1. OpenAPI Specification & Interactive Documentation

RepoGPT automatically publishes its complete, strongly-typed OpenAPI 3.1 specification:
- **Interactive Swagger UI**: `http://localhost:8000/docs` (or via Caddy at `https://your-domain/docs` in development mode)
- **OpenAPI Schema (JSON)**: `http://localhost:8000/api/openapi.json`
- **TypeScript Type Definitions**: Synchronized directly into `frontend/src/api/schema.d.ts`

---

## 2. Authentication & Security Baseline (§7.4, §11)

### 2.1 Token Architecture
- **Access Tokens**: Short-lived (15 minutes) JSON Web Tokens (JWT) signed with HMAC-SHA256. Sent via `Authorization: Bearer <token>` header.
- **Refresh Tokens**: Long-lived (7 days) cryptographically random tokens stored in secure, `HttpOnly`, `SameSite=Strict` cookies scoped to `/api/v1/auth`. Features automatic reuse detection and immediate family revocation upon breach (§11.2).
- **Anti-CSRF Protection**: State-changing requests (`POST`, `PUT`, `PATCH`, `DELETE`) require the `X-CSRF-Token` header matching the user's session token.

### 2.2 Anti-Enumeration Behavior (§7.5, §11.7)
To completely prevent user-enumeration and repository-probing attacks:
- Requests lacking authentication credentials receive `401 Unauthorized`.
- Requests from authenticated users attempting to access non-existent or unauthorized resources receive identical `404 Not Found` responses.

---

## 3. Server-Sent Events (SSE) Protocol (§9.4, §12.4)

RepoGPT utilizes SSE for real-time ingestion progress and streaming LLM token generation. Caddy is configured with `flush_interval -1` to disable proxy buffering.

### 3.1 Ingestion Job Progress Stream (`GET /api/v1/jobs/{job_id}/stream`)

```
event: progress
data: {"stage": "parsing", "progress": 45, "message": "Parsing AST symbols in 120 files"}

event: completed
data: {"stage": "ready", "progress": 100, "message": "Repository indexed successfully"}
```

### 3.2 Chat & QA Stream (`POST /api/v1/repos/{repo_id}/chat/stream`)

```
event: token
data: {"token": "Authentication"}

event: token
data: {"token": " is"}

event: token
data: {"token": " implemented in "}

event: citation
data: {"source_id": "S1", "path": "backend/app/core/security.py", "lines": [25, 45]}

event: confidence
data: {"score": 0.94, "category": "high", "reasons": ["Direct symbol match", "Verified citation bounds"]}

event: done
data: {"conversation_id": "607f1f77bcf86cd799439011", "message_id": "607f1f77bcf86cd799439022"}
```

---

## 4. API Catalogue Overview

### Authentication (`/api/v1/auth`)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Register new user account with Argon2 password hashing |
| `POST` | `/api/v1/auth/login` | Authenticate user, set refresh cookie, return access token |
| `POST` | `/api/v1/auth/refresh` | Rotate refresh token and issue new access token |
| `POST` | `/api/v1/auth/logout` | Revoke active session and clear cookies |
| `GET` | `/api/v1/auth/me` | Fetch authenticated user profile and quota usage |

### Repositories & Ingestion (`/api/v1/repos`)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/repos` | List accessible repositories |
| `POST` | `/api/v1/repos` | Ingest repository via public/private GitHub URL or ZIP upload |
| `GET` | `/api/v1/repos/{id}` | Get repository details, indexing state, and stats |
| `DELETE` | `/api/v1/repos/{id}` | Delete repository, snapshots, symbols, and vector indices |
| `POST` | `/api/v1/repos/{id}/sync` | Trigger incremental sync against new Git commit |

### Code Exploration & Dependency Graph
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/repos/{id}/files` | Hierarchical file tree with AST symbol outlines |
| `GET` | `/api/v1/repos/{id}/files/{path}` | Syntax-highlighted file content with redacted secrets |
| `GET` | `/api/v1/repos/{id}/graph` | NetworkX dependency graph with centrality and cycle detection |
| `GET` | `/api/v1/repos/{id}/overview` | Architecture summary, tech stack, and reading order |

### Context-Aware Code Review (`/api/v1/reviews`)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/repos/{id}/reviews` | Trigger automated review via PR URL or multipart `.diff` |
| `GET` | `/api/v1/repos/{id}/reviews` | List past code reviews for repository |
| `GET` | `/api/v1/reviews/{id}` | Get review walkthrough, risk score, and findings |
| `PATCH`| `/api/v1/reviews/{id}/findings/{f_id}` | Accept, reject, or edit review finding |
| `POST` | `/api/v1/reviews/{id}/publish` | Publish accepted findings to GitHub (COMMENT review) |
| `GET` | `/api/v1/reviews/{id}/export` | Export review report as Markdown or JSON |

### GitHub Webhooks (`/api/v1/webhooks`)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/webhooks/github` | Ingest GitHub PR webhooks with HMAC-SHA256 signature verification |

### Evaluation & Telemetry (`/api/v1/eval`)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/eval/benchmarks` | List built-in and uploaded benchmarks |
| `POST` | `/api/v1/eval/estimate` | Estimate pre-flight token, cost, and time requirements |
| `POST` | `/api/v1/eval/runs` | Launch multi-strategy evaluation run |
| `GET` | `/api/v1/eval/runs/{id}` | Retrieve run metrics, calibration diagrams, and question traces |
| `GET` | `/api/v1/eval/reviews` | Benchmark metrics on 6 seeded patches |
