# Contributing to RepoGPT

We welcome contributions to RepoGPT!

## Guidelines
1. **Vertical Slices**: All new features must include backend routes, schemas, tests, and frontend UI updates.
2. **Quality Gates**:
   - Backend: `ruff check`, `ruff format --check`, `mypy`, and `pytest`.
   - Frontend: `npm run lint`, `npm run typecheck`, `npm test`, and `npm run build`.
3. **Security**:
   - Never commit secrets or API keys.
   - Run tests with test fixtures that construct fake tokens at runtime.
   - Never execute ingested code.
4. **Git Hygiene**:
   - Use Conventional Commit format: `feat(...)`, `fix(...)`, `docs(...)`, `test(...)`.
