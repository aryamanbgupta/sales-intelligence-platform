# Architecture: Roofing Lead Intelligence Platform

## System Overview

```
                         ┌─────────────────────────────────────────────┐
                         │              PIPELINE (offline)              │
                         │                                             │
  ┌──────────┐     ┌─────▼─────┐     ┌─────────────┐     ┌──────────┐ │
  │   GAF    │────▶│ Scraper   │────▶│ Perplexity  │────▶│ OpenAI   │ │
  │ Website  │     │(Playwright)│     │ (Research)  │     │(Scoring) │ │
  └──────────┘     └───────────┘     └─────────────┘     └────┬─────┘ │
                                                               │       │
                         └─────────────────────────────────────┼───────┘
                                                               │
                                                         ┌─────▼─────┐
                                                         │  SQLite   │
                                                         │ Database  │
                                                         └─────┬─────┘
                                                               │
                                                         ┌─────▼─────┐
                                                         │  FastAPI  │
                                                         │  REST API │
                                                         └─────┬─────┘
                                                               │
                                                         ┌─────▼─────┐
                                                         │  Next.js  │
                                                         │ Dashboard │
                                                         └───────────┘
```

The pipeline runs offline (triggered manually or via cron). It scrapes, researches, scores, and stores. The API and frontend read from the database. Clean separation — the dashboard never waits on scraping or LLM calls.

---

## Project Structure

```
backend/
  app/
    __init__.py
    main.py                 # FastAPI app, CORS, lifespan, router registration
    config.py               # Env vars, paths, constants
    db/
      __init__.py
      database.py           # Engine, session factory, Base
      models.py             # SQLAlchemy ORM models
    api/
      __init__.py
      leads.py              # GET /leads, GET /leads/{id}, GET /stats
      pipeline.py           # POST /pipeline/scrape, POST /pipeline/enrich
      schemas.py            # Pydantic request/response models
    pipeline/
      __init__.py
      scraper.py            # Playwright scraper for GAF
      enricher.py           # Two-stage: Perplexity research → OpenAI structuring
      scoring.py            # Lead scoring logic (inputs to OpenAI prompt)
    services/
      __init__.py
      lead_service.py       # Query helpers: filtering, sorting, pagination
  .env
  pyproject.toml

frontend/
  src/
    app/
      page.tsx              # Dashboard (lead table + stats)
      leads/[id]/page.tsx   # Lead detail view
      layout.tsx
      globals.css
    components/
      dashboard/
        StatsBar.tsx        # Summary stat cards
        LeadTable.tsx       # Sortable, paginated table
        FilterSidebar.tsx   # Score, certification, rating filters
        SearchBar.tsx
      leads/
        LeadDetailCard.tsx  # Header with score + contact info
        InsightsPanel.tsx   # AI-generated insights section
        DraftEmail.tsx      # Generated outreach email
        ScoreBreakdown.tsx  # Explainable score factors
    lib/
      types.ts              # TypeScript interfaces
      api.ts                # Fetch helpers for backend endpoints
      constants.ts
```

---

## Core Components

### 1. Scraping Pipeline

**File:** `backend/app/pipeline/scraper.py`

**What it does:** Launches a headless Chromium browser, navigates to GAF's contractor directory for ZIP 10013 with 25-mile radius, and extracts all contractor records.

**Why Playwright:** GAF's site is JavaScript-rendered and returns 403 to plain HTTP requests. Playwright with stealth settings renders the page like a real browser.

**Flow:**
1. Launch browser with stealth user-agent and viewport
2. Navigate to GAF search URL with ZIP code and distance params
3. Wait for contractor cards to render
4. Handle pagination — click "Load More" or navigate pages until all results are captured
5. For each contractor card, extract: name, address, phone, website, certification level, star rating, review count
6. Return list of contractor dicts

**Key decisions:**
- Scraper is a standalone function, not a class with state — easy to call from API endpoint or script
- Takes `zip_code` and `distance` as parameters — not hardcoded to 10013
- Returns raw dicts; database insertion is handled by the caller
- Random delays between page interactions to avoid detection

---

### 2. Database Layer

**Files:** `backend/app/db/database.py`, `backend/app/db/models.py`

**What it does:** Stores scraped contractor data and AI-generated enrichments in a relational schema.

**Schema:**

```
contractors
├── id                  INTEGER PRIMARY KEY
├── gaf_id              TEXT UNIQUE          -- dedupe key from GAF (name+address hash if no ID)
├── name                TEXT NOT NULL
├── address             TEXT
├── city                TEXT
├── state               TEXT
├── zip_code            TEXT
├── phone               TEXT
├── website             TEXT
├── certification       TEXT                 -- "Master Elite", "Certified", etc.
├── rating              REAL                 -- star rating (0-5)
├── review_count        INTEGER
├── services            TEXT                 -- JSON array of services offered
├── scraped_at          DATETIME
├── created_at          DATETIME
└── updated_at          DATETIME

lead_insights
├── id                  INTEGER PRIMARY KEY
├── contractor_id       INTEGER FK → contractors.id (UNIQUE)
├── lead_score          INTEGER              -- 0-100
├── score_breakdown     TEXT                 -- JSON: {certification: 25, reviews: 18, ...}
├── research_summary    TEXT                 -- Perplexity's synthesized research
├── citations           TEXT                 -- JSON array of source URLs from Perplexity
├── talking_points      TEXT                 -- JSON array of strings
├── buying_signals      TEXT                 -- JSON array of strings
├── pain_points         TEXT                 -- JSON array of strings
├── recommended_pitch   TEXT
├── why_now             TEXT                 -- time-sensitive signal (storms, growth, etc.)
├── draft_email         TEXT
├── enriched_at         DATETIME
├── created_at          DATETIME
└── updated_at          DATETIME
```

**Key decisions:**
- Two tables, not one. Raw scraped data is separated from AI-generated insights. This lets us re-enrich without re-scraping, and re-scrape without losing insights.
- `gaf_id` as a dedupe key enables upserts — safe to re-run the scraper.
- `contractor_id` is UNIQUE on `lead_insights` — one insight record per contractor.
- JSON fields stored as TEXT (SQLite-compatible). In Postgres these become native JSONB with indexing.
- SQLAlchemy ORM with `declarative_base` — swap SQLite for Postgres by changing one connection string.

---

### 3. AI Enrichment Pipeline (Two-Stage)

**File:** `backend/app/pipeline/enricher.py`

This is the core differentiator. Two LLMs, each doing what they're best at.

**Stage 1: Perplexity — Web Research**

For each contractor, send a research query to Perplexity (sonar-pro model via OpenAI-compatible API):

```
Research "{contractor_name}" roofing contractor located at {address}.
Find:
- Company overview and size
- Google reviews sentiment and themes
- Recent projects or notable work
- Any news mentions
- Recent storm or severe weather in their service area
- Signs of growth (hiring, new trucks, expanded territory)
- BBB rating or complaints
- Website quality and services highlighted
```

Perplexity returns:
- Synthesized research text (the enrichment gold)
- Citations array (URLs of sources it used)

**Stage 2: OpenAI — Structured Scoring & Insights**

Feed the raw GAF data + Perplexity research into OpenAI (gpt-4o-mini) with structured output / JSON mode:

```json
{
  "lead_score": 82,
  "score_breakdown": {
    "certification_tier": 25,
    "review_volume": 18,
    "rating_quality": 12,
    "business_signals": 15,
    "why_now_urgency": 12
  },
  "buying_signals": [
    "High volume of storm damage repair work",
    "Recently expanded service area"
  ],
  "pain_points": [
    "Current supplier has inconsistent delivery times (per Google reviews)",
    "Growing faster than material supply can keep up"
  ],
  "talking_points": [
    "Mention their Master Elite certification — they take quality seriously",
    "Ask about their storm restoration pipeline and material lead times"
  ],
  "recommended_pitch": "Position as reliable, high-volume supplier for storm season...",
  "why_now": "Major hailstorm hit their primary service area 3 weeks ago...",
  "draft_email": "Subject: Supporting your storm season demand..."
}
```

**Why two stages:**
- Perplexity excels at web search with grounded citations — you can't get this from OpenAI alone
- OpenAI excels at structured, schema-guaranteed JSON output — Perplexity's raw text would need fragile parsing
- The combination produces insights grounded in real web data, formatted for consistent programmatic use

**Processing:**
- Runs sequentially per contractor (Perplexity → OpenAI)
- Batch loop over all contractors that lack insights or have stale enrichments
- Delay between API calls for rate limiting
- Errors are caught per-contractor — one failure doesn't stop the batch

---

### 4. REST API

**Files:** `backend/app/api/leads.py`, `backend/app/api/pipeline.py`, `backend/app/api/schemas.py`

**Endpoints:**

```
GET  /api/leads
     ?page=1&per_page=20
     &sort_by=lead_score&sort_order=desc
     &min_score=50&max_score=100
     &certification=Master Elite
     &search=ABC Roofing
     → paginated lead list with basic info + score

GET  /api/leads/{id}
     → full contractor data + complete AI insights

GET  /api/stats
     → { total_leads, avg_score, high_priority_count,
         certification_breakdown, score_distribution }

POST /api/pipeline/scrape
     ?zip_code=10013&distance=25
     → triggers scraping, returns { contractors_found, new, updated }

POST /api/pipeline/enrich
     ?force=false
     → triggers enrichment for unenriched leads, returns { enriched_count }

GET  /api/pipeline/status
     → { last_scrape, last_enrichment, total_contractors, total_enriched }
```

**Key decisions:**
- Read endpoints are simple DB queries with filtering — fast, no LLM calls in the request path
- Pipeline endpoints trigger the actual work and return results synchronously (fine for ~30-50 leads)
- Pydantic schemas for all request/response models — type-safe, self-documenting
- FastAPI auto-generates OpenAPI docs at `/docs`

---

### 5. Frontend Dashboard

**Stack:** Next.js (App Router) + Tailwind CSS

**Dashboard Page (`/`):**
```
┌──────────────────────────────────────────────────────────────┐
│  RoofLeads AI                               [Run Pipeline]   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────────┐                │
│  │  47  │  │  12  │  │  23  │  │  4.2 avg │                │
│  │Total │  │ Hot  │  │ Warm │  │  Rating  │                │
│  └──────┘  └──────┘  └──────┘  └──────────┘                │
│                                                              │
│  ┌────────────┐  ┌───────────────────────────────────────┐  │
│  │  FILTERS   │  │  [Search contractors...]               │  │
│  │            │  │                                         │  │
│  │  Score     │  │  Score │ Name        │ Cert  │ Rating  │  │
│  │  ○ Hot 70+ │  │  ──────┼─────────────┼───────┼─────────│  │
│  │  ○ Warm    │  │   92   │ ABC Roofing │ ME    │ ★★★★★   │  │
│  │  ○ Cold    │  │   78   │ XYZ Roofing │ Cert  │ ★★★★    │  │
│  │            │  │   65   │ 123 Roofing │ Cert  │ ★★★★    │  │
│  │  Cert      │  │   41   │ Budget Roof │ —     │ ★★★     │  │
│  │  □ Master  │  │                                         │  │
│  │  □ Cert    │  │  [← Prev]    Page 1 of 3    [Next →]  │  │
│  └────────────┘  └───────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

**Lead Detail Page (`/leads/[id]`):**
```
┌──────────────────────────────────────────────────────────────┐
│  ← Back to Leads                                             │
│                                                              │
│  ABC Roofing Co.                          Score: 92 ■■■■■   │
│  Master Elite Certified                                      │
│  123 Main St, New York, NY 10013                             │
│  (555) 123-4567  •  abcroofing.com                          │
│                                                              │
│  ┌─ Why Now ─────────────────────────────────────────────┐  │
│  │ Hailstorm hit NE New Jersey 2 weeks ago — this        │  │
│  │ contractor's service area. Likely surge in demand.     │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─ Talking Points ──────────────────────────────────────┐  │
│  │ • Mention their Master Elite status — pride point      │  │
│  │ • Ask about storm season inventory planning            │  │
│  │ • Their Google reviews praise fast turnaround —        │  │
│  │   they need a supplier who can match that speed        │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─ Buying Signals ────────┐  ┌─ Pain Points ───────────┐  │
│  │ • High storm repair vol │  │ • Delivery complaints    │  │
│  │ • Expanding territory   │  │ • Premium shingle avail  │  │
│  └─────────────────────────┘  └──────────────────────────┘  │
│                                                              │
│  ┌─ Score Breakdown ────────────────────────────────────┐   │
│  │ Certification ■■■■■■■■░░  25/30                       │  │
│  │ Review Volume ■■■■■■░░░░  18/20                       │  │
│  │ Rating        ■■■■■░░░░░  12/15                       │  │
│  │ Biz Signals   ■■■■■■░░░░  15/20                       │  │
│  │ Why Now       ■■■■■■■■░░  12/15                       │  │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ Draft Outreach Email ────────────────────────[Copy]─┐  │
│  │ Subject: Supporting your storm season demand          │  │
│  │                                                        │  │
│  │ Hi [name],                                             │  │
│  │ I noticed ABC Roofing's stellar reputation ...         │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  Sources: contractor-website.com, google.com/reviews, ...   │
└──────────────────────────────────────────────────────────────┘
```

**Key decisions:**
- Server components for initial data fetch (fast page loads, SEO irrelevant but good practice)
- Client components only where interactivity is needed (filters, sort, search)
- Tailwind utility classes — no custom CSS file to manage
- Responsive layout — works on laptop screens (primary use case for sales reps)

---

## Data Flow Summary

```
1. SCRAPE
   Playwright → GAF website → raw contractor dicts
   → INSERT INTO contractors (upsert on gaf_id)

2. ENRICH (per contractor)
   contractors row → Perplexity prompt → research text + citations
   research + contractor data → OpenAI prompt → structured JSON
   → INSERT INTO lead_insights (upsert on contractor_id)

3. SERVE
   GET /api/leads → SELECT contractors JOIN lead_insights with filters
   GET /api/leads/{id} → single row join with full insights

4. DISPLAY
   Dashboard page → fetch /api/leads → render table
   Detail page → fetch /api/leads/{id} → render insights panels
```

---

## Add-On Features (time permitting)

### "Why Now" Signals
Already baked into the Perplexity research prompt. If Perplexity finds recent storm activity, growth signals, or time-sensitive news, it surfaces in the `why_now` field. Displayed prominently as a highlighted banner on the lead detail page. No extra work — just prompt engineering.

### Draft Outreach Email
Generated by OpenAI as part of the structured output. Personalized using contractor name, certification, and the identified pain points / buying signals. Displayed with a "Copy to Clipboard" button on the detail page.

### Lead Score Explainability
The `score_breakdown` JSON field contains individual factor scores. Rendered as labeled progress bars on the detail page. Sales reps can see exactly *why* a lead scored high or low.

### Perplexity Source Citations
Citations returned by Perplexity are stored in the `citations` JSON field. Displayed as clickable links at the bottom of the lead detail page. Builds trust — reps can verify the research.

### CSV Export
`GET /api/leads/export` returns all leads as a downloadable CSV. Sales reps can import into their CRM or share with their manager.

---

## Future Production Improvements

**Database:**
- Migrate to Postgres (change one connection string in config)
- Add Alembic for schema migrations
- Connection pooling via pgBouncer
- JSONB columns with GIN indexes for filtering on JSON fields

**Pipeline Scaling:**
- Move to Celery + Redis task queue for async pipeline execution
- Fan out scraping across ZIP codes in parallel workers
- Scheduled re-scraping (weekly cron) with change detection
- Cache Perplexity results for 7 days to control API costs

**Search:**
- Postgres full-text search (tsvector) for contractor name/address lookup
- pgvector column on lead_insights for semantic search over research summaries

**Auth & Multi-Tenant:**
- JWT-based authentication for sales reps
- Territory assignment — each rep sees leads in their region
- Row-level security in Postgres partitioned by territory/rep

**Observability:**
- Structured logging for every pipeline step and API call
- Track LLM token usage and latency per enrichment
- Pipeline health dashboard with alerting on failures
- Eval set for insight quality (periodic human review of AI outputs)

**Integrations:**
- CRM export (Salesforce, HubSpot) — push leads directly
- Sync rep notes and activity back to the platform
- Email integration — send drafted emails from the platform
