"""Tests for enricher functions — uses patch_db fixture for in-memory DB."""

import json
from datetime import datetime, timezone

from app.db.models import Contractor, LeadInsight
from app.pipeline.enricher import (
    get_unenriched_contractors,
    ingest_contractors,
    persist_research_result,
)
from app.pipeline.research import ResearchResult


def _insert_contractor(session, gaf_id="C001", name="Test Co"):
    """Helper to insert a contractor directly."""
    c = Contractor(gaf_id=gaf_id, name=name, address="Test City, TS, 00000")
    session.add(c)
    session.commit()
    session.refresh(c)
    return c


class TestGetUnenrichedContractors:

    def test_no_insights_row(self, patch_db):
        session = patch_db()
        _insert_contractor(session, "C001", "No Insights Co")

        result = get_unenriched_contractors(session)
        assert len(result) == 1
        assert result[0].gaf_id == "C001"
        session.close()

    def test_empty_research_summary(self, patch_db):
        session = patch_db()
        c = _insert_contractor(session, "C002", "Empty Research Co")
        li = LeadInsight(contractor_id=c.id, research_summary="")
        session.add(li)
        session.commit()

        result = get_unenriched_contractors(session)
        assert len(result) == 1
        session.close()

    def test_excludes_enriched(self, patch_db):
        session = patch_db()
        c = _insert_contractor(session, "C003", "Enriched Co")
        li = LeadInsight(
            contractor_id=c.id,
            research_summary="Full research text here.",
            citations='["https://example.com"]',
        )
        session.add(li)
        session.commit()

        result = get_unenriched_contractors(session)
        assert len(result) == 0
        session.close()

    def test_with_limit(self, patch_db):
        session = patch_db()
        _insert_contractor(session, "C004", "Co A")
        _insert_contractor(session, "C005", "Co B")
        _insert_contractor(session, "C006", "Co C")

        result = get_unenriched_contractors(session, limit=2)
        assert len(result) == 2
        session.close()


class TestPersistResearchResult:

    def test_creates_insight(self, patch_db):
        session = patch_db()
        c = _insert_contractor(session, "C010", "New Insight Co")

        result = ResearchResult(
            contractor_id=c.id,
            contractor_name="New Insight Co",
            research_summary="Found great reviews and BBB A+ rating.",
            citations=["https://bbb.org/test"],
            success=True,
        )
        persist_research_result(session, result)

        li = session.query(LeadInsight).filter_by(contractor_id=c.id).first()
        assert li is not None
        assert "BBB A+" in li.research_summary
        assert json.loads(li.citations) == ["https://bbb.org/test"]
        session.close()

    def test_updates_existing(self, patch_db):
        session = patch_db()
        c = _insert_contractor(session, "C011", "Update Co")
        li = LeadInsight(
            contractor_id=c.id,
            research_summary="Old research.",
            citations="[]",
        )
        session.add(li)
        session.commit()

        result = ResearchResult(
            contractor_id=c.id,
            contractor_name="Update Co",
            research_summary="New updated research.",
            citations=["https://new-source.com"],
            success=True,
        )
        persist_research_result(session, result)

        li = session.query(LeadInsight).filter_by(contractor_id=c.id).first()
        assert li.research_summary == "New updated research."
        session.close()

    def test_skips_failed_result(self, patch_db):
        session = patch_db()
        c = _insert_contractor(session, "C012", "Failed Co")

        result = ResearchResult(
            contractor_id=c.id,
            contractor_name="Failed Co",
            research_summary="",
            success=False,
            error="Rate limited",
        )
        persist_research_result(session, result)

        li = session.query(LeadInsight).filter_by(contractor_id=c.id).first()
        assert li is None
        session.close()


class TestIngestContractors:

    def test_ingest_new(self, patch_db):
        results = ingest_contractors([
            {"name": "Ingested Co", "address": "Test City, TS"},
        ])
        assert len(results) == 1
        assert results[0].name == "Ingested Co"
        assert results[0].id is not None  # ID populated after commit

    def test_ingest_updates_existing(self, patch_db):
        ingest_contractors([
            {"name": "Dup Co", "address": "Addr1", "gaf_id": "DUP1", "phone": "111"},
        ])
        ingest_contractors([
            {"name": "Dup Co", "address": "Addr1", "gaf_id": "DUP1", "phone": "222"},
        ])

        session = patch_db()
        c = session.query(Contractor).filter_by(gaf_id="DUP1").first()
        assert c.phone == "222"
        session.close()

    def test_ingest_skips_no_name(self, patch_db):
        results = ingest_contractors([
            {"name": "", "address": "Addr"},
            {"address": "Addr"},  # no name key
        ])
        assert len(results) == 0
