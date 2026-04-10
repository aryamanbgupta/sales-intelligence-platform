"""Shared test fixtures for the pipeline test suite."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Database fixtures — in-memory SQLite, no disk I/O
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def db_engine():
    """Create an in-memory SQLite engine with all tables."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    """Yield a DB session that rolls back after each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def patch_db(db_engine, monkeypatch):
    """Monkeypatch SessionLocal and init_db so lazy-import code uses the test DB.

    Functions like store_contractors and update_profile_details do:
        from app.db.database import SessionLocal, init_db
    inside the function body. This fixture patches those module-level objects
    so each call gets a session bound to the in-memory engine.
    """
    TestSession = sessionmaker(bind=db_engine)

    # Re-create tables fresh for each test
    Base.metadata.drop_all(bind=db_engine)
    Base.metadata.create_all(bind=db_engine)

    monkeypatch.setattr("app.db.database.SessionLocal", TestSession)
    monkeypatch.setattr("app.db.database.init_db", lambda: None)
    monkeypatch.setattr("app.db.database.engine", db_engine)

    return TestSession


# ---------------------------------------------------------------------------
# Sample data fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_coveo_result():
    """A single realistic Coveo API result object."""
    with open(FIXTURES_DIR / "coveo_response.json") as f:
        return json.load(f)


@pytest.fixture()
def sample_contractor_dict():
    """A realistic contractor dict as produced by _parse_contractor."""
    return {
        "gaf_id": "1004859",
        "name": "ABC Roofing & Siding Inc",
        "address": "New York, NY, 10013",
        "city": "New York",
        "state": "NY",
        "zip_code": "10013",
        "phone": "(212) 555-0199",
        "website": "",
        "certification": "Master Elite",
        "certifications_raw": json.dumps([
            "Master Elite\u00ae Weather Stopper\u00ae Roofing Contractor",
            "GAF Certified\u2122 Contractor",
        ]),
        "rating": 4.8,
        "review_count": 127,
        "services": json.dumps(["Steep Slope", "Solar", "Timberline HDZ\u00ae"]),
        "latitude": 40.7195,
        "longitude": -74.0089,
        "distance_miles": 1.23,
        "profile_url": "https://www.gaf.com/en-us/roofing-contractors/residential/usa/ny/new-york/abc-roofing-1004859",
        "image_url": "https://img.gaf.com/contractors/1004859.jpg",
    }
