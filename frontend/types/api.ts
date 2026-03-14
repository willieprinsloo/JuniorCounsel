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
  organisation_id?: number | null;
  organisation_name?: string | null;
  role?: string | null;
  created_at?: string;
  updated_at?: string;
}

// Password Reset types
export interface ForgotPasswordRequest {
  email: string;
}

export interface ForgotPasswordResponse {
  message: string;
}

export interface VerifyResetTokenRequest {
  token: string;
}

export interface VerifyResetTokenResponse {
  valid: boolean;
  message: string;
}

export interface ResetPasswordRequest {
  token: string;
  new_password: string;
}

export interface ResetPasswordResponse {
  message: string;
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

// Intake Question types
export interface IntakeQuestion {
  field: string;
  prompt: string;
  required: boolean;
  type?: string;
  options?: string[];
}

export interface IntakeQuestionsResponse {
  draft_session_id: string;
  questions: IntakeQuestion[];
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

// Chat Session types
export interface ChatSession {
  id: string;
  case_id: string;
  user_id: number;
  title: string | null;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  chat_session_id: string;
  question: string;
  answer: string;
  confidence: number;
  sources: SearchResult[] | null;
  created_at: string;
}

export interface ChatSessionDetail {
  id: string;
  case_id: string;
  user_id: number;
  title: string | null;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
}

export interface ChatSessionCreate {
  case_id: string;
  title?: string;
}

export interface ChatSessionListResponse {
  data: ChatSession[];
  page: number;
  per_page: number;
  total: number;
  next_page: number | null;
}

// Token Usage types
export interface UsageSummary {
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  total_cost_usd: number;
  request_count: number;
}

export interface UsageByTypeItem {
  usage_type: string;
  total_tokens: number;
  total_cost_usd: number;
  request_count: number;
}

export interface TopCaseItem {
  case_id: string;
  total_cost_usd: number;
  total_tokens: number;
}

export interface UsageDashboard {
  summary: UsageSummary;
  by_type: UsageByTypeItem[];
  top_cases: TopCaseItem[];
  organisation_id: number | null;
  user_id: number | null;
  start_date: string;
  end_date: string;
}

// Admin types
export enum OrganisationRole {
  ADMIN = 'admin',
  PRACTITIONER = 'practitioner',
  STAFF = 'staff',
}

export interface OrganisationMembership {
  organisation_id: number;
  organisation_name: string;
  role: OrganisationRole;
  joined_at: string;
}

export interface AdminUser {
  id: number;
  email: string;
  full_name: string | null;
  created_at: string;
  updated_at: string;
  organisations: OrganisationMembership[];
}

export interface AdminUserCreate {
  email: string;
  password: string;
  full_name?: string;
}

export interface AdminUserUpdate {
  email?: string;
  password?: string;
  full_name?: string;
}

export interface AdminUserListResponse {
  data: AdminUser[];
  page: number;
  per_page: number;
  total: number;
  next_page: number | null;
}

export interface OrganisationCreate {
  name: string;
  contact_email?: string;
  is_active?: boolean;
}

export interface OrganisationUpdate {
  name?: string;
  contact_email?: string;
  is_active?: boolean;
}

export interface OrganisationListResponse {
  data: Organisation[];
  page: number;
  per_page: number;
  total: number;
  next_page: number | null;
}

export interface OrganisationMember {
  id: number;
  user_id: number;
  email: string;
  full_name: string | null;
  role: OrganisationRole;
  joined_at: string;
}

export interface OrganisationMemberAdd {
  user_id: number;
  role: OrganisationRole;
}

export interface OrganisationMemberUpdate {
  role: OrganisationRole;
}

export interface OrganisationMemberListResponse {
  data: OrganisationMember[];
  page: number;
  per_page: number;
  total: number;
  next_page: number | null;
}

export interface RulebookUpload {
  document_type: string;
  jurisdiction: string;
  version: string;
  source_yaml: string;
  label?: string;
}

export interface RulebookUpdate {
  label?: string;
  source_yaml?: string;
}

export interface RulebookDetail extends Rulebook {
  source_yaml?: string;
}
