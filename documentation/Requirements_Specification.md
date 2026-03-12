## Junior Counsel – Requirements Specification

### 1. Introduction

This Requirements Specification captures what the new Junior Counsel platform must achieve, based on:

- The existing system behaviour and architecture.
- New functional goals for document processing, drafting, and RAG.
- Market context from the customer email describing advocates and attorneys as target users.

The primary objective is to deliver a **court‑ready drafting assistant for South African legal practitioners**, with strong support for research and document management.

---

### 2. Business and Market Requirements

#### BR‑1 Primary Value Proposition – Court‑Ready Drafting

- The system’s main unique selling point must be the ability to generate **court‑ready legal documents** (e.g. affidavits, pleadings, heads of argument) suitable for filing in South African courts.
- Legal research and generic drafting are important supporting features, but **all product decisions must prioritise court‑ready drafting quality.**

#### BR‑2 Support for Practising Advocates

- The system must support workflows common to practising advocates:
  - Drafting pleadings, argumentative documents, affidavits, and heads of argument based on briefs and case materials.
  - Handling matters predominantly in the High Court and above.
- The quality of drafts must be good enough that experienced advocates are comfortable signing them after human review.

#### BR‑3 Support for Attorneys and Smaller Firms

- The system must enable attorneys, especially in **small and medium‑sized firms**, to:
  - Draft more court documents in‑house, even when they do not consider themselves specialist drafters.
  - Reduce reliance on external advocates for routine drafting, thereby retaining more revenue.
- The drafting assistant must be **guided and supportive**, reducing the skill and time barrier to high‑quality drafting.

#### BR‑4 Individual Adoption in Larger Firms

- The system must be usable and valuable for **individual attorneys or advocates** within larger firms, even where firm‑wide tools (e.g. Harvey AI) exist.
- The platform must:
  - Be accessible as a standalone web application with self‑service onboarding.
  - Offer drafting capabilities that are clearly differentiated from generic firm‑wide tools.

#### BR‑5 South African Litigation Focus (Initial)

- The initial implementation must focus on **South African civil litigation practice**, including:
  - High Court and Magistrates’ Court document types.
  - Local procedural rules, terminology, and document structures.
- The architecture must allow additional jurisdictions later without extensive refactoring.

#### BR‑6 Differentiation from Generic AI Tools

- Compared to general tools (ChatGPT, Claude, etc.) and content platforms (Juta, LexisNexis), Junior Counsel must:
  - Provide **structured, rule‑driven drafting** aligned with court expectations.
  - Always show/recover **sources and citations** for factual or legal propositions drawn from uploaded materials.
  - Provide **guided intake and validation** rather than requiring the user to craft complex prompts.

---

### 3. Functional Requirements

#### 3.1 Organisation, User, and Case Management

- **FR‑1**: The system must support **organisations/companies** (e.g. law firms or advocates’ chambers) as first-class entities.
- **FR‑1a**: Each organisation must have one or more **organisation admins** who can:
  - Invite users by email.
  - Assign and revoke roles (e.g. admin, practitioner, staff).
  - View and manage the organisation’s subscription/billing metadata (if applicable later).
- **FR‑1b**: Users must belong to at least one organisation; a user may optionally belong to multiple organisations.
- **FR‑1c**: Cases and documents must be scoped to an organisation, and by default are **shared among all authorised users in that organisation**, subject to role-based access (e.g. some users may have read-only access).
- **FR‑1d**: The system must allow, but not require, finer-grained sharing controls within an organisation (e.g. restricting a sensitive case to a subgroup), to be configured by organisation admins.
- **FR‑2**: The system must allow authenticated users to create, view, update, and archive cases within organisations they are permitted to access.
- **FR‑3**: Each case must serve as a container for documents, chat sessions, and drafting sessions.
- **FR‑4**: Access control must ensure that users can only see and modify cases and documents they are authorised to access, taking both organisation and role into account.

#### 3.2 Document Ingestion, OCR, and Processing

- **FR‑5**: Users must be able to upload multiple documents to a case in a single operation.
- **FR‑6**: The system must detect whether a document needs OCR (e.g. image‑based PDFs, image files) and mark it accordingly.
- **FR‑7**: Document processing (OCR, text extraction, chunking, embedding, indexing) must be performed asynchronously via a queue; HTTP requests must only enqueue work, not perform it.
- **FR‑8**: The system must track per‑document processing status:
  - `overall_status` (queued, processing, completed, failed).
  - `stage` (uploading, ocr, text_extraction, chunking, embedding, indexing).
  - `stage_progress` (0–100).
- **FR‑9**: The system must store OCR results and, where possible, confidence measures and basic layout information (e.g. page and text positioning) to support precise citations.

#### 3.3 Document Classification and Metadata

- **FR‑10**: The system must allow users to classify each document with:
  - `document_type` (e.g. pleading, evidence, correspondence, order, research, other).
  - Optional subtype and tags.
- **FR‑11**: The system must provide AI‑based suggestions for document type and subtype, which users can accept or override.
- **FR‑12**: Users must be able to filter and search documents within a case by type, subtype, tags, and processing status.

#### 3.4 Progress Indicators and Notifications

- **FR‑13**: The system must maintain `UploadSession`s grouping documents uploaded together, with batch‑level status and counts (total, completed, failed).
- **FR‑14**: The API must expose document and upload‑session status sufficient for the frontend to render progress bars and status indicators.
- **FR‑15**: The system must notify users when:
  - Document processing completes (success or failure).
  - Draft generation completes (success or failure).
- **FR‑16**: Notifications must at least be available in‑app and may optionally be delivered via email.

#### 3.5 Vector Search and RAG

- **FR‑17**: The system must store vector embeddings for `DocumentChunk`s in a Postgres+pgvector schema.
- **FR‑18**: Each `DocumentChunk` must include metadata fields to distinguish content types and roles (e.g. document type, section type, semantic role).
- **FR‑19**: Search endpoints must:
  - Accept natural‑language queries.
  - Support filters by document type, role, tags, and case.
  - Return ranked chunks with sufficient context (snippet, page, paragraph) for user evaluation.
- **FR‑20**: RAG‑based Q&A endpoints must:
  - Use search results to construct the context.
  - Return answers with explicit citations to the underlying chunks/documents.
  - Provide enough metadata for the UI to highlight and navigate to sources.

#### 3.6 Chat and Proactive Assistant Behaviour

- **FR‑21**: The system must support `ChatSession`s associated with cases, storing all user and assistant messages.
- **FR‑22**: When a user opens a case, the system must return:
  - Active DraftSessions and their statuses.
  - Suggested next drafting actions (e.g. continue an existing draft or start a new one).
- **FR‑23**: The assistant must be able to:
  - Prompt the user with clarifying or intake questions when they return to a case.
  - Guide them through selecting which document they wish to generate next.
- **FR‑24**: Long‑running tasks triggered by the assistant (research, generation) must run asynchronously; the user must be informed that processing is underway and notified when it concludes.

#### 3.7 Drafting and DraftSessions

- **FR‑25**: The system must support `DraftSession`s linked to specific cases and document types.
- **FR‑26**: Each DraftSession must be associated with a specific `Rulebook` version and retain that association for its lifetime.
- **FR‑27**: DraftSessions must follow a status lifecycle that at minimum covers initializing, awaiting_intake, generating, ready, and failed.
- **FR‑28**: The system must automatically run a **research step** for new DraftSessions, selecting relevant documents and building a case profile and outline in the background.
- **FR‑29**: The system must drive **intake questioning** from the rulebook’s intake schema, asking one question at a time and storing answers.
- **FR‑30**: The system must only proceed to draft generation when required intake answers are present, given the rulebook’s validation rules.
- **FR‑31**: Draft generation must:
  - Produce a structured DraftDoc JSON with sections and paragraphs.
  - Attach or reference citations to the supporting source material.
- **FR‑32**: Users must be able to review and edit drafts, including:
  - Normal view (clean document with small citation markers).
  - Audit mode (split view with source snippets for each citation).

#### 3.8 Finalisation and Export

- **FR‑33**: The system must support citation verification for DraftDocs before finalisation.
- **FR‑34**: The system must run completeness checks using rulebook validation rules and highlight missing sections or inputs before finalisation.
- **FR‑35**: Users must be able to choose a citation format (e.g. endnotes, inline, none) when finalising.
- **FR‑36**: The system must export court‑ready PDFs with correct formatting for common South African court documents.
- **FR‑37**: The system must maintain version history for drafts so previous versions can be inspected.

#### 3.9 Rulebook and YAML Management (Admin)

- **FR‑38**: Rulebooks must be stored in Postgres with both raw YAML (`source_yaml`) and parsed JSON (`rules_json`).
- **FR‑39**: Each rulebook must be identified by document type, jurisdiction, version, and status (draft, published, deprecated).
- **FR‑40**: The system must validate rulebooks against a well‑defined schema before they can be marked `published`.
- **FR‑41**: Only rulebooks with status `published` may be used for new DraftSessions.
- **FR‑42**: Admin users must be able to:
  - Create, edit, and delete draft rulebooks.
  - Publish and deprecate rulebooks.
  - Duplicate existing rulebooks as new versions.
- **FR‑43**: The admin UI must provide:
  - A syntax‑highlighted YAML editor.
  - Real‑time validation feedback on errors.
  - A test harness to run validation and sample generation against a rulebook.

#### 3.10 Token Usage Tracking and Cost Management

- **FR‑44**: The system must track all API token usage for cost attribution and transparency:
  - LLM generation calls (Q&A, drafting)
  - Embedding generation calls (document processing, search)
  - OCR API calls (if using paid service)
- **FR‑45**: Each API call must record:
  - Provider (openai, anthropic) and model used
  - Token counts (input tokens, output tokens, total tokens)
  - User, organisation, and case attribution
  - Resource context (draft_session_id, document_id, chat_session_id, etc.)
  - Estimated cost in USD based on current API pricing
  - Timestamp
- **FR‑46**: Users must be able to view their own usage dashboard showing:
  - Monthly token usage and estimated costs
  - Breakdown by usage type (drafting, Q&A, embeddings, OCR)
  - Top cases by cost
  - Usage trends over time (last 6 months)
- **FR‑47**: Organisation admins must be able to view organisation‑wide usage:
  - Total usage across all users in the organisation
  - Per‑user usage breakdown
  - Per‑case cost attribution
  - Filterable by date range, user, case, usage type
  - Exportable usage reports (CSV format)
- **FR‑48**: The system must support optional usage quotas and alerts:
  - Monthly token quotas per organisation (null = unlimited)
  - Monthly cost quotas in USD (null = unlimited)
  - Automatic enforcement (return HTTP 429 when quota exceeded)
  - Warning notifications sent at 80% and 100% quota usage
  - Grace period configuration for quota overruns

---

### 4. Non‑Functional Requirements

#### 4.1 Performance

- **NFR‑1**: Upload requests must return (after enqueuing processing) within a few seconds under normal load, regardless of document size.
- **NFR‑2**: Search endpoints must typically respond within 1–2 seconds for normal queries over realistic document volumes.
- **NFR‑3**: Q&A/drafting endpoints must respond within reasonable limits determined largely by model latency (typically under 5–8 seconds for a first answer), with results streamed where appropriate.
- **NFR‑4**: Status updates for document and draft processing must be visible in the UI with effective latency of no more than 5 seconds (via polling or event streaming).

#### 4.2 Scalability and Reliability

- **NFR‑5**: The queue and worker architecture must support horizontal scaling of processing and drafting workers without changes to business logic.
- **NFR‑6**: Long‑running jobs must be idempotent and resilient to worker restarts; repeating a job must not corrupt state.
- **NFR‑7**: Failures in OCR or drafting must surface clear, actionable error messages to users and admins, and allow for manual retry.
- **NFR‑7a**: All heavy operations (document processing, OCR, RAG research, draft generation, citation verification) must be executed via a durable job queue, not directly in API request/response handlers.
- **NFR‑7b**: It must be possible to scale the number of worker processes/containers independently of the API layer to handle increased load, without code changes (configuration only).

#### 4.3 Security and Compliance

- **NFR‑8**: All access must be authenticated; sensitive operations (e.g. rulebook editing, case access) must be authorised according to user roles.
- **NFR‑9**: All application traffic must be encrypted in transit using TLS.
- **NFR‑10**: Sensitive data at rest (documents, personal info) must be stored in encrypted storage where required by regulation or agreed with the customer.
- **NFR‑11**: The system must support operation in a South African data centre to meet local data residency expectations.
- **NFR‑12**: Audit logs must be maintained for key actions, including:
  - Logins and authentication changes.
  - Rulebook creation, modification, and publication.
  - Document deletions.
  - Draft finalisation and exports.

#### 4.4 Maintainability and Extensibility

- **NFR‑13**: New document types and jurisdictions should be introducible by adding or modifying rulebooks (YAML + DB records) without core code changes, except where new features are required.
- **NFR‑14**: AI providers (LLMs, embeddings, OCR) must be accessed via clear abstractions so they can be swapped or reconfigured without pervasive changes.
- **NFR‑15**: The API must be documented using an OpenAPI/Swagger definition and must follow stable versioning practices when breaking changes are introduced.

#### 4.5 Usability

- **NFR‑16**: The user interface must use legal domain terms (cases, pleadings, affidavits, etc.) and avoid exposing low‑level AI concepts to end users.
- **NFR‑17**: Information about status and progress must be presented in a way that is immediately understandable (e.g. simple labels and progress bars).
- **NFR‑18**: Admin tooling must provide clear feedback on validation errors when editing YAML, including locations and human‑readable messages.
- **NFR‑19**: The system must provide integrated, contextual help (inline hints, tooltips, and first-time overlays) for complex flows such as drafting, attaching evidence, and managing rulebooks, and must allow users to give simple feedback (e.g. thumbs-up/down with optional comment) on help elements to support continuous improvement.

---

### 5. Assumptions and Constraints

- **AC‑1**: Initial users are South African legal practitioners with varying levels of drafting confidence and technical familiarity.
- **AC‑2**: Initial deployments are expected to be single‑region (South Africa), with possible expansion to multi‑region later.
- **AC‑3**: LLM and embedding providers may change over time; the system must be robust to such changes via configuration.
- **AC‑4**: This document does not define pricing or licensing models, but functional and non‑functional requirements must support both solo practitioners and firm‑level usage.
- **AC‑5**: Retrieval over external common‑law corpora (e.g. imported judgments, statutory databases) may be added later; the search and RAG design must allow additional corpora or indices to be integrated alongside case documents without major redesign.

