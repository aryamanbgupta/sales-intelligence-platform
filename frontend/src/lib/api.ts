import type { LeadListResponse, LeadDetail, StatsResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchApi<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`);
  }
  return res.json();
}

export interface LeadQueryParams {
  page?: number;
  per_page?: number;
  sort_by?: string;
  sort_order?: string;
  min_score?: number;
  max_score?: number;
  certification?: string;
  search?: string;
}

export function getLeads(params: LeadQueryParams = {}): Promise<LeadListResponse> {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      searchParams.set(key, String(value));
    }
  });
  return fetchApi<LeadListResponse>(`/api/leads?${searchParams.toString()}`);
}

export function getLead(id: number): Promise<LeadDetail> {
  return fetchApi<LeadDetail>(`/api/leads/${id}`);
}

export function getStats(): Promise<StatsResponse> {
  return fetchApi<StatsResponse>("/api/stats");
}
