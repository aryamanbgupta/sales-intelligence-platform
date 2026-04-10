"""Tests for lead_service — filtering, sorting, pagination, stats."""

import json

from app.db.models import Contact, Contractor, LeadInsight
from app.services.lead_service import get_lead_detail, get_leads, get_stats


def _make_contractor(session, gaf_id, name, **kwargs):
    """Insert a contractor and return the ORM object."""
    c = Contractor(
        gaf_id=gaf_id,
        name=name,
        address=kwargs.get("address", "Test City, TS, 00000"),
        city=kwargs.get("city", "Test City"),
        state=kwargs.get("state", "TS"),
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


def _make_insight(session, contractor_id, lead_score, **kwargs):
    """Insert a lead insight and return the ORM object."""
    li = LeadInsight(
        contractor_id=contractor_id,
        lead_score=lead_score,
        research_summary=kwargs.get("research_summary", "Some research."),
        citations=kwargs.get("citations", "[]"),
        score_breakdown=kwargs.get("score_breakdown", '{}'),
        talking_points=kwargs.get("talking_points", '[]'),
        buying_signals=kwargs.get("buying_signals", '[]'),
        pain_points=kwargs.get("pain_points", '[]'),
        recommended_pitch=kwargs.get("recommended_pitch", "Pitch text."),
        why_now=kwargs.get("why_now", "No urgency."),
        draft_email=kwargs.get("draft_email", "Hi, ..."),
    )
    session.add(li)
    session.commit()
    session.refresh(li)
    return li


def _make_contact(session, contractor_id, full_name, title="Owner"):
    """Insert a contact and return the ORM object."""
    ct = Contact(
        contractor_id=contractor_id,
        full_name=full_name,
        title=title,
        source="perplexity_research",
        confidence="high",
    )
    session.add(ct)
    session.commit()
    session.refresh(ct)
    return ct


# =========================================================================
# get_leads
# =========================================================================


class TestGetLeads:

    def test_returns_all_contractors(self, db_session):
        _make_contractor(db_session, "A1", "Alpha Co")
        _make_contractor(db_session, "A2", "Beta Co")
        _make_contractor(db_session, "A3", "Gamma Co")

        leads, total = get_leads(db_session)
        assert total == 3
        assert len(leads) == 3

    def test_pagination(self, db_session):
        for i in range(5):
            _make_contractor(db_session, f"P{i}", f"Page Co {i}")

        leads, total = get_leads(db_session, page=1, per_page=2)
        assert total == 5
        assert len(leads) == 2

        leads2, _ = get_leads(db_session, page=3, per_page=2)
        assert len(leads2) == 1  # last page has 1 item

    def test_sort_by_lead_score_desc(self, db_session):
        c1 = _make_contractor(db_session, "S1", "Low Score")
        c2 = _make_contractor(db_session, "S2", "High Score")
        c3 = _make_contractor(db_session, "S3", "Mid Score")
        _make_insight(db_session, c1.id, 20)
        _make_insight(db_session, c2.id, 80)
        _make_insight(db_session, c3.id, 50)

        leads, _ = get_leads(db_session, sort_by="lead_score", sort_order="desc")
        scores = [l["lead_score"] for l in leads]
        assert scores == [80, 50, 20]

    def test_sort_by_name_asc(self, db_session):
        _make_contractor(db_session, "N1", "Charlie Co")
        _make_contractor(db_session, "N2", "Alpha Co")
        _make_contractor(db_session, "N3", "Bravo Co")

        leads, _ = get_leads(db_session, sort_by="name", sort_order="asc")
        names = [l["name"] for l in leads]
        assert names == ["Alpha Co", "Bravo Co", "Charlie Co"]

    def test_filter_min_score(self, db_session):
        c1 = _make_contractor(db_session, "F1", "Low")
        c2 = _make_contractor(db_session, "F2", "High")
        _make_insight(db_session, c1.id, 30)
        _make_insight(db_session, c2.id, 70)

        leads, total = get_leads(db_session, min_score=50)
        assert total == 1
        assert leads[0]["name"] == "High"

    def test_filter_max_score(self, db_session):
        c1 = _make_contractor(db_session, "M1", "Low")
        c2 = _make_contractor(db_session, "M2", "High")
        _make_insight(db_session, c1.id, 30)
        _make_insight(db_session, c2.id, 70)

        leads, total = get_leads(db_session, max_score=50)
        assert total == 1
        assert leads[0]["name"] == "Low"

    def test_filter_min_and_max_score(self, db_session):
        c1 = _make_contractor(db_session, "R1", "Low")
        c2 = _make_contractor(db_session, "R2", "Mid")
        c3 = _make_contractor(db_session, "R3", "High")
        _make_insight(db_session, c1.id, 20)
        _make_insight(db_session, c2.id, 50)
        _make_insight(db_session, c3.id, 80)

        leads, total = get_leads(db_session, min_score=30, max_score=60)
        assert total == 1
        assert leads[0]["name"] == "Mid"

    def test_filter_certification(self, db_session):
        _make_contractor(db_session, "C1", "Elite Co", certification="Master Elite")
        _make_contractor(db_session, "C2", "Cert Co", certification="Certified")
        _make_contractor(db_session, "C3", "Also Elite", certification="Master Elite")

        leads, total = get_leads(db_session, certification="Master Elite")
        assert total == 2
        names = {l["name"] for l in leads}
        assert names == {"Elite Co", "Also Elite"}

    def test_search_by_name(self, db_session):
        _make_contractor(db_session, "X1", "ABC Roofing")
        _make_contractor(db_session, "X2", "XYZ Roofing")
        _make_contractor(db_session, "X3", "ABC Siding")

        leads, total = get_leads(db_session, search="ABC")
        assert total == 2
        names = {l["name"] for l in leads}
        assert names == {"ABC Roofing", "ABC Siding"}

    def test_search_case_insensitive(self, db_session):
        _make_contractor(db_session, "CI1", "ABC Roofing")

        leads, total = get_leads(db_session, search="abc")
        assert total == 1

    def test_contractor_without_insight_included(self, db_session):
        _make_contractor(db_session, "NI1", "No Insight Co")

        leads, total = get_leads(db_session)
        assert total == 1
        assert leads[0]["lead_score"] is None

    def test_null_scores_sorted_last_desc(self, db_session):
        c1 = _make_contractor(db_session, "NL1", "Scored Co")
        _make_contractor(db_session, "NL2", "Unscored Co")
        _make_insight(db_session, c1.id, 60)

        leads, _ = get_leads(db_session, sort_by="lead_score", sort_order="desc")
        assert leads[0]["name"] == "Scored Co"
        assert leads[1]["name"] == "Unscored Co"
        assert leads[1]["lead_score"] is None

    def test_lead_dict_keys(self, db_session):
        _make_contractor(db_session, "K1", "Key Test Co")

        leads, _ = get_leads(db_session)
        expected_keys = {
            "id", "name", "city", "state", "certification", "rating",
            "review_count", "lead_score", "phone", "website", "image_url",
            "distance_miles", "years_in_business",
        }
        assert set(leads[0].keys()) == expected_keys


# =========================================================================
# get_lead_detail
# =========================================================================


class TestGetLeadDetail:

    def test_returns_none_for_missing(self, db_session):
        result = get_lead_detail(db_session, 9999)
        assert result is None

    def test_basic_contractor_fields(self, db_session):
        c = _make_contractor(
            db_session, "D1", "Detail Co",
            city="Brooklyn", state="NY", phone="555-1234",
        )
        result = get_lead_detail(db_session, c.id)

        assert result["id"] == c.id
        assert result["name"] == "Detail Co"
        assert result["city"] == "Brooklyn"
        assert result["phone"] == "555-1234"

    def test_includes_insights(self, db_session):
        c = _make_contractor(db_session, "D2", "Insight Co")
        _make_insight(
            db_session, c.id, 75,
            talking_points='["Ask about storm season"]',
            why_now="Hailstorm last week.",
        )

        result = get_lead_detail(db_session, c.id)
        assert result["insights"] is not None
        assert result["insights"]["lead_score"] == 75
        assert result["insights"]["talking_points"] == ["Ask about storm season"]
        assert result["insights"]["why_now"] == "Hailstorm last week."

    def test_no_insights_returns_none(self, db_session):
        c = _make_contractor(db_session, "D3", "No Insight Co")

        result = get_lead_detail(db_session, c.id)
        assert result["insights"] is None

    def test_includes_contacts(self, db_session):
        c = _make_contractor(db_session, "D4", "Contact Co")
        _make_contact(db_session, c.id, "John Doe", "President")
        _make_contact(db_session, c.id, "Jane Doe", "VP Operations")

        result = get_lead_detail(db_session, c.id)
        assert len(result["contacts"]) == 2
        names = {ct["full_name"] for ct in result["contacts"]}
        assert names == {"John Doe", "Jane Doe"}

    def test_no_contacts_returns_empty_list(self, db_session):
        c = _make_contractor(db_session, "D5", "No Contact Co")

        result = get_lead_detail(db_session, c.id)
        assert result["contacts"] == []


# =========================================================================
# get_stats
# =========================================================================


class TestGetStats:

    def test_empty_database(self, db_session):
        result = get_stats(db_session)
        assert result["total_leads"] == 0
        assert result["avg_score"] is None
        assert result["high_priority_count"] == 0
        assert result["certification_breakdown"] == {}

    def test_total_leads(self, db_session):
        _make_contractor(db_session, "ST1", "Co A")
        _make_contractor(db_session, "ST2", "Co B")
        _make_contractor(db_session, "ST3", "Co C")

        result = get_stats(db_session)
        assert result["total_leads"] == 3

    def test_avg_score(self, db_session):
        c1 = _make_contractor(db_session, "AV1", "Co A")
        c2 = _make_contractor(db_session, "AV2", "Co B")
        _make_insight(db_session, c1.id, 60)
        _make_insight(db_session, c2.id, 40)

        result = get_stats(db_session)
        assert result["avg_score"] == 50.0

    def test_high_priority_count(self, db_session):
        c1 = _make_contractor(db_session, "HP1", "Low")
        c2 = _make_contractor(db_session, "HP2", "High")
        c3 = _make_contractor(db_session, "HP3", "Also High")
        _make_insight(db_session, c1.id, 40)
        _make_insight(db_session, c2.id, 70)
        _make_insight(db_session, c3.id, 85)

        result = get_stats(db_session)
        assert result["high_priority_count"] == 2

    def test_certification_breakdown(self, db_session):
        _make_contractor(db_session, "CB1", "ME1", certification="Master Elite")
        _make_contractor(db_session, "CB2", "ME2", certification="Master Elite")
        _make_contractor(db_session, "CB3", "C1", certification="Certified")
        _make_contractor(db_session, "CB4", "U1")  # no certification

        result = get_stats(db_session)
        assert result["certification_breakdown"]["Master Elite"] == 2
        assert result["certification_breakdown"]["Certified"] == 1
        assert result["certification_breakdown"]["Uncertified"] == 1

    def test_score_distribution_buckets(self, db_session):
        c1 = _make_contractor(db_session, "SD1", "Co1")
        c2 = _make_contractor(db_session, "SD2", "Co2")
        c3 = _make_contractor(db_session, "SD3", "Co3")
        c4 = _make_contractor(db_session, "SD4", "Co4")
        _make_insight(db_session, c1.id, 10)   # 0-25
        _make_insight(db_session, c2.id, 40)   # 26-50
        _make_insight(db_session, c3.id, 60)   # 51-75
        _make_insight(db_session, c4.id, 90)   # 76-100

        result = get_stats(db_session)
        assert result["score_distribution"]["0-25"] == 1
        assert result["score_distribution"]["26-50"] == 1
        assert result["score_distribution"]["51-75"] == 1
        assert result["score_distribution"]["76-100"] == 1
