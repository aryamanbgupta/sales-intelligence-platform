"""
Enrichment orchestrator — connects the research engine to the database.

Responsibilities:
    1. Query the DB for contractors that need enrichment
    2. Run Perplexity research (Stage 1)
    3. Persist research results back to lead_insights
    4. (Stage 2 — OpenAI scoring — will be added separately)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.database import SessionLocal, init_db
from app.db.models import Contractor, LeadInsight
from app.pipeline.research import (
    BatchResearchReport,
    ResearchResult,
    research_batch_sync,
)

logger = logging.getLogger(__name__)


def get_unenriched_contractors(
    session: Session,
    limit: int | None = None,
) -> list[Contractor]:
    """Find contractors that have no lead_insights record (or empty research)."""
    query = (
        session.query(Contractor)
        .outerjoin(LeadInsight, Contractor.id == LeadInsight.contractor_id)
        .filter(
            (LeadInsight.id.is_(None))
            | (LeadInsight.research_summary.is_(None))
            | (LeadInsight.research_summary == "")
        )
    )
    if limit:
        query = query.limit(limit)
    return query.all()


def get_all_contractors(session: Session) -> list[Contractor]:
    """Return all contractors in the database."""
    return session.query(Contractor).all()


def persist_research_result(session: Session, result: ResearchResult) -> None:
    """Write a single research result to the lead_insights table.

    Upserts — creates a new row or updates existing one for the contractor.
    """
    if not result.success:
        logger.warning(
            f"Skipping persistence for '{result.contractor_name}' — research failed: {result.error}"
        )
        return

    existing = (
        session.query(LeadInsight)
        .filter(LeadInsight.contractor_id == result.contractor_id)
        .first()
    )

    if existing:
        existing.research_summary = result.research_summary
        existing.citations = json.dumps(result.citations)
        existing.enriched_at = datetime.now(timezone.utc)
        existing.updated_at = datetime.now(timezone.utc)
    else:
        insight = LeadInsight(
            contractor_id=result.contractor_id,
            research_summary=result.research_summary,
            citations=json.dumps(result.citations),
            enriched_at=datetime.now(timezone.utc),
        )
        session.add(insight)

    session.commit()


def run_research_enrichment(
    force: bool = False,
    limit: int | None = None,
    concurrency: int = 3,
) -> BatchResearchReport:
    """Main entry point: research all unenriched contractors and persist results.

    Args:
        force: If True, re-research ALL contractors (even those already enriched).
        limit: Max number of contractors to process. None = all.
        concurrency: Parallel API call limit.

    Returns:
        BatchResearchReport with summary stats.
    """
    init_db()
    session = SessionLocal()

    try:
        if force:
            contractors = get_all_contractors(session)
        else:
            contractors = get_unenriched_contractors(session, limit=limit)

        if not contractors:
            logger.info("No contractors need enrichment.")
            return BatchResearchReport()

        logger.info(f"Starting research enrichment for {len(contractors)} contractors...")

        # Convert ORM objects to dicts for the research engine
        contractor_dicts = [c.to_dict() for c in contractors]

        def _on_progress(result: ResearchResult, completed: int, total: int):
            status = "OK" if result.success else f"FAILED: {result.error}"
            logger.info(f"  [{completed}/{total}] {result.contractor_name}: {status}")

        # Run the batch research
        report = research_batch_sync(
            contractor_dicts,
            concurrency=concurrency,
            on_progress=_on_progress,
        )

        # Persist successful results
        persisted = 0
        for result in report.results:
            if result.success:
                persist_research_result(session, result)
                persisted += 1

        logger.info(
            f"Research enrichment complete: {persisted} persisted, "
            f"{report.failed} failed, {report.total_duration_seconds:.1f}s total"
        )

        return report

    finally:
        session.close()


def ingest_contractors(contractors_data: list[dict]) -> list[Contractor]:
    """Insert or update contractors from raw dicts (e.g., from scraper or manual input).

    Each dict should have at minimum: name, address.
    Optional: city, state, zip_code, phone, website, certification, rating,
              review_count, services.

    Returns list of Contractor ORM objects (with IDs populated).
    """
    init_db()
    session = SessionLocal()

    try:
        results = []
        for data in contractors_data:
            name = data.get("name", "").strip()
            if not name:
                logger.warning(f"Skipping contractor with no name: {data}")
                continue

            address = data.get("address", "")
            gaf_id = data.get("gaf_id") or Contractor.generate_gaf_id(name, address)

            # Upsert: check if this contractor already exists
            existing = session.query(Contractor).filter(Contractor.gaf_id == gaf_id).first()

            if existing:
                # Update fields
                existing.name = name
                existing.address = address
                existing.city = data.get("city", existing.city)
                existing.state = data.get("state", existing.state)
                existing.zip_code = data.get("zip_code", existing.zip_code)
                existing.phone = data.get("phone", existing.phone)
                existing.website = data.get("website", existing.website)
                existing.certification = data.get("certification", existing.certification)
                existing.rating = data.get("rating", existing.rating)
                existing.review_count = data.get("review_count", existing.review_count)
                existing.services = json.dumps(data["services"]) if "services" in data and isinstance(data["services"], list) else existing.services
                existing.updated_at = datetime.now(timezone.utc)
                results.append(existing)
                logger.info(f"Updated existing contractor: {name}")
            else:
                contractor = Contractor(
                    gaf_id=gaf_id,
                    name=name,
                    address=address,
                    city=data.get("city"),
                    state=data.get("state"),
                    zip_code=data.get("zip_code"),
                    phone=data.get("phone"),
                    website=data.get("website"),
                    certification=data.get("certification"),
                    rating=data.get("rating"),
                    review_count=data.get("review_count"),
                    services=json.dumps(data["services"]) if "services" in data and isinstance(data["services"], list) else None,
                )
                session.add(contractor)
                results.append(contractor)
                logger.info(f"Inserted new contractor: {name}")

        session.commit()

        # Refresh to get IDs
        for c in results:
            session.refresh(c)

        logger.info(f"Ingested {len(results)} contractors.")
        return results

    finally:
        session.close()
