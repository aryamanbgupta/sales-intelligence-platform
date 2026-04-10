"""Query helpers for lead data — filtering, sorting, pagination."""

from typing import Dict, List, Optional, Tuple

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.db.models import Contact, Contractor, LeadInsight


# ---------------------------------------------------------------------------
# Paginated lead list
# ---------------------------------------------------------------------------

# Whitelist of sortable columns to prevent injection via dynamic column names.
_SORT_COLUMNS = {
    "lead_score": LeadInsight.lead_score,
    "name": Contractor.name,
    "rating": Contractor.rating,
    "review_count": Contractor.review_count,
    "certification": Contractor.certification,
    "distance_miles": Contractor.distance_miles,
}


def get_leads(
    session: Session,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "lead_score",
    sort_order: str = "desc",
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
    certification: Optional[str] = None,
    search: Optional[str] = None,
) -> Tuple[List[dict], int]:
    """Return a page of leads with basic info + lead_score.

    Returns (list_of_lead_dicts, total_matching_count).
    """
    query = (
        session.query(Contractor, LeadInsight.lead_score)
        .outerjoin(LeadInsight, Contractor.id == LeadInsight.contractor_id)
    )

    # --- Filters ---
    if min_score is not None:
        query = query.filter(LeadInsight.lead_score >= min_score)
    if max_score is not None:
        query = query.filter(LeadInsight.lead_score <= max_score)
    if certification:
        query = query.filter(Contractor.certification == certification)
    if search:
        query = query.filter(Contractor.name.ilike(f"%{search}%"))

    # Total count before pagination
    total = query.count()

    # --- Sorting ---
    col = _SORT_COLUMNS.get(sort_by, LeadInsight.lead_score)
    if sort_order == "desc":
        query = query.order_by(col.desc().nullslast())
    else:
        query = query.order_by(col.asc().nullsfirst())

    # --- Pagination ---
    offset = (page - 1) * per_page
    rows = query.offset(offset).limit(per_page).all()

    # Build compact dicts for the list view
    leads = []
    for contractor, lead_score in rows:
        leads.append({
            "id": contractor.id,
            "name": contractor.name,
            "city": contractor.city,
            "state": contractor.state,
            "certification": contractor.certification,
            "rating": contractor.rating,
            "review_count": contractor.review_count,
            "lead_score": lead_score,
            "phone": contractor.phone,
            "website": contractor.website,
            "image_url": contractor.image_url,
            "distance_miles": contractor.distance_miles,
            "years_in_business": contractor.years_in_business,
        })

    return leads, total


# ---------------------------------------------------------------------------
# Single lead detail
# ---------------------------------------------------------------------------


def get_lead_detail(session: Session, lead_id: int) -> Optional[dict]:
    """Return full contractor data with nested insights and contacts."""
    contractor = session.query(Contractor).filter(Contractor.id == lead_id).first()
    if not contractor:
        return None

    result = contractor.to_dict()

    # Nest insights (1:1 relationship)
    if contractor.insights:
        result["insights"] = contractor.insights.to_dict()
    else:
        result["insights"] = None

    # Nest contacts (1:many)
    result["contacts"] = [c.to_dict() for c in contractor.contacts]

    return result


# ---------------------------------------------------------------------------
# Dashboard stats
# ---------------------------------------------------------------------------


def get_stats(session: Session) -> dict:
    """Return aggregate statistics for the dashboard."""
    total_leads = session.query(Contractor).count()

    avg_score = (
        session.query(func.avg(LeadInsight.lead_score))
        .filter(LeadInsight.lead_score.isnot(None))
        .scalar()
    )

    high_priority = (
        session.query(func.count(LeadInsight.id))
        .filter(LeadInsight.lead_score >= 70)
        .scalar()
    ) or 0

    # Certification breakdown
    cert_rows = (
        session.query(Contractor.certification, func.count())
        .group_by(Contractor.certification)
        .all()
    )
    certification_breakdown = {
        (cert or "Uncertified"): count for cert, count in cert_rows
    }

    # Score distribution in buckets
    buckets = (
        session.query(
            func.count(case((LeadInsight.lead_score.between(0, 25), 1))),
            func.count(case((LeadInsight.lead_score.between(26, 50), 1))),
            func.count(case((LeadInsight.lead_score.between(51, 75), 1))),
            func.count(case((LeadInsight.lead_score.between(76, 100), 1))),
        )
        .first()
    )
    score_distribution = {
        "0-25": buckets[0] if buckets else 0,
        "26-50": buckets[1] if buckets else 0,
        "51-75": buckets[2] if buckets else 0,
        "76-100": buckets[3] if buckets else 0,
    }

    return {
        "total_leads": total_leads,
        "avg_score": round(avg_score, 1) if avg_score is not None else None,
        "high_priority_count": high_priority,
        "certification_breakdown": certification_breakdown,
        "score_distribution": score_distribution,
    }
