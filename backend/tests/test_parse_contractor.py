"""Tests for scraper._parse_contractor — pure function, no DB or network."""

import json

from app.pipeline.scraper import _parse_contractor


class TestParseResidentialContractor:
    """Parse a full residential Coveo result."""

    def test_all_fields_extracted(self, sample_coveo_result):
        result = _parse_contractor(sample_coveo_result)

        assert result["gaf_id"] == "1004859"
        assert result["name"] == "ABC Roofing & Siding Inc"
        assert result["city"] == "New York"
        assert result["state"] == "NY"
        assert result["zip_code"] == "10013"
        assert result["phone"] == "(212) 555-0199"
        assert result["certification"] == "Master Elite"
        assert result["rating"] == 4.8
        assert result["review_count"] == 127
        assert result["latitude"] == 40.7195
        assert result["longitude"] == -74.0089
        assert "abc-roofing-1004859" in result["profile_url"]
        assert result["image_url"] == "https://img.gaf.com/contractors/1004859.jpg"

    def test_gaf_id_is_string(self, sample_coveo_result):
        result = _parse_contractor(sample_coveo_result)
        assert isinstance(result["gaf_id"], str)

    def test_website_always_empty(self, sample_coveo_result):
        result = _parse_contractor(sample_coveo_result)
        assert result["website"] == ""

    def test_certifications_raw_is_json(self, sample_coveo_result):
        result = _parse_contractor(sample_coveo_result)
        parsed = json.loads(result["certifications_raw"])
        assert isinstance(parsed, list)
        assert len(parsed) == 2

    def test_distance_rounding(self, sample_coveo_result):
        result = _parse_contractor(sample_coveo_result)
        assert result["distance_miles"] == 1.23

    def test_services_merged(self, sample_coveo_result):
        result = _parse_contractor(sample_coveo_result)
        services = json.loads(result["services"])
        assert "Steep Slope" in services
        assert "Solar" in services
        assert "Timberline HDZ\u00ae" in services


class TestParseCommercialContractor:
    """Parse a commercial Coveo result."""

    def test_commercial_cert_fields_used(self):
        result_data = {
            "title": "Commercial Roofing Co",
            "raw": {
                "gaf_contractor_id": 9999,
                "gaf_navigation_title": "Commercial Roofing Co",
                "gaf_contractor_type": "Commercial",
                "gaf_f_city": "Brooklyn",
                "gaf_f_state_code": "NY",
                "gaf_postal_code": "11201",
                "gaf_phone": "(718) 555-0100",
                "gaf_rating": 4.5,
                "gaf_number_of_reviews": 50,
                "gaf_latitude": 40.69,
                "gaf_longitude": -73.99,
                "distanceinmiles": 5.0,
                "gaf_f_contractor_certifications_and_awards_commercial": [
                    "Chairman's Circle\u2122"
                ],
                "gaf_f_contractor_specialties_commercial": ["Low Slope"],
                "gaf_f_contractor_technologies_commercial": [],
                "gaf_featured_image_src": "",
                "uri": "https://www.gaf.com/en-us/roofing-contractors/commercial/usa/ny/brooklyn/commercial-roofing-9999",
            },
        }
        result = _parse_contractor(result_data)
        assert result["certification"] == "Chairman's Circle"
        services = json.loads(result["services"])
        assert "Low Slope" in services


class TestParseEdgeCases:
    """Edge cases and missing fields."""

    def test_missing_rating(self):
        result = _parse_contractor({
            "title": "No Rating Co",
            "raw": {"gaf_contractor_id": 1, "gaf_navigation_title": "No Rating Co"},
        })
        assert result["rating"] == 0.0

    def test_missing_reviews(self):
        result = _parse_contractor({
            "title": "No Reviews Co",
            "raw": {"gaf_contractor_id": 2, "gaf_navigation_title": "No Reviews Co"},
        })
        assert result["review_count"] == 0

    def test_address_formatting(self):
        result = _parse_contractor({
            "raw": {
                "gaf_contractor_id": 3,
                "gaf_navigation_title": "Test",
                "gaf_f_city": "Hoboken",
                "gaf_f_state_code": "NJ",
                "gaf_postal_code": "07030",
            },
        })
        assert result["address"] == "Hoboken, NJ, 07030"

    def test_address_partial_fields(self):
        result = _parse_contractor({
            "raw": {
                "gaf_contractor_id": 4,
                "gaf_navigation_title": "Test",
                "gaf_f_city": "Hoboken",
            },
        })
        assert result["address"] == "Hoboken"
        assert result["state"] == ""
        assert result["zip_code"] == ""

    def test_empty_services(self):
        result = _parse_contractor({
            "raw": {"gaf_contractor_id": 5, "gaf_navigation_title": "Test"},
        })
        assert json.loads(result["services"]) == []
