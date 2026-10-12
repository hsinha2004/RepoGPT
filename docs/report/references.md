# Major Project Report — Scholarly & Technical References

This document records the foundational academic literature, industry frameworks, and software libraries utilized in the design and implementation of **RepoGPT** per §19 of the system specification.

---

## 1. Academic Literature & Foundational Papers

1. **Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W., Rocktäschel, T., Riedel, S., & Kiela, D. (2020).**
   *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.*
   Advances in Neural Information Processing Systems (NeurIPS 2020), 33, 9459–9474.
   - **Application in RepoGPT:** Foundational architectural paradigm for grounding language models on dynamic repository code chunks rather than relying solely on parametric weights.

2. **Feng, Z., Guo, D., Tang, D., Duan, N., Feng, X., Gong, M., Shou, L., Qin, B., Liu, T., Daxin, J., & Zhou, M. (2020).**
   *CodeBERT: A Pre-Trained Model for Programming and Natural Languages.*
   Findings of the Association for Computational Linguistics (EMNLP 2020), 1536–1547.
   - **Application in RepoGPT:** Bi-modal representations bridging natural language developer queries and source code tokens during dense semantic retrieval.

3. **Guo, D., Ren, S., Lu, S., Feng, Z., Tang, D., Liu, S., Long, C., Duan, N., Alex, B., Daxin, J., & Zhou, M. (2021).**
   *GraphCodeBERT: Pre-training Code Representations with Data Flow.*
   International Conference on Learning Representations (ICLR 2021).
   - **Application in RepoGPT:** Informs the integration of structural dependency graphs and AST semantic flows into code-aware retrieval and chunking.

4. **Gao, Y., Xiong, Y., Wang, X., Wang, K., Jiang, Z., Zhu, H., Wang, J., Wang, L., Chen, H., & Dou, Z. (2023).**
   *Retrieval-Augmented Generation for Large Language Models: A Survey.*
   arXiv preprint arXiv:2312.10997.
   - **Application in RepoGPT:** Informs the multi-stage pipeline design (pre-retrieval routing, iterative re-querying, hybrid fusion, post-generation grounding verification).

5. **Robertson, S., & Zaragoza, H. (2009).**
   *The Probabilistic Relevance Framework: BM25 and Beyond.*
   Foundations and Trends in Information Retrieval, 3(4), 333–342.
   - **Application in RepoGPT:** Sparse lexical retrieval via `bm25s` for exact identifier, variable, and error code matching.

6. **Cormack, G. V., Clarke, C. L., & Buettcher, S. (2009).**
   *Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods.*
   Proceedings of the 32nd International ACM SIGIR Conference on Research and Development in Information Retrieval, 758–759.
   - **Application in RepoGPT:** Rank aggregation combining BM25 lexical scores and dense cosine similarities ($k=60$) in `backend/app/services/retrieval/fusion.py`.

7. **Gao, L., Dai, Z., & Callan, J. (2022).**
   *Precise Zero-Shot Dense Retrieval without Relevance Labels (HyDE).*
   Proceedings of the 61st Annual Meeting of the Association for Computational Linguistics (ACL 2023).
   - **Application in RepoGPT:** Hypothetical Document Embeddings for query expansion when initial retrieval sufficiency score falls below the 0.30 threshold.

8. **Nogueira, R., & Cho, K. (2019).**
   *Passage Re-ranking with BERT.*
   arXiv preprint arXiv:1901.04085.
   - **Application in RepoGPT:** Cross-encoder reranking (`Xenova/ms-marco-MiniLM-L-6-v2`) refining the top 30 candidate chunks down to the top 8 context windows.

---

## 2. Frameworks & Software Specifications

9. **LangGraph (LangChain, Inc., 2024).**
   *Building Stateful, Multi-Actor Applications with LLMs.*
   - **Application in RepoGPT:** State machine graph pipelines for interactive Q&A (`qa_graph.py`) and context-aware code review (`review_graph.py`).

10. **Tree-sitter (Tree-sitter Authors, 2024).**
    *An Incremental Parsing System for Programming Tools.*
    - **Application in RepoGPT:** Concrete syntax tree parsing across Python, TypeScript, JavaScript, Go, and Rust in `ParserRegistry`.

11. **ChromaDB (Chroma, Inc., 2024).**
    *The AI-Native Open-Source Embedding Database.*
    - **Application in RepoGPT:** High-performance vector database with HNSW indexing for dense embeddings.

12. **FAISS (Meta AI Research, 2024).**
    *Efficient and Robust Approximate Nearest Neighbor Search.*
    - **Application in RepoGPT:** In-memory fallback vector store implementation.

13. **GitHub REST API (GitHub, Inc., 2024).**
    *GitHub REST API Documentation & Webhook Specifications.*
    - **Application in RepoGPT:** Repository tarball acquisition, pull request diff retrieval, constant-time HMAC-SHA256 webhook verification, and automated COMMENT review publishing.

14. **FastAPI (Tiangolo, 2024).**
    *Modern, Fast Web Framework for Building APIs with Python 3.10+.*
    - **Application in RepoGPT:** High-concurrency async REST API with automatic OpenAPI 3.1 schema export and SSE streaming.

15. **XYFlow / React Flow (webkid GmbH, 2024).**
    *Interactive Node-Based UI Components for React.*
    - **Application in RepoGPT:** Frontend interactive dependency graph rendering with `elkjs` hierarchical auto-layout.
