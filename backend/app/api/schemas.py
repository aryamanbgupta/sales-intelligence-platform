"""Pydantic request/response models for the REST API."""

from typing import Dict, List, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Shared / nested schemas
# ---------------------------------------------------------------------------


class PaginationMeta(BaseModel):
    page: int
    per_page: int
    total_items: int
    total_pages: int


class ContactOut(BaseModel):
    id: int
    full_name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    source: str
    confidence: Optional[str] = None


class LeadInsightOut(BaseModel):
    lead_score: Optional[int] = None
    score_breakdown: dict = {}
    research_summary: Optional[str] = None
    citations: List[str] = []
    talking_points: List[str] = []
    buying_signals: List[str] = []
    pain_points: List[str] = []
    recommended_pitch: Optional[str] = None
    why_now: Optional[str] = None
    draft_email: Optional[str] = None
    enriched_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Lead list (compact)
# ---------------------------------------------------------------------------


class LeadListItem(BaseModel):
    id: int
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    certification: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    lead_score: Optional[int] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    image_url: Optional[str] = None
    distance_miles: Optional[float] = None
    years_in_business: Optional[int] = None


class LeadListResponse(BaseModel):
    data: List[LeadListItem]
    pagination: PaginationMeta


# ---------------------------------------------------------------------------
# Lead detail (full)
# ---------------------------------------------------------------------------


class LeadDetail(BaseModel):
    id: int
    gaf_id: str
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    certification: Optional[str] = None
    certifications_raw: List[str] = []
    rating: Optional[float] = None
    review_count: Optional[int] = None
    services: List[str] = []
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance_miles: Optional[float] = None
    years_in_business: Optional[int] = None
    about: Optional[str] = None
    profile_url: Optional[str] = None
    image_url: Optional[str] = None
    scraped_at: Optional[str] = None
    insights: Optional[LeadInsightOut] = None
    contacts: List[ContactOut] = []


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


class StatsResponse(BaseModel):
    total_leads: int
    avg_score: Optional[float] = None
    high_priority_count: int
    certification_breakdown: Dict[str, int] = {}
    score_distribution: Dict[str, int] = {}


# ---------------------------------------------------------------------------
# Pipeline responses
# ---------------------------------------------------------------------------


class ScrapeResponse(BaseModel):
    contractors_found: int
    new: int
    updated: int


class EnrichResponse(BaseModel):
    research: dict
    scoring: dict
    contacts: dict


class PipelineStatusResponse(BaseModel):
    total_contractors: int
    with_research: int
    with_scores: int
    with_contacts: int
    awaiting_research: int
    awaiting_scoring: int
    awaiting_contacts: int
