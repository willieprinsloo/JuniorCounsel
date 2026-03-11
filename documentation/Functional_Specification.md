## Junior Counsel – Functional Specification

### 1. Purpose and Scope

This document describes the functional behaviour of the **new Junior Counsel system**.  
It focuses on what the system must do for:

- **End users**: advocates and attorneys using the platform for drafting and research.
- **Admin users**: users who configure and maintain rulebooks (YAML), document types, and quality controls.

The primary value proposition is **court‑ready drafting for South African litigation practice**, with supporting legal research and document management.

---

### 2. Actors

- **End User (Lawyer/Paralegal)**
  - Creates and manages cases.
  - Uploads, classifies, and reviews documents.
  - Uses AI search and chat to understand case materials.
  - Starts and completes drafting workflows to generate court‑ready documents.

- **Admin User**
  - Manages rulebooks and intake schemas stored in Postgres.
  - Tests rulebooks against sample inputs.
  - Manages document type catalog and configuration for the drafting engine.

- **Organisation Admin (Company/Firm Admin)**
  - Manages organisation (company/firm) details.
  - Invites and removes users for that organisation.
  - Assigns roles (admin, practitioner, staff) within the organisation.
  - Oversees which cases and rulebooks are available to their organisation.

---

### 3. Core Domain Objects

#### 3.1 Case

- **Description**: Container for all work on a particular matter.
- **Key attributes**: title, description, case type, status, tags, key dates, jurisdiction.
- **Relations**:
  - Has many `Document`s.
  - Has many `ChatSession`s.
  - Has many `DraftSession`s.

#### 3.2 Document

- **Description**: An uploaded or generated file associated with a case.
- **Key attributes**:
  - File metadata: name, extension, pages, size, storage path.
  - Classification: document type (e.g. pleading, evidence, correspondence, order, research), optional subtype, tags, notes.
  - Processing state:
    - `overall_status`: queued, processing, completed, failed.
    - `stage`: uploading, ocr, text_extraction, chunking, embedding, indexing.
    - `stage_progress`: numeric 0–100.
    - OCR flags, confidence, and error messages where applicable.
  - Associations to case, upload session, and creator.
- **Relations**:
  - Belongs to a `Case`.
  - Has many `DocumentChunk`s.

#### 3.3 DocumentChunk

- **Description**: A semantically meaningful segment of a document used for search and RAG.
- **Key attributes**:
  - Text content, page number, paragraph range.
  - Vector embedding.
  - Metadata:
    - document type, section type (heading, body, annexure, table, footnote), semantic role (facts, orders_sought, argument, background, etc.).
    - references to source positions (e.g. bounding boxes) when available.
- **Relations**:
  - Belongs to a `Document`.
  - Referenced from search results and citations.

#### 3.4 UploadSession

- **Description**: Logical batch of documents uploaded together.
- **Key attributes**:
  - Case, user, list of associated documents.
  - Status, total document count, completed count, failed count.
- **Purpose**:
  - Drives batch‑level progress indicators and notifications.

#### 3.5 ChatSession

- **Description**: Conversation between user and AI assistant, optionally scoped to a case.
- **Key attributes**:
  - Case, user, topic, message history, associated documents and citations, timestamps.
- **Purpose**:
  - Supports research‑style interactions and explanations related to case materials.

#### 3.6 DraftSession

- **Description**: A single drafting workflow for a specific document type within a case.
- **Key attributes**:
  - Case, user, document type, title.
  - Status lifecycle: initializing, awaiting_intake, generating, ready, failed.
  - Linked rulebook ID and version.
  - Case profile, intake answers, outline, DraftDoc JSON, timestamps.
  - Notification preferences (e.g. notify on completion).
- **Relations**:
  - Belongs to a `Case`.
  - Uses one published `Rulebook` version.

#### 3.7 Rulebook

- **Description**: Versioned configuration for drafting a given document type and jurisdiction.
- **Key attributes**:
  - Document type, jurisdiction, version, status (draft, published, deprecated), label.
  - `source_yaml`: raw YAML edited by admins.
  - `rules_json`: validated JSON representation (intake schema, document template, validation rules).
  - Content hash, created/updated metadata.
- **Purpose**:
  - Single source of truth for:
    - Document structure and sections.
    - Intake questions and required fields.
    - Validation and completeness rules.
    - Drafting prompts and style guidance.

---

### 4. End‑User Flows

#### 4.1 Case Management

- Create new cases with basic metadata (title, description, type, jurisdiction).
- View a case workspace with:
  - Summary panel (dates, status, parties, tags).
  - Materials tab listing all documents.
  - Chat tab showing conversations for the case.
  - Drafts tab listing all `DraftSession`s.
- Update case metadata and archive or close cases as needed.

#### 4.2 Document Upload and Classification

- Upload one or more documents to a case:
  - Select files.
  - Optionally specify a default document type for the batch.
  - System creates an `UploadSession` and initial `Document` records with `overall_status = queued`.
- Provide or refine classification:
  - Set or edit document type and subtype.
  - Add or remove tags and notes.
  - Accept or override AI‑suggested type/subtype.
- View processing progress:
  - Per‑document status and stage progress.
  - Per‑upload session summary (e.g. 3/5 completed).
  - Once an upload session completes, the assistant can proactively suggest next steps (e.g. “Now that these documents are ready, what would you like to generate?”).

#### 4.3 Background Processing and OCR

- Once uploaded, the system:
  - Detects whether each document requires OCR.
  - Enqueues processing jobs for OCR, text extraction, chunking, embedding, and indexing.
  - Updates status and progress fields as each stage completes.
- User experience:
  - User is never blocked by processing; they can navigate elsewhere in the app.
  - On completion or failure, the user receives in‑app notification and optional email.

#### 4.4 Search and Research (RAG)

- User can search within a case or across all cases:
  - Submit natural‑language queries.
  - Apply filters by document type, semantic role, tags, and date ranges.
- System returns:
  - Ranked list of `DocumentChunk`s with text snippets.
  - Linked document, page, and paragraph information.
  - Document type and role indicators.
- For Q&A:
  - User asks questions in a chat interface.
  - System retrieves relevant chunks and generates answers.
  - Every answer includes citations linking back to chunk and document metadata.

#### 4.5 Proactive Drafting Assistant

- When user opens a case:
  - System fetches drafting context for that case: active `DraftSession`s and suggested document types.
  - If no draft is active, system prompts user: “What document do you want to generate?”.
  - If new documents were recently processed for this case, the assistant highlights them and asks proactively whether the user wants to draft something using those materials.
- Starting a new draft:
  - User selects a document type and optionally names the draft.
  - System creates a `DraftSession` and triggers a background research job:
    - Gathers relevant documents.
    - Builds a case profile and initial outline using rulebook rules and RAG.
  - User may continue working while research completes.
- Intake questioning:
  - Once research is ready, assistant invites the user to answer guided questions derived from the rulebook intake schema.
  - Questions are asked one at a time in a clear, structured UI.
  - Answers are stored and validated; missing critical information is highlighted.

#### 4.6 Draft Generation and Review

- Triggering draft generation:
  - When required intake is complete, user (or system) starts draft generation.
  - Draft generation runs asynchronously in a queue; `DraftSession` status is updated to `generating`.
- Completion:
  - On success, status transitions to `ready` and DraftDoc JSON is stored.
  - System notifies user via in‑app message and optional email.
- Reviewing drafts:
  - User opens the draft in a structured editor showing sections and paragraphs.
  - Normal View:
    - Clean presentation with small citation markers.
  - Audit Mode:
    - Split view showing draft text on one side and linked source snippets on the other.
  - User can:
    - Edit text (rich text operations).
    - Inspect citations and navigate back to source documents.

#### 4.7 Finalisation and Export

- Before finalisation, system can run:
  - Citation verification.
  - Completeness checks based on rulebook validation rules.
- Finalisation:
  - User selects citation format (e.g. endnotes, inline, none).
  - System generates a court‑ready PDF (and optionally Word/Docx).
  - System preserves version history for drafts.

#### 4.8 Help & Learn

- The system provides a **Help & Learn experience** focused on integrated, contextual help rather than long-form manuals.
- Contextual help includes:
  - Inline hints and helper text near complex controls (e.g. drafting options, citation tools, rulebook admin).
  - “What is this?” tooltips on key UI elements (e.g. DraftSession status, document types, evidence tags).
  - Short, task-focused overlays for first-time flows (e.g. “How to start your first draft”).
- A lightweight Help menu gives access to:
  - A small set of curated “how-to” topics.
  - Links to support/contact and privacy/terms.
- Users can give thumbs-up/down feedback on individual help tooltips or overlays, with optional comments, so admins can improve or retire confusing help content over time.

---

### 5. Worker‑Based Orchestration and Scalability

#### 5.1 Job Types and Responsibilities

- **DocumentProcessingJob**
  - Triggered when a document is uploaded.
  - Performs OCR (if needed), text extraction, chunking, embedding, and indexing.
  - Updates per‑document status (`overall_status`, `stage`, `stage_progress`) and upload‑session progress.
  - Emits `document.completed` or `document.failed` events when done.

- **DraftResearchJob**
  - Triggered when a new DraftSession is created.
  - Runs RAG over case materials, builds a case profile and outline using the selected rulebook.
  - Marks DraftSession as `awaiting_intake` and persists summarised research context.
  - Emits `draft.research_ready` so the assistant can start asking questions when the user is in the case.

- **DraftGenerationJob**
  - Triggered explicitly by the user (or automatically once intake is complete).
  - Uses the rulebook, intake answers, and research context to call the drafting LLM and produce DraftDoc JSON.
  - Validates the DraftDoc, persists it, creates citations, and updates DraftSession status to `ready` (or `failed`).
  - Emits `draft.completed` or `draft.failed` events for notifications.

- **Auxiliary Jobs (optional)**
  - Citation verification jobs, audit‑rebuild jobs, and export jobs can also be queued to keep the UI responsive for very large drafts.

#### 5.2 Queue and Worker Model

- API layer:
  - Accepts user actions (upload, start draft, start generation) and **enqueues jobs** into a durable queue (e.g. Redis‑backed).
  - Returns immediately with IDs for documents, upload sessions, and DraftSessions so the frontend can show pending states.
- Worker pool:
  - Horizontally scalable pool of workers for each job type.
  - Jobs are idempotent and transactional where they modify persistent state.
  - Job timeouts and retry policies are defined per job type (e.g. OCR vs drafting).

#### 5.3 Eventing and Notifications

- Workers publish domain events when significant transitions occur:
  - `document.completed`, `document.failed`, `upload_session.completed`.
  - `draft.research_ready`, `draft.completed`, `draft.failed`.
- Notification layer:
  - Consumes events and:
    - Pushes in‑app updates via SSE/WebSockets or short‑interval polling.
    - Sends optional email notifications when long‑running jobs complete.
    - Triggers proactive prompts in the assistant when a batch of documents has finished processing (e.g. suggest relevant document types to generate).
- Frontend:
  - Subscribes to updates for the current user’s relevant IDs (cases, upload sessions, DraftSessions).
  - Updates progress indicators and banners without blocking user interaction.

#### 5.4 Scaling Behaviour

- Adding more workers increases throughput for:
  - Document ingestion and OCR (I/O and CPU‑heavy).
  - Draft research and generation (LLM‑bound).
- API servers:
  - Stay focused on fast, lightweight operations (validation, enqueuing, reads).
  - Do not execute heavy processing, which allows independent scaling of API and workers.

---

### 6. Admin Flows

#### 5.1 Rulebook Management

- View list of rulebooks:
  - Filter by document type, jurisdiction, and status.
  - Inspect metadata (version, last updated, updated by).
- Create and edit rulebooks:
  - Edit raw YAML (`source_yaml`) in a syntax‑highlighted editor.
  - On save, backend parses and validates YAML into `rules_json`.
  - Save as `draft` when validation passes; show detailed error messages if it fails.
- Version control:
  - Duplicate an existing rulebook as a new version.
  - Publish a validated draft, making it available for new DraftSessions.
  - Deprecate older versions without affecting existing drafts linked to those versions.

#### 5.2 Rulebook Testing

- From the rulebook edit screen, admin can:
  - Use an auto‑generated intake form based on `rules_json` to provide sample answers.
  - Optionally select example documents for test runs.
- Test actions:
  - Run validation‑only to see if all required inputs/sections are satisfied.
  - Run a full test to generate a sample DraftDoc using the standard drafting pipeline.
- Results:
  - Validation summary (pass/fail with messages).
  - Outline and sample content of the generated DraftDoc.
  - Warnings around missing or weakly supported sections.

#### 5.3 Monitoring and Troubleshooting

- Admin can:
  - View recent processing failures for documents and drafts with error details.
  - View simple dashboards for queue length, throughput, and error rates.
  - Inspect status of long‑running jobs for specific cases or users.

---

### 7. External Integrations (Functional View)

- **Authentication**
  - Integrate with a chosen auth mechanism (e.g. external provider or built‑in JWT) so only authorised users can access cases and documents.
- **AI Providers**
  - Provide abstraction for LLMs and embedding models so that different providers (OpenAI, Anthropic, local models) can be used without changing business logic.
- **Notification Channels**
  - Provide mechanisms for in‑app notifications and optional email notifications triggered by document processing completion and draft readiness.

---

### 8. Out‑of‑Scope for This Version

- Full multi‑jurisdiction support beyond South Africa (architecture should allow this later).
- Deep integrations with third‑party practice management or billing systems.
- Real‑time collaborative editing of drafts by multiple users.

