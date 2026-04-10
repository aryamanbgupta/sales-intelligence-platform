"""
Enrichment orchestrator — connects research, scoring, and contact engines to the database.

Responsibilities:
    1. Query the DB for contractors that need enrichment
    2. Run Perplexity research (Stage 1)
    3. Persist research results back to lead_insights
    4. Run OpenAI scoring (Stage 2) on researched contractors
    5. Persist scoring results back to lead_insights
    6. Extract decision-maker contacts from research text
    7. Persist contacts to the contacts table
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.database import SessionLocal, init_db
from app.db.models import Contact, Contractor, LeadInsight
from app.pipeline.research import (
    BatchResearchReport,
    ResearchResult,
    research_batch_sync,
)
from app.pipeline.scoring import (
    BatchScoringReport,
    ScoringResult,
    score_batch_sync,
)
from app.pipeline.contact_enrichment import (
    BatchContactReport,
    ContactExtractionResult,
    ContactInfo,
    run_contact_extraction_sync,
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


# ---------------------------------------------------------------------------
# Stage 2: OpenAI Scoring
# ---------------------------------------------------------------------------


def get_unscored_contractors(
    session: Session,
    limit: int | None = None,
) -> list[Contractor]:
    """Find contractors that have research but no lead score."""
    query = (
        session.query(Contractor)
        .join(LeadInsight, Contractor.id == LeadInsight.contractor_id)
        .filter(LeadInsight.research_summary.isnot(None))
        .filter(LeadInsight.research_summary != "")
        .filter(
            (LeadInsight.lead_score.is_(None))
        )
    )
    if limit:
        query = query.limit(limit)
    return query.all()


def get_researched_contractors(
    session: Session,
    limit: int | None = None,
) -> list[Contractor]:
    """Find all contractors that have research (for force-rescore)."""
    query = (
        session.query(Contractor)
        .join(LeadInsight, Contractor.id == LeadInsight.contractor_id)
        .filter(LeadInsight.research_summary.isnot(None))
        .filter(LeadInsight.research_summary != "")
    )
    if limit:
        query = query.limit(limit)
    return query.all()


def build_research_map(session: Session, contractor_ids: list[int]) -> dict[int, str]:
    """Load research summaries for a set of contractors.

    Returns {contractor_id: research_summary_text}.
    """
    insights = (
        session.query(LeadInsight)
        .filter(LeadInsight.contractor_id.in_(contractor_ids))
        .all()
    )
    return {
        i.contractor_id: (i.research_summary or "")
        for i in insights
    }


def persist_scoring_result(session: Session, result: ScoringResult) -> None:
    """Write a single scoring result to the lead_insights table.

    Updates the existing row (created during Stage 1 research).
    """
    if not result.success:
        logger.warning(
            f"Skipping scoring persistence for '{result.contractor_name}' — "
            f"scoring failed: {result.error}"
        )
        return

    existing = (
        session.query(LeadInsight)
        .filter(LeadInsight.contractor_id == result.contractor_id)
        .first()
    )

    if existing:
        existing.lead_score = result.lead_score
        existing.score_breakdown = json.dumps(result.score_breakdown)
        existing.talking_points = json.dumps(result.talking_points)
        existing.buying_signals = json.dumps(result.buying_signals)
        existing.pain_points = json.dumps(result.pain_points)
        existing.recommended_pitch = result.recommended_pitch
        existing.why_now = result.why_now
        existing.draft_email = result.draft_email
        existing.updated_at = datetime.now(timezone.utc)
    else:
        # Edge case: research row doesn't exist yet (shouldn't happen in normal flow)
        insight = LeadInsight(
            contractor_id=result.contractor_id,
            lead_score=result.lead_score,
            score_breakdown=json.dumps(result.score_breakdown),
            talking_points=json.dumps(result.talking_points),
            buying_signals=json.dumps(result.buying_signals),
            pain_points=json.dumps(result.pain_points),
            recommended_pitch=result.recommended_pitch,
            why_now=result.why_now,
            draft_email=result.draft_email,
            enriched_at=datetime.now(timezone.utc),
        )
        session.add(insight)

    session.commit()


def run_scoring_enrichment(
    force: bool = False,
    limit: int | None = None,
    concurrency: int = 5,
) -> BatchScoringReport:
    """Main entry point: score all unscored contractors and persist results.

    Only processes contractors that already have Perplexity research.

    Args:
        force: If True, re-score ALL researched contractors.
        limit: Max number of contractors to process. None = all.
        concurrency: Parallel OpenAI API calls.

    Returns:
        BatchScoringReport with summary stats.
    """
    init_db()
    session = SessionLocal()

    try:
        if force:
            contractors = get_researched_contractors(session, limit=limit)
        else:
            contractors = get_unscored_contractors(session, limit=limit)

        if not contractors:
            logger.info("No contractors need scoring.")
            return BatchScoringReport()

        logger.info(f"Starting scoring enrichment for {len(contractors)} contractors...")

        # Load research summaries
        contractor_ids = [c.id for c in contractors]
        research_map = build_research_map(session, contractor_ids)

        # Convert ORM objects to dicts
        contractor_dicts = [c.to_dict() for c in contractors]

        def _on_progress(result: ScoringResult, completed: int, total: int):
            status = f"score={result.lead_score}" if result.success else f"FAILED: {result.error}"
            logger.info(f"  [{completed}/{total}] {result.contractor_name}: {status}")

        # Run the batch scoring
        report = score_batch_sync(
            contractor_dicts,
            research_map=research_map,
            concurrency=concurrency,
            on_progress=_on_progress,
        )

        # Persist successful results
        persisted = 0
        for result in report.results:
            if result.success:
                persist_scoring_result(session, result)
                persisted += 1

        logger.info(
            f"Scoring enrichment complete: {persisted} persisted, "
            f"{report.failed} failed, {report.total_duration_seconds:.1f}s total"
        )

        return report

    finally:
        session.close()


# ---------------------------------------------------------------------------
# Stage 3: Contact Extraction
# ---------------------------------------------------------------------------


def get_contractors_without_contacts(
    session: Session,
    limit: int | None = None,
) -> list[Contractor]:
    """Find contractors that have research but no contacts yet."""
    query = (
        session.query(Contractor)
        .join(LeadInsight, Contractor.id == LeadInsight.contractor_id)
        .filter(LeadInsight.research_summary.isnot(None))
        .filter(LeadInsight.research_summary != "")
        .filter(~Contractor.id.in_(
            session.query(Contact.contractor_id).distinct()
        ))
    )
    if limit:
        query = query.limit(limit)
    return query.all()


def persist_contact_result(
    session: Session,
    result: ContactExtractionResult,
) -> int:
    """Write extracted contacts to the contacts table.

    Returns number of contacts persisted.
    """
    if not result.success or not result.contacts:
        return 0

    persisted = 0
    for contact in result.contacts:
        # Dedupe: skip if same name+contractor already exists
        existing = (
            session.query(Contact)
            .filter(Contact.contractor_id == result.contractor_id)
            .filter(Contact.full_name == contact.full_name)
            .first()
        )
        if existing:
            # Update with any new info
            if contact.title and not existing.title:
                existing.title = contact.title
            if contact.email and not existing.email:
                existing.email = contact.email
            if contact.phone and not existing.phone:
                existing.phone = contact.phone
            if contact.linkedin_url and not existing.linkedin_url:
                existing.linkedin_url = contact.linkedin_url
            existing.updated_at = datetime.now(timezone.utc)
        else:
            new_contact = Contact(
                contractor_id=result.contractor_id,
                full_name=contact.full_name,
                title=contact.title,
                email=contact.email,
                phone=contact.phone,
                linkedin_url=contact.linkedin_url,
                source=contact.source or "perplexity_research",
                confidence=contact.confidence or "medium",
            )
            session.add(new_contact)
            persisted += 1

    session.commit()
    return persisted


def run_contact_enrichment(
    force: bool = False,
    limit: int | None = None,
    concurrency: int = 5,
) -> BatchContactReport:
    """Main entry point: extract contacts for researched contractors.

    Args:
        force: If True, re-extract for ALL researched contractors
               (existing contacts are deduped, not replaced).
        limit: Max contractors to process.
        concurrency: Parallel OpenAI calls.

    Returns:
        BatchContactReport with summary stats.
    """
    init_db()
    session = SessionLocal()

    try:
        if force:
            contractors = get_researched_contractors(session, limit=limit)
        else:
            contractors = get_contractors_without_contacts(session, limit=limit)

        if not contractors:
            logger.info("No contractors need contact extraction.")
            return BatchContactReport()

        logger.info(f"Starting contact extraction for {len(contractors)} contractors...")

        contractor_ids = [c.id for c in contractors]
        research_map = build_research_map(session, contractor_ids)
        contractor_dicts = [c.to_dict() for c in contractors]

        def _on_progress(result: ContactExtractionResult, completed: int, total: int):
            count = len(result.contacts) if result.success else 0
            status = f"{count} contacts" if result.success else f"FAILED: {result.error}"
            logger.info(f"  [{completed}/{total}] {result.contractor_name}: {status}")

        report = run_contact_extraction_sync(
            contractor_dicts,
            research_map=research_map,
            concurrency=concurrency,
            on_progress=_on_progress,
        )

        # Persist
        total_persisted = 0
        for result in report.results:
            if result.success:
                total_persisted += persist_contact_result(session, result)

        logger.info(
            f"Contact extraction complete: {total_persisted} new contacts persisted, "
            f"{report.total_contacts_found} total found, "
            f"{report.total_duration_seconds:.1f}s"
        )

        return report

    finally:
        session.close()


def ingest_contractors(contractors_data: list[dict]) -> list[Contractor]:
    """Insert or update contractors from raw dicts (e.g., from scraper or manual input).

    Each dict should have at minimum: name, address.
    Optional: city, state, zip_code, phone, website, certification,
              certifications_raw, rating, review_count, services,
              years_in_business, about, profile_url, image_url,
              latitude, longitude, distance_miles.

    Returns list of Contractor ORM objects (with IDs populated).
    """
    init_db()
    session = SessionLocal()

    def _json_col(data, key):
        """Serialize a list field to JSON text for storage."""
        val = data.get(key)
        if val and isinstance(val, list):
            return json.dumps(val)
        return None

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
                existing.name = name
                existing.address = address
                existing.city = data.get("city", existing.city)
                existing.state = data.get("state", existing.state)
                existing.zip_code = data.get("zip_code", existing.zip_code)
                existing.phone = data.get("phone", existing.phone)
                existing.website = data.get("website", existing.website)
                existing.certification = data.get("certification", existing.certification)
                existing.certifications_raw = _json_col(data, "certifications_raw") or existing.certifications_raw
                existing.rating = data.get("rating", existing.rating)
                existing.review_count = data.get("review_count", existing.review_count)
                existing.services = _json_col(data, "services") or existing.services
                existing.latitude = data.get("latitude", existing.latitude)
                existing.longitude = data.get("longitude", existing.longitude)
                existing.distance_miles = data.get("distance_miles", existing.distance_miles)
                existing.years_in_business = data.get("years_in_business", existing.years_in_business)
                existing.about = data.get("about", existing.about)
                existing.profile_url = data.get("profile_url", existing.profile_url)
                existing.image_url = data.get("image_url", existing.image_url)
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
                    certifications_raw=_json_col(data, "certifications_raw"),
                    rating=data.get("rating"),
                    review_count=data.get("review_count"),
                    services=_json_col(data, "services"),
                    latitude=data.get("latitude"),
                    longitude=data.get("longitude"),
                    distance_miles=data.get("distance_miles"),
                    years_in_business=data.get("years_in_business"),
                    about=data.get("about"),
                    profile_url=data.get("profile_url"),
                    image_url=data.get("image_url"),
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
