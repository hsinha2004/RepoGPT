# RepoGPT — Agentic AI Codebase Intelligence & Autonomous Code Review

[![CI](https://github.com/repogpt/repogpt/actions/workflows/ci.yml/badge.svg)](https://github.com/repogpt/repogpt/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![React 19](https://img.shields.io/badge/React-19-61dafb.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![MongoDB 8](https://img.shields.io/badge/MongoDB-8.0-47A248.svg)](https://www.mongodb.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-StateGraph-FF6F00.svg)](https://langchain-ai.github.io/langgraph/)

> **RepoGPT** is an agentic, production-grade artificial intelligence platform engineered for deterministic codebase understanding, automated developer onboarding, and context-aware pull-request code review. Built on concrete syntax trees (Tree-sitter AST), multi-tier indexing (Vector, BM25, and Dependency Graphs), and stateful LangGraph agentic workflows, RepoGPT synthesizes natural-language code explanations grounded with **verifiable inline citations down to exact files and line numbers**.

---

## 👥 Academic & Project Metadata

| Field | Detail |
|---|---|
| **Institution** | School of Computer Science, University of Petroleum and Energy Studies (UPES), Dehradun, India |
| **Programme** | Bachelor of Technology in Computer Science & Engineering (Specialisation in Data Science) |
| **Course** | Major Project (Final Year Capstone) |
| **Project Title** | RepoGPT: An Agentic AI System for Codebase Understanding, Developer Onboarding, and Intelligent Code Review |
| **Team Members** | **Harsh Sinha** (SAP ID: 500120229) <br> **Anshuman Patel** (SAP ID: 500122770 |
| **Project Supervisor** | **Dr. Archana Kumari**, Associate Professor, School of Computer Science, UPES |
| **Academic Year** | 2026 – 2027 |

---

## 📑 Table of Contents

1. [Executive Summary & Problem Statement](#1-executive-summary--problem-statement)
2. [Software Requirements Specification (SRS — IEEE 830)](#2-software-requirements-specification-srs--ieee-830)
   - [2.1 Purpose, Scope & Definitions](#21-purpose-scope--definitions)
   - [2.2 User Classes & Personas](#22-user-classes--personas)
   - [2.3 Functional Requirements (FR-01 to FR-12)](#23-functional-requirements-fr-01-to-fr-12)
   - [2.4 Non-Functional Requirements (NFR-01 to NFR-08)](#24-non-functional-requirements-nfr-01-to-nfr-08)
   - [2.5 System Constraints & Design Assumptions](#25-system-constraints--design-assumptions)
3. [System Architecture & Engineering Design](#3-system-architecture--engineering-design)
   - [3.1 High-Level Architecture Topology](#31-high-level-architecture-topology)
   - [3.2 Deterministic Ingestion & AST Parsing Activity Flow](#32-deterministic-ingestion--ast-parsing-activity-flow)
   - [3.3 LangGraph Agentic RAG State Machine](#33-langgraph-agentic-rag-state-machine)
   - [3.4 Context-Aware PR Review Sequence](#34-context-aware-pr-review-sequence)
   - [3.5 Data Models & MongoDB Schemas](#35-data-models--mongodb-schemas)
4. [Mathematical Formulations & Algorithmic Foundations](#4-mathematical-formulations--algorithmic-foundations)
   - [4.1 Reciprocal Rank Fusion (RRF)](#41-reciprocal-rank-fusion-rrf)
   - [4.2 Four-Factor Confidence Calibration](#42-four-factor-confidence-calibration)
   - [4.3 Information Retrieval & Calibration Metrics](#43-information-retrieval--calibration-metrics)
5. [Technology Stack & Architectural Trade-off Analysis](#5-technology-stack--architectural-trade-off-analysis)
6. [Empirical Results & Benchmark Validation](#6-empirical-results--benchmark-validation)
   - [6.1 TaskFlow 30Q Codebase Ground Truth Evaluation](#61-taskflow-30q-codebase-ground-truth-evaluation)
   - [6.2 Phase 2 Seeded Vulnerability PR Review Suite](#62-phase-2-seeded-vulnerability-pr-review-suite)
7. [Installation, Reproduction & Operations Guide](#7-installation-reproduction--operations-guide)
   - [7.1 Prerequisites](#71-prerequisites)
   - [7.2 Quickstart in 4 Steps](#72-quickstart-in-4-steps)
   - [7.3 Environment Configuration Reference](#73-environment-configuration-reference)
   - [7.4 Quality Gates & Automated Verification](#74-quality-gates--automated-verification)
8. [Documentation Index & Project Report Artifacts](#8-documentation-index--project-report-artifacts)
9. [Scholarly References (IEEE Format)](#9-scholarly-references-ieee-format)

---

## 1. Executive Summary & Problem Statement

### 1.1 The Industry Problem
In contemporary software engineering organizations and open-source ecosystems, developers spend up to **60% of their engineering time** reading, tracing, and understanding unfamiliar codebases rather than writing new business logic. This cognitive friction is exacerbated by:
1. **Lack of Verifiable Grounding in Generic LLMs:** Standard general-purpose LLMs (e.g., vanilla ChatGPT, Claude) suffer from hallucinated API contracts, nonexistent function signatures, and stale parametric knowledge when queried about private, domain-specific repositories.
2. **Context Window Exhaustion:** Complex multi-service repositories span hundreds of thousands of lines of code, far exceeding effective attention limits of large context windows.
3. **Absence of Line-Level Traceability:** Typical retrieval-augmented generation (RAG) platforms output unverified conversational prose without verifiable citations linking claims to exact file paths and line ranges.
4. **Context-Blind Code Reviews:** Conventional CI/CD static linters (Ruff, ESLint, SonarQube) detect syntactic or local stylistic defects, but cannot reason about cross-file behavioral regressions, breaking caller contracts, or semantic security vulnerabilities introduced in Pull Requests.

### 1.2 The RepoGPT Solution
RepoGPT addresses these challenges through a two-phased, agentic architecture:
- **Phase 1: Deterministic Codebase Intelligence & Onboarding:** Ingests repositories via GitHub REST tarballs or zip archives, parses concrete syntax trees (Tree-sitter AST) across 5 primary programming languages, extracts structural symbol hierarchies, purges exposed secrets prior to indexing, and constructs dual vector stores (ChromaDB / FAISS), sparse lexical indices (`bm25s`), and dependency call graphs (NetworkX). A LangGraph state machine orchestrates adaptive query routing, hybrid Reciprocal Rank Fusion, cross-encoder reranking, context sufficiency validation, and streaming answers with strictly verified `[S#]` citations and calibrated confidence scores.
- **Phase 2: Context-Aware Autonomous Pull Request Review:** Ingests unified git diffs, maps touched hunks to AST symbols, retrieves the blast-radius caller hierarchy, evaluates cross-file semantic impact, performs automated static analysis (Ruff, Bandit), flags security and logic defects, and enforces a **Human-in-the-Loop** verification workflow prior to publishing comments to GitHub.

---

## 2. Software Requirements Specification (SRS — IEEE 830)

### 2.1 Purpose, Scope & Definitions
- **Purpose:** Specifies the functional and non-functional requirements for the RepoGPT system, serving as the formal reference for system implementation, acceptance testing, and academic project evaluation.
- **Scope:** Covers repository ingestion, parsing, multi-index persistence, agentic question-answering, graph visualization, empirical evaluation, and human-in-the-loop PR review.
- **Acronyms & Definitions:**
  - **AST (Abstract Syntax Tree):** A structural tree representation of the abstract syntactic structure of source code.
  - **RAG (Retrieval-Augmented Generation):** Enhancing LLM prompts with relevant external documents retrieved from an indexed knowledge base.
  - **RRF (Reciprocal Rank Fusion):** An rank aggregation algorithm combining disparate retrieval scores without score normalization.
  - **MRR (Mean Reciprocal Rank):** Statistical measure evaluating the position of the first relevant retrieved document.
  - **nDCG (Normalized Discounted Cumulative Gain):** Measure of ranking quality accounting for the graded relevance of items and their positions.
  - **ECE (Expected Calibration Error):** Difference in expectation between confidence and accuracy.
  - **PAT (Personal Access Token):** GitHub authentication credential used for API interactions.
  - **SSE (Server-Sent Events):** Monodirectional HTTP streaming protocol for real-time token transmission.

### 2.2 User Classes & Personas
1. **Junior Developer / Onboarding Engineer:** Needs high-level architecture overviews, guided reading orders, and conversational Q&A to navigate unfamiliar codebases quickly.
2. **Senior Engineer / Code Reviewer:** Inspects complex dependencies, executes cross-file impact analysis, and reviews automated PR findings before merging code.
3. **System Administrator / DevOps Lead:** Monitors worker queues, background job health, user accounts, system telemetry, and compliance audit logs.
4. **Security & Compliance Auditor:** Examines automated secret redaction logs, STRIDE security controls, and ensures private repository isolation.

### 2.3 Functional Requirements (FR-01 to FR-12)

```
+---------------------------------------------------------------------------------------------------------+
|                                  FUNCTIONAL REQUIREMENTS MATRIX                                         |
+-------+----------------------------------+--------------------------------------------------------------+
| ID    | Requirement Title                | Core Functional Specification                                |
+-------+----------------------------------+--------------------------------------------------------------+
| FR-01 | Multi-Language AST Parsing       | Parse Python, TypeScript, JavaScript, Java, and Go using     |
|       |                                  | Tree-sitter. Extract functions, classes, imports, and calls. |
| FR-02 | Entropy Secret Redaction         | Scan and redact AWS keys, GitHub PATs, JWTs, and private keys|
|       |                                  | prior to chunking, vector embedding, or LLM exposure.        |
| FR-03 | Multi-Index Representation       | Generate dense vector embeddings (768-d FastEmbed), sparse   |
|       |                                  | BM25s tokens, and NetworkX dependency graphs per snapshot.   |
| FR-04 | Hybrid Retrieval & RRF           | Execute concurrent BM25 and vector queries, aggregating top  |
|       |                                  | candidate chunks using Reciprocal Rank Fusion (k=60).        |
| FR-05 | Cross-Encoder Reranking          | Rerank top 30 candidates using Xenova/ms-marco-MiniLM-L-6-v2 |
|       |                                  | down to top 8 context windows.                               |
| FR-06 | LangGraph Agentic QA Workflow    | Route queries adaptively, test context sufficiency (>0.30),  |
|       |                                  | trigger HyDE query expansion on deficit, and stream answers. |
| FR-07 | Inline Citation Verification     | Enforce [S#] citations in generation; verify each citation   |
|       |                                  | against actual retrieved text; strip ungrounded assertions.  |
| FR-08 | 4-Factor Confidence Calibration  | Compute composite score from Retrieval Relevance, Citation   |
|       |                                  | Validity, Question Coverage, and Grounding Ratio.            |
| FR-09 | ELK Dependency Graph Visualizer  | Render interactive file/module graphs with PageRank, degree  |
|       |                                  | centrality, and circular import cycle detection.             |
| FR-10 | Automated Onboarding Overview    | Synthesize tech stack detection, entry points, reading order,|
|       |                                  | and suggested questions upon repository ingestion.           |
| FR-11 | Context-Aware PR Review (Phase 2)| Parse git diff hunks, map touched symbols to callers, run    |
|       |                                  | static analysis, and classify findings into 4 severity tiers.|
| FR-12 | Human-in-the-Loop PR Approval    | Provide Accept/Reject/Edit controls; publish accepted review |
|       |                                  | findings to GitHub PR comments via REST API.                 |
+-------+----------------------------------+--------------------------------------------------------------+
```

### 2.4 Non-Functional Requirements (NFR-01 to NFR-08)
- **NFR-01 (Performance & Latency):** Ingestion must parse and index a 10,000 LOC repository in under 45 seconds. Hybrid retrieval must return candidate chunks in under 120ms (p50). SSE streaming must emit the first token within 800ms of query arrival.
- **NFR-02 (Reliability & Fault Tolerance):** Celery background tasks must implement exponential backoff retry policies (up to 3 retries). In the event of a remote LLM API outage, the system must gracefully fall back to alternative configured providers or cached embeddings.
- **NFR-03 (Security & Zero Code Execution):** Ingested repositories are strictly treated as inert text. Under no circumstances does RepoGPT execute, compile, build, or run user repository scripts. Personal Access Tokens must be encrypted at rest using AES-GCM-256 (`Fernet`).
- **NFR-04 (Scalability & Multi-Tenancy):** Backend API and Celery workers must be stateless, sharing persistence across MongoDB 8, Redis 7, and ChromaDB. Repositories must be strictly partitioned by `repo_id` across database collections and vector spaces.
- **NFR-05 (Usability & Accessibility):** Frontend UI must adhere to WCAG 2.1 AA standards, featuring a cohesive light theme, responsive mobile-to-desktop viewports, and keyboard accessibility (global `Cmd+K` / `Ctrl+K` command palette).
- **NFR-06 (Portability & Hardware Independence):** Core embedding generation uses `FastEmbed` ONNX CPU runtimes, eliminating mandatory GPU or CUDA hardware requirements for on-premise deployments.
- **NFR-07 (Auditability & Compliance):** All authentication events, administrative operations, repository deletions, and PR review publications must write immutable records to the `audit_logs` collection.
- **NFR-08 (Maintainability & Clean Architecture):** Strict hexagonal architecture separating API delivery (`app/api`), business engine services (`app/engine`), agent graphs (`app/agents`), and core domain schemas (`app/core`).

### 2.5 System Constraints & Design Assumptions
- **Language Boundaries:** Tier-1 AST parsing is guaranteed for Python, TypeScript, JavaScript, Java, and Go. Best-effort token chunking applies to other plain-text formats.
- **Memory Ceiling:** Default Docker Compose development profile is configured to operate within 4GB RAM total system allocation.
- **Human Review Principle:** The automated PR review pipeline intentionally omits automated merge or commit capabilities; all findings require explicit human sign-off.

---

## 3. System Architecture & Engineering Design

### 3.1 High-Level Architecture Topology

```mermaid
flowchart TB
  subgraph Client_Layer ["Client Layer (Presentation)"]
    SPA["React 19 SPA (Vite, Tailwind v4, Zustand)"]
    CP["Command Palette (Cmd+K)"]
    GraphUI["Cytoscape & ELK Dependency Graph"]
  end

  subgraph Gateway_Layer ["Gateway & Reverse Proxy"]
    Caddy["Caddy 2 Reverse Proxy (Auto-HTTPS)"]
  end

  subgraph Application_Layer ["Application & Worker Layer"]
    FastAPI["FastAPI Backend (Python 3.12, Async)"]
    Celery["Celery Distributed Workers (Redis Broker)"]
    LangGraph["LangGraph StateGraph Agent Engine"]
  end

  subgraph Storage_Layer ["Data Persistence & Storage Layer"]
    Mongo[("MongoDB 8.0: Metadata, Users, Conversations")]
    Redis[("Redis 7.0: Celery Queue, Token Cache, Rate Limiting")]
    Chroma[("ChromaDB / FAISS: 768-d Vector Embeddings")]
    Disk[("Shared Volume: Repositories, BM25s, Snapshots")]
  end

  subgraph External_Services ["External Cloud Services"]
    GitHub["GitHub REST API (Tarballs, PRs, Webhooks)"]
    LLMs["LLM Providers (Gemini, Anthropic, OpenAI, Ollama)"]
  end

  SPA -->|HTTPS / WSS| Caddy
  Caddy -->|/api/*| FastAPI
  Caddy -->|Static Assets| SPA
  FastAPI -->|Enqueue Jobs| Redis
  FastAPI --> LangGraph
  FastAPI --> Mongo
  FastAPI --> Chroma
  FastAPI --> Disk
  Celery --> Redis
  Celery --> Mongo
  Celery --> Chroma
  Celery --> Disk
  Celery --> GitHub
  FastAPI --> GitHub
  LangGraph --> LLMs
  Celery --> LLMs
```

### 3.2 Deterministic Ingestion & AST Parsing Activity Flow

```mermaid
flowchart TD
  A([Start Ingestion: GitHub URL or ZIP]) --> B[Download Tarball / Extract Files]
  B --> C[Filter Files: .gitignore, Binary, Max 500KB]
  C --> D[Entropy Secret Scanning & Redaction]
  D --> E{File Language?}
  E -->|Python, TS, JS, Java, Go| F[Tree-Sitter AST Concrete Parsing]
  E -->|Other Supported| G[Fallback Line-Aware Window Chunking]
  F --> H[Extract Symbol Hierarchy: Classes, Functions, Calls]
  H --> I[Generate AST-Aligned Semantic Chunks]
  G --> I
  I --> J[Compute 768-d Embeddings via FastEmbed]
  I --> K[Tokenize & Build BM25s Inverted Index]
  H --> L[Build NetworkX Dependency Graph & Run PageRank]
  J --> M[Persist ChromaDB Collection]
  K --> N[Persist BM25 Index to Storage]
  L --> O[Persist Graph Nodes & Edges to MongoDB]
  M & N & O --> P([Ingestion Complete: State Ready])
```

### 3.3 LangGraph Agentic RAG State Machine

```mermaid
stateDiagram-v2
  [*] --> QueryRouting: User Query Received

  state QueryRouting {
    [*] --> ClassifyIntent
    ClassifyIntent --> VectorOnly: Conceptual Question
    ClassifyIntent --> KeywordOnly: Identifier / Symbol Name
    ClassifyIntent --> HybridRerank: Complex Architectural / Call-Flow Question
  }

  QueryRouting --> HybridRetrieval: Route Dispatched

  state HybridRetrieval {
    [*] --> ParallelFetch
    ParallelFetch --> DenseSearch: ChromaDB (768-d Cosine)
    ParallelFetch --> SparseSearch: BM25s (Lexical Tokens)
    DenseSearch --> RRF_Merge: Reciprocal Rank Fusion
    SparseSearch --> RRF_Merge
    RRF_Merge --> CrossEncoder: Rerank Top 30 Candidates
    CrossEncoder --> TopK: Select Top 8 Context Chunks
  }

  HybridRetrieval --> ContextSufficiencyCheck: Evaluate Relevance

  state ContextSufficiencyCheck {
    [*] --> ScoreSufficiency
    ScoreSufficiency --> Sufficient: Score >= 0.30
    ScoreSufficiency --> Insufficient: Score < 0.30
    Insufficient --> QueryExpansion: HyDE / Query Reformulation
    QueryExpansion --> ParallelFetch: Re-retrieve Context
  }

  ContextSufficiencyCheck --> AnswerGeneration: Context Satisfied

  state AnswerGeneration {
    [*] --> StreamLLMTokens: Emit Tokens via SSE
    StreamLLMTokens --> ParseCitations: Extract [S#] References
    ParseCitations --> VerifyGrounding: Cross-Check Against Retrieved Chunks
    VerifyGrounding --> CalibrateConfidence: Compute 4-Factor Score
  }

  AnswerGeneration --> [*]: Final Response Delivered
```

### 3.4 Context-Aware PR Review Sequence

```mermaid
sequenceDiagram
  autonumber
  actor User as Developer / Reviewer
  participant API as FastAPI Backend
  participant Worker as Celery Worker
  participant AST as Tree-Sitter & Graph Service
  participant Rerank as Retrieval & Reranker
  participant LLM as LangGraph Review Agent
  participant GH as GitHub REST API

  User->>API: Submit PR URL / Upload .diff
  API->>Worker: Enqueue PR Review Job
  Worker->>Worker: Parse Unified Diff (unidiff)
  Worker->>AST: Map Diff Hunks to Changed Symbols
  AST->>AST: Identify Immediate Callers & Downstream Dependents
  Worker->>Rerank: Retrieve Blast-Radius Context (Callers, Tests, Similar Patterns)
  Worker->>Worker: Execute Static Analysis (Ruff, Bandit)
  Worker->>LLM: Invoke Review StateGraph (Diff + Context + Linter Outputs)
  LLM->>Worker: Output Structured Findings (Severity, File, Line, Suggestion)
  Worker->>API: Persist Review Record (Status: Pending Approval)
  API->>User: Display Interactive Review Dashboard
  User->>API: Accept / Reject / Edit Findings
  User->>API: Trigger Publish to GitHub
  API->>GH: POST /repos/{owner}/{repo}/pulls/{number}/reviews
  GH-->>User: Review Comments Visible on GitHub PR
```

### 3.5 Data Models & MongoDB Schemas

RepoGPT persists state into MongoDB 8 utilizing typed Pydantic models. Core collections include:

```
+----------------------------------------------------------------------------------------------------+
|                                    MONGODB COLLECTION SCHEMAS                                      |
+-------------------+--------------------------------------------------------------------------------+
| Collection Name   | Primary Fields & Types                                                         |
+-------------------+--------------------------------------------------------------------------------+
| users             | _id (ObjectId), email (str, unique), password_hash (str), name (str),          |
|                   | role ("user" | "admin"), is_active (bool), github_pat_encrypted (str),        |
|                   | created_at (datetime), last_login_at (datetime)                                |
+-------------------+--------------------------------------------------------------------------------+
| repositories      | _id (ObjectId), name (str), owner (str), source ("github" | "zip"),            |
|                   | default_branch (str), status ("pending" | "indexing" | "ready" | "failed"),    |
|                   | stats (loc, files, symbols), error_message (str), created_at (datetime)        |
+-------------------+--------------------------------------------------------------------------------+
| file_snapshots    | _id (ObjectId), repo_id (ObjectId), path (str), language (str),                |
|                   | size_bytes (int), line_count (int), sha256 (str), ast_extracted (bool),        |
|                   | symbols (list[SymbolSummary]), content_storage_key (str)                       |
+-------------------+--------------------------------------------------------------------------------+
| graph_nodes       | _id (ObjectId), repo_id (ObjectId), node_id (str), label (str),                |
|                   | type ("file" | "class" | "function"), path (str), pagerank (float),            |
|                   | in_degree (int), out_degree (int)                                              |
+-------------------+--------------------------------------------------------------------------------+
| graph_edges       | _id (ObjectId), repo_id (ObjectId), source (str), target (str),                |
|                   | kind ("imports" | "calls" | "defines" | "inherits")                            |
+-------------------+--------------------------------------------------------------------------------+
| conversations     | _id (ObjectId), repo_id (ObjectId), user_id (ObjectId), title (str),           |
|                   | messages (list[ChatMessage]), created_at (datetime), updated_at (datetime)      |
+-------------------+--------------------------------------------------------------------------------+
| reviews           | _id (ObjectId), repo_id (ObjectId), pr_number (int), title (str),              |
|                   | commit_sha (str), status ("analyzing" | "completed" | "published"),            |
|                   | findings (list[ReviewFinding]), created_at (datetime)                         |
+-------------------+--------------------------------------------------------------------------------+
| benchmarks        | _id (ObjectId), name (str), strategy (str), metrics (hit_at_5, mrr, ndcg, ece),|
|                   | question_count (int), latency_p50 (float), created_at (datetime)               |
+-------------------+--------------------------------------------------------------------------------+
| audit_logs        | _id (ObjectId), actor_id (ObjectId), action (str), target_type (str),          |
|                   | target_id (str), ip (str), created_at (datetime), metadata (dict)              |
+-------------------+--------------------------------------------------------------------------------+
```

---

## 4. Mathematical Formulations & Algorithmic Foundations

### 4.1 Reciprocal Rank Fusion (RRF)
To unify disparate scoring scales between dense cosine vector similarity ($\in [-1, 1]$) and sparse BM25 scores ($\in [0, \infty)$), RepoGPT implements Cormack et al.'s Reciprocal Rank Fusion:

$$RRF\_Score(d \in D) = \sum_{m \in M} \frac{1}{k + r_m(d)}$$

Where:
- $M$ is the set of retrieval models ($M = \{\text{Dense Vector}, \text{BM25s}\}$).
- $r_m(d)$ represents the ordinal rank of document $d$ within retriever $m$ (1-indexed).
- $k$ is the smoothing constant set to $k = 60$ (mitigating rank sensitivity for top-tier candidates).

### 4.2 Four-Factor Confidence Calibration
Every generated answer undergoes post-generation verification, outputting a scalar confidence metric $C \in [0.0, 1.0]$:

$$Confidence = w_1 R + w_2 C + w_3 K + w_4 G$$

Subject to $\sum_{i=1}^4 w_i = 1.0$, parameterized as:
1. **$R$ (Retrieval Relevance, $w_1 = 0.35$):** Normalized cross-encoder probability score of top retrieved chunks.
2. **$C$ (Citation Validity, $w_2 = 0.30$):** Ratio of syntactically emitted citations $[S\#]$ that successfully map to actual retrieved chunks:
   $$C = \frac{|\text{Valid Citations}|}{|\text{Emitted Citations}|}$$
3. **$K$ (Question Coverage, $w_3 = 0.15$):** Semantic cosine similarity between question embedding and final synthesized response embedding.
4. **$G$ (Grounding Ratio, $w_4 = 0.20$):** Proportion of factual statements in the answer verified against chunk text spans via NLI token alignment.

### 4.3 Information Retrieval & Calibration Metrics
During benchmarking, the evaluation harness calculates:

- **Mean Reciprocal Rank (MRR):**
  $$MRR = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$$
- **Normalized Discounted Cumulative Gain (nDCG@K):**
  $$DCG@K = \sum_{i=1}^K \frac{2^{rel_i} - 1}{\log_2(i + 1)}, \quad nDCG@K = \frac{DCG@K}{IDCG@K}$$
- **Expected Calibration Error (ECE):**
  $$ECE = \sum_{b=1}^B \frac{|B_b|}{N} |\text{acc}(B_b) - \text{conf}(B_b)|$$

---

## 5. Technology Stack & Architectural Trade-off Analysis

```
+--------------------------------------------------------------------------------------------------------------+
|                                    TECHNOLOGY STACK COMPARISON MATRIX                                        |
+--------------------+-------------------+-----------------------+---------------------------------------------+
| Layer              | Selected Choice   | Alternative Evaluated | Engineering Justification                   |
+--------------------+-------------------+-----------------------+---------------------------------------------+
| Backend Framework  | FastAPI           | Django, Flask         | Native async/await event loop, Pydantic v2  |
|                    | (Python 3.12)     |                       | auto-validation, high SSE streaming speed.  |
| Agent Orchestration| LangGraph         | LlamaIndex Workflows, | Cyclic state graph semantics, fine-grained  |
|                    | StateGraph        | AutoGen               | state persistence, sufficiency re-routing.  |
| Metadata Storage   | MongoDB 8.0       | PostgreSQL + JSONB    | Flexible schema for nested AST symbols and  |
|                    | (AsyncMongoClient)|                       | graph nodes; high throughput document write.|
| Vector Database    | ChromaDB + FAISS  | Pinecone, Milvus      | Dual support: local embedded FAISS or       |
|                    | (Dual Interface)  |                       | containerized Chroma; zero cloud dependency.|
| Lexical Search     | bm25s             | Elasticsearch, Tantivy| Lightweight in-memory/disk inverted index   |
|                    | (Code Tokenizer)  |                       | tailored for camelCase/snake_case tokens.   |
| Embeddings Engine  | FastEmbed (ONNX)  | PyTorch SentenceTrans.| 4x faster CPU inference; zero CUDA or PyTorch|
|                    | 768-d Jina Code   |                       | heavy bloat in container images.            |
| Code AST Parsing   | Tree-sitter       | ANTLR, PyCG           | Concrete incremental syntax trees across 5  |
|                    | Language Packs    |                       | languages with microsecond parse times.     |
| Frontend Framework | React 19 + Vite   | Next.js, Nuxt         | Fast client-side SPA rendering; instant HMR |
|                    | TypeScript Strict |                       | dev experience; optimized Docker static build|
| UI Styling System  | Tailwind CSS v4   | CSS Modules, MUI      | Modern utility-first CSS; strict responsive |
|                    | Lucide Icons      |                       | layout; curated high-contrast light theme.  |
+--------------------+-------------------+-----------------------+---------------------------------------------+
```

---

## 6. Empirical Results & Benchmark Validation

### 6.1 TaskFlow 30Q Codebase Ground Truth Evaluation
Evaluated across 30 multi-faceted questions (architectural routing, auth lifecycle, database transactions, background workers, and error models) on the `TaskFlow` test repository:

```
+---------------------------------------------------------------------------------------------------+
|                            RETRIEVAL STRATEGY BENCHMARK EVALUATION (N=30)                         |
+--------------------+---------+---------+---------+----------+-------------+-----------+-----------+
| Retrieval Strategy | Hit@1   | Hit@3   | Hit@5   | MRR      | nDCG@10     | Latency   | Citation  |
|                    |         |         |         |          |             | (p50)     | Precision |
+--------------------+---------+---------+---------+----------+-------------+-----------+-----------+
| Keyword Only (BM25)| 0.400   | 0.633   | 0.700   | 0.528    | 0.612       | 18 ms     | 0.74      |
| Vector Only (Dense)| 0.567   | 0.767   | 0.833   | 0.684    | 0.741       | 42 ms     | 0.81      |
| Hybrid (RRF k=60)  | 0.700   | 0.867   | 0.900   | 0.791    | 0.835       | 54 ms     | 0.88      |
| **Hybrid + Rerank**| **0.767**| **0.900**| **0.933**| **0.842**| **0.881**   | **98 ms** | **0.92**  |
| Adaptive Auto      | 0.733   | 0.867   | 0.933   | 0.821    | 0.864       | 78 ms     | 0.91      |
+--------------------+---------+---------+---------+----------+-------------+-----------+-----------+
```

### 6.2 Phase 2 Seeded Vulnerability PR Review Suite
Evaluated against 6 synthetic pull-request diff patches containing realistic enterprise defect patterns:

```
+----------------------------------------------------------------------------------------------------+
|                                PHASE 2 PR REVIEW DEFECT BENCHMARK                                  |
+----+-----------------------------+---------------------+-------------------+-----------------------+
| ID | Vulnerability / Defect Type | Severity Category   | Detected by Agent | Localization Accuracy |
+----+-----------------------------+---------------------+-------------------+-----------------------+
| 01 | SQL Injection (Raw Query)   | Critical / Security | Yes (Recall: 1.0) | Exact Line Match (±0) |
| 02 | Auth Bypass (Missing Guard) | Critical / Security | Yes (Recall: 1.0) | Exact Line Match (±0) |
| 03 | Race Condition (Locking)    | High / Concurrency  | Yes (Recall: 1.0) | Exact Line Match (±0) |
| 04 | Sensitive Data Leak (Logs)  | High / Privacy      | Yes (Recall: 1.0) | Exact Line Match (±0) |
| 05 | Breaking API Contract       | Medium / Contract   | Yes (Recall: 1.0) | Exact Line Match (±0) |
| 06 | N+1 Query Antipattern       | Medium / Performance| Yes (Recall: 1.0) | Exact Line Match (±0) |
+----+-----------------------------+---------------------+-------------------+-----------------------+
|    | **OVERALL METRIC**          | **6 / 6 (100%)**    | **100% Precision**| **0.0 Avg Line Error**|
+----+-----------------------------+---------------------+-------------------+-----------------------+
```

---

## 7. Installation, Reproduction & Operations Guide

### 7.1 Prerequisites
- **Operating System:** Linux (Ubuntu 22.04+), macOS (13+), or Windows 11 with WSL2 / PowerShell.
- **Container Runtime:** Docker Engine 24+ and Docker Compose v2.
- **Local Dev Runtimes (if running natively):** Python 3.12+, Node.js 22+, Git.

### 7.2 Quickstart in 4 Steps

```bash
# 1. Clone the repository
git clone https://github.com/hsinha2004/RepoGPT.git
cd RepoGPT

# 2. Generate cryptographically secure secrets and .env configuration
make setup

# 3. Launch all services via Docker Compose
make dev

# 4. Seed system administrator and sample TaskFlow repository
make seed
```
Access the application at `http://localhost:5173`. Sign in with the administrator credentials generated during `make setup`.

### 7.3 Environment Configuration Reference

All settings are managed via `.env` (validated by Pydantic Settings at startup):

| Variable | Description | Default / Options |
|---|---|---|
| `LLM_PROVIDER` | Active LLM inference provider | `gemini` (Free tier), `anthropic`, `openai`, `ollama`, `fake` |
| `LLM_API_KEY` | Remote LLM provider API key | Required for remote APIs; empty for `ollama` / `fake` |
| `LLM_MODEL` | Primary reasoning model name | `gemini-2.0-flash`, `claude-3-5-sonnet-20241022`, `gpt-4o` |
| `EMBEDDING_PROVIDER` | Vector embedding engine | `fastembed` (ONNX CPU default), `openai`, `gemini`, `fake` |
| `EMBEDDING_MODEL` | Code embedding model identifier | `jinaai/jina-embeddings-v2-base-code` (768-d) |
| `VECTOR_STORE` | Primary vector database | `chroma` (Containerized) or `faiss` (File-based) |
| `ROUTER_MODE` | Agentic retrieval router policy | `hybrid` (Heuristics + fast classifier), `heuristic`, `llm` |
| `FEATURE_PR_REVIEW` | Toggle Phase 2 code review engine | `true` or `false` |
| `JWT_SECRET_KEY` | Cryptographic secret for auth tokens | 64-char hex string (auto-generated by `make setup`) |
| `MONGODB_URI` | MongoDB connection URI | `mongodb://repogpt:repogpt@localhost:27017/repogpt` |
| `REDIS_URI` | Redis broker and cache URI | `redis://localhost:6379/0` |

### 7.4 Quality Gates & Automated Verification

Execute full quality checks locally prior to committing:

```bash
# Execute unit and integration tests (Backend pytest + Frontend vitest)
make test

# Execute code formatting and linting (Ruff check + ESLint)
make lint

# Execute strict static type checking (mypy + tsc --noEmit)
make typecheck

# Run system health doctor (Ports, storage volumes, container status)
make doctor
```

---

## 8. Documentation Index & Project Report Artifacts

Comprehensive engineering documentation and diagram sources are indexed in the repository:

- [**Complete System Specification (SPEC.md)**](docs/SPEC.md): 120KB technical build specification covering milestones M1 to M20.
- [**Architectural Overview & LangGraph Topology**](docs/architecture.md): In-depth state transitions and memory management.
- [**REST API & SSE Protocol Reference**](docs/api.md): Complete OpenAPI endpoint documentation and streaming events.
- [**Production Deployment & Hardening Guide**](docs/deployment.md): AWS EC2 setup, SSL termination, and disaster recovery.
- [**Evaluation Methodology & Mathematical Proofs**](docs/evaluation.md): Metric definitions, calibration curves, and reproduction steps.
- [**Security Threat Model & STRIDE Analysis**](docs/security.md): Threat mitigation, secret redaction, and token protection.
- [**Mermaid Report Diagrams Collection**](docs/report/):
  - [System Architecture Diagram](docs/report/system-architecture.mmd)
  - [Component Architecture](docs/report/component.mmd)
  - [Ingestion Activity Flowchart](docs/report/ingestion-activity.mmd)
  - [LangGraph Q&A Agent Flow](docs/report/qa-langgraph.mmd)
  - [Context-Aware Review Flow](docs/report/review-flow.mmd)
  - [Chat Streaming Sequence](docs/report/chat-sequence.mmd)
  - [Data Model & Entities](docs/report/data-model.mmd)
  - [Container Deployment Topology](docs/report/deployment.mmd)
  - [Engineering Methodology Flow](docs/report/methodology.mmd)
  - [Use Case Actor Model](docs/report/use-case.mmd)

---

## 9. Scholarly References (IEEE Format)

1. P. Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," in *Advances in Neural Information Processing Systems (NeurIPS)*, vol. 33, pp. 9459–9474, 2020.
2. Z. Feng et al., "CodeBERT: A Pre-Trained Model for Programming and Natural Languages," in *Findings of the Association for Computational Linguistics (EMNLP)*, pp. 1536–1547, 2020.
3. D. Guo et al., "GraphCodeBERT: Pre-training Code Representations with Data Flow," in *International Conference on Learning Representations (ICLR)*, 2021.
4. Y. Gao et al., "Retrieval-Augmented Generation for Large Language Models: A Survey," *arXiv preprint arXiv:2312.10997*, 2023.
5. S. Robertson and H. Zaragoza, "The Probabilistic Relevance Framework: BM25 and Beyond," *Foundations and Trends in Information Retrieval*, vol. 3, no. 4, pp. 333–342, 2009.
6. G. V. Cormack, C. L. A. Clarke, and S. Buettcher, "Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods," in *Proc. 32nd International ACM SIGIR Conference on Research and Development in Information Retrieval*, pp. 758–759, 2009.
7. L. Gao, Z. Dai, and J. Callan, "Precise Zero-Shot Dense Retrieval without Relevance Labels (HyDE)," in *Proc. 61st Annual Meeting of the Association for Computational Linguistics (ACL)*, 2023.
8. R. Nogueira and K. Cho, "Passage Re-ranking with BERT," *arXiv preprint arXiv:1901.04085*, 2019.
9. Tree-sitter Authors, "An Incremental Parsing System for Programming Tools," *Tree-sitter Documentation*, 2024. [Online]. Available: https://tree-sitter.github.io/tree-sitter/
10. LangChain Inc., "LangGraph: Building Stateful Multi-Actor Applications with LLMs," 2024. [Online]. Available: https://langchain-ai.github.io/langgraph/

---

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.  
Copyright (c) 2026 Harsh Sinha & Anshuman Patel.
