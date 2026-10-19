# Product Requirements Document (PRD)
## ResearchOS: Enterprise Research Intelligence Agent

- **Document status:** Draft for implementation planning
- **Version:** 0.1
- **Product type:** Enterprise research and evidence synthesis platform
- **Primary interface:** Web application and API
- **Initial deployment model:** Single application deployment with background worker; designed for multi-tenant support

---

## 1. Executive summary

ResearchOS is an AI-assisted research platform that turns complex research questions into structured, source-backed reports. It plans research, uses approved tools and MCP servers, retrieves information from public and authorized internal sources, extracts claims, detects conflicting evidence, and generates reports with traceable citations.

ResearchOS is not intended to be an unconstrained autonomous agent. Its workflow is bounded by permissions, tool policies, execution budgets, validation rules, and human approval for consequential write operations.

## 2. Problem statement

Research work is fragmented across websites, technical documentation, academic papers, source-code repositories, APIs, and enterprise documents. Researchers manually repeat search, extraction, comparison, verification, and report-writing tasks. This takes time and makes it difficult to reproduce how a conclusion was reached.

### Problem to solve

Provide a repeatable research workflow that reduces manual effort while making the evidence, source limitations, conflicts, and decisions inspectable.

### Example scenario

A user asks: “Compare open-source vector databases for an enterprise RAG platform, including filtering, performance evidence, scale, security, licensing, ecosystem, and operational trade-offs.”

The system should produce a comparison grounded in identifiable sources, disclose gaps and disagreements, and explain the recommendation against stated requirements.

## 3. Product goals

1. Turn a natural-language request into a research plan with explicit questions and acceptance criteria.
2. Search multiple approved source types through APIs, native connectors, and MCP tools.
3. Preserve source provenance from retrieval through final citation.
4. Use hybrid retrieval and ML-based ranking to surface relevant evidence.
5. Extract structured claims and flag unsupported or conflicting statements.
6. Generate useful reports with citations, limitations, and a reproducible run record.
7. Enforce access control, bounded execution, and auditability.
8. Measure retrieval, citation, task-completion, latency, and cost quality.

## 4. Non-goals for the MVP

- Training a foundation model from scratch.
- Unrestricted autonomous browsing or arbitrary code execution.
- Automatically publishing externally or changing business records without approval.
- Supporting every MCP server and enterprise connector at launch.
- Guaranteeing that every generated claim is true.
- Replacing expert review in regulated or high-impact decisions.
- Starting with a microservices or Kubernetes-heavy architecture before demand requires it.

## 5. Target users and use cases

### Primary users

- Technical researchers and engineers
- Product and strategy analysts
- AI/ML practitioners
- Enterprise knowledge workers
- Research leads reviewing evidence and reports

### MVP use cases

1. Technology and vendor comparison.
2. Open-source repository and dependency research.
3. Research-paper discovery and synthesis.
4. Research over a user-authorized document collection.
5. Evidence-backed technical due diligence.

## 6. User journeys

### Journey A: Start a research run

1. User submits a question, scope, constraints, and desired output.
2. The planner creates atomic research questions and a proposed source strategy.
3. The system checks tool availability, policy, and execution budgets.
4. The run starts and displays progress, sources found, and current stage.
5. The user can cancel the run or provide clarification.

### Journey B: Inspect evidence

1. User opens a report finding.
2. The interface shows its supporting passages, source metadata, retrieval time, and citation.
3. Contradictory or weak evidence is clearly marked.
4. The user can flag a finding or request additional research.

### Journey C: Export a report

1. The report agent creates a structured report.
2. Citation validation checks source references and passage associations.
3. The user reviews the report and exports Markdown or HTML.
4. The system stores the report and audit metadata according to retention policy.

## 7. Functional requirements

| ID | Requirement | Priority | Acceptance criteria |
|---|---|---|---|
| FR-01 | Research request API | P0 | Validated request creates a research-run record and returns a run ID. |
| FR-02 | Research planning | P0 | Planner emits typed tasks, dependencies, source needs, and completion criteria. |
| FR-03 | Controlled tool registry | P0 | Every callable tool has a schema, policy, timeout, and permission declaration. |
| FR-04 | Web search connector | P0 | Search results include URL, title, snippet, retrieval time, and provider metadata when available. |
| FR-05 | GitHub connector | P1 | Read-only repository, release, issue, and file lookups are supported within configured scopes. |
| FR-06 | MCP client | P0 | Client discovers tools, validates inputs, applies policy, and records tool outcomes. |
| FR-07 | Document ingestion | P0 | Supported text/PDF/HTML documents are normalized and linked to source metadata. |
| FR-08 | Hybrid retrieval | P0 | Keyword and vector retrieval can be combined and reranked. |
| FR-09 | Evidence provenance | P0 | Every extracted claim links to a source and supporting passage or is marked unsupported. |
| FR-10 | Claim verification | P0 | Verifier can mark supported, contradicted, insufficient evidence, or needs review. |
| FR-11 | Research report | P0 | Report includes executive summary, findings, citations, limitations, and methodology. |
| FR-12 | Bounded research loop | P0 | Maximum steps, time, tool calls, and model budget are enforced. |
| FR-13 | Run history | P0 | Authorized users can inspect run status, stages, errors, and outputs. |
| FR-14 | Human approval | P0 | Write-capable tools require an explicit approval step before execution. |
| FR-15 | Evaluation suite | P0 | Test set measures retrieval, citation validity, claim support, and task completion. |
| FR-16 | Tenant-aware authorization | P1 | Cross-tenant reads are denied by API, storage, and retrieval layers. |
| FR-17 | Export | P1 | User can export validated report as Markdown; HTML may follow. |
| FR-18 | Observability | P0 | Run traces include agent stages, tool calls, latency, errors, and token/cost metadata where available. |

Priority definitions: P0 = required for MVP; P1 = next milestone.

## 8. Non-functional requirements

### Reliability
- Persist research state and allow failed runs to resume safely where supported.
- Use bounded retries with backoff for transient provider failures.
- Do not retry non-idempotent write operations automatically without a safe idempotency strategy.
- Return explicit partial-completion status when a provider fails.

### Performance
- Run independent, safe research tasks concurrently.
- Stream progress updates to the UI.
- Establish latency targets after measuring a representative baseline.
- Apply per-provider concurrency and rate limits.

### Security and privacy
- Authenticate users and authorize every request and resource access.
- Keep secrets out of prompts, source documents, logs, and client bundles.
- Treat retrieved content and MCP results as untrusted data.
- Use least-privilege credentials and read-only access by default.
- Require approval for consequential write actions.
- Define retention and deletion policies for documents, reports, traces, and personal data.

### Maintainability
- Use typed schemas at API and agent boundaries.
- Keep provider-specific integrations behind adapters.
- Version skills, prompts, tool schemas, and evaluation datasets.
- Require tests for new tools and workflow branches.

## 9. AI/ML requirements

1. Embedding-based semantic retrieval using a selected embedding model.
2. BM25 or equivalent keyword retrieval.
3. Hybrid result fusion and optional cross-encoder reranking.
4. Structured claim and entity extraction.
5. Contradiction analysis using rules, NLI models, or LLM verification.
6. Evidence-quality features such as relevance, source type, freshness, corroboration, and coverage.
7. Evaluation using labeled examples and human review.

Scores must be treated as signals, not proof of truth. A numerical confidence score must not be presented as calibrated probability unless calibration has been tested.

## 10. Report format

1. Title, question, scope, and generation timestamp.
2. Executive summary.
3. Methodology and source-selection approach.
4. Findings with inline citations.
5. Comparison tables where relevant.
6. Conflicting evidence and unresolved questions.
7. Limitations and confidence rationale.
8. Recommendation tied to user-defined criteria.
9. Source list and research-run identifier.

## 11. Success metrics

Initial metrics to collect:

- Retrieval Recall@K and NDCG@K
- Citation correctness and citation coverage
- Claim support rate from human-reviewed samples
- Contradiction detection precision and recall on a labeled test set
- Tool-selection success rate
- Research task completion rate
- P50/P95 run latency
- Cost per completed research run
- Failure and retry rates
- Security test pass rate

Numeric release thresholds will be set after a baseline is measured on a representative evaluation set. Do not use LLM self-assessment as the sole quality metric.

## 12. MVP scope and release plan

### Phase 1: Foundation
- PRD/TRD, schemas, API, database, configuration, authentication integration.
- Tool registry and one search provider.
- Research-run lifecycle and audit events.

### Phase 2: Research workflow
- Planner, discovery, evidence extraction, verification, and reporting nodes.
- Bounded orchestration, state persistence, and failure handling.

### Phase 3: RAG and connectors
- HTML/PDF ingestion, chunking, embeddings, keyword retrieval, vector search, reranking.
- Add GitHub or scholarly search as the second connector.
- Add MCP client integration.

### Phase 4: Evaluation and security
- Labeled benchmark, citation tests, prompt-injection tests, permission tests, cost and latency tracing.

### Phase 5: UI and deployment
- Research dashboard, source viewer, report export, Docker setup, CI checks, and staging deployment.

An eight-week single-developer schedule is an initial planning estimate, not a delivery guarantee. Re-estimate after a technical spike for the selected LLM, search provider, and MCP servers.

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Hallucinated or unsupported claims | Claim-to-passage links, citation validation, and abstention when evidence is weak |
| Prompt injection in retrieved content | Treat content as data, restrict tool permissions, isolate execution, and test adversarial cases |
| Provider outages or rate limits | Timeouts, bounded retries, quotas, circuit-breaking where needed, and partial-result reporting |
| High inference and search costs | Per-run budgets, caching, model routing, and cost tracking |
| Source bias or stale information | Source diversity, timestamps, freshness rules, and conflict reporting |
| Unauthorized data exposure | Tenant isolation, source permission checks, least privilege, and security tests |
| Agent loops or runaway execution | Step limits, wall-clock deadline, tool-call budget, and explicit stop conditions |
| Dependency/API changes | Version constraints, lock file, integration tests, and staged upgrades |

## 14. Open decisions before production

- LLM provider and fallback policy
- Search provider and licensing
- Vector store: Qdrant or PostgreSQL/pgvector
- Authentication provider and enterprise SSO needs
- Supported file types and maximum document sizes
- Data residency, retention, and deletion requirements
- Deployment target and expected concurrency
- Which MCP servers are approved and who owns their credentials

## 15. Definition of done for MVP

The MVP is ready for a controlled pilot when:

- An end-to-end research run works from request to cited report.
- All tool calls pass through a policy-controlled registry.
- Evidence can be traced to original sources and passage locations.
- Failed providers produce visible, bounded partial failures.
- Research runs have limits and can be inspected through traces.
- Unit, integration, security, and evaluation tests run in CI.
- Cross-tenant access tests pass for every supported data path.
- The team has documented known limitations and measured a baseline on the evaluation set.
