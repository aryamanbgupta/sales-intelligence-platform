"""Pipeline endpoints — trigger scraping and enrichment."""

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.schemas import EnrichResponse, PipelineStatusResponse, ScrapeResponse
from app.db.database import get_session
from app.db.models import Contact, Contractor, LeadInsight

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.post("/scrape", response_model=ScrapeResponse)
def scrape(
    zip_code: str = Query("10013"),
    distance: int = Query(25, ge=5, le=100),
):
    """Trigger scraping from GAF directory. Blocks until complete."""
    from app.pipeline.scraper import (
        scrape_contractors,
        scrape_profile_details,
        store_contractors,
        update_profile_details,
    )

    # Run async scraper in this thread's event loop
    # (safe — sync handlers run in a thread pool with no existing loop)
    contractors = asyncio.run(scrape_contractors(zip_code, distance))

    # Persist to database
    result = store_contractors(contractors)

    # Scrape profile pages for website / years_in_business / about
    profile_entries = [
        {"gaf_id": c["gaf_id"], "profile_url": c["profile_url"]}
        for c in contractors
        if c.get("profile_url")
    ]
    if profile_entries:
        details = asyncio.run(scrape_profile_details(profile_entries, concurrency=3))
        update_profile_details(details)

    return ScrapeResponse(
        contractors_found=len(contractors),
        new=result["new"],
        updated=result["updated"],
    )


@router.post("/enrich", response_model=EnrichResponse)
def enrich(
    force: bool = Query(False),
    limit: Optional[int] = Query(None, ge=1),
):
    """Run all 3 enrichment stages sequentially."""
    from app.pipeline.enricher import (
        run_contact_enrichment,
        run_research_enrichment,
        run_scoring_enrichment,
    )

    research_report = run_research_enrichment(force=force, limit=limit)
    scoring_report = run_scoring_enrichment(force=force, limit=limit)
    contact_report = run_contact_enrichment(force=force, limit=limit)

    return EnrichResponse(
        research={
            "total": research_report.total,
            "succeeded": research_report.succeeded,
            "failed": research_report.failed,
            "duration_seconds": round(research_report.total_duration_seconds, 1),
        },
        scoring={
            "total": scoring_report.total,
            "succeeded": scoring_report.succeeded,
            "failed": scoring_report.failed,
            "duration_seconds": round(scoring_report.total_duration_seconds, 1),
        },
        contacts={
            "total": contact_report.total,
            "succeeded": contact_report.succeeded,
            "failed": contact_report.failed,
            "contacts_found": contact_report.total_contacts_found,
            "duration_seconds": round(contact_report.total_duration_seconds, 1),
        },
    )


@router.get("/status", response_model=PipelineStatusResponse)
def pipeline_status(session: Session = Depends(get_session)):
    """Return pipeline health summary."""
    total = session.query(Contractor).count()
    researched = (
        session.query(LeadInsight)
        .filter(LeadInsight.research_summary.isnot(None))
        .filter(LeadInsight.research_summary != "")
        .count()
    )
    scored = (
        session.query(LeadInsight)
        .filter(LeadInsight.lead_score.isnot(None))
        .count()
    )
    with_contacts = (
        session.query(Contact.contractor_id).distinct().count()
    )

    return PipelineStatusResponse(
        total_contractors=total,
        with_research=researched,
        with_scores=scored,
        with_contacts=with_contacts,
        awaiting_research=total - researched,
        awaiting_scoring=researched - scored,
        awaiting_contacts=researched - with_contacts,
    )
