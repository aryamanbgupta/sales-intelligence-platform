"""Tests for scraper.store_contractors and scraper.update_profile_details.

These functions do lazy imports of SessionLocal/init_db, so we use the
patch_db fixture to redirect them to the in-memory test database.
"""

import json

from app.db.models import Contractor
from app.pipeline.scraper import store_contractors, update_profile_details


class TestStoreContractors:

    def test_store_new_contractors(self, patch_db, sample_contractor_dict):
        result = store_contractors([sample_contractor_dict])

        assert result["new"] == 1
        assert result["updated"] == 0
        assert result["total"] == 1

        # Verify in DB
        session = patch_db()
        c = session.query(Contractor).filter_by(gaf_id="1004859").first()
        assert c is not None
        assert c.name == "ABC Roofing & Siding Inc"
        session.close()

    def test_store_duplicate_gaf_id(self, patch_db, sample_contractor_dict):
        store_contractors([sample_contractor_dict])
        result = store_contractors([sample_contractor_dict])

        assert result["new"] == 0
        assert result["updated"] == 1
        assert result["total"] == 1

    def test_store_updates_mutable_fields(self, patch_db, sample_contractor_dict):
        store_contractors([sample_contractor_dict])

        updated = {**sample_contractor_dict, "phone": "(212) 999-0000", "rating": 4.9}
        store_contractors([updated])

        session = patch_db()
        c = session.query(Contractor).filter_by(gaf_id="1004859").first()
        assert c.phone == "(212) 999-0000"
        assert c.rating == 4.9
        session.close()

    def test_store_empty_list(self, patch_db):
        result = store_contractors([])
        assert result == {"new": 0, "updated": 0, "total": 0}

    def test_store_multiple_contractors(self, patch_db, sample_contractor_dict):
        second = {**sample_contractor_dict, "gaf_id": "9999999", "name": "Other Co"}
        result = store_contractors([sample_contractor_dict, second])

        assert result["new"] == 2
        assert result["total"] == 2


class TestUpdateProfileDetails:

    def test_update_website(self, patch_db, sample_contractor_dict):
        store_contractors([sample_contractor_dict])

        count = update_profile_details([
            {"gaf_id": "1004859", "website": "https://abcroofing.com", "years_in_business": None, "about": ""},
        ])
        assert count == 1

        session = patch_db()
        c = session.query(Contractor).filter_by(gaf_id="1004859").first()
        assert c.website == "https://abcroofing.com"
        session.close()

    def test_update_years(self, patch_db, sample_contractor_dict):
        store_contractors([sample_contractor_dict])

        update_profile_details([
            {"gaf_id": "1004859", "website": "", "years_in_business": 25, "about": ""},
        ])

        session = patch_db()
        c = session.query(Contractor).filter_by(gaf_id="1004859").first()
        assert c.years_in_business == 25
        session.close()

    def test_update_about(self, patch_db, sample_contractor_dict):
        store_contractors([sample_contractor_dict])

        update_profile_details([
            {"gaf_id": "1004859", "website": "", "years_in_business": None, "about": "We are the best."},
        ])

        session = patch_db()
        c = session.query(Contractor).filter_by(gaf_id="1004859").first()
        assert c.about == "We are the best."
        session.close()

    def test_update_skips_empty_values(self, patch_db, sample_contractor_dict):
        """Empty strings should not overwrite existing data."""
        store_contractors([{**sample_contractor_dict, "website": "https://existing.com"}])

        # Pass empty website — should NOT overwrite
        update_profile_details([
            {"gaf_id": "1004859", "website": "", "years_in_business": None, "about": ""},
        ])

        session = patch_db()
        c = session.query(Contractor).filter_by(gaf_id="1004859").first()
        assert c.website == "https://existing.com"
        session.close()

    def test_update_missing_gaf_id(self, patch_db):
        """Should skip gracefully when gaf_id doesn't exist in DB."""
        count = update_profile_details([
            {"gaf_id": "NONEXISTENT", "website": "https://ghost.com", "years_in_business": None, "about": ""},
        ])
        assert count == 0
