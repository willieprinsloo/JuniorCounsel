# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Junior Counsel** is a legal document processing and drafting system for South African litigation practice. The system uses RAG (Retrieval-Augmented Generation) to help advocates and attorneys draft court-ready documents (affidavits, pleadings, heads of argument) based on case materials.

**Current Status**: In early development. The project is a rebuild/rewrite. The `old code/` directory contains the previous Django-based implementation for reference only. Active development is in `src/`.

**Target Users**: South African legal practitioners (advocates and attorneys) who need to draft court documents with proper citations and evidence support.

## Project Structure

```
src/
├── app/
│   ├── core/           # Configuration, database, logging
│   ├── auth/           # Authentication logic (to be implemented)
│   ├── persistence/    # SQLAlchemy models and repositories
│   └── api/v1/         # REST endpoints (to be implemented)
tests/                  # pytest unit and integration tests
documentation/          # Requirements, architecture, and functional specs
old code/jc/            # Legacy Django implementation (reference only)
```

## Technology Stack

### Core Stack (from development_guidelines.md)
- **Language**: Python 3.9+
- **Framework**: Flask 3.0+ (or FastAPI - final choice TBD)
- **Database**: PostgreSQL with pgvector extension
- **ORM**: SQLAlchemy 2.0+
- **Auth**: Flask Basic Authentication or JWT (TBD)
- **Testing**: pytest
- **Queue**: Redis/Valkey with RQ or Celery
- **Config**: Pydantic BaseSettings with `.env`

### Frontend (planned)
- Next.js (React + TypeScript)
- Tailwind CSS

## Development Commands

### Environment Setup
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies (when requirements.txt exists)
pip install -r requirements.txt
```

### Database
```bash
# In development/test, use Base.metadata.create_all() for schema
# Production: manual SQL for schema changes
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_example.py

# Run with coverage
pytest --cov=src/app
```

### Code Quality
Follow the patterns in `documentation/development_guidelines.md`:
- Use SQLAlchemy 2.0 mapped_column syntax
- Repository pattern for data access
- Pydantic for validation and config
- Context managers for DB sessions

## Architecture Overview

### Worker-Based Orchestration
**CRITICAL**: All heavy work (OCR, embeddings, RAG, drafting, verification) runs in **background workers**, NOT in API request handlers. The API layer only enqueues jobs and returns immediately.

### Job Types
1. **DocumentProcessingJob**: OCR, text extraction, chunking, embedding, indexing
2. **DraftResearchJob**: RAG search, case profiling, outline generation
3. **DraftGenerationJob**: LLM-based drafting of court documents
4. **Auxiliary Jobs**: Citation verification, audit rebuild, PDF/DOCX export

### Event-Driven Notifications
Workers emit domain events (`document.completed`, `draft.research_ready`, etc.) that drive:
- In-app notifications (SSE/WebSocket or polling)
- Optional email notifications (via Resend API)
- Proactive assistant prompts

### Data Model (Core Entities)
- **Organisation**: Law firms/chambers; users belong to organisations
- **User**: Authenticated practitioners
- **OrganisationUser**: Join table with roles (admin, practitioner, staff)
- **Case**: Container for documents, chat sessions, and drafts
- **Document**: Uploaded or generated files with processing state tracking
- **DocumentChunk**: Vector-embedded segments for RAG (stored in pgvector)
- **UploadSession**: Batch tracking for multi-document uploads
- **ChatSession**: Q&A conversations within a case context
- **DraftSession**: Drafting workflow with status lifecycle
- **Rulebook**: YAML-based configuration for document types (intake schema, templates, validation rules)
- **Citation**: Links between generated documents and source chunks

### Status Tracking Pattern
Documents and DraftSessions use a multi-level status pattern:
- `overall_status`: queued, processing, completed, failed
- `stage`: specific processing stage (ocr, text_extraction, chunking, embedding, etc.)
- `stage_progress`: 0-100 numeric progress

## Key Design Principles

### Court-Ready Drafting Focus
The primary value proposition is generating **court-ready documents** for South African litigation. All product decisions prioritize drafting quality over generic research features.

### Rulebook-Driven Approach
Each document type (affidavit, pleading, heads of argument) has a versioned **Rulebook** stored in Postgres:
- `source_yaml`: Raw YAML edited by admins
- `rules_json`: Validated, parsed JSON
- Defines: intake questions, document structure, validation rules, drafting prompts

### Proactive Assistant
The system proactively guides users:
- After documents finish processing: "What do you want to generate?"
- After draft research completes: "Let's answer a few questions"
- After draft generation: "Your draft is ready to review"

### Citation Integrity
Every generated statement must be traceable to source documents with:
- Page and paragraph references
- Bounding box coordinates (when available)
- Audit mode showing side-by-side source excerpts

## API Design Standards

### Versioning
All endpoints under `/api/v1/...`

### Response Format
```json
{
  "data": [...],
  "page": 1,
  "per_page": 20,
  "total": 100,
  "next_page": 2
}
```

### Error Format
```json
{
  "error": "Invalid credentials",
  "code": 401
}
```

### Search & Pagination
- Query params: `q`, `page`, `per_page`, `sort`, `order`
- Default `per_page=20`, max `100`
- Case-insensitive substring search using `ILIKE`
- Support filters by document type, semantic role, tags, dates

## Testing Strategy

### Test Database
Use `TEST_DATABASE_URL` from environment for isolated test runs.

### Fixtures (tests/conftest.py)
```python
@pytest.fixture(scope="session")
def app():
    os.environ["ENV"] = "test"
    _app = create_app()
    Base.metadata.drop_all(get_engine())
    Base.metadata.create_all(get_engine())
    yield _app
    Base.metadata.drop_all(get_engine())

@pytest.fixture()
def client(app):
    return app.test_client()

@pytest.fixture()
def db_session():
    with session_scope() as s:
        yield s
```

### Test Coverage Requirements
- Unit tests for all repositories (CRUD operations, filters, transactions)
- Integration tests for API endpoints (auth, validation, pagination)
- Job handler tests with mocked AI providers
- Event emission and notification tests

## AI Provider Abstraction

All AI/ML operations go through provider interfaces in `core/ai_providers.py`:
- **Embeddings**: Vector generation for document chunks
- **Chat/Q&A**: RAG-based question answering
- **Drafting**: Structured document generation

**Why**: Allows swapping OpenAI, Anthropic, or local models without changing business logic.

**Testing**: Use stub providers that return fixed responses for deterministic tests.

## Important Constraints

### Security
- All access must be authenticated and role-authorized
- HTTPS required for all traffic
- No plain-text passwords (use werkzeug.security password hashing)
- Rate-limit login attempts
- South African data residency for compliance

### Scalability
- API servers are stateless and horizontally scalable
- Workers scale independently per queue type
- DB connection pooling: `pool_size=5, max_overflow=10, pool_pre_ping=True`
- Jobs must be idempotent and handle worker restarts

### Performance Targets
- Upload/enqueue requests: < 3 seconds
- Search queries: 1-2 seconds
- Q&A/drafting: 5-8 seconds (model-dependent), with streaming
- Status updates visible within 5 seconds

## Documentation References

Critical reading for understanding the system:
1. **documentation/development_guidelines.md**: Technical standards (DB, API, testing patterns)
2. **documentation/Requirements_Specification.md**: Business and functional requirements
3. **documentation/Architecture.md**: Component architecture and data flow
4. **documentation/Functional_Specification.md**: User flows and domain objects
5. **documentation/Development_Plan.md**: Phased implementation approach

The old code directory (`old code/jc/`) contains a Django-based implementation with extensive docs on RAG pipelines, vector search, and legal document processing - useful for reference but not the active codebase.

## Common Gotchas

1. **Don't do heavy work in API handlers** - always enqueue jobs for OCR, embeddings, LLM calls
2. **Status tracking is multi-level** - update both `overall_status` and `stage`/`stage_progress`
3. **DraftSessions are tied to Rulebook versions** - once created, they retain that version for life
4. **Organisation scoping** - cases and documents belong to organisations, not just users
5. **pgvector indexes** - use HNSW or IVF for vector similarity, always combine with metadata filters
6. **Citation format choice** - users choose endnotes/inline/none at finalisation time, not during generation
