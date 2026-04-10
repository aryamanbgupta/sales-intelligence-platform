"""Tests for FastAPI endpoints — uses TestClient with DB dependency override."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_session
from app.db.models import Contact, Contractor, LeadInsight
from app.main import app

# ---------------------------------------------------------------------------
# Shared test engine — StaticPool ensures the same in-memory DB across threads
# ---------------------------------------------------------------------------

_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSession = sessionmaker(bind=_engine)


def _override_get_session():
    session = _TestSession()
    try:
        yield session
    finally:
        session.close()


app.dependency_overrides[get_session] = _override_get_session


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_tables():
    """Recreate all tables for each test."""
    Base.metadata.drop_all(bind=_engine)
    Base.metadata.create_all(bind=_engine)
    yield


@pytest.fixture()
def session():
    """Yield a session for seeding test data."""
    s = _TestSession()
    yield s
    s.close()


client = TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _insert_contractor(session, gaf_id, name, **kwargs):
    c = Contractor(
        gaf_id=gaf_id,
        name=name,
        address=kwargs.get("address", "City, ST, 00000"),
        city=kwargs.get("city", "City"),
        state=kwargs.get("state", "ST"),
        certification=kwargs.get("certification"),
        rating=kwargs.get("rating"),
        review_count=kwargs.get("review_count"),
        phone=kwargs.get("phone"),
        website=kwargs.get("website"),
    )
    session.add(c)
    session.commit()
    session.refresh(c)
    return c


def _insert_insight(session, contractor_id, lead_score, **kwargs):
    li = LeadInsight(
        contractor_id=contractor_id,
        lead_score=lead_score,
        research_summary=kwargs.get("research_summary", "Research text."),
        citations=kwargs.get("citations", "[]"),
        score_breakdown=kwargs.get("score_breakdown", "{}"),
        talking_points=kwargs.get("talking_points", "[]"),
        buying_signals=kwargs.get("buying_signals", "[]"),
        pain_points=kwargs.get("pain_points", "[]"),
        recommended_pitch=kwargs.get("recommended_pitch", "Pitch."),
        why_now=kwargs.get("why_now", "No urgency."),
        draft_email=kwargs.get("draft_email", "Hi, ..."),
    )
    session.add(li)
    session.commit()
    session.refresh(li)
    return li


def _insert_contact(session, contractor_id, full_name, title="Owner"):
    ct = Contact(
        contractor_id=contractor_id,
        full_name=full_name,
        title=title,
        source="perplexity_research",
        confidence="high",
    )
    session.add(ct)
    session.commit()
    return ct


# =========================================================================
# GET /api/health
# =========================================================================


class TestHealth:

    def test_health(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# =========================================================================
# GET /api/leads
# =========================================================================


class TestListLeads:

    def test_empty_database(self):
        resp = client.get("/api/leads")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"] == []
        assert data["pagination"]["total_items"] == 0

    def test_returns_leads_with_pagination(self, session):
        for i in range(5):
            _insert_contractor(session, f"L{i}", f"Lead {i}")

        resp = client.get("/api/leads?page=1&per_page=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 2
        assert data["pagination"]["total_items"] == 5
        assert data["pagination"]["total_pages"] == 3

    def test_pagination_meta_fields(self, session):
        _insert_contractor(session, "PM1", "Co A")

        resp = client.get("/api/leads?page=1&per_page=10")
        pagination = resp.json()["pagination"]
        assert pagination["page"] == 1
        assert pagination["per_page"] == 10
        assert pagination["total_items"] == 1
        assert pagination["total_pages"] == 1

    def test_sort_by_score_desc(self, session):
        c1 = _insert_contractor(session, "SD1", "Low")
        c2 = _insert_contractor(session, "SD2", "High")
        _insert_insight(session, c1.id, 30)
        _insert_insight(session, c2.id, 80)

        resp = client.get("/api/leads?sort_by=lead_score&sort_order=desc")
        leads = resp.json()["data"]
        assert leads[0]["name"] == "High"
        assert leads[1]["name"] == "Low"

    def test_filter_min_score(self, session):
        c1 = _insert_contractor(session, "FS1", "Low")
        c2 = _insert_contractor(session, "FS2", "High")
        _insert_insight(session, c1.id, 30)
        _insert_insight(session, c2.id, 70)

        resp = client.get("/api/leads?min_score=50")
        data = resp.json()
        assert data["pagination"]["total_items"] == 1
        assert data["data"][0]["name"] == "High"

    def test_filter_certification(self, session):
        _insert_contractor(session, "FC1", "Elite", certification="Master Elite")
        _insert_contractor(session, "FC2", "Cert", certification="Certified")

        resp = client.get("/api/leads?certification=Master+Elite")
        data = resp.json()
        assert data["pagination"]["total_items"] == 1
        assert data["data"][0]["name"] == "Elite"

    def test_search(self, session):
        _insert_contractor(session, "SE1", "ABC Roofing")
        _insert_contractor(session, "SE2", "XYZ Siding")

        resp = client.get("/api/leads?search=ABC")
        data = resp.json()
        assert data["pagination"]["total_items"] == 1
        assert data["data"][0]["name"] == "ABC Roofing"

    def test_lead_list_item_shape(self, session):
        c = _insert_contractor(session, "SH1", "Shape Co", city="Brooklyn", state="NY")
        _insert_insight(session, c.id, 55)

        resp = client.get("/api/leads")
        item = resp.json()["data"][0]
        assert item["name"] == "Shape Co"
        assert item["lead_score"] == 55
        assert item["city"] == "Brooklyn"
        # Heavy fields must not leak into list view
        assert "research_summary" not in item
        assert "draft_email" not in item
        assert "insights" not in item

    def test_invalid_page_rejected(self):
        resp = client.get("/api/leads?page=0")
        assert resp.status_code == 422

    def test_per_page_capped_at_100(self):
        resp = client.get("/api/leads?per_page=200")
        assert resp.status_code == 422


# =========================================================================
# GET /api/leads/{id}
# =========================================================================


class TestGetLead:

    def test_not_found(self):
        resp = client.get("/api/leads/9999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Lead not found"

    def test_returns_full_detail(self, session):
        c = _insert_contractor(session, "DT1", "Detail Co", city="Manhattan", state="NY")
        _insert_insight(
            session, c.id, 72,
            talking_points='["Talk about storms"]',
            buying_signals='["Expanding territory"]',
            pain_points='["Slow delivery"]',
            why_now="Recent hailstorm.",
            draft_email="Subject: Hello...",
            research_summary="Detailed research text.",
            citations='["https://example.com"]',
        )
        _insert_contact(session, c.id, "John Doe", "President")

        resp = client.get(f"/api/leads/{c.id}")
        assert resp.status_code == 200
        data = resp.json()

        # Contractor fields
        assert data["name"] == "Detail Co"
        assert data["city"] == "Manhattan"
        assert data["gaf_id"] == "DT1"

        # Insights
        assert data["insights"]["lead_score"] == 72
        assert data["insights"]["talking_points"] == ["Talk about storms"]
        assert data["insights"]["why_now"] == "Recent hailstorm."
        assert data["insights"]["citations"] == ["https://example.com"]

        # Contacts
        assert len(data["contacts"]) == 1
        assert data["contacts"][0]["full_name"] == "John Doe"
        assert data["contacts"][0]["title"] == "President"

    def test_detail_without_insights(self, session):
        c = _insert_contractor(session, "DT2", "No Insight Co")

        resp = client.get(f"/api/leads/{c.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["insights"] is None
        assert data["contacts"] == []


# =========================================================================
# GET /api/stats
# =========================================================================


class TestStats:

    def test_empty_database(self):
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_leads"] == 0
        assert data["avg_score"] is None
        assert data["high_priority_count"] == 0

    def test_stats_with_data(self, session):
        c1 = _insert_contractor(session, "ST1", "Co A", certification="Master Elite")
        c2 = _insert_contractor(session, "ST2", "Co B", certification="Master Elite")
        c3 = _insert_contractor(session, "ST3", "Co C", certification="Certified")
        _insert_insight(session, c1.id, 80)
        _insert_insight(session, c2.id, 40)
        _insert_insight(session, c3.id, 60)

        resp = client.get("/api/stats")
        data = resp.json()
        assert data["total_leads"] == 3
        assert data["avg_score"] == 60.0
        assert data["high_priority_count"] == 1
        assert data["certification_breakdown"]["Master Elite"] == 2
        assert data["certification_breakdown"]["Certified"] == 1

    def test_score_distribution(self, session):
        c1 = _insert_contractor(session, "SB1", "C1")
        c2 = _insert_contractor(session, "SB2", "C2")
        _insert_insight(session, c1.id, 15)   # 0-25
        _insert_insight(session, c2.id, 90)   # 76-100

        resp = client.get("/api/stats")
        dist = resp.json()["score_distribution"]
        assert dist["0-25"] == 1
        assert dist["26-50"] == 0
        assert dist["51-75"] == 0
        assert dist["76-100"] == 1


# =========================================================================
# GET /api/pipeline/status
# =========================================================================


class TestPipelineStatus:

    def test_empty_database(self):
        resp = client.get("/api/pipeline/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_contractors"] == 0
        assert data["with_research"] == 0
        assert data["with_scores"] == 0
        assert data["with_contacts"] == 0

    def test_with_data(self, session):
        c1 = _insert_contractor(session, "PS1", "Co A")
        c2 = _insert_contractor(session, "PS2", "Co B")
        _insert_insight(session, c1.id, 60, research_summary="Research text.")
        _insert_insight(session, c2.id, None, research_summary="Research only.")
        _insert_contact(session, c1.id, "Owner A")

        resp = client.get("/api/pipeline/status")
        data = resp.json()
        assert data["total_contractors"] == 2
        assert data["with_research"] == 2
        assert data["with_scores"] == 1
        assert data["with_contacts"] == 1
        assert data["awaiting_scoring"] == 1
