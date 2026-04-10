"""Tests for ORM model methods — Contractor and LeadInsight."""

import json
from datetime import datetime, timezone

from app.db.models import Contractor, LeadInsight


class TestContractorToDict:

    def test_all_fields_present(self):
        c = Contractor(
            id=1,
            gaf_id="ABC123",
            name="Test Roofing",
            address="New York, NY, 10013",
            city="New York",
            state="NY",
            zip_code="10013",
            phone="(212) 555-0100",
            website="https://test.com",
            certification="Master Elite",
            certifications_raw='["Master Elite", "Certified"]',
            rating=4.5,
            review_count=100,
            services='["Steep Slope", "Solar"]',
            latitude=40.72,
            longitude=-74.01,
            distance_miles=1.5,
            years_in_business=20,
            about="Great company",
            profile_url="https://gaf.com/test",
            image_url="https://img.gaf.com/test.jpg",
            scraped_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        d = c.to_dict()

        assert d["id"] == 1
        assert d["gaf_id"] == "ABC123"
        assert d["name"] == "Test Roofing"
        assert d["certifications_raw"] == ["Master Elite", "Certified"]
        assert d["services"] == ["Steep Slope", "Solar"]
        assert d["scraped_at"] == "2025-01-01T00:00:00+00:00"

    def test_null_fields_handled(self):
        c = Contractor(
            id=2,
            gaf_id="NULL1",
            name="Minimal Co",
            certifications_raw=None,
            services=None,
            scraped_at=None,
        )
        d = c.to_dict()

        assert d["certifications_raw"] == []
        assert d["services"] == []
        assert d["scraped_at"] is None
        assert d["website"] is None
        assert d["rating"] is None


class TestGenerateGafId:

    def test_deterministic(self):
        id1 = Contractor.generate_gaf_id("Test Co", "123 Main St")
        id2 = Contractor.generate_gaf_id("Test Co", "123 Main St")
        assert id1 == id2

    def test_case_insensitive(self):
        id1 = Contractor.generate_gaf_id("Test Co", "123 Main St")
        id2 = Contractor.generate_gaf_id("TEST CO", "123 MAIN ST")
        assert id1 == id2

    def test_empty_address(self):
        id1 = Contractor.generate_gaf_id("Test Co", "")
        id2 = Contractor.generate_gaf_id("Test Co", None)
        # Both should produce the same hash (empty string normalization)
        assert isinstance(id1, str)
        assert len(id1) == 16
        assert id1 == id2


class TestServicesList:

    def test_parsing(self):
        c = Contractor(services='["Steep Slope", "Solar"]')
        assert c.services_list == ["Steep Slope", "Solar"]

    def test_empty(self):
        c = Contractor(services=None)
        assert c.services_list == []


class TestLeadInsightToDict:

    def test_all_fields_present(self):
        li = LeadInsight(
            id=1,
            contractor_id=10,
            research_summary="Great company with strong reviews.",
            citations='["https://bbb.org/test", "https://yelp.com/test"]',
            lead_score=85,
            score_breakdown='{"certification": 25, "reviews": 18}',
            talking_points='["GAF Master Elite certified"]',
            buying_signals='["Expanding to new territory"]',
            pain_points='["Slow material delivery"]',
            recommended_pitch="Focus on reliable supply chain.",
            why_now="Recent hail storm in area.",
            draft_email="Dear Test Co, ...",
            enriched_at=datetime(2025, 1, 15, tzinfo=timezone.utc),
        )
        d = li.to_dict()

        assert d["contractor_id"] == 10
        assert d["lead_score"] == 85
        assert d["citations"] == ["https://bbb.org/test", "https://yelp.com/test"]
        assert d["score_breakdown"] == {"certification": 25, "reviews": 18}
        assert d["talking_points"] == ["GAF Master Elite certified"]
        assert d["buying_signals"] == ["Expanding to new territory"]
        assert d["pain_points"] == ["Slow material delivery"]
        assert d["recommended_pitch"] == "Focus on reliable supply chain."
        assert d["why_now"] == "Recent hail storm in area."
        assert d["draft_email"] == "Dear Test Co, ..."
        assert d["enriched_at"] == "2025-01-15T00:00:00+00:00"

    def test_null_json_fields(self):
        li = LeadInsight(
            id=2,
            contractor_id=11,
            citations=None,
            score_breakdown=None,
            talking_points=None,
            buying_signals=None,
            pain_points=None,
            enriched_at=None,
        )
        d = li.to_dict()

        assert d["citations"] == []
        assert d["score_breakdown"] == {}
        assert d["talking_points"] == []
        assert d["enriched_at"] is None
