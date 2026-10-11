# RepoGPT Architecture Decision Records (ADRs)

This document records architectural decisions made where `docs/SPEC.md` permits options or is silent, following the Context -> Decision -> Consequences structure.

---

## ADR-001: Absence of Email Service
- **Context**: User password resets and account verification typically use an SMTP or third-party email provider (e.g. SendGrid, SES).
- **Decision**: RepoGPT intentionally avoids an external email dependency. Admins generate temporary one-time passwords for users via `/api/v1/admin/users/{user_id}/reset-password`, which sets `must_change_password=True` forcing password change on next login.
- **Consequences**: Zero external email service setup or failure mode; simplified local deployment; full auditability of password resets.

## ADR-002: Dual Vector Store Strategy (ChromaDB + FAISS)
- **Context**: The project proposal specifies "Chroma or FAISS".
- **Decision**: Implement a unified `VectorStore` interface supporting both ChromaDB (default server mode) and FAISS (`IndexFlatIP` file-based mode). Evaluation suite allows direct comparative ablation between them.
- **Consequences**: Flexibility for deployment in resource-constrained or single-binary environments via FAISS, and horizontally scalable vector services via ChromaDB.

## ADR-003: PyMongo Native Async over Motor
- **Context**: PyMongo 4.9+ introduces native `AsyncMongoClient` while Motor is deprecated in modern MongoDB ecosystems.
- **Decision**: Use `pymongo.AsyncMongoClient` directly throughout `app.db.mongo`.
- **Consequences**: Direct compatibility with official MongoDB drivers, avoidance of legacy wrapper bugs, unified connection handling.

## ADR-004: Windows Local Developer Compatibility
- **Context**: The primary development environment is Windows with PowerShell, where Docker Desktop or native CLI tools may vary.
- **Decision**: Tooling supports both Docker containerized execution and local direct execution (`uv` / Python 3.12+ and Node.js v22+ npm/Vite), with cross-platform scripts and Makefile targets.
- **Consequences**: Tests and quality gates run seamlessly on Windows local shell, Linux containers, and GitHub Actions CI.
