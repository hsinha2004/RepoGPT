## Description
<!-- Provide a clear description of changes made and why -->

## Related Milestone
- [ ] M0: Foundation
- [ ] M1: Auth & Security Baseline
- [ ] M2: Ingestion & Jobs
- [ ] M3: Parsing, Redaction, Chunking
- [ ] M4: Indexing
- [ ] M5: Retrieval & Router
- [ ] M6: Agentic QA & Chat
- [ ] M7: Graph, Analysis & Overview
- [ ] M8: Evaluation
- [ ] M9: Phase 1 Gate — Hardening
- [ ] M10: Phase 2 — PR Review
- [ ] M11: Production & Delivery
- [ ] M12: Finalisation

## Quality Checklist
- [ ] Backend tests pass (`pytest`) with >=80% coverage
- [ ] Backend linter clean (`ruff check` and `ruff format --check`)
- [ ] Backend typecheck clean (`mypy`)
- [ ] Frontend tests pass (`vitest`)
- [ ] Frontend typecheck clean (`tsc --noEmit`)
- [ ] Frontend build succeeds (`npm run build`)
- [ ] No realistic secrets committed (`gitleaks`)
- [ ] No TODO/FIXME placeholders left in production code paths
