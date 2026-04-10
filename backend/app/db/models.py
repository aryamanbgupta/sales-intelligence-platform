import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Contractor(Base):
    """Raw scraped data from GAF directory. One row per contractor."""

    __tablename__ = "contractors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    gaf_id = Column(Text, unique=True, nullable=False, index=True)
    name = Column(Text, nullable=False)
    address = Column(Text)
    city = Column(Text)
    state = Column(Text)
    zip_code = Column(Text)
    phone = Column(Text)
    website = Column(Text)
    certification = Column(Text)       # "Master Elite", "Certified", etc.
    certifications_raw = Column(Text)  # JSON array of all certifications
    rating = Column(Float)             # star rating 0-5
    review_count = Column(Integer)
    services = Column(Text)            # JSON array of services offered
    latitude = Column(Float)
    longitude = Column(Float)
    distance_miles = Column(Float)     # distance from search location
    years_in_business = Column(Integer)  # years of operation
    about = Column(Text)                # company description from profile
    profile_url = Column(Text)          # GAF profile page URL
    image_url = Column(Text)            # profile image URL
    scraped_at = Column(DateTime, default=_utcnow)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # Relationship to insights
    insights = relationship("LeadInsight", back_populates="contractor", uselist=False)

    @staticmethod
    def generate_gaf_id(name: str, address: str) -> str:
        """Deterministic dedupe key from name + address."""
        raw = f"{name.strip().lower()}|{(address or '').strip().lower()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @property
    def services_list(self) -> list[str]:
        if not self.services:
            return []
        return json.loads(self.services)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "gaf_id": self.gaf_id,
            "name": self.name,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "phone": self.phone,
            "website": self.website,
            "certification": self.certification,
            "certifications_raw": json.loads(self.certifications_raw) if self.certifications_raw else [],
            "rating": self.rating,
            "review_count": self.review_count,
            "services": self.services_list,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "distance_miles": self.distance_miles,
            "years_in_business": self.years_in_business,
            "about": self.about,
            "profile_url": self.profile_url,
            "image_url": self.image_url,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
        }


class LeadInsight(Base):
    """AI-generated enrichment data. One row per contractor."""

    __tablename__ = "lead_insights"
    __table_args__ = (
        UniqueConstraint("contractor_id", name="uq_lead_insights_contractor"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    contractor_id = Column(Integer, ForeignKey("contractors.id"), nullable=False)

    # --- Perplexity research output (Stage 1) ---
    research_summary = Column(Text)    # synthesized research text
    citations = Column(Text)           # JSON array of source URLs

    # --- OpenAI structured scoring (Stage 2) ---
    lead_score = Column(Integer)       # 0-100
    score_breakdown = Column(Text)     # JSON: {certification: 25, reviews: 18, ...}
    talking_points = Column(Text)      # JSON array of strings
    buying_signals = Column(Text)      # JSON array of strings
    pain_points = Column(Text)         # JSON array of strings
    recommended_pitch = Column(Text)
    why_now = Column(Text)             # time-sensitive signal
    draft_email = Column(Text)

    enriched_at = Column(DateTime, default=_utcnow)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # Relationship back to contractor
    contractor = relationship("Contractor", back_populates="insights")

    def to_dict(self) -> dict:
        def _parse_json(val):
            if not val:
                return []
            return json.loads(val)

        return {
            "id": self.id,
            "contractor_id": self.contractor_id,
            "research_summary": self.research_summary,
            "citations": _parse_json(self.citations),
            "lead_score": self.lead_score,
            "score_breakdown": _parse_json(self.score_breakdown) if self.score_breakdown else {},
            "talking_points": _parse_json(self.talking_points),
            "buying_signals": _parse_json(self.buying_signals),
            "pain_points": _parse_json(self.pain_points),
            "recommended_pitch": self.recommended_pitch,
            "why_now": self.why_now,
            "draft_email": self.draft_email,
            "enriched_at": self.enriched_at.isoformat() if self.enriched_at else None,
        }
