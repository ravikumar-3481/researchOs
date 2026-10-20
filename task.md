# Project Task Tracker

## Project status

- **Project:** ResearchOS, Enterprise Research Intelligence Agent
- **Current milestone:** Project specification and coding-agent workflow
- **Overall status:** Planning
- **Last updated:** 2026-10-19
- **Important note:** Project documentation exists; this file does not imply that the application itself has been implemented or tested.

## Completed major tasks

- [x] `TASK-001` - Draft the product requirements document. Evidence: `PRD.md`.
- [x] `TASK-002` - Draft the technical requirements document. Evidence: `TRD.md`.
- [x] `TASK-003` - Create an initial Python dependency specification. Evidence: `requirements.txt`. Status caveat: dependency resolution and installation have not been verified.
- [x] `TASK-004` - Define coding-agent operating instructions and cross-chat handoff workflow. Evidence: `AGENTS.md`.
- [x] `TASK-005` - Create change-log and task-tracker templates. Evidence: `changes.md`, `task.md`.

## In progress

- [ ] `TASK-006` - Confirm initial provider choices and implement the runnable backend foundation.
  - Scope: project packaging, settings validation, FastAPI app, health endpoints, PostgreSQL connection, and first migration.
  - Acceptance: app starts with validated configuration; health endpoints behave correctly; database setup and migrations are documented and tested.

## Remaining major tasks

### P0 - First working research flow
- [ ] `TASK-007` - Define typed research request, run state, source, evidence, claim, and report schemas.
- [ ] `TASK-008` - Implement research-run API and persistence.
- [ ] `TASK-009` - Implement a policy-controlled tool registry and one read-only search adapter.
- [ ] `TASK-010` - Implement bounded planner → search → evidence extraction → verification → report workflow.
- [ ] `TASK-011` - Preserve source provenance and validate citations.
- [ ] `TASK-012` - Add unit and integration tests for the end-to-end flow.

### P1 - RAG and integrations
- [ ] `TASK-013` - Implement document ingestion, chunking, embeddings, hybrid retrieval, and reranking.
  - Progress: PDF loader (`document_loader.py`) and Web scraper/parser (`web_data_loader.py`) implemented and verified. Remaining: text chunking, embeddings, and vector indexing.
- [ ] `TASK-014` - Add one MCP server integration with schema validation and execution policy.
- [ ] `TASK-015` - Add a second source connector, such as GitHub or scholarly metadata search.
- [ ] `TASK-016` - Add contradiction analysis and research evaluation dataset.

### P1 - Security and operations
- [ ] `TASK-017` - Implement authentication, authorization, and tenant isolation.
- [ ] `TASK-018` - Add run budgets, cancellation, audit events, and tracing.
- [ ] `TASK-019` - Add prompt-injection, SSRF, secret-redaction, and cross-tenant security tests.
- [ ] `TASK-020` - Add Docker Compose, CI checks, staging deployment, backups, and operational documentation.

### P2 - User interface and enterprise extensions
- [ ] `TASK-021` - Build research progress dashboard and source viewer.
- [ ] `TASK-022` - Add report export and approval UI.
- [ ] `TASK-023` - Add approved enterprise document connectors and configurable retention policies.
- [ ] `TASK-024` - Establish quality, latency, and cost release thresholds from measured baselines.

## Known issues and blockers

- LLM provider/model and search provider are not yet selected.
- Vector store choice (Qdrant or PostgreSQL/pgvector) is not finalized.
- Authentication provider and enterprise SSO requirements are not finalized.
- `requirements.txt` contains version ranges and has not been resolved into a tested lock file.
- No application code, database migration, integration test, or deployment has been verified by this documentation-only step.

## Next recommended action

1. Confirm the initial LLM provider, search provider, and vector-store choice.
2. Create the Python package structure and configuration.
3. Implement FastAPI startup, health endpoints, database connectivity, and the first migration.
4. Add tests and run the project checks.
5. Update `changes.md` with final line references and update this tracker only after verifying acceptance criteria.
