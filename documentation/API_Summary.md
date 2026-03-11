# Junior Counsel API Summary

**Status:** Phase 2 Complete
**API Version:** v1
**Base URL:** `http://localhost:8000`
**OpenAPI Docs:** `http://localhost:8000/docs`
**ReDoc:** `http://localhost:8000/redoc`

## Overview

Complete REST API implementation for Junior Counsel legal document processing system. All endpoints require JWT authentication (except registration and login).

## Authentication

### Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/auth/register` | Create new user account | No |
| POST | `/api/v1/auth/login` | Login and get JWT token | No |
| GET | `/api/v1/auth/me` | Get current user info | Yes |

### Authentication Flow

1. **Register:** POST `/api/v1/auth/register` with `{email, password, full_name}`
2. **Login:** POST `/api/v1/auth/login` with OAuth2 form data `{username=email, password}`
3. **Response:** Receive `{access_token, token_type: "bearer"}`
4. **Use Token:** Include in requests: `Authorization: Bearer {access_token}`
5. **Token Expiry:** 30 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)

### Example

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "advocate@example.com", "password": "secret123", "full_name": "John Smith"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=advocate@example.com&password=secret123"

# Response
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}

# Use token
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## API Resources

### 1. Organisations

Multi-tenant container for cases and users.

| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| POST | `/organisations/` | Create organisation | 201, OrganisationResponse |
| GET | `/organisations/{id}` | Get by ID | 200, OrganisationResponse |
| GET | `/organisations/` | List active orgs | 200, [OrganisationResponse] |
| PATCH | `/organisations/{id}` | Update organisation | 200, OrganisationResponse |
| DELETE | `/organisations/{id}` | Soft delete (is_active=false) | 204 No Content |

**Create Schema:**
```json
{
  "name": "Smith & Associates",
  "contact_email": "info@smith.co.za",
  "is_active": true
}
```

### 2. Cases

Legal case container for documents and drafts.

| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| POST | `/cases/` | Create case | 201, CaseResponse |
| GET | `/cases/{id}` | Get by ID (UUID) | 200, CaseResponse |
| GET | `/cases/?organisation_id={id}` | List with pagination | 200, CaseListResponse |
| PATCH | `/cases/{id}` | Update case | 200, CaseResponse |
| DELETE | `/cases/{id}` | Hard delete | 204 No Content |

**Query Parameters (GET /cases/):**
- `organisation_id` (required): Filter by organisation
- `status`: Filter by CaseStatusEnum (active, closed, archived)
- `case_type`: Filter by case type (civil, criminal, etc.)
- `q`: Search in title and description (case-insensitive)
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20, max: 100)
- `sort`: Sort field (default: created_at)
- `order`: Sort order (asc/desc, default: desc)

**Create Schema:**
```json
{
  "organisation_id": 1,
  "title": "Smith v Jones",
  "owner_id": 123,
  "description": "Contract dispute",
  "case_type": "civil",
  "jurisdiction": "Gauteng High Court"
}
```

**List Response:**
```json
{
  "data": [...],
  "page": 1,
  "per_page": 20,
  "total": 150,
  "next_page": 2
}
```

### 3. Documents

Uploaded or generated documents with processing status tracking.

| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| POST | `/documents/` | Create document record | 201, DocumentResponse |
| GET | `/documents/{id}` | Get by ID (UUID) | 200, DocumentResponse |
| GET | `/documents/?case_id={id}` | List with pagination | 200, DocumentListResponse |
| PATCH | `/documents/{id}` | Update metadata | 200, DocumentResponse |
| PATCH | `/documents/{id}/status` | Update processing status | 200, DocumentResponse |
| DELETE | `/documents/{id}` | Hard delete | 204 No Content |

**Query Parameters (GET /documents/):**
- `case_id` (required): Filter by case
- `document_type`: Filter by type (pleading, evidence, etc.)
- `status`: Filter by DocumentStatusEnum (queued, processing, completed, failed)
- `q`: Search in filename (case-insensitive)
- `page`, `per_page`, `sort`, `order`: Pagination params

**Create Schema:**
```json
{
  "case_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "affidavit.pdf",
  "upload_session_id": "660e8400-e29b-41d4-a716-446655440001",
  "needs_ocr": true
}
```

**Status Update Schema:**
```json
{
  "overall_status": "processing",
  "stage": "embedding",
  "stage_progress": 75,
  "error_message": null
}
```

**Status Flow:**
- `queued` → Worker picks up job
- `processing` → OCR, text extraction, chunking, embedding
  - `stage`: ocr, text_extraction, chunking, embedding, indexing
  - `stage_progress`: 0-100
- `completed` → Ready for RAG
- `failed` → Error occurred (see error_message)

### 4. Upload Sessions

Batch upload tracking for multiple documents.

| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| POST | `/upload-sessions/` | Create upload session | 201, UploadSessionResponse |
| GET | `/upload-sessions/{id}` | Get by ID (UUID) | 200, UploadSessionResponse |
| GET | `/upload-sessions/?case_id={id}` | List with pagination | 200, UploadSessionListResponse |

**Create Schema:**
```json
{
  "case_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_documents": 10
}
```

**Response includes progress:**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "case_id": "550e8400-e29b-41d4-a716-446655440000",
  "uploaded_by_id": 123,
  "total_documents": 10,
  "completed_documents": 7,
  "failed_documents": 1,
  "created_at": "2026-03-11T14:30:00Z"
}
```

### 5. Draft Sessions

Document drafting workflow with rulebook-driven generation.

| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| POST | `/draft-sessions/` | Create draft session | 201, DraftSessionResponse |
| GET | `/draft-sessions/{id}` | Get by ID (UUID) | 200, DraftSessionResponse |
| GET | `/draft-sessions/?case_id={id}` | List with pagination | 200, DraftSessionListResponse |
| PATCH | `/draft-sessions/{id}` | Update session | 200, DraftSessionResponse |
| DELETE | `/draft-sessions/{id}` | Hard delete | 204 No Content |

**Query Parameters (GET /draft-sessions/):**
- `case_id` (required): Filter by case
- `status`: Filter by DraftSessionStatusEnum
- `page`, `per_page`, `sort`, `order`: Pagination params

**Create Schema:**
```json
{
  "case_id": "550e8400-e29b-41d4-a716-446655440000",
  "rulebook_id": 5,
  "title": "Affidavit for Motion Application",
  "document_type": "affidavit"
}
```

**Status Flow:**
- `intake` → User answers intake questions
- `research` → RAG search for relevant excerpts (background job)
- `drafting` → LLM generates draft (background job)
- `review` → User reviews and edits
- `completed` → Final document ready

**Update Schema:**
```json
{
  "title": "Updated Title",
  "intake_responses": {
    "deponent_name": "John Smith",
    "capacity": "Plaintiff",
    "facts": ["Signed contract on 2025-01-15", "Payment not received"]
  },
  "status": "research"
}
```

### 6. Rulebooks

Versioned YAML-based rules for document types (intake schema, templates, validation).

| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| POST | `/rulebooks/` | Create rulebook | 201, RulebookResponse |
| GET | `/rulebooks/{id}` | Get by ID | 200, RulebookResponse |
| GET | `/rulebooks/` | List with pagination | 200, RulebookListResponse |
| GET | `/rulebooks/published/{type}/{jurisdiction}` | Get published version | 200, RulebookResponse |
| PATCH | `/rulebooks/{id}` | Update rulebook | 200, RulebookResponse |
| DELETE | `/rulebooks/{id}` | Hard delete | 204 No Content |

**Query Parameters (GET /rulebooks/):**
- `document_type`: Filter by type (affidavit, pleading, heads_of_argument)
- `jurisdiction`: Filter by jurisdiction
- `status`: Filter by RulebookStatusEnum (draft, published, deprecated)
- `page`, `per_page`, `sort`, `order`: Pagination params

**Create Schema:**
```json
{
  "document_type": "affidavit",
  "jurisdiction": "Gauteng High Court",
  "version": "1.0.0",
  "source_yaml": "intake_questions:\n  - name: deponent_name\n    type: text\n...",
  "label": "Standard Affidavit Template"
}
```

**Lifecycle:**
- `draft` → Editable by admins
- `published` → Active version used for new DraftSessions
- `deprecated` → Old version (existing DraftSessions still use it)

**Published Lookup Example:**
```bash
GET /api/v1/rulebooks/published/affidavit/Gauteng%20High%20Court
```
Returns the latest published rulebook for that document type and jurisdiction.

## Response Formats

### Success Response (Single Resource)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "field1": "value1",
  "field2": "value2",
  "created_at": "2026-03-11T14:30:00Z",
  "updated_at": "2026-03-11T15:45:00Z"
}
```

### Success Response (List with Pagination)

```json
{
  "data": [
    { "id": "...", "field1": "..." },
    { "id": "...", "field1": "..." }
  ],
  "page": 1,
  "per_page": 20,
  "total": 150,
  "next_page": 2
}
```

### Error Response

```json
{
  "error": "Error message",
  "detail": "Detailed description",
  "code": 404
}
```

### HTTP Status Codes

- **200 OK**: Successful GET/PATCH request
- **201 Created**: Successful POST request
- **204 No Content**: Successful DELETE request
- **400 Bad Request**: Validation error
- **401 Unauthorized**: Missing or invalid JWT token
- **404 Not Found**: Resource not found
- **409 Conflict**: Duplicate resource (e.g., email already exists)
- **500 Internal Server Error**: Server error

## Enum Values

### CaseStatusEnum
- `active` - Case is active
- `closed` - Case has been closed
- `archived` - Case is archived

### DocumentStatusEnum
- `queued` - Waiting for processing
- `processing` - Currently being processed
- `completed` - Processing finished successfully
- `failed` - Processing failed (see error_message)

### DraftSessionStatusEnum
- `intake` - Collecting intake responses
- `research` - RAG research in progress
- `drafting` - LLM drafting in progress
- `review` - User reviewing draft
- `completed` - Draft finalized

### RulebookStatusEnum
- `draft` - Editable, not yet published
- `published` - Active version
- `deprecated` - Old version (no longer used for new drafts)

### OrganisationRoleEnum (not yet used in API)
- `admin` - Organisation administrator
- `practitioner` - Legal practitioner (advocate/attorney)
- `staff` - Staff member

## Data Flow Examples

### Complete Upload-to-Draft Flow

```bash
# 1. Register/Login
POST /api/v1/auth/register
POST /api/v1/auth/login
# -> Get access_token

# 2. Create organisation
POST /api/v1/organisations/
# -> org_id: 1

# 3. Create case
POST /api/v1/cases/
{
  "organisation_id": 1,
  "title": "Smith v Jones",
  "case_type": "civil",
  "jurisdiction": "Gauteng High Court"
}
# -> case_id: "550e8400-..."

# 4. Create upload session (optional, for batch tracking)
POST /api/v1/upload-sessions/
{
  "case_id": "550e8400-...",
  "total_documents": 5
}
# -> upload_session_id: "660e8400-..."

# 5. Upload documents (create document records)
POST /api/v1/documents/
{
  "case_id": "550e8400-...",
  "filename": "contract.pdf",
  "upload_session_id": "660e8400-...",
  "needs_ocr": true
}
# -> document_id: "770e8400-..."
# Repeat for each document

# 6. Workers process documents (background)
# - OCR extraction
# - Text chunking
# - Embedding generation
# - Indexing in pgvector
# Workers update status via:
PATCH /api/v1/documents/770e8400-.../status
{
  "overall_status": "processing",
  "stage": "embedding",
  "stage_progress": 75
}

# 7. Monitor document status
GET /api/v1/documents/770e8400-...
# -> overall_status: "completed"

# 8. Get published rulebook
GET /api/v1/rulebooks/published/affidavit/Gauteng%20High%20Court
# -> rulebook_id: 5

# 9. Start draft session
POST /api/v1/draft-sessions/
{
  "case_id": "550e8400-...",
  "rulebook_id": 5,
  "title": "Affidavit for Motion",
  "document_type": "affidavit"
}
# -> draft_session_id: "880e8400-..."
# -> status: "intake"

# 10. Submit intake responses
PATCH /api/v1/draft-sessions/880e8400-...
{
  "intake_responses": {
    "deponent_name": "John Smith",
    "capacity": "Plaintiff",
    "facts": ["Contract signed", "Payment not received"]
  },
  "status": "research"
}
# Workers start RAG research (background)

# 11. Monitor draft status
GET /api/v1/draft-sessions/880e8400-...
# -> status: "research" | "drafting" | "review" | "completed"

# 12. Get final draft
GET /api/v1/draft-sessions/880e8400-...
# -> final_content: "I, John Smith, ..."
```

## Security

### Authentication
- JWT tokens with HS256 algorithm
- Tokens expire after 30 minutes (configurable)
- Passwords hashed with bcrypt (via passlib)

### Authorization
- All endpoints (except register/login) require valid JWT token
- Current implementation: User must be authenticated
- Future: Role-based access control (RBAC) with OrganisationRoleEnum

### Data Access
- Cases scoped to organisations
- Documents scoped to cases
- DraftSessions scoped to cases
- Users can access resources in their organisations (future: via OrganisationUser)

## Development

### Running the API

```bash
# Start server with hot-reload
cd /path/to/JuniorCounsel
PYTHONPATH=src uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Interactive API Docs

- **Swagger UI**: http://localhost:8000/docs
  - Try out endpoints directly
  - See request/response schemas
  - Authorize with JWT token

- **ReDoc**: http://localhost:8000/redoc
  - Clean documentation view
  - Searchable
  - Export as HTML

### Environment Variables

Required in `.env`:

```bash
# Database
DATABASE_URL=postgresql://localhost/junior_counsel_dev
TEST_DATABASE_URL=postgresql://localhost/junior_counsel_test

# Authentication
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Application
APP_NAME=Junior Counsel
APP_URL=http://localhost:8000
RELOAD=true
```

## Testing

### Manual Testing with curl

```bash
# Health check (no auth)
curl http://localhost:8000/health

# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "test123", "full_name": "Test User"}'

# Login
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=test123" | jq -r '.access_token')

# Create organisation (with auth)
curl -X POST http://localhost:8000/api/v1/organisations/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Org", "contact_email": "org@example.com"}'
```

### Automated Tests (Future)

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests (API endpoints)
pytest tests/integration/ -v

# Full test suite
pytest --cov=src/app
```

## Next Steps

Phase 2 is complete. Remaining work:

### Phase 2.4 - Worker Integration
- Redis/Valkey queue setup
- RQ or Celery worker implementation
- DocumentProcessingJob handler
- DraftResearchJob handler
- DraftGenerationJob handler
- Job status polling endpoints

### Phase 2.5 - Integration Testing
- Create test database (`createdb junior_counsel_test`)
- Install pgvector extension
- Run Phase 1 unit tests (pytest tests/unit/)
- Write API integration tests (pytest tests/integration/)
- Test authentication flow
- Test pagination
- Test filtering
- Test error handling

### Phase 3 - AI Integration
- OpenAI/Anthropic API clients
- Embedding generation (document chunks)
- RAG search implementation (pgvector similarity)
- LLM drafting with structured prompts
- Citation extraction and validation
- Streaming response support

### Phase 4 - Frontend
- Next.js application
- Authentication UI (login/register)
- Case management dashboard
- Document upload UI with progress tracking
- Draft session wizard (intake → research → review)
- Document viewer with citation highlighting

## API Statistics

- **Total Routes**: 39
- **API v1 Endpoints**: 33
- **Resource Types**: 7 (Auth, Organisations, Cases, Documents, UploadSessions, DraftSessions, Rulebooks)
- **CRUD Resources**: 6 (Organisations, Cases, Documents, UploadSessions, DraftSessions, Rulebooks)
- **Paginated Endpoints**: 6 (Cases, Documents, UploadSessions, DraftSessions, Rulebooks, Organisations)
- **Filter Parameters**: 11 unique filters across resources
- **Pydantic Schemas**: 20 schemas (Create, Update, Response, List types)

---

**Generated**: 2026-03-11
**API Version**: 1.0.0
**Phase**: 2.3 Complete
**Status**: Ready for database testing and worker integration
