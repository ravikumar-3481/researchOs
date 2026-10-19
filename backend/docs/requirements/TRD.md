# Technical Requirements Document (TRD)
## ResearchOS: Enterprise Research Intelligence Agent

- **Document status:** Draft for implementation
- **Version:** 0.1
- **Related document:** `PRD.md`
- **Architecture style:** Modular monolith plus background worker
- **Primary language:** Python
- **Frontend:** Next.js / React / TypeScript

---

## 1. Technical overview

ResearchOS consists of a web client, a FastAPI service, a graph-based research orchestrator, background workers, a tool/MCP execution layer, ingestion and retrieval modules, persistent storage, and observability.

The initial deployment should keep the number of services small. Module boundaries must be explicit so components can be extracted later if independent scaling or isolation becomes necessary.

## 2. Architecture principles

1. Typed contracts at every service and agent boundary.
2. Explicit workflow state instead of unconstrained agent-to-agent conversation.
3. Tool execution always passes through authorization and policy enforcement.
4. Source provenance is preserved through ingestion, retrieval, extraction, and reporting.
5. LLM outputs are untrusted until schema-validated and checked.
6. Expensive or long-running work executes in a background worker.
7. Every run has step, time, tool-call, and cost limits.
8. External providers are accessed through replaceable adapters.
9. Security and evaluation are part of CI, not a final-only activity.

## 3. Proposed stack

| Layer | Technology | Notes |
|---|---|---|
| Web UI | Next.js, React, TypeScript | Research runs, source inspection, report viewer |
| API | FastAPI, Pydantic | REST endpoints and optional SSE progress stream |
| Workflow | LangGraph | Stateful graph, conditional transitions, checkpointing |
| LLM integration | Provider SDK behind an adapter | Provider-independent application interfaces |
| MCP | Official Python MCP SDK/client | Discover and invoke approved MCP tools |
| Relational store | PostgreSQL | Users, runs, tasks, source metadata, claims, audit records |
| Vector retrieval | Qdrant or pgvector | Choose one for MVP |
| Keyword retrieval | PostgreSQL full-text search or BM25 | Evaluate based on dataset and deployment simplicity |
| Object storage | S3-compatible storage | Original files and generated report artifacts |
| Cache/queue | Redis plus Celery or another supported worker | Queueing and cache; durable workflow state remains separate |
| ML | sentence-transformers, Transformers, scikit-learn, PyTorch | Embeddings, reranking, classification, evaluation |
| Migrations | Alembic | Database schema changes |
| Tests | pytest, pytest-asyncio | Unit, integration, and workflow tests |
| Lint/format | Ruff, optional mypy | Static checks and consistency |
| Tracing | OpenTelemetry plus chosen trace backend | Latency, spans, errors, model/tool traces |
| Packaging | Docker, Docker Compose | Local and staging environments |
| CI/CD | GitHub Actions | Lint, tests, security checks, build |

The exact library versions must be resolved and tested in the target environment. `requirements.txt` provides version ranges; a deployment lock file should be generated after compatibility testing.

## 4. Logical components

### 4.1 API layer

Responsibilities:
- Validate incoming requests.
- Authenticate and authorize users.
- Create and query research runs.
- Return status and report artifacts.
- Stream progress events when enabled.
- Apply request limits and correlation IDs.

Suggested routes:

| Method | Route | Purpose |
|---|---|---|
| POST | `/api/v1/research-runs` | Create a research run |
| GET | `/api/v1/research-runs/{run_id}` | Get run status and summary |
| GET | `/api/v1/research-runs/{run_id}/events` | Stream run events (SSE, if implemented) |
| GET | `/api/v1/research-runs/{run_id}/evidence` | List evidence visible to the caller |
| GET | `/api/v1/research-runs/{run_id}/report` | Retrieve completed report |
| POST | `/api/v1/research-runs/{run_id}/cancel` | Request cancellation |
| POST | `/api/v1/research-runs/{run_id}/approvals/{approval_id}` | Approve/deny a pending action |
| GET | `/health/live` | Liveness check |
| GET | `/health/ready` | Readiness check |

Do not expose internal tool execution as an unrestricted public endpoint.

### 4.2 Orchestration layer

Implement the research graph with typed state. Suggested state fields:

- `run_id`, `tenant_id`, `user_id`
- `request`, `scope`, `constraints`, `output_format`
- `plan`, `tasks`, `task_statuses`
- `selected_tools`, `tool_call_count`, `model_usage`
- `sources`, `documents`, `evidence`, `claims`
- `verification_results`, `unresolved_questions`
- `report`, `errors`, `warnings`
- `started_at`, `updated_at`, `deadline_at`

Graph nodes:
1. `validate_request`
2. `plan_research`
3. `authorize_and_select_tools`
4. `execute_research_tasks`
5. `normalize_sources`
6. `retrieve_evidence`
7. `extract_claims`
8. `analyze_and_verify`
9. `evaluate_completeness`
10. `generate_report`
11. `validate_citations`
12. `persist_result`

Conditional transitions:
- Retry a transient provider failure only within configured limits.
- Loop to planning/research only if evidence is insufficient and budgets remain.
- Ask for user clarification if the question is materially underspecified.
- Stop and return a partial report when the deadline or budget is exhausted.
- Never route around authorization or approval gates.

### 4.3 Tool registry and execution

Every tool definition should include:
- Stable tool ID and version
- Provider and execution adapter
- Input/output schema
- Required scopes and permission level
- Allowed tenant/user context
- Timeout, retry policy, and rate limit
- Idempotency classification
- Data sensitivity classification
- Audit/logging policy
- Approval requirement for side effects

Execution sequence:
1. Resolve the tool by stable ID.
2. Verify caller, tenant, scopes, and run policy.
3. Validate arguments against the schema.
4. Enforce destination/network restrictions where relevant.
5. Apply timeout, quota, and cancellation.
6. Execute using scoped credentials.
7. Validate and size-limit the response.
8. Record a redacted audit event and trace span.
9. Return structured output to the workflow.

Do not allow arbitrary shell execution or unrestricted Python execution in the MVP.

### 4.4 MCP client manager

- Connect only to explicitly configured MCP servers.
- Support the required transport(s) supported by the selected SDK and deployment.
- Discover tool schemas at connection time and validate them.
- Apply per-server and per-tool allowlists.
- Use scoped credentials and secret references, never hard-coded tokens.
- Enforce timeouts, output size limits, cancellation, and quotas.
- Treat tool results and tool descriptions as untrusted input.
- Record server identity, tool name, schema/version where available, result status, latency, and a redacted argument summary.
- Fail closed if authorization or policy evaluation is unavailable.
- Require human approval for configured side-effecting operations.

MCP standardizes tool connectivity; it does not replace application authorization, isolation, or auditing.

## 5. Data model

Use PostgreSQL as the source of truth for transactional metadata. Suggested entities:

### `organizations`
- `id` UUID primary key
- `name`
- `created_at`

### `users`
- `id` UUID primary key
- `organization_id` foreign key
- `external_subject_id`
- `role`
- `created_at`

### `research_runs`
- `id` UUID primary key
- `organization_id`, `created_by`
- `question`, `scope`, `constraints_json`
- `status` (`queued`, `running`, `waiting_approval`, `completed`, `partial`, `failed`, `cancelled`)
- `workflow_version`
- `budget_json`
- `started_at`, `completed_at`, `created_at`

### `research_tasks`
- `id`, `run_id`
- `task_key`, `task_type`, `status`
- `input_json`, `output_json`
- `attempt_count`, `started_at`, `completed_at`

### `sources`
- `id`, `organization_id`
- `canonical_uri`, `source_type`, `title`
- `published_at`, `retrieved_at`
- `content_hash`, `version`, `metadata_json`

### `documents`
- `id`, `source_id`, `organization_id`
- `storage_uri`, `mime_type`, `processing_status`
- `page_count`, `metadata_json`

### `chunks`
- `id`, `document_id`, `organization_id`
- `chunk_index`, `text`, `location_json`
- `embedding_model`, `content_hash`

### `claims`
- `id`, `run_id`, `organization_id`
- `claim_text`, `claim_type`, `normalized_value_json`
- `verification_status`, `confidence_rationale`

### `claim_evidence`
- `claim_id`, `chunk_id`
- `relationship` (`supports`, `contradicts`, `context`)
- `explanation`, `created_at`

### `tool_calls`
- `id`, `run_id`, `organization_id`
- `tool_id`, `provider`, `status`
- `started_at`, `duration_ms`, `error_code`
- `redacted_arguments_json`, `result_metadata_json`

### `approvals`
- `id`, `run_id`, `requested_action`
- `requested_by`, `reviewed_by`, `status`
- `created_at`, `reviewed_at`

### `audit_events`
- `id`, `organization_id`, `actor_id`
- `action`, `resource_type`, `resource_id`
- `timestamp`, `correlation_id`, `redacted_details_json`

Use foreign keys, indexes, database constraints, and migrations. Add row-level security or equivalent application-level isolation backed by tests. Do not store secrets in these tables.

## 6. RAG and ingestion pipeline

### Ingestion
1. Accept only approved source types and file sizes.
2. Parse HTML, PDF, and plain text with controlled parsers.
3. Normalize whitespace and remove boilerplate where safe.
4. Compute a content hash for deduplication.
5. Preserve canonical URL, retrieval time, publication date when available, document version, and location metadata.
6. Chunk with structure-aware splitting where possible.
7. Create embeddings and index metadata.
8. Record processing errors without losing source provenance.

### Retrieval
1. Authorize the user and tenant before retrieval.
2. Apply metadata and access filters.
3. Retrieve keyword candidates.
4. Retrieve semantic candidates.
5. Fuse and deduplicate candidates.
6. Rerank the top candidates with a cross-encoder or another evaluated reranker.
7. Return passages with source IDs and exact locations.
8. Log retrieval metrics without unnecessarily logging sensitive text.

Chunk sizes and overlap must be tuned using evaluation data rather than fixed as universal constants.

## 7. AI/ML modules

### Embeddings
- Use a configurable embedding model and record its version.
- Re-embed documents when changing incompatible embedding spaces.
- Keep embedding generation behind an interface.

### Reranking
- Start with a pretrained cross-encoder if latency and hardware permit.
- Measure NDCG@K and Recall@K before and after reranking.
- Add a reranker timeout and graceful fallback.

### Claim extraction
- Use Pydantic schemas for structured LLM output.
- Validate units, dates, entity references, and required source links.
- Reject malformed output and retry only within limits.

### Contradiction detection
- Use deterministic comparisons for numeric values, dates, units, and definitions where possible.
- Use an NLI model or LLM-based verifier as a supporting signal.
- Distinguish contradiction, temporal change, different scope, and insufficient evidence.
- Require source passages for verification decisions.

### Evidence scoring
- Use interpretable features: relevance, source type, recency, independent corroboration, and directness of support.
- Do not equate domain reputation or repeated copies of one source with independent confirmation.
- Do not expose an uncalibrated score as a probability of truth.

## 8. API schemas

### Create research run request

```json
{
  "question": "Compare open-source vector databases for enterprise RAG",
  "scope": {
    "topics": ["filtering", "licensing", "security", "performance"],
    "source_types": ["official_docs", "papers", "repositories"]
  },
  "constraints": {
    "max_steps": 30,
    "max_tool_calls": 50,
    "deadline_seconds": 900
  },
  "output_format": "markdown"
}
```

The server must apply stricter configured ceilings if client values exceed policy. Never trust client-supplied tenant IDs or permissions.

### Research run response

```json
{
  "run_id": "server-generated-uuid",
  "status": "queued",
  "created_at": "ISO-8601 timestamp"
}
```

These are illustrative schemas. Use typed Pydantic models and a versioned API contract in the implementation.

## 9. Security requirements

- OIDC/OAuth integration or a trusted identity gateway.
- Authorization checks on every run, evidence, report, and approval endpoint.
- Tenant ID derived from authenticated identity, not from an untrusted request body.
- Least-privilege service accounts and read-only connectors by default.
- Secrets stored in a managed secret store in production.
- TLS in transit and encryption at rest through the hosting platform or storage layer.
- Prompt-injection testing for web pages, PDFs, repository files, and MCP output.
- Network egress allowlists for browser and fetch tools; block private/internal addresses unless explicitly approved for a controlled connector.
- File type validation, size limits, parser timeouts, and malware scanning where appropriate.
- Redaction of tokens, credentials, and sensitive data in logs.
- Approval workflow for side-effecting tools.
- Audit retention and deletion rules.
- Dependency and container vulnerability scanning in CI.

## 10. Reliability and limits

Every run must have:
- Maximum graph steps
- Maximum wall-clock duration
- Maximum tool calls and per-tool timeouts
- Maximum document size and total ingested bytes
- Maximum model token/cost budget where provider usage data allows
- Maximum retry count
- Cancellation support
- Explicit partial-result behavior

Use idempotency keys for run creation and other retried operations. Use bounded exponential backoff for transient failures. Do not blindly retry authorization errors or invalid tool arguments.

## 11. Observability

Record structured events for:
- Run and workflow stage transitions
- Tool/provider selection and outcome
- Retrieval candidate counts and ranking metrics
- Model name/version, latency, and token usage where available
- Validation failures and retry reasons
- Verification outcomes
- Report generation and citation validation

Use correlation IDs across API, worker, workflow, and tool calls. Redact sensitive data and avoid storing full prompts or document contents by default unless an explicit, protected debugging policy permits it.

## 12. Testing strategy

### Unit tests
- Schemas and validation
- Chunking and source normalization
- Tool policy decisions
- Claim normalization
- Citation formatting and validation
- Budget and stopping conditions

### Integration tests
- Database and migrations
- Search provider adapters
- MCP tool discovery and invocation
- Vector retrieval and reranking
- Workflow checkpoint/resume
- API authentication and authorization

### Security tests
- Cross-tenant access attempts
- Prompt injection from retrieved content
- Malicious MCP tool output
- SSRF and private-network access restrictions
- Secret leakage in logs
- Oversized and malformed documents
- Unauthorized write operations

### Evaluation tests
- Fixed research-question dataset
- Gold evidence passages
- Expected claims and known contradictions
- Citation support review
- Retrieval Recall@K and NDCG@K
- Task completion, latency, and cost regression

## 13. Local development and deployment

Suggested local services:
- API container
- Background worker
- PostgreSQL
- Redis
- Selected vector database if Qdrant is chosen
- Optional local tracing UI

Use Docker Compose for local dependencies. Store local credentials in an ignored `.env` file and provide `.env.example` with placeholders only.

Production baseline:
- Separate development, staging, and production environments
- CI linting, type checks, unit/integration tests, dependency scans, and container build
- Database migrations as a controlled deployment step
- Health/readiness checks
- Backups and restore tests
- Centralized logs and tracing
- Secret manager and rotation process
- Rollback procedure

Do not add Kubernetes until deployment and scaling requirements justify its operational cost.

## 14. Configuration

Suggested environment variables:

```dotenv
APP_ENV=development
APP_NAME=ResearchOS
API_V1_PREFIX=/api/v1
DATABASE_URL=postgresql+psycopg://researchos:change-me@localhost:5432/researchos
REDIS_URL=redis://localhost:6379/0
LLM_PROVIDER=openai
OPENAI_API_KEY=
OPENAI_MODEL=
EMBEDDING_MODEL=
VECTOR_STORE=qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
SEARCH_PROVIDER=
SEARCH_API_KEY=
OTEL_SERVICE_NAME=researchos-api
LOG_LEVEL=INFO
```

Never commit real secrets. Use Pydantic Settings to validate configuration at startup. Fail fast when a required production setting is missing.

## 15. Suggested repository layout

```text
researchos/
├── apps/
│   ├── api/
│   └── web/
├── services/
│   ├── worker/
│   └── ingestion/
├── src/researchos/
│   ├── agents/
│   ├── orchestration/
│   ├── tools/
│   ├── mcp/
│   ├── retrieval/
│   ├── ml/
│   ├── ingestion/
│   ├── security/
│   ├── storage/
│   ├── evaluation/
│   ├── schemas/
│   └── config.py
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── security/
│   └── evaluation/
├── migrations/
├── infra/
│   └── docker/
├── docs/
│   ├── PRD.md
│   ├── TRD.md
│   └── THREAT_MODEL.md
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── docker-compose.yml
├── .env.example
└── README.md
```

## 16. Implementation sequence

1. Establish project packaging, configuration, schemas, database, migrations, and health endpoints.
2. Implement a single research-run API and background execution path.
3. Build the tool registry and one read-only search connector.
4. Implement a minimal graph: plan → search → extract evidence → verify → report.
5. Add source persistence and citation validation.
6. Add hybrid retrieval, embeddings, and reranking.
7. Add the MCP client and one selected MCP server.
8. Add authorization, budgets, audit trails, and adversarial tests.
9. Build the UI, report viewer, and run progress view.
10. Establish evaluation baselines, staging deployment, and operational runbooks.

## 17. Technical decisions requiring confirmation

- LLM provider and model
- Search API provider
- Qdrant versus pgvector
- Identity provider and SSO requirements
- Supported MCP servers and transport
- Deployment platform
- Data retention, residency, and compliance needs
- Expected request volume and concurrency

Resolve these decisions before a production deployment. Keep them configurable where reasonable, but avoid introducing abstraction layers that do not solve a current requirement.
