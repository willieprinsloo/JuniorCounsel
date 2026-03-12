-- Junior Counsel Initial Database Schema
-- Migration 001: Create all core tables
-- Created: 2026-03-12

-- Enable pgvector extension for vector embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- AUTHENTICATION & ORGANIZATION
-- ============================================================

-- Organizations (law firms, chambers)
CREATE TABLE organisations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Users (advocates, attorneys, staff)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Organisation-User relationship (many-to-many with roles)
CREATE TABLE organisation_users (
    id SERIAL PRIMARY KEY,
    organisation_id INTEGER NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'practitioner',
    joined_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(organisation_id, user_id)
);

-- ============================================================
-- CASES & DOCUMENTS
-- ============================================================

-- Cases (matter/file containers)
CREATE TABLE cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organisation_id INTEGER NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
    owner_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    case_type VARCHAR(100),
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    jurisdiction VARCHAR(255),
    case_metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Documents (uploaded files)
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    filename VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    file_size BIGINT,
    mime_type VARCHAR(100),
    pages INTEGER,
    document_type VARCHAR(50) NOT NULL DEFAULT 'other',
    overall_status VARCHAR(50) NOT NULL DEFAULT 'queued',
    stage VARCHAR(50),
    stage_progress INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Document chunks (for vector search)
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text_content TEXT NOT NULL,
    page_number INTEGER,
    bounding_box JSONB,
    token_count INTEGER,
    embedding vector(1536),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Upload sessions (batch tracking)
CREATE TABLE upload_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    document_count INTEGER NOT NULL DEFAULT 0,
    completed_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'in_progress',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- DRAFTING & RULEBOOKS
-- ============================================================

-- Rulebooks (document type templates)
CREATE TABLE rulebooks (
    id SERIAL PRIMARY KEY,
    document_type VARCHAR(100) NOT NULL,
    jurisdiction VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    label VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    source_yaml TEXT,
    rules_json JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_type, jurisdiction, version)
);

-- Draft sessions (document generation workflow)
CREATE TABLE draft_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rulebook_id INTEGER NOT NULL REFERENCES rulebooks(id) ON DELETE RESTRICT,
    title VARCHAR(500) NOT NULL,
    document_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'initializing',
    case_profile JSONB,
    research_summary JSONB,
    outline JSONB,
    intake_responses JSONB,
    draft_doc JSONB,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Citations (links between drafts and source chunks)
CREATE TABLE citations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    draft_session_id UUID NOT NULL REFERENCES draft_sessions(id) ON DELETE CASCADE,
    document_chunk_id UUID NOT NULL REFERENCES document_chunks(id) ON DELETE CASCADE,
    marker VARCHAR(16) NOT NULL,
    citation_text TEXT NOT NULL,
    page_number INTEGER,
    paragraph_number INTEGER,
    similarity_score REAL,
    position_start INTEGER,
    position_end INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- INDEXES
-- ============================================================

-- Organisation indexes
CREATE INDEX idx_organisations_is_active ON organisations(is_active);

-- User indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_active ON users(is_active);

-- Organisation-User indexes
CREATE INDEX idx_organisation_users_org_id ON organisation_users(organisation_id);
CREATE INDEX idx_organisation_users_user_id ON organisation_users(user_id);

-- Case indexes
CREATE INDEX idx_cases_organisation_id ON cases(organisation_id);
CREATE INDEX idx_cases_owner_id ON cases(owner_id);
CREATE INDEX idx_cases_status ON cases(status);
CREATE INDEX idx_cases_created_at ON cases(created_at DESC);

-- Document indexes
CREATE INDEX idx_documents_case_id ON documents(case_id);
CREATE INDEX idx_documents_overall_status ON documents(overall_status);
CREATE INDEX idx_documents_document_type ON documents(document_type);
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);

-- Document chunk indexes
CREATE INDEX idx_document_chunks_document_id ON document_chunks(document_id);
CREATE INDEX idx_document_chunks_chunk_index ON document_chunks(document_id, chunk_index);

-- Upload session indexes
CREATE INDEX idx_upload_sessions_case_id ON upload_sessions(case_id);
CREATE INDEX idx_upload_sessions_user_id ON upload_sessions(user_id);
CREATE INDEX idx_upload_sessions_status ON upload_sessions(status);

-- Rulebook indexes
CREATE INDEX idx_rulebooks_document_type ON rulebooks(document_type);
CREATE INDEX idx_rulebooks_jurisdiction ON rulebooks(jurisdiction);
CREATE INDEX idx_rulebooks_status ON rulebooks(status);

-- Draft session indexes
CREATE INDEX idx_draft_sessions_case_id ON draft_sessions(case_id);
CREATE INDEX idx_draft_sessions_user_id ON draft_sessions(user_id);
CREATE INDEX idx_draft_sessions_rulebook_id ON draft_sessions(rulebook_id);
CREATE INDEX idx_draft_sessions_status ON draft_sessions(status);
CREATE INDEX idx_draft_sessions_created_at ON draft_sessions(created_at DESC);

-- Citation indexes
CREATE INDEX idx_citations_draft_session_id ON citations(draft_session_id);
CREATE INDEX idx_citations_document_chunk_id ON citations(document_chunk_id);
CREATE INDEX idx_citations_marker ON citations(draft_session_id, marker);

-- ============================================================
-- COMMENTS
-- ============================================================

COMMENT ON TABLE organisations IS 'Law firms, chambers, or legal organizations';
COMMENT ON TABLE users IS 'Authenticated practitioners and staff';
COMMENT ON TABLE organisation_users IS 'Many-to-many relationship with roles';
COMMENT ON TABLE cases IS 'Legal matters/files containing documents and drafts';
COMMENT ON TABLE documents IS 'Uploaded PDF/DOCX files with processing status';
COMMENT ON TABLE document_chunks IS 'Vector-embedded text segments for RAG';
COMMENT ON TABLE upload_sessions IS 'Batch upload tracking';
COMMENT ON TABLE rulebooks IS 'Document type templates (YAML configurations)';
COMMENT ON TABLE draft_sessions IS 'Draft generation workflow instances';
COMMENT ON TABLE citations IS 'Links between generated drafts and source chunks';

-- ============================================================
-- COMPLETION
-- ============================================================

-- Migration complete
SELECT 'Migration 001: Initial schema created successfully' AS status;
