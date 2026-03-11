# Phase 2 - API Endpoint Specification

## Overview

This document defines all REST API endpoints to be implemented in Phase 2, based on the Phase 1 repository implementations.

**Total Endpoints**: 27
**Pagination Required**: 6 endpoints
**Authentication**: Required on all endpoints
**Base URL**: `/api/v1`

---

## 1. Organisation Endpoints

### 1.1 List User's Organisations
```
GET /api/v1/organisations
```

**Authentication**: Required
**Returns**: List of organisations the authenticated user belongs to

**Response**:
```json
{
  "data": [
    {
      "id": 1,
      "name": "Smith & Partners Attorneys",
      "contact_email": "admin@smithpartners.co.za",
      "is_active": true,
      "user_role": "admin",
      "created_at": "2026-01-15T10:30:00Z"
    }
  ]
}
```

### 1.2 Get Organisation Details
```
GET /api/v1/organisations/{id}
```

**Authentication**: Required
**Authorization**: User must belong to organisation

**Response**:
```json
{
  "data": {
    "id": 1,
    "name": "Smith & Partners Attorneys",
    "contact_email": "admin@smithpartners.co.za",
    "is_active": true,
    "user_count": 15,
    "case_count": 42,
    "created_at": "2026-01-15T10:30:00Z"
  }
}
```

### 1.3 Create Organisation
```
POST /api/v1/organisations
```

**Authentication**: Required
**Authorization**: Any authenticated user (becomes admin of new org)

**Request**:
```json
{
  "name": "New Law Firm",
  "contact_email": "admin@newfirm.co.za"
}
```

**Response**: `201 Created`

### 1.4 Invite User to Organisation
```
POST /api/v1/organisations/{id}/users
```

**Authentication**: Required
**Authorization**: User must be admin of organisation

**Request**:
```json
{
  "email": "advocate@example.com",
  "role": "practitioner"
}
```

**Response**: `201 Created`

### 1.5 Remove User from Organisation
```
DELETE /api/v1/organisations/{org_id}/users/{user_id}
```

**Authentication**: Required
**Authorization**: Admin only

**Response**: `204 No Content`

---

## 2. Case Endpoints

### 2.1 List Cases (Paginated)
```
GET /api/v1/cases?organisation_id={id}&status={status}&page={page}&per_page={per_page}&sort={field}&order={asc|desc}
```

**Authentication**: Required
**Authorization**: User must belong to organisation

**Query Parameters**:
- `organisation_id` (required): Filter by organisation
- `status` (optional): active, closed, archived
- `case_type` (optional): Filter by case type
- `q` (optional): Search in title and description (case-insensitive)
- `page` (optional, default=1): Page number
- `per_page` (optional, default=20, max=100): Items per page
- `sort` (optional, default=created_at): Sort field
- `order` (optional, default=desc): asc or desc

**Response**:
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "organisation_id": 1,
      "owner_id": 5,
      "title": "Smith v. Jones - High Court",
      "description": "Breach of contract matter",
      "case_type": "civil_litigation",
      "status": "active",
      "jurisdiction": "south_africa_high_court",
      "document_count": 15,
      "draft_count": 2,
      "created_at": "2026-03-01T09:00:00Z",
      "updated_at": "2026-03-10T14:30:00Z"
    }
  ],
  "page": 1,
  "per_page": 20,
  "total": 42,
  "pages": 3
}
```

### 2.2 Create Case
```
POST /api/v1/cases
```

**Authentication**: Required
**Authorization**: User must belong to organisation

**Request**:
```json
{
  "organisation_id": 1,
  "title": "New Matter - Urgent Application",
  "description": "Urgent interdict application",
  "case_type": "urgent_application",
  "jurisdiction": "south_africa_high_court"
}
```

**Response**: `201 Created`

### 2.3 Get Case Details
```
GET /api/v1/cases/{id}
```

**Response** includes full case details plus related counts

### 2.4 Update Case
```
PATCH /api/v1/cases/{id}
```

**Request**:
```json
{
  "title": "Updated Title",
  "status": "closed"
}
```

**Response**: `200 OK`

### 2.5 Delete Case
```
DELETE /api/v1/cases/{id}
```

**Response**: `204 No Content`

---

## 3. Document Endpoints

### 3.1 List Documents (Paginated)
```
GET /api/v1/documents?case_id={id}&document_type={type}&status={status}&page={page}&per_page={per_page}
```

**Query Parameters**:
- `case_id` (required): Filter by case
- `document_type` (optional): pleading, evidence, correspondence, order, research, other
- `status` (optional): queued, processing, completed, failed
- `q` (optional): Search in filename (case-insensitive)
- `page`, `per_page`, `sort`, `order`: Standard pagination

**Response**:
```json
{
  "data": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "case_id": "550e8400-e29b-41d4-a716-446655440000",
      "filename": "founding_affidavit.pdf",
      "file_size": 2457600,
      "mime_type": "application/pdf",
      "pages": 12,
      "document_type": "pleading",
      "document_subtype": "founding_affidavit",
      "tags": ["urgent", "main_application"],
      "overall_status": "completed",
      "stage": "indexing",
      "stage_progress": 100,
      "needs_ocr": false,
      "created_at": "2026-03-10T10:15:00Z"
    }
  ],
  "page": 1,
  "per_page": 20,
  "total": 15
}
```

### 3.2 Upload Document (Enqueue Processing)
```
POST /api/v1/documents
```

**Content-Type**: `multipart/form-data`

**Form Data**:
- `file`: Document file (PDF, DOCX, images)
- `case_id`: UUID of case
- `upload_session_id` (optional): UUID of upload session
- `document_type` (optional): Classification
- `tags` (optional): JSON array of tags

**Response**: `202 Accepted`
```json
{
  "data": {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "overall_status": "queued",
    "message": "Document processing enqueued"
  }
}
```

**Critical**: Must return `202 Accepted` (not `201 Created`) per NFR-7a (queue-based processing)

### 3.3 Get Document Details
```
GET /api/v1/documents/{id}
```

**Response** includes full metadata + processing status

### 3.4 Update Document Classification
```
PATCH /api/v1/documents/{id}
```

**Request**:
```json
{
  "document_type": "evidence",
  "document_subtype": "expert_report",
  "tags": ["medical", "expert"]
}
```

**Response**: `200 OK`

### 3.5 Delete Document
```
DELETE /api/v1/documents/{id}
```

**Response**: `204 No Content`

---

## 4. Upload Session Endpoints

### 4.1 List Upload Sessions (Paginated)
```
GET /api/v1/upload-sessions?case_id={id}&page={page}&per_page={per_page}
```

**Response**:
```json
{
  "data": [
    {
      "id": "770e8400-e29b-41d4-a716-446655440002",
      "case_id": "550e8400-e29b-41d4-a716-446655440000",
      "total_documents": 10,
      "completed_documents": 8,
      "failed_documents": 1,
      "in_progress": 1,
      "created_at": "2026-03-10T10:00:00Z"
    }
  ],
  "page": 1,
  "per_page": 20,
  "total": 5
}
```

### 4.2 Get Upload Session Status
```
GET /api/v1/upload-sessions/{id}
```

**Response** includes full batch status + list of documents

---

## 5. Draft Session Endpoints

### 5.1 List Draft Sessions (Paginated)
```
GET /api/v1/draft-sessions?case_id={id}&status={status}&page={page}&per_page={per_page}
```

**Query Parameters**:
- `case_id` (required): Filter by case
- `status` (optional): initializing, awaiting_intake, generating, ready, failed

**Response**:
```json
{
  "data": [
    {
      "id": "880e8400-e29b-41d4-a716-446655440003",
      "case_id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Founding Affidavit - Smith Matter",
      "document_type": "affidavit",
      "status": "awaiting_intake",
      "rulebook_id": 1,
      "rulebook_version": "1.0.0",
      "created_at": "2026-03-10T11:00:00Z"
    }
  ],
  "page": 1,
  "per_page": 20,
  "total": 2
}
```

### 5.2 Create Draft Session (Enqueue Research)
```
POST /api/v1/draft-sessions
```

**Request**:
```json
{
  "case_id": "550e8400-e29b-41d4-a716-446655440000",
  "document_type": "affidavit",
  "title": "Founding Affidavit - Smith Matter"
}
```

**Response**: `202 Accepted`
```json
{
  "data": {
    "id": "880e8400-e29b-41d4-a716-446655440003",
    "status": "initializing",
    "message": "Draft research job enqueued"
  }
}
```

**Critical**: Returns `202 Accepted` - research runs in background worker

### 5.3 Get Draft Session Details
```
GET /api/v1/draft-sessions/{id}
```

**Response**:
```json
{
  "data": {
    "id": "880e8400-e29b-41d4-a716-446655440003",
    "case_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "awaiting_intake",
    "case_profile": {
      "parties": ["Plaintiff: John Smith", "Defendant: Jane Jones"],
      "court": "Gauteng High Court, Johannesburg",
      "matter_type": "breach_of_contract"
    },
    "research_summary": "15 relevant documents found...",
    "outline": {
      "sections": ["Introduction", "Facts", "Legal Grounds", "Prayer"]
    },
    "intake_questions": [
      {
        "id": "deponent_name",
        "question": "Full name of deponent?",
        "type": "text",
        "required": true,
        "answered": false
      }
    ]
  }
}
```

### 5.4 Submit Intake Answers
```
POST /api/v1/draft-sessions/{id}/answers
```

**Request**:
```json
{
  "answers": {
    "deponent_name": "John Smith",
    "deponent_capacity": "Plaintiff",
    "date_of_events": "2025-12-15"
  }
}
```

**Response**: `200 OK`

### 5.5 Start Draft Generation (Enqueue Job)
```
POST /api/v1/draft-sessions/{id}/generate
```

**Response**: `202 Accepted`
```json
{
  "data": {
    "id": "880e8400-e29b-41d4-a716-446655440003",
    "status": "generating",
    "message": "Draft generation job enqueued"
  }
}
```

---

## 6. Rulebook Endpoints (Admin Only)

### 6.1 List Rulebooks (Paginated)
```
GET /api/v1/rulebooks?document_type={type}&jurisdiction={jurisdiction}&status={status}&page={page}&per_page={per_page}
```

**Authorization**: Admin only

**Query Parameters**:
- `document_type` (optional): affidavit, pleading, heads_of_argument, etc.
- `jurisdiction` (optional): south_africa_high_court, etc.
- `status` (optional): draft, published, deprecated

**Response**:
```json
{
  "data": [
    {
      "id": 1,
      "document_type": "affidavit",
      "jurisdiction": "south_africa_high_court",
      "version": "1.0.0",
      "label": "Standard Affidavit - High Court",
      "status": "published",
      "created_at": "2026-01-01T00:00:00Z"
    }
  ],
  "page": 1,
  "per_page": 20,
  "total": 12
}
```

### 6.2 Create Rulebook
```
POST /api/v1/rulebooks
```

**Authorization**: Admin only

**Request**:
```json
{
  "document_type": "affidavit",
  "jurisdiction": "south_africa_high_court",
  "version": "1.1.0",
  "label": "Updated Affidavit Rules",
  "source_yaml": "document_type: affidavit\n..."
}
```

**Response**: `201 Created`

### 6.3 Get Rulebook Details
```
GET /api/v1/rulebooks/{id}
```

**Response** includes both `source_yaml` and `rules_json`

### 6.4 Update Rulebook
```
PUT /api/v1/rulebooks/{id}
```

**Authorization**: Admin only
**Constraint**: Can only update rulebooks with status=draft

### 6.5 Publish Rulebook
```
POST /api/v1/rulebooks/{id}/publish
```

**Authorization**: Admin only
**Validates**: YAML against schema before publishing

**Response**: `200 OK` if valid, `422 Unprocessable Entity` if validation fails

### 6.6 Deprecate Rulebook
```
POST /api/v1/rulebooks/{id}/deprecate
```

**Authorization**: Admin only

**Response**: `200 OK`

---

## 7. Event Endpoints (Phase 3)

Deferred to Phase 3 when worker implementation begins.

---

## Standard Response Formats

### Success Response (List)
```json
{
  "data": [...],
  "page": 1,
  "per_page": 20,
  "total": 150,
  "pages": 8
}
```

### Success Response (Single)
```json
{
  "data": {...}
}
```

### Error Response
```json
{
  "error": "Organisation not found",
  "code": 404,
  "details": {
    "organisation_id": 999
  }
}
```

### Validation Error
```json
{
  "error": "Validation failed",
  "code": 400,
  "details": {
    "fields": {
      "email": ["Invalid email format"],
      "role": ["Must be one of: admin, practitioner, staff"]
    }
  }
}
```

---

## HTTP Status Codes

- `200 OK` - Successful GET, PATCH, PUT
- `201 Created` - Successful POST (synchronous)
- `202 Accepted` - Job enqueued (asynchronous) **← CRITICAL for NFR-7a**
- `204 No Content` - Successful DELETE
- `400 Bad Request` - Validation error
- `401 Unauthorized` - Not authenticated
- `403 Forbidden` - Not authorized (wrong role/organisation)
- `404 Not Found` - Resource doesn't exist
- `422 Unprocessable Entity` - Business logic error (e.g., YAML validation failed)

---

## Authentication

All endpoints require authentication via:
- **Basic Auth** (development/testing)
- **JWT** (production)

Headers:
```
Authorization: Bearer <token>
```

---

## Rate Limiting

- **Auth endpoints**: 5 requests per minute
- **Upload endpoints**: 10 requests per minute
- **Other endpoints**: 100 requests per minute

---

## Phase 2 Implementation Checklist

### Middleware (Phase 2.1)
- [ ] DB session management per request
- [ ] Error handling middleware (consistent JSON errors)
- [ ] Request logging with correlation IDs
- [ ] Authentication decorator (Basic Auth or JWT)
- [ ] Organisation scoping validation

### Endpoints (Phase 2.2)
- [ ] Organisations (5 endpoints)
- [ ] Cases (5 endpoints) ✅ Pagination
- [ ] Documents (5 endpoints) ✅ Pagination
- [ ] Upload Sessions (2 endpoints) ✅ Pagination
- [ ] Draft Sessions (5 endpoints) ✅ Pagination
- [ ] Rulebooks (6 endpoints) ✅ Pagination

### Queue Integration (Phase 2.3)
- [ ] Redis/RQ configuration
- [ ] `enqueue_document_processing()` function
- [ ] `enqueue_draft_research()` function
- [ ] `enqueue_draft_generation()` function
- [ ] Return 202 Accepted for async operations

### Testing (Phase 2.2/2.3)
- [ ] Integration tests for all endpoints
- [ ] Auth enforcement tests
- [ ] Organisation scoping tests (prevent cross-org access)
- [ ] Pagination tests
- [ ] Job enqueuing tests (verify jobs created)

---

**Document Version**: 1.0
**Created**: 2026-03-11
**Phase**: 2 Preparation
**Status**: Ready for implementation
