export interface PaginationMeta {
  page: number;
  per_page: number;
  total_items: number;
  total_pages: number;
}

export interface ContactOut {
  id: number;
  full_name: string | null;
  title: string | null;
  email: string | null;
  phone: string | null;
  linkedin_url: string | null;
  source: string;
  confidence: string | null;
}

export interface LeadInsightOut {
  lead_score: number | null;
  score_breakdown: Record<string, number>;
  research_summary: string | null;
  citations: string[];
  talking_points: string[];
  buying_signals: string[];
  pain_points: string[];
  recommended_pitch: string | null;
  why_now: string | null;
  draft_email: string | null;
  enriched_at: string | null;
}

export interface LeadListItem {
  id: number;
  name: string;
  city: string | null;
  state: string | null;
  certification: string | null;
  rating: number | null;
  review_count: number | null;
  lead_score: number | null;
  phone: string | null;
  website: string | null;
  image_url: string | null;
  distance_miles: number | null;
  years_in_business: number | null;
}

export interface LeadListResponse {
  data: LeadListItem[];
  pagination: PaginationMeta;
}

export interface LeadDetail {
  id: number;
  gaf_id: string;
  name: string;
  address: string | null;
  city: string | null;
  state: string | null;
  zip_code: string | null;
  phone: string | null;
  website: string | null;
  certification: string | null;
  certifications_raw: string[];
  rating: number | null;
  review_count: number | null;
  services: string[];
  latitude: number | null;
  longitude: number | null;
  distance_miles: number | null;
  years_in_business: number | null;
  about: string | null;
  profile_url: string | null;
  image_url: string | null;
  scraped_at: string | null;
  insights: LeadInsightOut | null;
  contacts: ContactOut[];
}

export interface StatsResponse {
  total_leads: number;
  avg_score: number | null;
  high_priority_count: number;
  certification_breakdown: Record<string, number>;
  score_distribution: Record<string, number>;
}

export interface PipelineStatusResponse {
  total_contractors: number;
  with_research: number;
  with_scores: number;
  with_contacts: number;
  awaiting_research: number;
  awaiting_scoring: number;
  awaiting_contacts: number;
}
