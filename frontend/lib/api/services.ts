/**
 * API Service Methods
 *
 * Type-safe methods for interacting with the Junior Counsel backend.
 */

import { apiClient, APIError } from './client';
import type {
  LoginRequest,
  LoginResponse,
  User,
  ForgotPasswordRequest,
  ForgotPasswordResponse,
  VerifyResetTokenRequest,
  VerifyResetTokenResponse,
  ResetPasswordRequest,
  ResetPasswordResponse,
  Case,
  CaseCreate,
  CaseListResponse,
  Document,
  DocumentListResponse,
  DraftSession,
  DraftSessionCreate,
  DraftSessionListResponse,
  IntakeResponsesSubmit,
  CitationsListResponse,
  Rulebook,
  RulebookListResponse,
  SearchRequest,
  SearchResponse,
  QARequest,
  QAResponse,
} from '@/types/api';

// Authentication
export const authAPI = {
  login: async (credentials: LoginRequest): Promise<LoginResponse> => {
    const formData = new FormData();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);

    // Use upload method which handles FormData correctly
    const url = '/api/v1/auth/login';
    const baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    console.log('Login attempt:', { username: credentials.username, url: `${baseURL}${url}` });

    const response = await fetch(`${baseURL}${url}`, {
      method: 'POST',
      body: formData,
    });

    console.log('Login response:', { status: response.status, ok: response.ok });

    if (!response.ok) {
      const error = await response.json();
      console.error('Login error:', error);
      throw new APIError(
        error.detail || 'Login failed',
        response.status,
        error
      );
    }

    return response.json();
  },

  getCurrentUser: async (): Promise<User> => {
    return apiClient.get<User>('/api/v1/auth/me');
  },

  logout: async (): Promise<void> => {
    apiClient.setAuthToken(null);
  },

  forgotPassword: async (data: ForgotPasswordRequest): Promise<ForgotPasswordResponse> => {
    return apiClient.post<ForgotPasswordResponse>('/api/v1/auth/forgot-password', data);
  },

  verifyResetToken: async (data: VerifyResetTokenRequest): Promise<VerifyResetTokenResponse> => {
    return apiClient.post<VerifyResetTokenResponse>('/api/v1/auth/verify-reset-token', data);
  },

  resetPassword: async (data: ResetPasswordRequest): Promise<ResetPasswordResponse> => {
    return apiClient.post<ResetPasswordResponse>('/api/v1/auth/reset-password', data);
  },
};

// Cases
export const casesAPI = {
  list: async (params?: {
    organisation_id: number;
    status?: string;
    page?: number;
    per_page?: number;
  }): Promise<CaseListResponse> => {
    return apiClient.get<CaseListResponse>('/api/v1/cases/', params);
  },

  get: async (caseId: string): Promise<Case> => {
    return apiClient.get<Case>(`/api/v1/cases/${caseId}`);
  },

  create: async (data: CaseCreate & { organisation_id: number }): Promise<Case> => {
    return apiClient.post<Case>('/api/v1/cases/', data);
  },

  update: async (caseId: string, data: Partial<CaseCreate>): Promise<Case> => {
    return apiClient.patch<Case>(`/api/v1/cases/${caseId}`, data);
  },

  delete: async (caseId: string): Promise<void> => {
    return apiClient.delete<void>(`/api/v1/cases/${caseId}`);
  },
};

// Documents
export const documentsAPI = {
  list: async (params: {
    case_id: string;
    document_type?: string;
    status?: string;
    page?: number;
    per_page?: number;
  }): Promise<DocumentListResponse> => {
    return apiClient.get<DocumentListResponse>('/api/v1/documents/', params);
  },

  get: async (documentId: string): Promise<Document> => {
    return apiClient.get<Document>(`/api/v1/documents/${documentId}`);
  },

  upload: async (caseId: string, file: File): Promise<Document> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('case_id', caseId);

    return apiClient.upload<Document>('/api/v1/documents/upload', formData);
  },

  delete: async (documentId: string): Promise<void> => {
    return apiClient.delete<void>(`/api/v1/documents/${documentId}`);
  },

  retry: async (documentId: string): Promise<Document> => {
    return apiClient.post<Document>(`/api/v1/documents/${documentId}/retry`, {});
  },
};

// Draft Sessions
export const draftSessionsAPI = {
  list: async (params: {
    case_id: string;
    status?: string;
    page?: number;
    per_page?: number;
  }): Promise<DraftSessionListResponse> => {
    return apiClient.get<DraftSessionListResponse>('/api/v1/draft-sessions/', params);
  },

  get: async (draftSessionId: string): Promise<DraftSession> => {
    return apiClient.get<DraftSession>(`/api/v1/draft-sessions/${draftSessionId}`);
  },

  create: async (data: DraftSessionCreate): Promise<DraftSession> => {
    return apiClient.post<DraftSession>('/api/v1/draft-sessions/', data);
  },

  submitIntake: async (
    draftSessionId: string,
    data: IntakeResponsesSubmit
  ): Promise<DraftSession> => {
    return apiClient.post<DraftSession>(
      `/api/v1/draft-sessions/${draftSessionId}/answers`,
      data
    );
  },

  startGeneration: async (draftSessionId: string): Promise<DraftSession> => {
    return apiClient.post<DraftSession>(
      `/api/v1/draft-sessions/${draftSessionId}/start-generation`,
      {}
    );
  },

  getCitations: async (draftSessionId: string): Promise<CitationsListResponse> => {
    return apiClient.get<CitationsListResponse>(
      `/api/v1/draft-sessions/${draftSessionId}/citations`
    );
  },

  delete: async (draftSessionId: string): Promise<void> => {
    return apiClient.delete<void>(`/api/v1/draft-sessions/${draftSessionId}`);
  },
};

// Rulebooks
export const rulebooksAPI = {
  list: async (params?: {
    document_type?: string;
    jurisdiction?: string;
    status?: string;
    page?: number;
    per_page?: number;
  }): Promise<RulebookListResponse> => {
    return apiClient.get<RulebookListResponse>('/api/v1/rulebooks/', params);
  },

  get: async (rulebookId: number): Promise<Rulebook> => {
    return apiClient.get<Rulebook>(`/api/v1/rulebooks/${rulebookId}`);
  },

  getPublished: async (documentType: string, jurisdiction: string): Promise<Rulebook> => {
    return apiClient.get<Rulebook>('/api/v1/rulebooks/published', {
      document_type: documentType,
      jurisdiction: jurisdiction,
    });
  },
};

// Search
export const searchAPI = {
  search: async (request: SearchRequest): Promise<SearchResponse> => {
    return apiClient.post<SearchResponse>('/api/v1/search/', request);
  },
};

// Q&A
export const qaAPI = {
  ask: async (request: QARequest, chatSessionId?: string): Promise<QAResponse> => {
    const url = chatSessionId
      ? `/api/v1/qa/?chat_session_id=${chatSessionId}`
      : '/api/v1/qa/';
    return apiClient.post<QAResponse>(url, request);
  },
};

// Chat Sessions
import type { ChatSession, ChatSessionDetail, ChatSessionCreate, ChatSessionListResponse } from '@/types/api';

export const chatSessionsAPI = {
  create: async (data: ChatSessionCreate): Promise<ChatSession> => {
    return apiClient.post<ChatSession>('/api/v1/chat-sessions/', data);
  },

  list: async (params: {
    case_id: string;
    page?: number;
    per_page?: number;
  }): Promise<ChatSessionListResponse> => {
    return apiClient.get<ChatSessionListResponse>('/api/v1/chat-sessions/', params);
  },

  get: async (chatSessionId: string): Promise<ChatSessionDetail> => {
    return apiClient.get<ChatSessionDetail>(`/api/v1/chat-sessions/${chatSessionId}`);
  },

  delete: async (chatSessionId: string): Promise<void> => {
    return apiClient.delete<void>(`/api/v1/chat-sessions/${chatSessionId}`);
  },
};

// Token Usage
import type { UsageSummary, UsageDashboard } from '@/types/api';

export const usageAPI = {
  getDashboard: async (params?: {
    organisation_id?: number;
    user_id?: number;
    start_date?: string;
    end_date?: string;
  }): Promise<UsageDashboard> => {
    return apiClient.get<UsageDashboard>('/api/v1/usage/dashboard/', params);
  },

  getDocumentUsage: async (documentId: string): Promise<UsageSummary> => {
    return apiClient.get<UsageSummary>(`/api/v1/usage/document/${documentId}`);
  },
};

// Admin - User Management
import type {
  AdminUser,
  AdminUserCreate,
  AdminUserUpdate,
  AdminUserListResponse,
} from '@/types/api';

export const adminUsersAPI = {
  list: async (params?: {
    q?: string;
    page?: number;
    per_page?: number;
    sort?: string;
    order?: string;
  }): Promise<AdminUserListResponse> => {
    return apiClient.get<AdminUserListResponse>('/api/v1/admin/users/', params);
  },

  get: async (userId: number): Promise<AdminUser> => {
    return apiClient.get<AdminUser>(`/api/v1/admin/users/${userId}`);
  },

  create: async (data: AdminUserCreate): Promise<AdminUser> => {
    return apiClient.post<AdminUser>('/api/v1/admin/users/', data);
  },

  update: async (userId: number, data: AdminUserUpdate): Promise<AdminUser> => {
    return apiClient.patch<AdminUser>(`/api/v1/admin/users/${userId}`, data);
  },

  delete: async (userId: number): Promise<void> => {
    return apiClient.delete<void>(`/api/v1/admin/users/${userId}`);
  },
};

// Admin - Organisation Management
import type {
  Organisation,
  OrganisationCreate,
  OrganisationUpdate,
  OrganisationListResponse,
  OrganisationMember,
  OrganisationMemberAdd,
  OrganisationMemberUpdate,
  OrganisationMemberListResponse,
} from '@/types/api';

export const adminOrganisationsAPI = {
  list: async (params?: {
    is_active?: boolean;
    page?: number;
    per_page?: number;
    sort?: string;
    order?: string;
  }): Promise<OrganisationListResponse> => {
    return apiClient.get<OrganisationListResponse>('/api/v1/admin/organisations/', params);
  },

  get: async (organisationId: number): Promise<Organisation> => {
    return apiClient.get<Organisation>(`/api/v1/admin/organisations/${organisationId}`);
  },

  create: async (data: OrganisationCreate): Promise<Organisation> => {
    return apiClient.post<Organisation>('/api/v1/admin/organisations/', data);
  },

  update: async (organisationId: number, data: OrganisationUpdate): Promise<Organisation> => {
    return apiClient.patch<Organisation>(`/api/v1/admin/organisations/${organisationId}`, data);
  },

  // Member management
  listMembers: async (
    organisationId: number,
    params?: {
      role?: string;
      page?: number;
      per_page?: number;
    }
  ): Promise<OrganisationMemberListResponse> => {
    return apiClient.get<OrganisationMemberListResponse>(
      `/api/v1/admin/organisations/${organisationId}/members`,
      params
    );
  },

  addMember: async (
    organisationId: number,
    data: OrganisationMemberAdd
  ): Promise<OrganisationMember> => {
    return apiClient.post<OrganisationMember>(
      `/api/v1/admin/organisations/${organisationId}/members`,
      data
    );
  },

  updateMemberRole: async (
    organisationId: number,
    userId: number,
    data: OrganisationMemberUpdate
  ): Promise<OrganisationMember> => {
    return apiClient.patch<OrganisationMember>(
      `/api/v1/admin/organisations/${organisationId}/members/${userId}`,
      data
    );
  },

  removeMember: async (organisationId: number, userId: number): Promise<void> => {
    return apiClient.delete<void>(
      `/api/v1/admin/organisations/${organisationId}/members/${userId}`
    );
  },
};

// Admin - Rulebook Management
import type {
  Rulebook,
  RulebookUpload,
  RulebookUpdate,
  RulebookDetail,
} from '@/types/api';

export const adminRulebooksAPI = {
  upload: async (data: RulebookUpload): Promise<Rulebook> => {
    return apiClient.post<Rulebook>('/api/v1/admin/rulebooks/', data);
  },

  update: async (rulebookId: number, data: RulebookUpdate): Promise<Rulebook> => {
    return apiClient.patch<Rulebook>(`/api/v1/admin/rulebooks/${rulebookId}`, data);
  },

  publish: async (rulebookId: number): Promise<Rulebook> => {
    return apiClient.post<Rulebook>(`/api/v1/admin/rulebooks/${rulebookId}/publish`, {});
  },

  deprecate: async (rulebookId: number): Promise<Rulebook> => {
    return apiClient.post<Rulebook>(`/api/v1/admin/rulebooks/${rulebookId}/deprecate`, {});
  },
};
