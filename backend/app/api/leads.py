"""Lead endpoints — browse, filter, and drill into contractor leads."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.schemas import (
    LeadDetail,
    LeadListResponse,
    PaginationMeta,
    StatsResponse,
)
from app.db.database import get_session
from app.services.lead_service import get_lead_detail, get_leads, get_stats

router = APIRouter(prefix="/api", tags=["leads"])


@router.get("/leads", response_model=LeadListResponse)
def list_leads(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = Query("lead_score"),
    sort_order: str = Query("desc"),
    min_score: Optional[int] = Query(None, ge=0, le=100),
    max_score: Optional[int] = Query(None, ge=0, le=100),
    certification: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    session: Session = Depends(get_session),
):
    leads, total = get_leads(
        session,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        sort_order=sort_order,
        min_score=min_score,
        max_score=max_score,
        certification=certification,
        search=search,
    )
    total_pages = (total + per_page - 1) // per_page if total > 0 else 0
    return LeadListResponse(
        data=leads,
        pagination=PaginationMeta(
            page=page,
            per_page=per_page,
            total_items=total,
            total_pages=total_pages,
        ),
    )


@router.get("/leads/{lead_id}", response_model=LeadDetail)
def get_lead(
    lead_id: int,
    session: Session = Depends(get_session),
):
    lead = get_lead_detail(session, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.get("/stats", response_model=StatsResponse)
def stats(session: Session = Depends(get_session)):
    return get_stats(session)
