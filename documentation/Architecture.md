## Junior Counsel – System Architecture

### 1. Purpose

This document describes the **technical architecture** of the new Junior Counsel platform.  
It connects the functional and requirements specifications to a concrete, scalable design that follows the project’s development guidelines.

---

### 2. High-Level Overview

Junior Counsel is a **web-based, worker-backed AI system** with the following major components:

- **Web Frontend**: Next.js (React + TypeScript) SPA, responsible for UX, case workspace, document upload, chat, drafting UI, and admin tools.
- **API Backend**: Python (Django REST or FastAPI), stateless HTTP API providing business capabilities and orchestrating jobs via a queue.
- **Worker Services**: Background workers (RQ/Celery) that execute heavy operations (OCR, embeddings, RAG, drafting, verification, export) pulled from a durable queue.
- **Data Layer**: PostgreSQL + pgvector for relational and vector data; object storage for uploaded and generated files.
- **Queue & Events**: Redis/Valkey used as a job queue and lightweight event bus.
- **Notification Layer**: Listens to domain events and creates in-app notifications and optional emails.

At a high level, **all heavy work runs in workers**, allowing the API to stay responsive and each worker pool to scale independently.

---

### 3. Component Architecture

#### 3.1 Web Frontend

- **Technology**: Next.js (React + TypeScript) aligned with the development guidelines.
- **Responsibilities**:
  - Authentication and session handling.
  - Case workspace:
    - List and manage cases.
    - Organise documents, chat sessions, and drafts.
  - Document upload, classification, and status display (including progress).
  - Chat interface (research and drafting assistant).
  - Drafting UI:
    - Intake questions.
    - DraftDoc editor (Normal view + Audit view).
    - Finalisation and export flows.
  - Admin consoles:
    - Rulebook/YAML management.
    - Rulebook testing.
    - Basic operational dashboards (queue status, failures).
- **Integration**:
  - Talks to API Backend over HTTPS/JSON.
  - Subscribes to events via SSE/WebSockets or short-interval polling.

#### 3.2 API Backend

- **Technology**: Python service (Django REST or FastAPI) with:
  - OpenAPI documentation.
  - Strict separation between HTTP layer, domain logic, and integration code.
- **Responsibilities**:
  - **Auth & access control**:
    - Integrate with Attica or a built-in JWT provider.
    - Expose user profile and firm information.
  - **Case & document management**:
    - CRUD for `Case`, `Document`, `UploadSession`, `ChatSession`, `DraftSession`.
    - Document metadata, classification, and search filters.
  - **Search & RAG endpoints**:
    - Semantic, hybrid, and enhanced RAG queries backed by pgvector.
  - **Drafting orchestration**:
    - Creating DraftSessions.
    - Exposing DraftDoc APIs (retrieve, update, verify, rebuild, export triggers).
  - **Rulebook & YAML management**:
    - Storing `Rulebook` rows (raw YAML + parsed JSON) in Postgres.
    - Validation and test harness endpoints for admins.
  - **Event exposure**:
    - SSE/WebSocket endpoints or event polling to surface job status and proactive assistant prompts.
  - **Queue interaction only**:
    - Enqueues jobs for workers (no heavy CPU/IO work in request handlers).
    - Reads job and status information from DB/Redis.

#### 3.3 Worker Services

- **Technology**: Python workers running under a queue framework (e.g. RQ or Celery) connected to Redis/Valkey.
- **Logical worker types** (can be separate processes/containers):

1. **DocumentProcessingWorker**
   - Inputs: `DocumentProcessingJob(document_id, upload_session_id)`.
   - Steps:
     - Fetch document metadata and file.
     - Run OCR if `needs_ocr=true`.
     - Extract text and layout.
     - Chunk content and compute embeddings.
     - Persist chunks into `document_chunks` with pgvector fields.
     - Update document and upload-session statuses.
     - Emit `document.completed` / `document.failed`, and `upload_session.completed` when all docs are done.

2. **DraftResearchWorker**
   - Inputs: `DraftResearchJob(draft_session_id)`.
   - Steps:
     - Load case, documents, and selected rulebook.
     - Run RAG search to collect relevant passages.
     - Build a case profile and initial outline using rulebook rules.
     - Persist research context on `DraftSession`, set status to `awaiting_intake`.
     - Emit `draft.research_ready` event.

3. **DraftGenerationWorker**
   - Inputs: `DraftGenerationJob(draft_session_id)`.
   - Steps:
     - Load rulebook, intake answers, and research context.
     - Call drafting LLM to produce DraftDoc JSON.
     - Validate DraftDoc via `ValidationService`.
     - Persist DraftDoc JSON and create `Document` + `Citation` rows.
     - Set `DraftSession` status to `ready` or `failed`.
     - Emit `draft.completed` / `draft.failed` events.

4. **Auxiliary Workers (optional)**
   - Citation verification jobs.
   - Audit rebuild jobs.
   - PDF/DOCX export jobs (if not done synchronously for small documents).

Workers are **stateless** beyond configuration and connect only to Redis, Postgres, and object storage.

---

### 4. Data Architecture

#### 4.1 Relational Schema (Core Tables)

- `users`:
  - Identity and profile, mapped to auth provider IDs.
- `organisations`:
  - Law firms, chambers, or companies using the platform.
  - Metadata such as name, contact details, and status.
- `organisation_users`:
  - Join table linking users to organisations with role information (e.g. admin, practitioner, staff).
- `cases`:
  - Case metadata, status, type, tags, and jurisdiction.
  - Foreign key to `organisations` (owning organisation) and optionally to a primary `user` owner.
- `documents`:
  - File metadata, classification (type/subtype), tags, notes.
  - Processing state (overall_status, stage, stage_progress).
  - OCR flags and confidence scores.
  - Version chain for AI-generated and manually edited documents.
- `document_chunks`:
  - Chunked text, page/paragraph positions.
  - Embedding vector(s) with pgvector columns and indexes.
  - Metadata: document_type, section_type, semantic_role (facts, orders_sought, etc.).
- `upload_sessions`:
  - Group of documents uploaded together.
  - Totals and progress fields to support batch progress indicators.
- `chat_sessions`, `llm_responses`:
  - Chat context and answer history per case.
- `draft_sessions`:
  - Drafting workflows per case + document type.
  - Status lifecycle, linked rulebook version, intake answers, research summary.
- `draft_docs` (or equivalent):
  - Stored DraftDoc JSON for each draft (if not embedded directly on `documents`).
- `rulebooks`:
  - `document_type`, `jurisdiction`, `version`, `status`.
  - `source_yaml` (raw) and `rules_json` (parsed).
  - `content_hash` and metadata.
- `citations`:
  - Links between generated documents, chunks, and source positions.

#### 4.2 Vector Storage

- Postgres with `pgvector` extension.
- Main embedding column on `document_chunks` with:
  - One primary embedding dimension (e.g. 1,536).
  - HNSW or IVF index for fast similarity search.
- Queries always combine:
  - Vector similarity.
  - Filters on case, document type, and semantic_role.

#### 4.3 File Storage

- Object storage (S3-compatible) or mounted filesystem for:
  - Uploaded originals.
  - Generated PDFs/DOCX.
  - Optional cached intermediate artifacts (e.g. OCR output).
- `documents` and draft metadata store logical paths/URLs only.

---

### 5. Queue and Event Architecture

#### 5.1 Job Queue

- Redis/Valkey hosts:
  - Named queues per job type (e.g. `documents`, `draft-research`, `draft-generation`, `verification`).
  - Job payloads containing IDs and minimal parameters.
- API Backend:
  - Only enqueues jobs; never performs heavy processing inline.
  - Reads job-related status only from Postgres and (optionally) Redis.
- Workers:
  - Poll their dedicated queue.
  - Acknowledge completion or failure.
  - Use retries with bounded limits for transient issues.

#### 5.2 Event Propagation

- Workers publish domain events when key transitions occur:
  - `document.completed`, `document.failed`, `upload_session.completed`.
  - `draft.research_ready`, `draft.completed`, `draft.failed`.
- Events can be:
  - Written to an `events` table in Postgres for durability, or
  - Broadcast via Redis pub/sub channels with DB writes for persistence.
- Notification Layer:
  - Subscribes to events.
  - Creates **in-app notifications**.
  - Sends optional emails via an email provider (e.g. Resend via HTTP API, or SMTP as a fallback).

#### 5.3 Frontend Consumption

- The frontend:
  - Connects to an SSE/WebSocket endpoint or polls `/events` for the current user.
  - Updates progress bars and banners.
  - Triggers **proactive prompts** such as:
    - After `upload_session.completed`: “Your documents are ready—what do you want to generate?”
    - After `draft.research_ready`: “I’ve reviewed your documents for [type]. Let’s answer a few questions.”
    - After `draft.completed`: “Your draft [type] is ready to review.”

---

### 6. Scaling Strategy

- **API Backend**:
  - Stateless, scaled horizontally behind a load balancer.
  - Uses connection pooling for Postgres.
- **Workers**:
  - Independent deployments per queue type (e.g. more `documents` workers for OCR-heavy workloads).
  - Scaled up/down based on queue depth and processing SLAs.
- **Postgres + pgvector**:
  - Tuned for query patterns and indexing.
  - Can be augmented with read replicas if needed.
- **Redis/Valkey**:
  - Deployed redundantly if required, with monitoring for queue health.

---

### 7. Proactive Assistant Behaviour (Architectural View)

- Proactivity is driven by events and the drafting context endpoint:
  - When the user opens a case, API returns:
    - `DraftSession`s and their statuses.
    - Recent document processing events for that case.
  - When events such as `upload_session.completed` or `draft.research_ready` arrive:
    - Frontend shows contextual prompts and actions (e.g. “Start a founding affidavit”, “Resume your draft”).
- This keeps the assistant logic **stateless and event-driven**, rather than coupling it to long-running HTTP requests.

---

### 8. Technology Choices (To Be Confirmed)

The final selection between Django REST and FastAPI, and between RQ and Celery, will follow the development guidelines and team preferences, but the architecture is defined so that:

- All heavy work is worker/queue-based.
- All business capabilities are exposed via clear, documented HTTP APIs.
- AI, OCR, and storage providers are accessed through narrow, swappable interfaces.

