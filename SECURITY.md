# Security Policy

RepoGPT takes software security seriously. Because our application ingests and parses third-party source code, we adhere to strict architectural controls, including zero code execution of ingested repositories, anti-enumeration by default, secret redaction, and prompt injection isolation.

For our full architectural threat model and controls checklist, see [docs/security.md](file:///c:/Users/harsh2.PC/Desktop/Major/docs/security.md).

---

## Supported Versions

| Version | Supported | Security Maintenance |
|---|---|---|
| `0.1.x` (Phase 1) | :white_check_mark: Yes | Active patches & security fixes |
| `< 0.1.0` | :x: No | Deprecated |

---

## Core Security Commitments

1. **Zero Untrusted Execution:** Untrusted code from ingested archives or repositories is never compiled, run, or imported. Parsing is performed strictly via static Tree-sitter AST extractors.
2. **Anti-Enumeration:** Scoped endpoints return `404 Not Found` for unauthorized requests to prevent leaking the existence of private repositories, conversations, or tasks.
3. **Secret Redaction:** High-entropy credentials, cloud keys, and tokens are redacted prior to indexing, embedding, or LLM synthesis.
4. **Local-First Mode:** Users requiring complete data privacy can run RepoGPT fully locally using `LLM_PROVIDER=ollama` or `fake` with ONNX FastEmbed, ensuring zero egress.

---

## Reporting a Vulnerability

If you discover a security vulnerability or weakness within RepoGPT:

1. **Do NOT open a public GitHub issue.**
2. Send an email report to our security maintainers at:
   - **Lead Developer:** Harsh Sinha (`security@repogpt.local`)
   - **Co-Developer:** Anshuman Patel (`security@repogpt.local`)
   - **Academic Supervisor:** Dr. Archana Kumari (UPES School of Computer Science)
3. **Please include in your report:**
   - Affected component(s) (e.g., Ingestion, Auth, API, Frontend)
   - Step-by-step reproduction instructions or proof of concept
   - Estimated impact and potential threat surface
   - Proposed remediations or patches (if available)

### Response & Remediation Timeline
- **Initial Acknowledgment:** Within 48 hours.
- **Triage & Severity Assessment:** Within 3 business days.
- **Remediation Release & Advisory:** Within 7 business days for Critical/High severity vulnerabilities.
