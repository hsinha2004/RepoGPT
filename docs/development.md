# RepoGPT — Developer & Contributor Guide

This guide describes how to set up the local development environment, run test suites and quality gates, add new tree-sitter language extractors, and integrate custom LLM/embedding providers.

---

## 1. Prerequisites

- **Python**: 3.12 or newer
- **Node.js**: 22 or newer (with npm)
- **Package Manager**: `uv` for Python (`pip install uv`)
- **Docker & Docker Compose**: v2.20+ (optional for native local execution, required for containerized dev)

---

## 2. Quickstart Setup

### Automated Setup via Makefile
```bash
make setup
```
This generates cryptographically secure secrets in `.env` using `scripts/generate_secrets.py` and installs git pre-commit hooks.

### Environment Configuration
Edit `.env` to configure your preferred LLM provider:
```bash
# Offline zero-key mode (works out of the box for tests and local development)
LLM_PROVIDER=fake
EMBEDDING_PROVIDER=fake
RERANKER_PROVIDER=fake

# Or real LLM provider (Gemini, Anthropic, OpenAI, Groq, Ollama)
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
```

### Running with Docker Compose
```bash
make dev
```
Starts backend API (`http://localhost:8000`), Celery worker, MongoDB (`localhost:27017`), Redis (`localhost:6379`), ChromaDB (`localhost:8001`), and Vite frontend with hot reload (`http://localhost:5173`).

### Seeding Initial Data
```bash
make seed
```
Creates default administrator account (`admin@repogpt.local` / `AdminPassword123!`) and indexes the TaskFlow fixture repository.

---

## 3. Running Locally Without Docker

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Or .\.venv\Scripts\Activate.ps1 on Windows
uv pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm ci
npm run dev
```

---

## 4. Quality Gates & Test Commands

Every pull request must pass the automated quality gates:

```bash
# Run all backend unit & integration tests (192 tests)
make test-backend

# Run frontend unit tests (24 tests)
make test-frontend

# Run linting (Ruff for Python, ESLint for TypeScript)
make lint

# Run type checking (strict Mypy for backend, tsc for frontend)
make typecheck

# Code formatting
make fmt

# End-to-end Playwright tests
make e2e
```

---

## 5. Adding a New Language Extractor

RepoGPT uses `tree-sitter` for AST parsing. To add support for a new programming language (e.g. Ruby, Java, C++):

1. **Add tree-sitter grammar package** to `backend/pyproject.toml` (e.g., `tree-sitter-java>=0.23.0`).
2. **Create extractor class** in `backend/app/services/parser/extractors/`:
   ```python
   from app.services.parser.base import BaseExtractor, ExtractedSymbol

   class JavaExtractor(BaseExtractor):
       language_name = "java"

       def extract_symbols(self, code: str, path: str) -> list[ExtractedSymbol]:
           tree = self.parser.parse(bytes(code, "utf8"))
           # Execute tree-sitter S-expression query for classes and methods
           ...
           return symbols
   ```
3. **Register extractor** in `backend/app/services/parser/registry.py`:
   ```python
   from app.services.parser.extractors.java import JavaExtractor

   self.register_extractor(".java", JavaExtractor())
   ```
4. **Add unit test** in `backend/tests/unit/test_extractors.py` verifying symbol extraction with exact line numbers.

---

## 6. Adding a New LLM or Embedding Provider

### Adding an LLM Provider
1. Inherit from `BaseLLMProvider` in `backend/app/services/llm/providers/base.py`.
2. Implement `generate_stream(...)` and `generate(...)`.
3. Register the provider name in `backend/app/services/llm/factory.py`.
4. Add pricing and token tracking constants to `backend/app/services/llm/pricing.py`.

### Adding an Embedding Provider
1. Inherit from `BaseEmbeddingProvider` in `backend/app/services/indexing/embeddings/base.py`.
2. Implement `embed_documents(texts: list[str]) -> list[list[float]]` and `embed_query(query: str) -> list[float]`.
3. Register the provider in `backend/app/services/indexing/embeddings/factory.py`.
