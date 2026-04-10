"""Tests for scraper._pick_top_certification — pure function."""

from app.pipeline.scraper import _pick_top_certification


class TestResidentialTiers:

    def test_presidents_club_highest(self):
        certs = [
            "GAF Certified\u2122 Contractor",
            "Master Elite\u00ae Weather Stopper\u00ae Roofing Contractor",
            "President's Club Award Winner",
        ]
        assert _pick_top_certification(certs) == "President's Club"

    def test_master_elite(self):
        certs = [
            "Master Elite\u00ae Weather Stopper\u00ae Roofing Contractor",
            "GAF Certified\u2122 Contractor",
        ]
        assert _pick_top_certification(certs) == "Master Elite"

    def test_certified_plus(self):
        certs = ["Certified Plus\u2122 Contractor"]
        assert _pick_top_certification(certs) == "Certified Plus"

    def test_certified_fallback(self):
        certs = ["GAF Certified\u2122 Contractor"]
        assert _pick_top_certification(certs) == "Certified"


class TestCommercialTiers:

    def test_chairmans_circle(self):
        certs = ["Chairman's Circle\u2122", "GoldElite\u2122 Contractor"]
        assert _pick_top_certification(certs) == "Chairman's Circle"

    def test_platinum_elite(self):
        certs = ["PlatinumElite\u2122 Contractor", "Certified"]
        assert _pick_top_certification(certs) == "PlatinumElite"

    def test_gold_elite(self):
        certs = ["GoldElite\u2122 Contractor"]
        assert _pick_top_certification(certs) == "GoldElite"

    def test_coatings_pro(self):
        certs = ["CoatingsPro Contractor"]
        assert _pick_top_certification(certs) == "CoatingsPro"


class TestEdgeCases:

    def test_empty_certs(self):
        assert _pick_top_certification([]) == "Uncertified"

    def test_unknown_cert_passthrough(self):
        certs = ["Some Unknown Certification"]
        assert _pick_top_certification(certs) == "Some Unknown Certification"

    def test_case_insensitive(self):
        certs = ["MASTER ELITE\u00ae WEATHER STOPPER\u00ae ROOFING CONTRACTOR"]
        assert _pick_top_certification(certs) == "Master Elite"

    def test_tier_priority_mixed(self):
        """President's Club should win even when mixed with commercial tiers."""
        certs = [
            "GoldElite\u2122 Contractor",
            "President's Club Award Winner",
            "Master Elite\u00ae Contractor",
        ]
        assert _pick_top_certification(certs) == "President's Club"
