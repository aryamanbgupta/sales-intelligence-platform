"""FastAPI application — CORS, lifespan, router registration."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.leads import router as leads_router
from app.api.pipeline import router as pipeline_router
from app.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup (idempotent)."""
    init_db()
    yield


app = FastAPI(
    title="Roofing Lead Intelligence API",
    description="AI-powered B2B sales intelligence for roofing distributors",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(leads_router)
app.include_router(pipeline_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
