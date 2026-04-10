"""Tests for prompts.build_research_prompt — pure function."""

from app.pipeline.prompts import build_research_prompt


def _make_contractor(**overrides):
    """Build a minimal contractor dict with optional overrides."""
    base = {
        "name": "Test Roofing LLC",
        "city": "New York",
        "state": "NY",
        "zip_code": "10013",
        "phone": "(212) 555-0100",
        "website": "",
        "certification": "Master Elite",
        "certifications_raw": [],
        "rating": 4.5,
        "review_count": 80,
        "services": ["Steep Slope"],
        "years_in_business": 15,
        "about": "We do great roofing.",
        "profile_url": "https://www.gaf.com/contractor/test",
    }
    base.update(overrides)
    return base


class TestPromptContent:

    def test_contains_contractor_name(self):
        prompt = build_research_prompt(_make_contractor(name="Alpha Roofing"))
        assert "Alpha Roofing" in prompt

    def test_contains_location(self):
        prompt = build_research_prompt(_make_contractor(city="Brooklyn", state="NY", zip_code="11201"))
        assert "Brooklyn" in prompt
        assert "NY" in prompt
        assert "11201" in prompt

    def test_includes_website_analysis(self):
        prompt = build_research_prompt(_make_contractor(website="https://alpharoofing.com"))
        assert "Website Analysis" in prompt
        assert "https://alpharoofing.com" in prompt

    def test_no_website_alternative(self):
        prompt = build_research_prompt(_make_contractor(website=""))
        assert "Web Presence" in prompt
        assert "Website Analysis" not in prompt

    def test_skips_years_when_known(self):
        prompt = build_research_prompt(_make_contractor(years_in_business=20))
        assert "How long have they been in business" not in prompt

    def test_asks_years_when_unknown(self):
        prompt = build_research_prompt(_make_contractor(years_in_business=None))
        assert "How long have they been in business" in prompt

    def test_truncates_long_about(self):
        long_about = "A" * 600
        prompt = build_research_prompt(_make_contractor(about=long_about))
        assert "..." in prompt
        # The full 600-char string should NOT appear
        assert long_about not in prompt

    def test_minimal_contractor(self):
        prompt = build_research_prompt({"name": "Bare Minimum Co"})
        assert "Bare Minimum Co" in prompt
        # Should not crash with missing fields
        assert "unknown location" in prompt
