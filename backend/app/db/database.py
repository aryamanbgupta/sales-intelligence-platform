from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL, DB_PATH

# Ensure the data directory exists
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},  # SQLite-specific
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()


def init_db():
    """Create all tables. Safe to call multiple times — no-ops on existing tables."""
    Base.metadata.create_all(bind=engine)


def get_session():
    """Yield a DB session, auto-closing on exit."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
