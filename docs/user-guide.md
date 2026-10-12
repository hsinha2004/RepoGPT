# RepoGPT — User & Developer Guide

This guide provides a task-oriented walkthrough for developers, educators, and software teams using **RepoGPT** for codebase understanding, architecture onboarding, and automated pull-request code reviews.

---

## 1. Getting Started & Dashboard

### 1.1 Authentication & Account Management
1. Navigate to `http://localhost:5173` (or your deployed domain).
2. Register an account or log in with the administrator credentials (`admin@repogpt.local` / `AdminPassword123!`).
3. Manage API tokens and GitHub Personal Access Tokens (PAT) in **Settings > Personal Access Tokens**.

---

## 2. Ingesting a Repository

RepoGPT processes codebases from public or private Git repositories or direct ZIP archive uploads.

### Step 1: Ingest via GitHub URL or ZIP
1. On the **Repositories** dashboard, click **Add Repository**.
2. Select your ingestion source:
   - **GitHub Repository**: Enter a GitHub repository URL (e.g., `https://github.com/psf/requests`). For private repositories, configure a GitHub PAT with `repo` scope.
   - **Upload ZIP Archive**: Drag and drop a repository `.zip` archive (up to 50 MB compressed).
3. Click **Start Ingestion**.

### Step 2: Real-time Ingestion Stepper
The live ingestion stepper streams progress across five phases:
1. `downloading` / `extracting`: Secure sandbox extraction.
2. `filtering`: Respects `.gitignore` and ignores binary assets and dependencies (`node_modules`, `.venv`).
3. `parsing`: Tree-sitter AST extraction of symbols and automated secret redaction.
4. `indexing`: Vector embedding generation, BM25 indexing, and NetworkX dependency graph construction.
5. `ready`: Repository is ready for instant Q&A, graph exploration, and code reviews.

---

## 3. Codebase Onboarding & Overview

Navigate to **Overview** to understand an unfamiliar repository in minutes:
- **Tech Stack Chips**: Automatically detected languages, frameworks, databases, and build systems.
- **Entry Points Table**: Primary application bootstrap files (e.g., `app/main.py`, `src/index.tsx`) with their architectural roles.
- **Key Modules & Reading Order**: Recommended step-by-step reading order for new contributors.
- **Suggested Questions**: Click any suggested question to immediately open a grounded chat.

---

## 4. Interactive Agentic Chat & Q&A

RepoGPT answers natural-language engineering questions with verifiable code citations.

### 4.1 Asking Questions
Ask complex questions about control flow and architecture:
- *"Where is JWT token validation implemented, and how are expired tokens handled?"*
- *"Trace the lifecycle of an incoming review request from HTTP router to MongoDB."*
- *"Does this repository use connection pooling for database operations?"*

### 4.2 Citations & Deep Linking
- Every factual claim is backed by inline citation tags (e.g. `[S1]`, `[S2]`).
- Clicking a citation opens the exact file in the code viewer, automatically scrolling and highlighting the referenced line range.
- The **Evidence Panel** displays the raw retrieved snippets, strategy used, and similarity scores.
- The **Confidence Badge** reports calibrated certainty (High, Medium, Low) with an explanation breakdown.

---

## 5. Visual Code Explorer & Dependency Graph

### 5.1 Code Explorer
- **Hierarchical Tree**: Browse directories and files with file size and line counts.
- **Symbol Outline**: Fast-jump to classes, methods, and functions parsed by tree-sitter.
- **Redaction Shield**: Sensitive secrets (API keys, private keys, database passwords) are automatically obfuscated with `[REDACTED_SECRET]`.

### 5.2 Interactive Dependency Graph
- **Hierarchical Layout**: Rendered via `@xyflow/react` and `elkjs` layout engine.
- **Cluster Filtering**: Toggle internal vs external dependencies, or focus on specific directories.
- **Cycle & Centrality Analysis**: Highlights circular dependency loops and ranks architectural hubs.

---

## 6. Context-Aware Pull Request Review (Phase 2)

RepoGPT delivers human-centric code reviews that examine changes in the context of the whole repository.

### 6.1 Creating a Review
1. Navigate to **Reviews** inside your repository.
2. Trigger a review using one of two methods:
   - **GitHub Pull Request URL**: Enter the URL of any open PR (e.g., `https://github.com/org/repo/pull/42`).
   - **Upload Diff / Patch**: Drag and drop a unified `.diff` or `.patch` file.
3. Automated GitHub Webhooks can also trigger reviews automatically upon PR creation or push.

### 6.2 Review Walkthrough & Findings Triage
- **Executive Risk Level**: Rated as `low`, `medium`, `high`, or `critical`.
- **Walkthrough Summary**: High-level explanation of changed behaviors.
- **Anchored Findings**: Static checks (Ruff E9/F/B/S) and semantic findings anchored to exact modified lines.
- **Finding Curation**:
  - Click **Accept** to approve a finding for publishing.
  - Click **Reject** to dismiss false positives.
  - Click **Edit** to adjust title, severity, or notes before publishing.

### 6.3 Publishing to GitHub
1. Click **Publish Review**.
2. RepoGPT publishes only **Accepted** findings as a single GitHub review with line-level comments.
3. **Safety Guarantee**: RepoGPT *never* approves, merges, or pushes code. It only submits informative `COMMENT` reviews for human peer review.
4. Export the entire review report as Markdown or JSON anytime.
