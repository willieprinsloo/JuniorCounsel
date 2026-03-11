## Junior Counsel – Development Plan

### 1. Goals and Principles

- Build the **backend first** (database, models, APIs, middleware, queue + workers), then layer on the frontend.
- Follow the `development_guidelines.md` structure (Python + Flask style back end, PostgreSQL + SQLAlchemy, pytest).
- Ensure **strong unit and integration test coverage** from the start.
- Use a **queue + worker** model for all heavy work so the system can scale horizontally.
- Design in a way that is easy for AI agents to assist with scaffolding, refactoring, and test generation.

---

### 2. Phase 1 – Backend Foundation (Project Skeleton & Database)

**Verification Agents**: `/arch-review`, `/ba-review`

#### 2.1 Create Project Structure

- Create `src/app/` with:
  - `core/`: configuration, logging, database/session setup, AI provider interfaces.
  - `auth/`: authentication logic (Basic Auth or JWT wrapper, depending on final choice).
  - `persistence/`: SQLAlchemy models and repository classes per aggregate.
  - `api/v1/`: Flask blueprints (or FastAPI routers) for versioned REST endpoints.
  - `__init__.py`: app factory and blueprint registration.
- Add:
  - `tests/` for pytest-based unit and integration tests.
  - `.env.example` and `requirements.txt`.
  - `pytest.ini` and (optionally) a small `Makefile` for common tasks.

**Agent Verification Steps**:
1. Run `/arch-review` to validate project structure follows architectural guidelines
2. Run `/ba-review` to confirm structure supports all required features from specs

#### 2.2 Implement Core Models in SQLAlchemy

- Define models aligned with the Requirements and Architecture docs:
  - `User`, `Organisation`, `OrganisationUser`
  - `Case`
  - `Document`, `DocumentChunk`
  - `UploadSession`
  - `ChatSession`, `LLMResponse`
  - `DraftSession`, `Rulebook`
  - `Citation`
- Include:
  - Proper types, indexes, and uniqueness constraints.
  - Created/updated timestamps.
  - Foreign keys and relationships that match the described flows.
  - Organisation scoping on multi-tenant tables.
- Use `Base.metadata.create_all()` for dev/test and prepare for migrations later if needed.

**Agent Verification Steps**:
1. Run `/arch-review` to validate:
   - Database schema design (indexes, constraints, foreign keys)
   - Organisation scoping on all multi-tenant entities
   - pgvector setup for `document_chunks.embedding`
   - Proper use of SQLAlchemy 2.0 `Mapped[]` and `mapped_column()`
2. Run `/ba-review` to confirm models support all FR-* requirements
3. Run `/qa-test` to verify model unit tests exist and pass

#### 2.3 Repositories and Unit Tests

- For each main entity, create repository classes under `persistence/`, e.g.:
  - `OrganisationRepository`, `CaseRepository`, `DocumentRepository`, `DraftSessionRepository`, `RulebookRepository`.
- Implement common operations:
  - Create, get by ID, list by user/case/status/type, update status/metadata.
  - **All list methods MUST support pagination** (page, per_page, sort, order).
- Write pytest unit tests against a test database (`TEST_DATABASE_URL`) to verify:
  - Correct inserts and queries.
  - Transaction boundaries (e.g. multiple updates in a single transaction).
  - Pagination works correctly.
  - Organisation scoping enforced.

**Agent Verification Steps**:
1. Run `/arch-review` to validate:
   - All data access goes through repositories (no direct model queries planned for endpoints)
   - Pagination implemented on all list methods
   - Repository pattern followed correctly
2. Run `/qa-test` to verify:
   - Unit tests exist for all repository methods
   - Test coverage >80%
   - Tests use fixtures correctly

---

### 3. Phase 2 – Middleware, Auth, and Core APIs

**Verification Agents**: `/arch-review`, `/security-audit`, `/qa-test`

#### 3.1 Middleware and Infrastructure

- Implement:
  - **DB session management** per request (open session at request start, close/rollback on error).
  - **Error handling** that returns consistent JSON error responses.
  - **Request logging** (including correlation/trace IDs).
  - **Authentication decorator** (Basic Auth per `development_guidelines.md`, or JWT wrapper if integrating with external auth).

**Agent Verification Steps**:
1. Run `/security-audit` to validate:
   - Password hashing implemented (no plain text)
   - Rate limiting on auth endpoints
   - Session management secure
2. Run `/arch-review` to validate middleware patterns
3. Run `/qa-test` to verify middleware tests exist

#### 3.2 Core REST APIs (CRUD and Metadata)

- Under `api/v1/`, implement endpoints with tests for:
  - `organisations`: List user's organisations, create (admin only)
  - `cases`: CRUD, filtering by status/type, **with pagination**
  - `documents`: CRUD for metadata (not heavy processing yet), **with pagination**
  - `upload-sessions`: read-only listing/status, **with pagination**
  - `chat-sessions`: basic creation and listing, **with pagination**
  - `draft-sessions`: basic creation and listing, **with pagination**
  - `rulebooks`: admin CRUD for YAML + JSON, **with pagination**
- Ensure:
  - **ALL list endpoints support pagination** (page, per_page, sort, order).
  - Standard response format (data, page, per_page, total, pages).
  - Auth is enforced consistently.
  - Validation errors are clear and test-covered.
  - Organisation scoping enforced on all queries.

**Agent Verification Steps**:
1. Run `/arch-review` to validate:
   - **ALL list endpoints have pagination parameters**
   - Endpoints use repositories (no direct model queries)
   - API only enqueues jobs (no heavy work)
   - Response/error formats consistent
2. Run `/api-doc` to generate OpenAPI spec for all endpoints
3. Run `/security-audit` to validate:
   - Authentication enforced
   - Organisation scoping prevents cross-org access
   - Input validation present
4. Run `/qa-test` to verify integration tests exist for all endpoints

#### 3.3 Queue Integration (Job Enqueuing Only)

- Integrate Redis/Valkey as a job queue (e.g. with RQ or Celery):
  - Configure a connection in `core/`.
  - Implement thin enqueuing functions (e.g. `enqueue_document_processing`, `enqueue_draft_research`, `enqueue_draft_generation`).
- Update API endpoints to:
  - Create DB records (e.g. `Document`, `UploadSession`, `DraftSession`).
  - Enqueue the appropriate job with the relevant IDs.
  - **Return 202 Accepted** with IDs and initial statuses (NOT 200/201).
- Add tests that:
  - Verify jobs are enqueued with correct payloads.
  - Use fake worker stubs in test mode to simulate job completion where needed.

**Agent Verification Steps**:
1. Run `/arch-review` to validate:
   - API endpoints only enqueue jobs (no heavy processing)
   - Proper use of 202 Accepted status code
   - Job payloads contain IDs only (not full objects)
2. Run `/worker-review` to validate queue integration patterns
3. Run `/qa-test` to verify enqueuing tests exist

---

### 4. Phase 3 – Workers, AI Integration, and Events

**Verification Agents**: `/worker-review`, `/arch-review`, `/qa-test`

#### 4.1 Worker Processes and Job Handlers

- Create worker entrypoints:
  - `worker_documents.py` for `DocumentProcessingJob`.
  - `worker_drafting.py` for `DraftResearchJob` and `DraftGenerationJob`.
  - (Optional) `worker_aux.py` for verification/export jobs.
- Implement handlers:
  - **DocumentProcessingJob**:
    - Load document record and file.
    - Run OCR if needed (stubbed in early development).
    - Extract text and layout.
    - Chunk and embed text (stub embeddings initially).
    - Write `DocumentChunk`s and update statuses.
    - **Update multi-level status** (overall_status, stage, stage_progress).
    - **Emit events** on completion/failure.
  - **DraftResearchJob**:
    - Load case, docs, and rulebook.
    - Run basic RAG search (start with simple queries).
    - Build a case profile and outline and store on `DraftSession`.
    - **Update status** to `awaiting_intake`.
    - **Emit `draft.research_ready` event**.
  - **DraftGenerationJob**:
    - Load rulebook, intake answers, and research context.
    - Call Drafting provider (stub first) to return a valid DraftDoc JSON.
    - Validate and persist DraftDoc + Document + Citations.
    - **Update status** to `ready` or `failed`.
    - **Emit `draft.completed` or `draft.failed` event**.
- Add unit tests for job handlers with:
  - Mocked providers (OCR, embeddings, LLM).
  - Assertions on DB state transitions and emitted events.

**Agent Verification Steps**:
1. Run `/worker-review` to validate:
   - **Workers are idempotent** (safe to retry)
   - **Events emitted** on all job completions
   - **Multi-level status tracking** (overall_status, stage, stage_progress)
   - Job payloads contain IDs only
   - Retry logic with bounded limits
2. Run `/arch-review` to validate worker architecture compliance
3. Run `/qa-test` to verify worker unit tests with mocked dependencies

#### 4.2 AI Provider Abstraction

- In `core/ai_providers.py`:
  - Define interfaces for embeddings, chat, and drafting.
  - Implement at least one real provider and one stub provider.
- All worker logic calls providers via these interfaces; tests use stub providers.

**Agent Verification Steps**:
1. Run `/arch-review` to validate provider abstraction pattern
2. Run `/qa-test` to verify stub providers work in tests

#### 4.3 Events and Notification Backbone

- Implement an event recording mechanism:
  - A simple `events` table or Redis pub/sub wrapper.
- Worker handlers emit events:
  - `document.completed`, `document.failed`, `upload_session.completed`.
  - `draft.research_ready`, `draft.completed`, `draft.failed`.
- API exposes:
  - A simple `/api/v1/events` endpoint (polling) or an SSE endpoint for real-time updates.
- Add tests:
  - Verify that events are written on job completion.
  - Verify that the events endpoint returns the expected events for a user/case.

**Agent Verification Steps**:
1. Run `/worker-review` to validate event emission in all workers
2. Run `/arch-review` to validate event-driven architecture
3. Run `/qa-test` to verify event tests exist

#### 4.4 Email Notifications (Resend)

- Introduce an `EmailProvider` abstraction in the backend.
- Implement a concrete provider using **Resend** (HTTP API), configured via environment variables (API key, from-address).
- Wire the Notification backbone to:
  - Send emails on selected events (e.g. document and draft completion) using the Resend provider.
  - Fall back to a no-op or test provider in development/test environments.
- Add tests with a fake provider to ensure notifications are triggered correctly without sending real email.

**Agent Verification Steps**:
1. Run `/arch-review` to validate notification abstraction
2. Run `/security-audit` to ensure no secrets in code
3. Run `/qa-test` to verify notification tests with fake provider

---

### 5. Phase 4 – Drafting Pipeline and Rulebooks

**Verification Agents**: `/ba-review`, `/arch-review`, `/qa-test`

#### 5.1 Rulebook Engine

- Implement a Rulebook service that:
  - Reads `source_yaml` from the `rulebooks` table.
  - Parses into `rules_json` according to the agreed YAML schema.
  - Validates against a declarative schema (Pydantic/JSON Schema).
  - Selects the correct rulebook version for a given document type and jurisdiction.
- Extend rulebook admin APIs:
  - Validate on save.
  - Support "draft" vs "published" publishing workflow.
- Tests:
  - YAML parsing and validation with good and bad examples.
  - Version selection logic.

**Agent Verification Steps**:
1. Run `/ba-review` to validate rulebook features meet FR-38 to FR-43
2. Run `/arch-review` to validate rulebook storage and versioning
3. Run `/qa-test` to verify YAML parsing tests exist

#### 5.2 Drafting Orchestration

- Implement a Drafting service that:
  - Given a `DraftSession` ID:
    - Loads session, rulebook, intake answers, and RAG results.
    - Builds the prompt for the drafting LLM.
    - Parses LLM output into a DraftDoc structure.
    - Validates the DraftDoc and persists it.
- Connect this service into `DraftGenerationJob`.
- Tests:
  - Use a stub LLM provider that returns fixed DraftDoc JSON.
  - Ensure all validation and persistence logic behaves as expected.

**Agent Verification Steps**:
1. Run `/ba-review` to validate drafting meets court-ready requirements (BR-1)
2. Run `/worker-review` to validate drafting job is idempotent and emits events
3. Run `/qa-test` to verify drafting tests with stub LLM provider

#### 5.3 DraftSession API Completion

- Finalise DraftSession-related APIs:
  - `POST /draft-sessions` (create and enqueue research).
  - `GET /draft-sessions/{id}` (full status and data).
  - `GET /draft-sessions` (list with **pagination**).
  - `POST /draft-sessions/{id}/answers` (store intake answers).
  - `POST /draft-sessions/{id}/start-generation` (enqueue generation).
- Integration tests:
  - End-to-end flows using test DB and stubbed providers, from DraftSession create through to DraftDoc persistence.

**Agent Verification Steps**:
1. Run `/arch-review` to validate:
   - List endpoint has pagination
   - API only enqueues jobs (returns 202)
   - Uses repository pattern
2. Run `/api-doc` to document draft session endpoints
3. Run `/qa-test` to verify integration tests exist

---

### 6. Phase 5 – Frontend Implementation

**Verification Agents**: `/frontend-dev`, `/ui-design`, `/qa-test`

#### 6.1 API Client and Shared Types

- Generate or hand-write a TypeScript client for all `api/v1` endpoints.
- Centralise HTTP logic (auth headers, error handling, retry) in a single client layer.
- Generate TS types from the backend OpenAPI spec.

**Agent Verification Steps**:
1. Run `/api-doc` to generate OpenAPI spec
2. Use spec to generate TypeScript types (openapi-typescript)
3. Run `/frontend-dev` to validate API client patterns

#### 6.2 Core Screens

- Build:
  - Authentication and profile screens.
  - Case list and case detail views.
  - Document upload screen with:
    - Per-document and per-upload-session progress.
    - In-app notifications for completion and failures.
  - Event subscription layer (SSE/WebSocket/polling) that feeds:
    - Status indicators.
    - Proactive prompts (e.g. "Your documents are ready—what do you want to generate?").

**Agent Verification Steps**:
1. Run `/ui-design` to:
   - Extract design patterns from old system (QA site, Gitea, old code)
   - Create design specification (colors, typography, spacing)
   - Ensure legal terminology used (NOT generic tech terms)
2. Run `/frontend-dev` to validate:
   - TypeScript strict mode (no `any`)
   - React Query for API state
   - Accessibility (ARIA labels, keyboard nav)
   - Pagination on all list views
3. Run `/qa-test` to verify component tests exist

#### 6.3 Drafting and Assistant UI

- Implement:
  - Case-level assistant sidebar that:
    - Shows active DraftSessions and their statuses.
    - Prompts to start a new draft after uploads complete.
  - Guided intake UI derived from rulebook schemas.
  - DraftDoc editor:
    - Normal view with subtle citation markers.
    - Audit view with side-by-side source excerpts.
  - Finalisation and export UI (citation format selection and PDF download).

**Agent Verification Steps**:
1. Run `/ui-design` to validate:
   - Citation visibility and navigation
   - Legal terminology used (Affidavit, Pleading, Heads of Argument)
   - Design consistent with old system
2. Run `/frontend-dev` to validate React best practices
3. Run `/ba-review` to confirm meets drafting workflow requirements (FR-25 to FR-32)
4. Run `/qa-test` to verify drafting UI component tests

#### 6.4 Admin UI

- Provide:
  - Rulebook listing and filter view (with **pagination**).
  - YAML editor with validation messages.
  - Rulebook test runner UI (sample answers + test generation).
  - Simple dashboards for worker queues, recent failures, and usage metrics.

**Agent Verification Steps**:
1. Run `/ui-design` to validate admin UI consistency
2. Run `/frontend-dev` to validate React patterns
3. Run `/security-audit` to ensure admin-only access enforced
4. Run `/qa-test` to verify admin UI tests

---

---

## 7. Phase 6 – Pre-Production Verification

**Verification Agents**: ALL agents in sequence

Before production deployment, run complete verification:

### 7.1 Requirements & Business Value
```bash
/ba-review
```
- Verify all MVP requirements (BR-1 to BR-6, FR-1 to FR-43, NFR-1 to NFR-19) are met
- Check court-ready drafting remains #1 priority
- Validate all features serve target users (advocates, attorneys)
- Generate requirements traceability matrix

### 7.2 Architecture & Database
```bash
/arch-review
```
- Validate database design (indexes, constraints, pgvector)
- **Confirm ALL list endpoints have pagination**
- Verify worker-based architecture (no heavy work in API handlers)
- Check organisation scoping on all multi-tenant tables
- Review technical debt register

### 7.3 Security & Compliance
```bash
/security-audit
```
- Check POPIA compliance (data export, deletion, retention)
- Validate authentication and authorization
- Verify organisation data isolation
- Scan for vulnerabilities (SQL injection, XSS, CSRF)
- Ensure no secrets in code

### 7.4 Worker & Queue Architecture
```bash
/worker-review
```
- Verify all workers are idempotent
- Confirm events emitted on all job completions
- Validate multi-level status tracking
- Check queue health monitoring

### 7.5 Testing & Quality
```bash
/qa-test
```
- Verify test coverage >80%
- Confirm all unit and integration tests pass
- Check E2E tests for critical flows
- Validate test fixtures and mocks

### 7.6 Performance
```bash
/perf-test
```
- Run load tests (1000+ concurrent users)
- Validate performance targets met:
  - Upload/enqueue: < 3s
  - Search queries: 1-2s
  - Q&A/drafting: < 5-8s
- Benchmark database queries
- Check worker throughput

### 7.7 API Documentation
```bash
/api-doc
```
- Verify OpenAPI spec complete
- Confirm all endpoints documented
- Generate TypeScript types
- Create integration guide

### 7.8 Frontend Quality
```bash
/frontend-dev
```
- Validate React/Next.js best practices
- Check TypeScript strict mode (no `any`)
- Verify accessibility compliance
- Confirm React Query usage

### 7.9 UI/UX Design
```bash
/ui-design
```
- Validate design consistency with old system
- Check legal terminology throughout
- Verify WCAG 2.1 AA compliance
- Confirm responsive design

---

## 8. Agent Usage Throughout Development

### Daily Development Workflow

**Before Starting Work**:
```bash
/ba-review      # Verify feature is in requirements
/arch-review    # Understand architectural approach
```

**During Development**:
- Write tests first (TDD approach)
- Use `/qa-test` to generate test templates
- Use `/arch-review` for design decisions
- Use `/security-audit` for security-sensitive code

**Before Committing**:
```bash
/qa-test        # Run tests, check coverage
/arch-review    # Validate patterns
```

**Before Creating PR**:
```bash
/ba-review      # Verify requirements met
/frontend-dev   # Check code quality (if frontend)
/ui-design      # Check design consistency (if UI)
/security-audit # Security check
```

### Agent Guidelines

- **Use agents proactively**: Don't wait for issues
- **Keep agents focused**: Well-defined, test-backed chunks of work
- **Trust agent output**: Agents validate against documented standards
- **Iterate with agents**: Run agents multiple times as code evolves

### Agent-Assisted Tasks

Agents can help:
- Scaffold models, repositories, and API endpoints
- Generate pytest test cases
- Refactor for consistent patterns
- Validate YAML rulebooks
- Generate OpenAPI specs
- Create TypeScript types
- Review security patterns
- Optimize performance

### Success Criteria

Development is on track when:
- ✅ `/ba-review` shows all requirements mapped to implementations
- ✅ `/arch-review` reports zero critical architecture violations
- ✅ `/security-audit` shows no critical/high vulnerabilities
- ✅ `/worker-review` confirms queue architecture correct
- ✅ `/qa-test` shows >80% coverage, all tests pass
- ✅ `/perf-test` confirms targets met
- ✅ `/api-doc` has complete OpenAPI spec
- ✅ `/frontend-dev` validates best practices
- ✅ `/ui-design` confirms consistency with old system

