# Architecture: Roofing Lead Intelligence Platform

## System Overview

```
                    ┌──────────────────────────────────────────────────────────┐
                    │                    PIPELINE (offline)                     │
                    │                                                          │
  ┌──────────┐     │  ┌───────────┐     ┌───────────┐     ┌───────────────┐  │
  │   GAF    │────▶│  │ Scraper   │────▶│ Perplexity│────▶│ OpenAI        │  │
  │ Website  │     │  │(Playwright)│     │ (Research) │     │ (Scoring +    │  │
  └──────────┘     │  └───────────┘     └───────────┘     │  Contacts)    │  │
                    │       │                  │            └───────┬───────┘  │
                    │       │ contractors      │ research_summary   │ lead_score│
                    │       │ table            │ + citations        │ insights  │
                    │       ▼                  ▼                    │ contacts  │
                    │  ┌──────────────────────────────────────────┐ │          │
                    │  │            SQLite Database                │◀┘          │
                    │  │  contractors │ lead_insights │ contacts   │            │
                    │  └──────────────────────┬───────────────────┘            │
                    └─────────────────────────┼────────────────────────────────┘
                                              │
                                        ┌─────▼─────┐
                                        │  FastAPI  │
                                        │  REST API │
                                        └─────┬─────┘
                                              │
                                        ┌─────▼─────┐
                                        │  Next.js  │
                                        │ Dashboard │
                                        │           │
                                        │ ┌───────┐ │
                                        │ │ Chat  │ │◀── OpenAI function-calling
                                        │ │ Agent │ │    agentic loop (tools query DB)
                                        │ └───────┘ │
                                        └───────────┘
```

The pipeline runs offline (triggered manually or via cron). It scrapes, researches, scores, extracts contacts, and stores. Each stage is independently runnable — re-score without re-researching, re-research without re-scraping. The API and frontend read from the database. Clean separation — the dashboard never waits on scraping or LLM calls.

---

## Project Structure

```
backend/
  main.py                   # Uvicorn launcher (python main.py → starts API server)
  app/
    __init__.py
    main.py                 # FastAPI app, CORS, lifespan, router registration
    config.py               # Env vars, paths, constants
    db/
      __init__.py
      database.py           # Engine, session factory, Base, get_session dependency
      models.py             # SQLAlchemy ORM models (Contractor, LeadInsight, Contact)
    api/
      __init__.py
      leads.py              # GET /api/leads, GET /api/leads/{id}, GET /api/stats
      pipeline.py           # POST /api/pipeline/scrape, POST /api/pipeline/enrich, GET /api/pipeline/status
      chat.py               # POST /api/chat — agentic chat endpoint (OpenAI function-calling loop)
      schemas.py            # Pydantic request/response models (11 schemas)
    pipeline/
      __init__.py
      scraper.py            # Playwright scraper for GAF (Coveo API interception)
      research.py           # Stage 1: Perplexity web research engine (async, batch)
      scoring.py            # Stage 2: Hybrid deterministic + LLM scoring engine
      contact_enrichment.py # Stage 3: Decision-maker contact extraction
      enricher.py           # Orchestrator: wires research → scoring → contacts → DB
      prompts.py            # All prompt templates (Perplexity + OpenAI scoring)
      cli.py                # CLI: ingest, research, score, contacts, status
    services/
      __init__.py
      lead_service.py       # Query helpers: filtering, sorting, pagination
      chat_service.py       # Agentic chat: system prompt, tool definitions, OpenAI loop
  tests/
    conftest.py             # Shared fixtures: in-memory SQLite, patch_db, sample data
    test_api.py             # FastAPI endpoint tests (TestClient + StaticPool)
    test_lead_service.py    # Service layer tests (filtering, sorting, stats)
    test_enricher.py        # Enricher orchestration tests
    test_models.py          # ORM model method tests
    test_research.py        # Perplexity research engine tests
    test_parse_contractor.py # Coveo response parsing tests
    test_store_contractors.py # DB upsert tests
    test_certifications.py  # Certification tier tests
    test_citations.py       # Citation extraction tests
    test_prompts.py         # Prompt template tests
  data/
    leads.db                # SQLite database (78 enriched contractors)
    sample_contractors.json # Sample data for testing without scraper
  .env
  pyproject.toml

frontend/
  src/
    app/
      layout.tsx              # App shell — IBM Plex fonts, floating pill nav, dark footer
      globals.css             # Tailwind imports, CSS vars (#FEFFF7 bg), dot grid utility
      page.tsx                # Dashboard — client component with URL-synced filters
      leads/[id]/page.tsx     # Lead detail — server component, single fetch
    components/
      dashboard/
        StatsBar.tsx          # 4 metric cells in sharp-bordered grid (Instalily "Why Now" style)
        LeadTable.tsx         # Sortable table with monospace headers, pill pagination
        FilterBar.tsx         # Inline score tier + certification pill filters
        LeadRow.tsx           # Single row: score pill, name + cert badge inline, est. volume, distance
      lead-detail/
        LeadHeader.tsx        # Name (4xl light), score pill, cert badge, meta, contacts
        ContactCard.tsx       # Decision-maker card with email/call/LinkedIn action buttons
        WhyNowBanner.tsx      # Left orange border accent, editorial layout
        TalkingPoints.tsx     # Numbered list (01, 02, 03 monospace)
        ScoreBreakdown.tsx    # 5 labeled progress bars with monospace labels
        InsightsGrid.tsx      # Buying signals (green) + pain points (red) two-column
        DraftEmail.tsx        # Dark #171717 card with semi-transparent inner card
        ResearchSummary.tsx   # Collapsible text + citation source pills
      chat/
        ChatPanel.tsx         # Floating agentic chat panel — toggle, message history, markdown rendering
      ui/
        ScorePill.tsx         # Color-coded full-pill badge (Hot/Warm/Cold)
        CertBadge.tsx         # Dark-fill monospace pill (President's Club, Master Elite)
        StarRating.tsx        # Star display with monospace rating number
        ProgressBar.tsx       # Horizontal bar with monospace label + value
        CopyButton.tsx        # Outlined pill button with checkmark animation
    lib/
      types.ts                # TypeScript interfaces matching all 11 Pydantic schemas
      api.ts                  # Fetch helpers: getLeads(), getLead(), getStats(), sendChatMessage()
      constants.ts            # Score tiers (60/40), cert config, breakdown labels
      utils.ts                # getScoreTier(), formatPhone(), formatDistance(), cleanUrl(), getVolumeTier()
```

---

## Core Components

### 1. Scraping Pipeline

**File:** `backend/app/pipeline/scraper.py`

**What it does:** Launches a headless Chromium browser, navigates to GAF's contractor directory for ZIP 10013 with 25-mile radius, and extracts all contractor records. Under the hood, GAF uses Coveo search-as-a-service — we intercept the Coveo API calls to get clean, structured JSON instead of parsing DOM elements.

**Why Playwright:** GAF's site is JavaScript-rendered and protected by Akamai bot detection. Playwright with stealth settings renders the page like a real browser and lets us capture the Coveo API token.

**Flow:**
1. Launch browser with stealth user-agent, viewport, and anti-detection JS
2. Navigate to GAF search URL with ZIP code and distance params
3. Intercept the Coveo REST API response (contractor data as JSON)
4. Extract the Bearer token and query context from the first request
5. Make additional paginated API calls directly to Coveo to fetch all results
6. Parse each result into a flat contractor dict
7. Optionally scrape individual profile pages for website URL, years in business, and about text

**Key decisions:**
- Scraper is a standalone async function — easy to call from API endpoint or script
- Takes `zip_code` and `distance` as parameters — not hardcoded to 10013
- Returns raw dicts; database insertion is handled by the caller
- Coveo API interception is more reliable than DOM scraping and returns structured JSON
- Profile page scraping runs with configurable concurrency for website/about data

---

### 2. Database Layer

**Files:** `backend/app/db/database.py`, `backend/app/db/models.py`

**What it does:** Stores scraped contractor data and AI-generated enrichments in a relational schema.

**Schema:**

```
contractors
├── id                  INTEGER PRIMARY KEY
├── gaf_id              TEXT UNIQUE          -- dedupe key (GAF contractor ID or name+address hash)
├── name                TEXT NOT NULL
├── address             TEXT
├── city                TEXT
├── state               TEXT
├── zip_code            TEXT
├── phone               TEXT
├── website             TEXT                 -- from profile page scraping
├── certification       TEXT                 -- "President's Club", "Master Elite", "Certified", etc.
├── certifications_raw  TEXT                 -- JSON array of all GAF certifications
├── rating              REAL                 -- star rating (0-5)
├── review_count        INTEGER
├── services            TEXT                 -- JSON array of services offered
├── latitude            REAL
├── longitude           REAL
├── distance_miles      REAL                 -- distance from search ZIP code
├── years_in_business   INTEGER              -- from profile page scraping
├── about               TEXT                 -- company description from profile page
├── profile_url         TEXT                 -- GAF profile page URL
├── image_url           TEXT                 -- profile image URL
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

```
contacts
├── id                  INTEGER PRIMARY KEY
├── contractor_id       INTEGER FK → contractors.id (indexed)
├── full_name           TEXT                 -- "Frank Notarnicola"
├── title               TEXT                 -- "Owner", "President", etc.
├── email               TEXT                 -- direct email
├── phone               TEXT                 -- direct phone
├── linkedin_url        TEXT                 -- LinkedIn profile URL
├── source              TEXT NOT NULL         -- "perplexity_research", "hunter_io", etc.
├── confidence          TEXT                 -- "high", "medium", "low"
├── created_at          DATETIME
└── updated_at          DATETIME
```

**Key decisions:**
- Three tables: raw scraped data, AI-generated insights, and decision-maker contacts. This lets us re-enrich without re-scraping, re-score without re-researching, and re-extract contacts independently.
- `gaf_id` as a dedupe key enables upserts — safe to re-run the scraper.
- `contractor_id` is UNIQUE on `lead_insights` — one insight record per contractor.
- Multiple contacts per contractor are allowed (owner + ops manager, etc.)
- JSON fields stored as TEXT (SQLite-compatible). In Postgres these become native JSONB with indexing.
- SQLAlchemy ORM with `declarative_base` — swap SQLite for Postgres by changing one connection string.

---

### 3. AI Enrichment Pipeline (Three-Stage)

**Files:** `backend/app/pipeline/enricher.py` (orchestrator), `backend/app/pipeline/research.py` (Stage 1), `backend/app/pipeline/scoring.py` (Stage 2), `backend/app/pipeline/contact_enrichment.py` (Stage 3)

This is the core differentiator. Multiple LLMs, each doing what they're best at.

**Stage 1: Perplexity — Web Research** (`research.py`)

For each contractor, send a research query to Perplexity (sonar-pro model via OpenAI-compatible API):

```
Research "{contractor_name}" roofing contractor located at {address}.
Find:
- Decision makers & key contacts (names, titles, emails, LinkedIn)
- Company overview and size
- Google reviews sentiment and themes
- Recent projects or notable work
- Any news mentions
- Recent storm or severe weather in their service area
- Signs of growth (hiring, new trucks, expanded territory)
- BBB rating or complaints
- Supplier & material intelligence
- Competitive positioning
```

Perplexity returns:
- Synthesized research text (the enrichment gold)
- Citations array (URLs of sources it used)

**Stage 2: OpenAI — Hybrid Scoring & Insights** (`scoring.py`)

Uses a **hybrid deterministic + LLM approach** — the key architectural decision.

*Deterministic scoring* (Python, 60/100 points max):
- `certification_tier` (0-30): President's Club=30, Master Elite=25, Certified Plus=20, Certified=15, Uncertified=5
- `review_volume` (0-20): log-scaled from review_count (500+ reviews → 18-20 pts)
- `rating_quality` (0-10): star rating weighted by review confidence (full weight at 50+ reviews)

*LLM scoring* (gpt-4o-mini, 40/100 points max):
- `business_signals` (0-20): growth, hiring, expansion — extracted from Perplexity research text
- `why_now_urgency` (0-20): storms, seasonal demand, supplier problems — extracted from research text

`lead_score = deterministic_subtotal + business_signals + why_now_urgency`

*Why hybrid instead of fully LLM or fully deterministic:*
- **Deterministic where objectively knowable**: Master Elite > Certified is a lookup table, not a judgment call. Computing it in Python guarantees reproducibility (same input = same score), costs nothing, and is auditable.
- **LLM where reading comprehension is required**: "They're hiring 3 new crews" and "hailstorm hit their area last week" are latent signals buried in 3000 chars of unstructured research text. Only an LLM can extract and score these.
- **Graceful degradation**: If OpenAI is down, the deterministic subtotal (60/100) still provides a usable ranking.
- **Cost**: ~$0.001 per contractor on gpt-4o-mini. All 76 contractors scored for ~$0.05 total.

The LLM also generates all qualitative outputs (no deterministic alternative exists):

```json
{
  "lead_score": 67,
  "score_breakdown": {
    "certification_tier": 30,
    "review_volume": 18,
    "rating_quality": 9,
    "business_signals": 10,
    "why_now_urgency": 0
  },
  "talking_points": [
    "Mention their 449 Google reviews — they clearly value reputation",
    "Ask about their storm restoration pipeline and material lead times"
  ],
  "buying_signals": [
    "High volume of storm damage repair work",
    "Recently expanded service area"
  ],
  "pain_points": [
    "Current supplier has inconsistent delivery times (per Google reviews)",
    "Growing faster than material supply can keep up"
  ],
  "recommended_pitch": "Position as reliable, high-volume supplier for storm season...",
  "why_now": "Major hailstorm hit their primary service area 3 weeks ago...",
  "draft_email": "Subject: Supporting your storm season demand..."
}
```

Key implementation details:
- Pre-computed deterministic scores are passed to the LLM as "locked — do not modify" context
- LLM scores are clamped to valid ranges (0-20) and arithmetic is enforced in Python (don't trust the LLM's addition)
- Uses `response_format={"type": "json_object"}` for guaranteed parseable output
- Retry logic with exponential backoff on transient failures (mirrors research.py pattern)

**Stage 3: OpenAI — Contact Extraction** (`contact_enrichment.py`)

Extracts decision-maker contact information from research text and persists to the `contacts` table. Uses a provider-based architecture:

- **PerplexityExtractor** (implemented): Parses the Perplexity research text using a lightweight OpenAI call to extract structured contact data (names, titles, emails, LinkedIn URLs). Assigns confidence levels based on source authority (state records = high, reviews = medium).
- **Hunter.io** (stub, ready to plug in): Domain-based email lookup. Requires API key.
- Custom providers can be added via `PROVIDER_REGISTRY`.

Contacts are deduplicated by name+contractor_id on persistence — re-running enriches existing contacts with new info rather than creating duplicates.

**Why three stages:**
- Perplexity excels at web search with grounded citations — you can't get this from OpenAI alone
- OpenAI excels at structured, schema-guaranteed JSON output — Perplexity's raw text would need fragile parsing
- The combination produces insights grounded in real web data, formatted for consistent programmatic use
- Separating scoring from contact extraction keeps prompts focused and outputs reliable

**Processing:**
- Stages run independently: research → scoring → contacts (each only processes contractors ready for that stage)
- Async batch processing with configurable concurrency (semaphore-controlled)
- Rate limiting between API calls
- Errors are caught per-contractor — one failure doesn't stop the batch
- CLI commands: `research`, `score`, `contacts` — each with `--force`, `--limit`, `--concurrency` flags

---

### 4. REST API

**Files:** `backend/app/main.py` (app), `backend/app/api/leads.py`, `backend/app/api/pipeline.py`, `backend/app/api/schemas.py`, `backend/app/services/lead_service.py`

**Starting the server:**

```bash
cd backend && uv run python main.py
# → Uvicorn running on http://0.0.0.0:8000
# → OpenAPI docs at http://localhost:8000/docs
```

**Endpoints:**

```
GET  /api/leads
     ?page=1&per_page=20
     &sort_by=lead_score&sort_order=desc
     &min_score=50&max_score=100
     &certification=Master Elite
     &search=ABC Roofing
     → { data: [LeadListItem], pagination: {page, per_page, total_items, total_pages} }

GET  /api/leads/{id}
     → { ...contractor fields, insights: LeadInsightOut | null, contacts: [ContactOut] }

GET  /api/stats
     → { total_leads, avg_score, high_priority_count,
         certification_breakdown, score_distribution }

POST /api/pipeline/scrape
     ?zip_code=10013&distance=25
     → triggers scraping + profile detail extraction
     → { contractors_found, new, updated }

POST /api/pipeline/enrich
     ?force=false&limit=10
     → runs all 3 enrichment stages sequentially (research → scoring → contacts)
     → { research: {total, succeeded, failed, duration_seconds},
         scoring: {...}, contacts: {..., contacts_found} }

GET  /api/pipeline/status
     → { total_contractors, with_research, with_scores, with_contacts,
         awaiting_research, awaiting_scoring, awaiting_contacts }

POST /api/chat
     body: { message: "Who are the top leads?", history: [{role, content}, ...] }
     → agentic loop: OpenAI selects tools, queries DB, iterates until final answer
     → { response: "Here are the top 3 leads by score:\n1. **Grapevine Pro**..." }

GET  /api/health
     → { status: "ok" }
```

**Architecture:**

The API layer is organized into three tiers:

1. **Schemas** (`schemas.py`): 11 Pydantic models enforce type safety on all request/response boundaries. List and detail views use separate schemas — `LeadListItem` returns ~12 fields for the table, while `LeadDetail` nests the full `LeadInsightOut` and `list[ContactOut]`. This avoids serializing multi-KB text fields (research_summary, draft_email) for every row.

2. **Service layer** (`lead_service.py`): Isolates SQLAlchemy query logic from route handlers. Three functions: `get_leads()` (filtering, sorting with NULL-safe ordering, pagination), `get_lead_detail()` (eager-loaded relationships), `get_stats()` (aggregation with CASE WHEN bucketing). All accept a `Session` parameter injected via `Depends(get_session)`.

3. **Routers** (`leads.py`, `pipeline.py`): Thin handlers that validate inputs via `Query()` constraints, call the service or pipeline layer, and return Pydantic models.

**Key decisions:**
- **All handlers are sync `def`** (not `async def`): The enricher functions call `asyncio.run()` internally. Calling them from an `async def` handler would crash (nested event loops). FastAPI runs sync handlers in a thread pool automatically, which avoids this issue.
- Read endpoints are simple DB queries with filtering — fast, no LLM calls in the request path
- Pipeline endpoints trigger the actual work and return results synchronously (fine for ~78 leads)
- `sort_by` uses a column whitelist to prevent SQL injection via dynamic column selection
- `per_page` capped at 100 to prevent full-table serialization
- CORS allows `localhost:3000` for the Next.js dev server
- `init_db()` runs in the FastAPI lifespan context manager (modern pattern, replaces deprecated `@app.on_event`)
- Pydantic schemas receive data from existing `to_dict()` methods on ORM models — JSON-stored fields arrive already parsed
- FastAPI auto-generates OpenAPI docs at `/docs`

---

### 5. Frontend Dashboard

**Stack:** Next.js 16 (App Router) + Tailwind CSS v4 + TypeScript

**Starting the server:**

```bash
cd frontend && npm run dev
# → http://localhost:3000
```

**Design Language — Instalily-Inspired:**

The frontend mirrors InstaLILY AI's brand aesthetic: industrial, editorial, deliberate.

- **Typography:** IBM Plex Sans (body/headings, weights 300–500) + IBM Plex Mono (all section eyebrow labels, data values, tags, filter chips — monospace, uppercase, `tracking-widest`)
- **Colors:** Off-white `#FEFFF7` background, near-black `#171717` text, `#404040` muted text. No gradients. Score tiers are the only color pops (orange/amber/neutral)
- **Navigation:** Floating dark gradient pill (`rgba(0,0,0,0.85)` → `rgba(51,51,51,0.85)`) with `backdrop-blur(2px)` and off-white border. Fixed at top. Monospace nav links, outlined CTA button
- **Cards:** No rounded-corner card containers on light backgrounds — open editorial layout with thin black borders (sharp corners). Dark sections use `#171717` with semi-transparent inner cards (`rgba(38,38,38,0.5)`, `rounded-2xl`)
- **Section labels:** IBM Plex Mono, 12px, weight 500, uppercase, `tracking-widest` — used as eyebrow labels for every section
- **Accents:** Left-border accent lines (`border-l-2`) for "Why Now" (orange) and "Recommended Pitch" (black), matching Instalily's testimonial side-rule pattern
- **Spacing:** Generous — `py-12` page padding, `space-y-8`/`space-y-10` between sections
- **Footer:** Dark `#181818`, seamlessly integrated

**Dashboard Page (`/`):**
```
┌──────────────────────────────────────────────────────────────┐
│  ┌─ floating pill nav ──────────────────────────────────┐   │
│  │ ROOFLEADS_   DASHBOARD  PIPELINE  [Deploy InstaWorkers]│  │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  LEAD INTELLIGENCE (monospace eyebrow)                       │
│  Find your next best customer. (4xl, font-light)             │
│                                                              │
│  ┌──────────┬──────────┬──────────┬──────────┐              │
│  │ 78       │ 33       │ 48.3     │ 76/78    │  sharp black │
│  │ TOTAL    │ TOP      │ AVG      │ ENRICHED │  bordered    │
│  │ LEADS    │ LEADS    │ SCORE    │          │  grid cells  │
│  └──────────┴──────────┴──────────┴──────────┘              │
│                                                              │
│  [Search contractors...]                                     │
│  (All) (Hot 60+) (Warm) (Cold) │ (All Certs) (Pres) (ME)   │
│                                                              │
│  SCORE  CONTRACTOR                          EST. VOLUME  DIST │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  [67]   Grapevine Pro  [President's Club]   High (449)  19.7 │
│  [65]   Great American [President's Club]   High (150)  24.1 │
│  [64]   One Call Const [Master Elite]       High (109)  18.3 │
│                                                              │
│              (Prev) (1) (2) (3) (4) (Next)                   │
└──────────────────────────────────────────────────────────────┘
```

**Lead Detail Page (`/leads/[id]`):**
```
┌──────────────────────────────────────────────────────────────┐
│  ← BACK TO LEADS (monospace, uppercase, tracked)             │
│                                                              │
│  Grapevine Pro (4xl, font-light)              [67] (pill)    │
│  [President's Club] ★4.7 (449)                               │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ (thin black line) │
│  Iselin, NJ · (732) 335-7770 · grapevinepro.com · 6 yrs    │
│                                                              │
│  KEY CONTACTS (monospace eyebrow)                            │
│  ┌──────────────────────┐ ┌──────────────────────┐          │
│  │ Frank N. — Owner     │ │ Maria S. — Ops Mgr   │          │
│  │ [✉] [📞] [in]       │ │ [✉] [📞] [in]       │          │
│  └──────────────────────┘ └──────────────────────┘          │
│                                                              │
│  ┃ WHY NOW (orange left border accent)                       │
│  ┃ Hailstorm hit NE New Jersey 2 weeks ago...                │
│                                                              │
│  TALKING POINTS              SCORE BREAKDOWN                 │
│  01  Mention their 449..     Certification ████████░ 30/30   │
│  02  Ask about storm..       Reviews      █████░░░░ 18/20   │
│  03  Their Google reviews    Rating       █████████░  9/10   │
│                              Biz Signals  █████░░░░░ 10/20   │
│  ──────────────────────      Why Now      ░░░░░░░░░░  0/20   │
│  BUYING SIGNALS              PAIN POINTS                     │
│  • High storm repair vol     • Delivery complaints           │
│  • Expanding territory       • Premium shingle avail         │
│                                                              │
│  ┃ RECOMMENDED PITCH (black left border accent)              │
│  ┃ Position as reliable, high-volume supplier for storm...   │
│                                                              │
│  ┌─ dark card (#171717, rounded-2xl) ────────────────────┐  │
│  │ DRAFT OUTREACH EMAIL                        [COPY]    │  │
│  │ Subject: Supporting your storm season demand           │  │
│  │ ┌─ semi-transparent inner card ────────────────────┐  │  │
│  │ │ Hi Frank, I noticed Grapevine Pro's stellar...   │  │  │
│  │ └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ▶ RESEARCH SUMMARY (collapsible)                            │
│  SOURCES: (bbb.org) (google.com) (yelp.com) (pill links)    │
└──────────────────────────────────────────────────────────────┘
```

**Component architecture (25 files):**

| Layer | Components | Pattern |
|-------|-----------|---------|
| `lib/` (4) | types, api, constants, utils | Pure TypeScript, no React |
| `ui/` (5) | ScorePill, CertBadge, StarRating, ProgressBar, CopyButton | Reusable primitives, monospace styling |
| `dashboard/` (4) | StatsBar, FilterBar, LeadTable, LeadRow | Client components, URL state sync |
| `lead-detail/` (8) | LeadHeader, ContactCard, WhyNowBanner, TalkingPoints, ScoreBreakdown, InsightsGrid, DraftEmail, ResearchSummary | Presentational, receive props |
| `app/` (4) | layout, globals.css, page (dashboard), leads/[id]/page (detail) | App shell + route pages |

**Key decisions:**
- **Dashboard is a client component** — uses `useSearchParams` + `useRouter` to sync filter/sort/page state to URL query params. All filters are bookmarkable. `useEffect` fetches from the API on every filter change with debounced search (300ms)
- **Lead detail is a server component** — single `fetch(/api/leads/{id})` at request time, passes data down as props. Only `CopyButton` and `ResearchSummary` (collapsible) are client components
- **No SWR/React Query** — plain `fetch` in `useEffect` is sufficient for this data scale (78 leads, no real-time updates, no optimistic mutations)
- **Score tier thresholds adjusted for real data** — current scores range 25–67, so tiers are Hot (60+), Warm (40–59), Cold (<40) rather than 70/50/30
- **All filter/sort params match the backend's API exactly** — `sort_by` values match the column whitelist in `lead_service.py`, filter names match `Query()` params in `leads.py`
- **Tailwind v4 with `@theme inline`** — CSS variables for brand colors, no `tailwind.config.ts` customization needed
- **IBM Plex loaded via `next/font/google`** — self-hosted, no layout shift. Sans weights 300/400/500/600, Mono weights 400/500/600

---

## Data Flow Summary

```
1. SCRAPE (scraper.py)
   Playwright → GAF website → intercept Coveo API → raw contractor dicts
   Playwright → individual profile pages → website, years_in_business, about
   → INSERT INTO contractors (upsert on gaf_id)

2. RESEARCH — Stage 1 (research.py)
   contractors row → Perplexity sonar-pro → research text + citations
   → INSERT INTO lead_insights.research_summary + citations (upsert on contractor_id)

3. SCORE — Stage 2 (scoring.py)
   contractors row → Python deterministic scoring → 60/100 base score
   research_summary + contractor data + base score → OpenAI gpt-4o-mini → structured JSON
   → UPDATE lead_insights SET lead_score, score_breakdown, talking_points,
     buying_signals, pain_points, recommended_pitch, why_now, draft_email

4. CONTACTS — Stage 3 (contact_enrichment.py)
   research_summary → OpenAI → extracted decision-maker names/titles/emails
   → INSERT INTO contacts (per contractor)

5. SERVE (app/api/ + app/services/lead_service.py)
   GET /api/leads → SELECT contractors LEFT JOIN lead_insights
     with filters (score range, certification, name search), sort, paginate
   GET /api/leads/{id} → Contractor.to_dict() + insights.to_dict() + contacts
   GET /api/stats → COUNT, AVG, GROUP BY certification, CASE WHEN score buckets
   POST /api/pipeline/scrape → asyncio.run(scrape_contractors()) + store_contractors()
   POST /api/pipeline/enrich → run_research → run_scoring → run_contacts
   GET /api/pipeline/status → count contractors/researched/scored/contacts

6. DISPLAY (Next.js frontend on :3000)
   Dashboard page (client component) → fetch /api/leads with URL-synced filters
     → StatsBar (4 metric cells) + FilterBar (score tier pills + cert pills + search)
     → LeadTable (sortable columns, paginated rows with ScorePill + CertBadge inline + Est. Volume)
   Detail page (server component) → fetch /api/leads/{id}
     → LeadHeader (name, score, cert, contacts with action buttons)
     → WhyNowBanner (orange left-border accent)
     → TalkingPoints (numbered 01–05) + ScoreBreakdown (5 progress bars)
     → InsightsGrid (buying signals + pain points)
     → DraftEmail (dark card with copy button)
     → ResearchSummary (collapsible) + citation source pills
```

---

## Implemented Features

### Hybrid Lead Scoring (Deterministic + LLM)
Lead scores combine Python-computed structured-data scores (certification, reviews, rating → 60 pts) with LLM-assessed qualitative signals from research text (business growth, urgency → 40 pts). This gives reproducibility on objective factors and contextual intelligence on subjective ones. Scores are explainable — each component is visible in `score_breakdown`.

### "Why Now" Urgency Signals
Extracted by OpenAI from the Perplexity research text. The LLM identifies time-sensitive triggers: recent storms, seasonal demand surges, supplier problems mentioned in reviews. Scored as a 0-20 component and surfaced as a narrative string. Displayed prominently as a highlighted banner on the lead detail page.

### Actionable Sales Intelligence
For every scored lead, the pipeline generates:
- **Talking points** (3-5): specific conversation starters referencing the contractor's data and research
- **Buying signals** (2-4): evidence-based indicators of material purchasing needs
- **Pain points** (2-4): problems the distributor can solve, sourced from reviews and research
- **Recommended pitch**: 2-3 sentences on how to position the distributor's value for this specific contractor

### Draft Outreach Email
Generated by OpenAI as part of the structured scoring output. Personalized using contractor name, certification, research findings, and identified pain points / buying signals. Includes subject line. Displayed with a "Copy to Clipboard" button on the detail page.

### Lead Score Explainability
The `score_breakdown` JSON field contains 5 individual factor scores with their max values. Rendered as labeled progress bars on the detail page. Sales reps can see exactly *why* a lead scored high or low:
- `certification_tier`: 0-30 (deterministic)
- `review_volume`: 0-20 (deterministic, log-scaled)
- `rating_quality`: 0-10 (deterministic, confidence-weighted)
- `business_signals`: 0-20 (LLM-scored from research)
- `why_now_urgency`: 0-20 (LLM-scored from research)

### Perplexity Source Citations
Citations returned by Perplexity are stored in the `citations` JSON field. Displayed as clickable links at the bottom of the lead detail page. Builds trust — reps can verify the research.

### Decision-Maker Contact Extraction
Contact names, titles, emails, and LinkedIn URLs are extracted from Perplexity research text using OpenAI and stored in the `contacts` table. Multiple contacts per contractor (owner + ops manager, etc.).

### CLI Pipeline Management
Full CLI for running each pipeline stage independently:
```bash
uv run python -m app.pipeline.cli ingest data/sample.json   # load contractor data
uv run python -m app.pipeline.cli research                    # Stage 1: Perplexity
uv run python -m app.pipeline.cli score                       # Stage 2: OpenAI scoring
uv run python -m app.pipeline.cli contacts                    # Stage 3: contact extraction
uv run python -m app.pipeline.cli status                      # pipeline health check
```
Each command supports `--force` (re-process all), `--limit N`, and `--concurrency N`.

### REST API with FastAPI
Full REST API serving enriched lead data to the frontend. Six endpoints across two routers: lead browsing (paginated list, detail, dashboard stats) and pipeline management (scrape, enrich, status). 11 Pydantic schemas enforce type safety. Service layer isolates query logic with support for multi-column sorting, score range filtering, certification filtering, and name search. All handlers are synchronous to avoid `asyncio.run()` nesting issues with the enrichment pipeline. OpenAPI docs auto-generated at `/docs`.

### Test Suite (119 tests)
Comprehensive test coverage across the full backend:
- **Service layer** (25 tests): Pagination, all filter combinations, sort ordering, NULL score handling, stats aggregation, score distribution bucketing
- **API endpoints** (19 tests): Full HTTP round-trip testing via FastAPI `TestClient` with in-memory SQLite (`StaticPool` for cross-thread sharing). Tests cover response shapes, pagination metadata, 404 handling, input validation (422), and pipeline status
- **Pipeline** (75 tests): Scraper parsing, research engine (async mocking), scoring deterministic functions, enricher orchestration, ORM model methods, certification tiers, citation extraction, prompt templates, DB upserts

Run with: `cd backend && uv run pytest -v`

### Frontend Dashboard (Instalily-Branded)
Full Next.js 16 dashboard with Instalily AI's design language. IBM Plex Sans/Mono typography, off-white `#FEFFF7` backgrounds, floating dark gradient pill navigation, sharp-bordered editorial layouts, and monospace uppercase section eyebrows. Two pages: a filterable/sortable lead table dashboard with URL-synced state, and a comprehensive lead detail page with 8 insight sections (header, why now, talking points, score breakdown, buying signals, pain points, draft email, research summary). Contact cards with direct email/call/LinkedIn action buttons. Draft email displayed in a dark `#171717` card with one-click copy. Score explainability rendered as labeled progress bars. Research citations as clickable monospace pill links. 25 components, zero external UI libraries.

Starting the full stack:
```bash
cd backend && uv run python main.py   # API on :8000
cd frontend && npm run dev             # Dashboard on :3000
```

---

## Additional Features (time permitting)

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
