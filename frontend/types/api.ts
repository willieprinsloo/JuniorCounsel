/**
 * TypeScript types matching the FastAPI backend schemas
 */

// Auth types
export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface User {
  id: number;
  email: string;
  full_name: string | null;
  created_at: string;
  updated_at: string;
}

// Organisation types
export interface Organisation {
  id: number;
  name: string;
  contact_email: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// Case types
export enum CaseStatus {
  ACTIVE = 'active',
  CLOSED = 'closed',
  ARCHIVED = 'archived',
}

export interface Case {
  id: string;
  organisation_id: number;
  owner_id: number | null;
  title: string;
  description: string | null;
  case_type: string | null;
  status: CaseStatus;
  jurisdiction: string | null;
  case_metadata: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface CaseCreate {
  title: string;
  description?: string;
  case_type?: string;
  jurisdiction?: string;
}

export interface CaseListResponse {
  data: Case[];
  page: number;
  per_page: number;
  total: number;
  next_page: number | null;
}

// Document types
export enum DocumentStatus {
  QUEUED = 'queued',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

export enum DocumentType {
  PLEADING = 'pleading',
  EVIDENCE = 'evidence',
  CORRESPONDENCE = 'correspondence',
  ORDER = 'order',
  RESEARCH = 'research',
  OTHER = 'other',
}

export interface Document {
  id: string;
  case_id: string;
  filename: string;
  file_size: number | null;
  mime_type: string | null;
  pages: number | null;
  document_type: DocumentType;
  overall_status: DocumentStatus;
  stage: string | null;
  stage_progress: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  data: Document[];
  page: number;
  per_page: number;
  total: number;
  next_page: number | null;
}

// Draft Session types
export enum DraftSessionStatus {
  INITIALIZING = 'initializing',
  AWAITING_INTAKE = 'awaiting_intake',
  RESEARCH = 'research',
  DRAFTING = 'drafting',
  REVIEW = 'review',
  READY = 'ready',
  FAILED = 'failed',
}

export interface DraftSession {
  id: string;
  case_id: string;
  user_id: number;
  rulebook_id: number;
  title: string;
  document_type: string;
  status: DraftSessionStatus;
  case_profile: Record<string, any> | null;
  research_summary: Record<string, any> | null;
  outline: Record<string, any> | null;
  intake_responses: Record<string, any> | null;
  draft_doc: Record<string, any> | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface DraftSessionCreate {
  case_id: string;
  rulebook_id: number;
  title: string;
  document_type: string;
}

export interface DraftSessionListResponse {
  data: DraftSession[];
  page: number;
  per_page: number;
  total: number;
  next_page: number | null;
}

export interface IntakeResponsesSubmit {
  intake_responses: Record<string, any>;
}

// Citation types
export interface Citation {
  marker: string;
  content: string;
  document_name: string;
  document_id: string;
  page: number | null;
  similarity: number | null;
}

export interface CitationsListResponse {
  draft_session_id: string;
  citations: Citation[];
  total_citations: number;
}

// Rulebook types
export enum RulebookStatus {
  DRAFT = 'draft',
  PUBLISHED = 'published',
  DEPRECATED = 'deprecated',
}

export interface Rulebook {
  id: number;
  document_type: string;
  jurisdiction: string;
  version: string;
  label: string | null;
  status: RulebookStatus;
  created_at: string;
  updated_at: string;
}

export interface RulebookListResponse {
  data: Rulebook[];
  page: number;
  per_page: number;
  total: number;
  next_page: number | null;
}

// Search & QA types
export interface SearchRequest {
  case_id: string;
  query: string;
  limit?: number;
  similarity_threshold?: number;
  document_type?: string;
}

export interface SearchResult {
  chunk_id: string;
  document_id: string;
  document_filename: string;
  content: string;
  page_number: number;
  similarity: number;
  citation: Record<string, any>;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
}

export interface QARequest {
  case_id: string;
  question: string;
  limit?: number;
}

export interface QAResponse {
  question: string;
  answer: string;
  sources: SearchResult[];
  confidence: number;
}
