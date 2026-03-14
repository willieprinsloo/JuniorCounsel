/**
 * Token usage API client.
 *
 * Provides methods for fetching token usage data and costs.
 */

import { apiClient } from './client';

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
  organisation_id?: number;
  user_id?: number;
  start_date?: string;
  end_date?: string;
}

export interface UsageQueryParams {
  organisation_id?: number;
  user_id?: number;
  case_id?: string;
  start_date?: string; // ISO format
  end_date?: string; // ISO format
  usage_type?: string;
  limit?: number;
}

/**
 * Get usage summary with optional filters.
 */
export async function getUsageSummary(params?: UsageQueryParams): Promise<UsageSummary> {
  const query = new URLSearchParams();
  if (params?.organisation_id) query.append('organisation_id', params.organisation_id.toString());
  if (params?.user_id) query.append('user_id', params.user_id.toString());
  if (params?.case_id) query.append('case_id', params.case_id);
  if (params?.start_date) query.append('start_date', params.start_date);
  if (params?.end_date) query.append('end_date', params.end_date);
  if (params?.usage_type) query.append('usage_type', params.usage_type);

  const url = `/api/v1/usage/summary${query.toString() ? `?${query}` : ''}`;
  return apiClient.get<UsageSummary>(url);
}

/**
 * Get usage breakdown by type (embedding, LLM generation, Q&A, OCR).
 */
export async function getUsageByType(params?: UsageQueryParams): Promise<UsageByTypeItem[]> {
  const query = new URLSearchParams();
  if (params?.organisation_id) query.append('organisation_id', params.organisation_id.toString());
  if (params?.user_id) query.append('user_id', params.user_id.toString());
  if (params?.start_date) query.append('start_date', params.start_date);
  if (params?.end_date) query.append('end_date', params.end_date);

  const url = `/api/v1/usage/by-type${query.toString() ? `?${query}` : ''}`;
  const response = await apiClient.get<{ usage_by_type: UsageByTypeItem[] }>(url);
  return response.usage_by_type;
}

/**
 * Get top cases by cost.
 */
export async function getTopCases(params?: UsageQueryParams): Promise<TopCaseItem[]> {
  const query = new URLSearchParams();
  if (params?.organisation_id) query.append('organisation_id', params.organisation_id.toString());
  if (params?.user_id) query.append('user_id', params.user_id.toString());
  if (params?.start_date) query.append('start_date', params.start_date);
  if (params?.end_date) query.append('end_date', params.end_date);
  if (params?.limit) query.append('limit', params.limit.toString());

  const url = `/api/v1/usage/top-cases${query.toString() ? `?${query}` : ''}`;
  const response = await apiClient.get<{ top_cases: TopCaseItem[] }>(url);
  return response.top_cases;
}

/**
 * Get complete usage dashboard (summary + breakdown + top cases).
 */
export async function getUsageDashboard(params?: UsageQueryParams): Promise<UsageDashboard> {
  const query = new URLSearchParams();
  if (params?.organisation_id) query.append('organisation_id', params.organisation_id.toString());
  if (params?.user_id) query.append('user_id', params.user_id.toString());
  if (params?.start_date) query.append('start_date', params.start_date);
  if (params?.end_date) query.append('end_date', params.end_date);

  const url = `/api/v1/usage/dashboard${query.toString() ? `?${query}` : ''}`;
  return apiClient.get<UsageDashboard>(url);
}

export const usageAPI = {
  getUsageSummary,
  getUsageByType,
  getTopCases,
  getUsageDashboard,
};
