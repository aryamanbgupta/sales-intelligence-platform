# Pipeline Documentation

## Overview

The data pipeline collects and enriches roofing contractor leads in four stages:

1. **Scrape** — Pull contractor listings from GAF's public directory via Coveo API interception, then visit each profile page for additional details
2. **Research** — Query Perplexity (sonar-pro) for web-sourced intelligence on each contractor: reputation, growth signals, supplier relationships, decision-makers
3. **Score** — Feed scraped data + research into OpenAI to produce hybrid lead scores (deterministic + LLM), talking points, and outreach drafts
4. **Contacts** — Extract decision-maker names and contact info from research text using OpenAI, with an extensible provider architecture for additional sources (Hunter.io, Apollo, etc.)

Stages are decoupled. Each can be re-run independently — re-scrape without losing research, re-research without re-scraping, re-score without re-researching, re-extract contacts without re-researching. All data is stored in SQLite at `backend/data/leads.db`.

```
  GAF Website            Perplexity API            OpenAI API              OpenAI API
      │                       │                        │                       │
      ▼                       ▼                        ▼                       ▼
  ┌────────┐  contractors ┌──────────┐ lead_insights ┌──────────┐ contacts ┌──────────┐
  │Scraper │─────────────▶│Research  │──────────────▶│ Scoring  │         │ Contact  │
  │        │    table      │ Engine   │    table       │ Engine   │         │Extractor │
  └────────┘               └──────────┘               └──────────┘         └──────────┘
  Playwright +              Async batch                Hybrid score          Provider-based
  Coveo API                 w/ retries                 60 det + 40 LLM      architecture
                                                            │                    ▲
                                                            │    lead_insights   │
                                                            └────────────────────┘
                                                              (reads research text)
```

---

## Stage 1: Scraping (GAF Directory)

### How It Works

GAF's website is JS-rendered and protected by Akamai bot detection (returns 403 to plain HTTP). Under the hood, the contractor search is powered by **Coveo** (a search-as-a-service platform). We exploit this with a two-phase approach:

**Phase 1 — Listing Scrape (Coveo API Interception)**

1. Playwright launches headless Chromium with stealth settings (spoofed `navigator.webdriver`, realistic user-agent) to bypass Akamai
2. The browser navigates to `https://www.gaf.com/en-us/roofing-contractors/residential?postalCode={zip}&countryCode=us&user=true&distance={miles}`
3. The page fires a POST to `https://platform.cloud.coveo.com/rest/search/v2` — we **intercept** this request to capture the Bearer token, request body, and first page of results
4. We then make **direct HTTP calls** to the Coveo API (no browser needed) to paginate through all results at 50 per page

This hybrid approach completes in ~15 seconds for 76 contractors and returns clean structured JSON.

**Phase 2 — Profile Scrape**

The Coveo listing API doesn't include website URLs, years in business, or company descriptions. For each contractor:

1. Playwright visits the profile page (e.g. `/roofing-contractors/residential/usa/ny/.../contractor-1004859`)
2. Extracts the **website URL** from the "Visit Website" link or JSON-LD `sameAs` field
3. Extracts **years in business** from "In business since YYYY" text
4. Extracts the **about text** from the company description section

Profile pages are scraped 3 at a time (configurable). The full run takes ~2-3 minutes for 76 contractors.

### Running the Scraper

```bash
cd backend
uv run python -m app.pipeline.scraper
```

Output:
```
Scraped 76 contractors from listings
Database: 76 new, 0 updated
Scraping 76 profile pages for details...
Updated 76 contractors with website/years/about
Profile data: 44 websites, 46 years-in-business, 48 about texts
```

### Programmatic Usage

```python
from app.pipeline.scraper import scrape_contractors, store_contractors
from app.pipeline.scraper import scrape_profile_details, update_profile_details

# Phase 1: Listings
contractors = await scrape_contractors(zip_code="10013", distance=25)
store_contractors(contractors)

# Phase 2: Profile details
profile_entries = [
    {"gaf_id": c["gaf_id"], "profile_url": c["profile_url"]}
    for c in contractors if c.get("profile_url")
]
details = await scrape_profile_details(profile_entries, concurrency=3)
update_profile_details(details)
```

### Data Coverage (ZIP 10013, 25mi radius)

| Field | Coverage | Notes |
|---|---|---|
| gaf_id, name, city, state, zip, phone | 76/76 (100%) | Always present from Coveo API |
| certification | 76/76 (100%) | 68 Master Elite, 11 President's Club |
| rating + review_count | 69/76 (91%) | 7 contractors have no Google reviews |
| website | 44/76 (58%) | ~30 contractors don't list a website on GAF |
| years_in_business | 46/76 (61%) | ~30 contractors don't list founding year |
| about (description) | 48/76 (63%) | Some profiles have no description |
| lat/lng, distance, profile_url | 76/76 (100%) | Always present from Coveo API |

### What the Scraper Does NOT Collect

| Field | Why | Where to get it |
|---|---|---|
| State license ID | Not on GAF's site | State licensing board DBs, or Perplexity research |
| Full street address | GAF only shows city/state/ZIP | Google Places API or Perplexity research |
| Revenue / employee count | Not public | Perplexity research, LinkedIn, Crunchbase |
| Google review text | On GAF profile but not worth scrape time | Google Places API or Perplexity |

---

## Stage 2: Perplexity Research

### How It Works

For each contractor, we send a comprehensive research query to the Perplexity API (`sonar-pro` model via OpenAI-compatible client). The prompt is built dynamically from all available scraped data, so Perplexity knows what we already have and focuses on finding new intelligence.

**What the prompt includes as context (from the scraper):**
- Name, location, phone, website URL
- GAF certification tier + all certifications
- Google rating and review count
- Services/specialties
- Years in business
- Company self-description (about text)
- GAF profile URL

**What the prompt asks Perplexity to find:**

| Research Area | What We're Looking For |
|---|---|
| **Decision Makers & Key Contacts** (HIGH PRIORITY) | Owner/president names from state business registrations, BBB, D&B, LinkedIn, company website, Google. Full name, title, source, direct email/phone, LinkedIn URL |
| Online Reputation | Google review themes, BBB rating, Angi/HomeAdvisor/Yelp/Houzz ratings, press coverage |
| Business Health & Growth | Company size, hiring activity, expansion signals, social media trends |
| Website Analysis | Services featured, material brands mentioned, careers page, site quality (only when website URL available) |
| Market & Weather Context | Recent severe weather in service area, local roofing demand, seasonal patterns |
| Supplier & Material Intelligence | Current material suppliers, product lines used, delivery complaints, job volume, buying groups |
| Competitive Positioning | Market position, differentiators, competitors, unique selling proposition |

The **Decision Makers** section is the highest-priority research area — it directs Perplexity to search state Secretary of State records, BBB profiles, D&B business listings, LinkedIn, company websites, and Google for owner/officer names. Even partial results (name + title, no email) are valuable for the sales team's outreach. This research text feeds directly into Stage 4 (Contact Extraction) for structured parsing.

The prompt adapts based on data availability — if we already know years in business, it doesn't ask; if no website is available, it asks Perplexity to search for one.

### Architecture

```
app/pipeline/
  prompts.py               # Prompt templates — Perplexity system/research + OpenAI scoring prompts
  research.py              # Perplexity API client — async batch processing, retries, rate limiting
  scoring.py               # OpenAI scoring engine — deterministic + LLM hybrid scoring
  contact_enrichment.py    # Contact extraction — provider-based architecture (Perplexity extract, Hunter.io stub)
  enricher.py              # Orchestrator — connects all engines to the database
  cli.py                   # CLI entry point for all pipeline operations
```

**Key design decisions:**

- **Async with controlled concurrency** — `asyncio.Semaphore` caps parallel API calls (default 3) to respect rate limits
- **Per-contractor error isolation** — one failure doesn't stop the batch; errors are logged and skipped
- **Exponential backoff** on transient failures (rate limits, connection errors) with configurable retry count (default 3)
- **Upsert on persist** — safe to re-run research; existing insights are updated, not duplicated
- **Prompt/engine separation** — `prompts.py` can be iterated on independently of the API client logic

### Running Research

```bash
cd backend

# Research all unenriched contractors
uv run python -m app.pipeline.cli research

# Research with higher concurrency (faster, more API load)
uv run python -m app.pipeline.cli research --concurrency 5

# Force re-research all contractors (even those already enriched)
uv run python -m app.pipeline.cli research --force

# Research a limited batch (e.g. for testing)
uv run python -m app.pipeline.cli research --limit 5

# Check pipeline status
uv run python -m app.pipeline.cli status
```

### Ingesting Data Manually

If the scraper hasn't run yet or you have contractor data from another source:

```bash
# Ingest from a JSON file
uv run python -m app.pipeline.cli ingest data/sample_contractors.json

# Ingest and immediately research
uv run python -m app.pipeline.cli ingest data/sample_contractors.json --research
```

The JSON file should be an array of objects with at minimum `name` and `address`. See `data/sample_contractors.json` for the full field set.

### Performance (ZIP 10013, 76 contractors)

| Metric | Value |
|---|---|
| Total time | ~310 seconds (~5 min) |
| Avg time per contractor | ~4.3 seconds |
| Success rate | 76/76 (100%) |
| Avg citations per contractor | 6.4 |
| Citation range | 2–9 per contractor |
| Avg research length | ~3,100 chars |
| Research length range | 1,432–5,707 chars |
| Concurrency used | 3 |

### Research Output

Each contractor gets a `lead_insights` row with:
- **`research_summary`** — Full research text from Perplexity, organized by topic
- **`citations`** — JSON array of source URLs that Perplexity grounded its research on

Example sources found: BBB profiles, Angi reviews, HomeAdvisor ratings, D&B business listings, USDOT carrier records, Indeed employee reviews, contractor websites, Owens Corning/CertainTeed directories.

Notable findings from the initial run:
- Identified contractors with **competitor supplier relationships** (e.g. Owens Corning certified)
- Found **BBB ratings and complaint histories**
- Discovered **employee review data** on Indeed (salary ranges, workplace culture)
- Detected **fleet registrations** via USDOT records
- Flagged potential **misclassifications** (e.g. gutter specialist listed under roofing)

### Configuration

All research settings live in `backend/app/config.py`:

```python
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")  # from .env
PERPLEXITY_BASE_URL = "https://api.perplexity.ai"
PERPLEXITY_MODEL = "sonar-pro"
PERPLEXITY_MAX_TOKENS = 4096
PERPLEXITY_TEMPERATURE = 0.2

ENRICHMENT_DELAY_SECONDS = 1.0   # delay between API calls (rate limiting)
MAX_RETRIES = 3                  # retries per contractor on transient failure
RETRY_BACKOFF_BASE = 2.0         # exponential backoff base (seconds)
```

Required in `backend/.env`:
```
PERPLEXITY_API_KEY=pplx-your-key-here
OPENAI_API_KEY=sk-your-key-here
```

---

## Stage 3: OpenAI Scoring

### How It Works

Scoring uses a **hybrid deterministic + LLM approach** to produce a 0–100 lead score and actionable sales intelligence for each contractor.

**Deterministic scoring (60/100 points)** — computed from structured data, no API call needed:

| Factor | Max Points | How It's Scored |
|---|---|---|
| `certification_tier` | 30 | President's Club=30, Master Elite=25, Certified Plus=20, Certified=15, Uncertified=5 |
| `review_volume` | 20 | Log-scale: 10 reviews≈7pts, 100≈13pts, 500+≈18-20pts. Proxy for job volume |
| `rating_quality` | 10 | Star rating weighted by review confidence (confidence = min(1.0, review_count/50)) |

**LLM scoring (40/100 points)** — scored by OpenAI from the Perplexity research text:

| Factor | Max Points | What It Measures |
|---|---|---|
| `business_signals` | 20 | Growth evidence: hiring, expansion, new equipment, revenue trends. 0 if no evidence, 15+ requires concrete data |
| `why_now_urgency` | 20 | Time-sensitive triggers: recent storms, supplier problems, rapid growth outpacing supply chain. 15+ requires imminent, documented triggers |

**Final score** = `certification_tier + review_volume + rating_quality + business_signals + why_now_urgency`

The deterministic subtotal is passed to OpenAI as locked scores — the LLM cannot modify them. The pipeline enforces correct arithmetic server-side (clamps LLM scores to 0–20 range, recomputes the sum rather than trusting the LLM's addition).

### Sales Intelligence Outputs

Beyond the score, OpenAI generates structured sales intelligence for each contractor:

| Output | Description |
|---|---|
| `talking_points` | 3–5 specific, actionable conversation starters referencing concrete data |
| `buying_signals` | 2–4 indicators the contractor may need a new/better materials supplier |
| `pain_points` | 2–4 problems the distributor could solve |
| `recommended_pitch` | 2–3 sentence value proposition tailored to this specific contractor |
| `why_now` | Time-sensitive reason to call this week (or "No immediate urgency" if none) |
| `draft_email` | 150–200 word cold outreach email with Subject line, personalized with findings |

### Running Scoring

```bash
cd backend

# Score all researched but unscored contractors
uv run python -m app.pipeline.cli score

# Force re-score all researched contractors
uv run python -m app.pipeline.cli score --force

# Score with higher concurrency
uv run python -m app.pipeline.cli score --concurrency 10

# Score a limited batch
uv run python -m app.pipeline.cli score --limit 10
```

### Configuration

```python
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"                # fast + cheap for structured extraction
OPENAI_SCORING_MAX_TOKENS = 2048
OPENAI_SCORING_TEMPERATURE = 0.3
```

---

## Stage 4: Contact Extraction

### How It Works

The sales team needs to know **who to call** at each contractor. Contact extraction parses the Perplexity research text (which already contains decision-maker information from Stage 2) into structured contact records using a lightweight OpenAI call.

For each contractor with research:
1. Load the research text from `lead_insights.research_summary`
2. Send it to OpenAI (`gpt-4o-mini`, temperature=0.1, JSON mode) with a prompt asking it to extract all mentioned people and their roles
3. Parse the structured JSON response into `Contact` records
4. Persist to the `contacts` table with name-based deduplication

### What Gets Extracted

For each person found in the research text:

| Field | Description | Example |
|---|---|---|
| `full_name` | Full name | "Frank Notarnicola" |
| `title` | Role/title at the company | "President", "Owner", "Operations Manager" |
| `email` | Direct email (only if explicitly stated in research) | "frank@example.com" |
| `phone` | Direct phone (only if different from company phone) | "(555) 123-4567" |
| `linkedin_url` | LinkedIn profile URL (only if found) | "https://linkedin.com/in/..." |
| `source` | Where the info was found | "NY Secretary of State", "BBB profile", "D&B listing" |
| `confidence` | Reliability level | "high" (state records, BBB, D&B), "medium" (website, reviews), "low" (inferred) |

### Running Contact Extraction

```bash
cd backend

# Extract contacts for all researched contractors that don't have contacts yet
uv run python -m app.pipeline.cli contacts

# Force re-extract for ALL researched contractors (dedupes, doesn't replace)
uv run python -m app.pipeline.cli contacts --force

# Limit to a batch
uv run python -m app.pipeline.cli contacts --limit 10
```

### Extensible Provider Architecture

Contact extraction uses a **provider-based design** that makes it straightforward to add new data sources beyond Perplexity research parsing.

```
contact_enrichment.py
  ├── extract_contacts_from_research()   ← ACTIVE: parses existing research text
  ├── find_contacts_hunter()             ← STUB: Hunter.io email lookup by domain
  ├── find_contacts_apollo()             ← FUTURE: Apollo.io contact enrichment
  └── PROVIDER_REGISTRY                  ← Registry mapping provider keys to functions
```

**Current providers:**

| Provider | Status | How It Works | Cost |
|---|---|---|---|
| `perplexity_extract` | Active | OpenAI parses research text for contacts | ~$0.001/contractor (gpt-4o-mini) |
| `hunter_io` | Stub (ready to plug in) | Email lookup by company domain via Hunter.io API | Free tier: 25/mo, paid from $49/mo |
| `apollo` | Placeholder | Contact enrichment via Apollo.io | TBD |
| `rocketreach` | Placeholder | Contact enrichment via RocketReach | TBD |

**To add a new provider:**

1. Write an async function matching the signature:
   ```python
   async def find_contacts_<provider>(
       client: AsyncOpenAI,  # or httpx.AsyncClient
       contractor: dict,
       research_text: str,
   ) -> ContactExtractionResult:
   ```
2. Add it to `PROVIDER_REGISTRY` in `contact_enrichment.py`:
   ```python
   PROVIDER_REGISTRY = {
       "perplexity_extract": "extract_contacts_from_research",
       "hunter_io": "find_contacts_hunter",        # ← uncomment
   }
   ```
3. Pass the provider key when calling `run_contact_extraction()`

The Hunter.io stub includes a complete implementation example in comments — just add an API key and uncomment.

### Deduplication

Contacts are deduplicated by `(contractor_id, full_name)`. Re-running extraction with `--force`:
- **Skips** contacts that already exist by name
- **Enriches** existing contacts with newly found info (e.g., adds an email to a record that previously only had name + title)
- **Never deletes** existing contacts

---

## REST API (FastAPI)

### Architecture

The API follows a three-tier pattern:

```
Routes (api/)  →  Service Layer (services/)  →  Database (db/)
  leads.py           lead_service.py              models.py
  pipeline.py                                     database.py
```

- **Routes** validate inputs (Pydantic schemas), call services, return responses
- **Service layer** builds SQLAlchemy queries, handles filtering/sorting/pagination
- **Database layer** provides the ORM models and session factory

All route handlers are **sync `def`** (not `async def`). This is intentional — the pipeline enricher functions call `asyncio.run()` internally, which crashes if called from an async context (nested event loops). Sync handlers run in FastAPI's thread pool automatically, sidestepping the issue.

### Starting the Server

```bash
cd backend
uv run python main.py
# Runs at http://localhost:8000 with hot reload
# Interactive API docs at http://localhost:8000/docs
```

### Endpoints

#### `GET /api/health`

Health check. Returns `{"status": "ok"}`.

#### `GET /api/leads`

Paginated, filterable, sortable list of leads. Returns compact items (no heavy text fields like research_summary or draft_email).

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | int (≥1) | 1 | Page number |
| `per_page` | int (1–100) | 20 | Items per page |
| `sort_by` | string | `lead_score` | Sort column: `lead_score`, `name`, `rating`, `review_count`, `certification`, `distance_miles` |
| `sort_order` | string | `desc` | `asc` or `desc` |
| `min_score` | int | — | Minimum lead score filter |
| `max_score` | int | — | Maximum lead score filter |
| `certification` | string | — | Exact match on certification tier |
| `search` | string | — | Case-insensitive name search (ILIKE) |

Response shape:
```json
{
  "data": [
    {
      "id": 1, "name": "ABC Roofing", "city": "Brooklyn", "state": "NY",
      "certification": "Master Elite", "rating": 4.8, "review_count": 127,
      "lead_score": 72, "phone": "(718) 555-0100", "website": "https://...",
      "image_url": "https://...", "distance_miles": 3.2, "years_in_business": 15
    }
  ],
  "pagination": {
    "page": 1, "per_page": 20, "total_items": 78, "total_pages": 4
  }
}
```

**Sort column whitelist** — the `sort_by` parameter is validated against a dict of allowed SQLAlchemy column objects (`_SORT_COLUMNS` in `lead_service.py`) to prevent SQL injection via dynamic column names.

**NULL handling** — contractors without scores are sorted last when sorting by `lead_score` desc (via `nullslast()`).

#### `GET /api/leads/{lead_id}`

Full detail for a single lead, including nested insights and contacts.

Response shape:
```json
{
  "id": 1, "gaf_id": "1004859", "name": "ABC Roofing",
  "city": "Brooklyn", "state": "NY", "phone": "...", "website": "...",
  "insights": {
    "lead_score": 72,
    "score_breakdown": {"certification_tier": 25, "review_volume": 13, ...},
    "research_summary": "Full research text...",
    "citations": ["https://bbb.org/...", "https://..."],
    "talking_points": ["Ask about storm season", ...],
    "buying_signals": ["Expanding territory", ...],
    "pain_points": ["Slow delivery times", ...],
    "recommended_pitch": "Value proposition...",
    "why_now": "Recent hailstorm in service area.",
    "draft_email": "Subject: ...\n\nHi Frank, ..."
  },
  "contacts": [
    {"full_name": "Frank N.", "title": "President", "email": null,
     "phone": null, "linkedin_url": null, "source": "perplexity_research",
     "confidence": "high"}
  ]
}
```

Returns 404 with `{"detail": "Lead not found"}` if the ID doesn't exist.

#### `GET /api/stats`

Dashboard aggregate statistics.

Response shape:
```json
{
  "total_leads": 78,
  "avg_score": 52.3,
  "high_priority_count": 12,
  "certification_breakdown": {"Master Elite": 68, "President's Club": 11, ...},
  "score_distribution": {"0-25": 5, "26-50": 20, "51-75": 35, "76-100": 18}
}
```

`high_priority_count` = contractors with `lead_score >= 70`.

#### `POST /api/pipeline/scrape`

Triggers the GAF scraper. Blocks until complete (typically ~2-3 minutes).

| Parameter | Type | Default | Description |
|---|---|---|---|
| `zip_code` | string | `10013` | ZIP code to search |
| `distance` | int (5–100) | `25` | Search radius in miles |

Runs Phase 1 (Coveo listing scrape) then Phase 2 (profile detail scrape) and persists results.

Response: `{"contractors_found": 76, "new": 76, "updated": 0}`

#### `POST /api/pipeline/enrich`

Runs all three enrichment stages sequentially: research → scoring → contacts.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `force` | bool | `false` | Re-enrich already-enriched contractors |
| `limit` | int (≥1) | — | Max contractors to process per stage |

Response:
```json
{
  "research": {"total": 76, "succeeded": 76, "failed": 0, "duration_seconds": 310.5},
  "scoring": {"total": 76, "succeeded": 76, "failed": 0, "duration_seconds": 45.2},
  "contacts": {"total": 76, "succeeded": 72, "failed": 4, "contacts_found": 58, "duration_seconds": 38.1}
}
```

#### `GET /api/pipeline/status`

Pipeline health summary — how many contractors have been processed through each stage.

Response:
```json
{
  "total_contractors": 78,
  "with_research": 78,
  "with_scores": 78,
  "with_contacts": 58,
  "awaiting_research": 0,
  "awaiting_scoring": 0,
  "awaiting_contacts": 20
}
```

### CORS

The API allows requests from `http://localhost:3000` and `http://127.0.0.1:3000` (Next.js frontend dev server). Configured in `app/main.py` via FastAPI's `CORSMiddleware`.

---

## Test Suite

### Running Tests

```bash
cd backend
uv run pytest                  # Run all tests
uv run pytest -v               # Verbose output
uv run pytest tests/test_api.py  # Run only API tests
```

### Test Architecture

**Service tests** (`test_lead_service.py`, 25 tests) — test the query helpers directly against an in-memory SQLite database with transaction-based rollback isolation via the `db_session` fixture in `conftest.py`.

**API tests** (`test_api.py`, 19 tests) — test the full HTTP stack using FastAPI's `TestClient`. Uses `StaticPool` to share a single in-memory SQLite connection across all threads (FastAPI runs sync handlers in a thread pool, and each thread would normally get a separate in-memory database). The `get_session` dependency is overridden at module level, and tables are dropped/recreated per test via an `autouse` fixture.

### Test Coverage

| Area | Tests | What's Covered |
|---|---|---|
| Health check | 1 | `GET /api/health` returns 200 |
| Lead listing | 10 | Pagination, sorting, filtering (score/certification/search), response shape, validation |
| Lead detail | 3 | Full detail with insights+contacts, without insights, 404 |
| Stats | 3 | Empty DB, aggregates, score distribution buckets |
| Pipeline status | 2 | Empty DB, mixed pipeline progress |
| `get_leads()` | 13 | All filter combos, sort directions, NULL score ordering, dict keys |
| `get_lead_detail()` | 6 | Missing ID, basic fields, insights, contacts, empty states |
| `get_stats()` | 6 | Empty DB, totals, averages, high priority, cert breakdown, score buckets |

---

## Database Schema

### Table: `contractors`

Populated by the scraper. One row per contractor, deduped by `gaf_id`.

| Column | Type | Description | Source |
|---|---|---|---|
| `id` | INTEGER PK | Auto-increment row ID | DB |
| `gaf_id` | TEXT UNIQUE | GAF contractor ID (e.g. "1004859") — dedupe key | Coveo API |
| `name` | TEXT | Company name | Coveo API |
| `address` | TEXT | Formatted as "City, State ZIP" | Coveo API |
| `city` | TEXT | City name | Coveo API |
| `state` | TEXT | 2-letter state code | Coveo API |
| `zip_code` | TEXT | Postal code | Coveo API |
| `phone` | TEXT | Phone number, formatted | Coveo API |
| `website` | TEXT | Contractor's own website URL | Profile page |
| `certification` | TEXT | Top GAF cert: "President's Club", "Master Elite", "Certified Plus", "Certified", or "Uncertified" | Coveo API |
| `certifications_raw` | TEXT (JSON) | JSON array of all certification strings | Coveo API |
| `rating` | REAL | Google star rating (0–5). Null if no reviews | Coveo API |
| `review_count` | INTEGER | Number of Google reviews. Null if no reviews | Coveo API |
| `services` | TEXT (JSON) | JSON array of specialties (e.g. "Solar", "Metal", "FORTIFIED Roof") | Coveo API |
| `latitude` | REAL | Geo latitude | Coveo API |
| `longitude` | REAL | Geo longitude | Coveo API |
| `distance_miles` | REAL | Distance from search ZIP in miles | Coveo API |
| `years_in_business` | INTEGER | Calculated from "In business since YYYY". Null if not listed | Profile page |
| `about` | TEXT | Company description from profile. Null if not listed | Profile page |
| `profile_url` | TEXT | Full GAF profile page URL | Coveo API |
| `image_url` | TEXT | Profile image/logo URL | Coveo API |
| `scraped_at` | DATETIME | When this record was last scraped | Auto |
| `created_at` | DATETIME | Row creation time | Auto |
| `updated_at` | DATETIME | Last update time | Auto |

### Table: `lead_insights`

Populated by Stage 2 (Research) and Stage 3 (Scoring). One row per contractor (FK to `contractors.id`, UNIQUE constraint).

| Column | Type | Populated By | Description |
|---|---|---|---|
| `id` | INTEGER PK | DB | Auto-increment |
| `contractor_id` | INTEGER FK UNIQUE | Research | References `contractors.id` |
| `research_summary` | TEXT | Research | Perplexity research output (full text) |
| `citations` | TEXT (JSON) | Research | Array of source URLs from Perplexity |
| `lead_score` | INTEGER | Scoring | 0–100 composite score (deterministic + LLM) |
| `score_breakdown` | TEXT (JSON) | Scoring | `{certification_tier: 25, review_volume: 13, rating_quality: 8, business_signals: 10, why_now_urgency: 5}` |
| `talking_points` | TEXT (JSON) | Scoring | Array of specific, actionable conversation starters |
| `buying_signals` | TEXT (JSON) | Scoring | Array of indicators contractor needs new supplier |
| `pain_points` | TEXT (JSON) | Scoring | Array of problems the distributor could solve |
| `recommended_pitch` | TEXT | Scoring | Tailored value proposition (2–3 sentences) |
| `why_now` | TEXT | Scoring | Time-sensitive call trigger |
| `draft_email` | TEXT | Scoring | 150–200 word personalized cold outreach email |
| `enriched_at` | DATETIME | Research | When enrichment last ran |
| `created_at` | DATETIME | DB | Row creation time |
| `updated_at` | DATETIME | DB | Last update time |

### Table: `contacts`

Populated by Stage 4 (Contact Extraction). Multiple rows per contractor allowed (e.g., owner + ops manager).

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `contractor_id` | INTEGER FK (indexed) | References `contractors.id` |
| `full_name` | TEXT | Person's full name |
| `title` | TEXT | Role at the company (Owner, President, VP, etc.) |
| `email` | TEXT | Direct email address (if publicly available) |
| `phone` | TEXT | Direct phone (if different from company phone) |
| `linkedin_url` | TEXT | LinkedIn profile URL |
| `source` | TEXT NOT NULL | Provider that found this contact ("perplexity_research", "hunter_io", "manual") |
| `confidence` | TEXT | "high", "medium", or "low" |
| `created_at` | DATETIME | Row creation time |
| `updated_at` | DATETIME | Last update time |

**Relationships:** `Contractor.contacts` is a one-to-many relationship. A contractor can have zero or many contacts. Contacts are deduplicated by `(contractor_id, full_name)`.

---

## Scalability

### Scraping Multiple ZIP Codes

The `gaf_id` column is a global dedupe key. Contractors in overlapping search radii are merged via upsert.

```python
zip_codes = ["10013", "07302", "11201", "10701", "06901"]
for zip_code in zip_codes:
    contractors = await scrape_contractors(zip_code=zip_code, distance=25)
    result = store_contractors(contractors)
```

### Residential vs Commercial

GAF has separate directories. Switching is a single parameter:

```python
res = await scrape_contractors(zip_code="10013", contractor_type="residential")
com = await scrape_contractors(zip_code="10013", contractor_type="commercial")
```

| | Residential | Commercial |
|---|---|---|
| **Top cert tiers** | President's Club > Master Elite > Certified Plus > Certified | Chairman's Circle > PlatinumElite > GoldElite > Certified |
| **Cert field** | `gaf_f_contractor_certifications_and_awards_residential` | `gaf_f_contractor_certifications_and_awards_commercial` |

### Database

- **Current:** SQLite — single-file, zero-config, suitable for up to ~10K rows
- **Production:** Swap to Postgres by changing `DATABASE_URL` in config. The SQLAlchemy ORM makes this a one-line change. JSON text columns become native JSONB with GIN indexes

### Production Task Queue (future)

```
Scheduler (cron)
  → Celery + Redis task queue
    → Worker 1: scrape("10013", 50) → store → scrape profiles
    → Worker 2: scrape("90210", 50) → store → scrape profiles
    → ...
  → All results land in shared Postgres
  → Research pipeline picks up new contractors
  → Scoring pipeline picks up newly researched contractors
  → Contact extraction runs on newly researched contractors
  → Hunter.io / Apollo enrichment for high-score leads (cost-efficient targeting)
```

---

## File Structure

```
backend/
  main.py                        # Uvicorn launcher (python main.py → starts API server)
  app/
    main.py                      # FastAPI app: lifespan, CORS, router registration, health check
    config.py                    # All settings: API keys, URLs, rate limits
    db/
      database.py                # SQLAlchemy engine, session factory, init_db()
      models.py                  # Contractor, LeadInsight, Contact ORM models
    pipeline/
      scraper.py                 # GAF scraper (Coveo interception + profile pages)
      prompts.py                 # Prompt templates — Perplexity research + OpenAI scoring
      research.py                # Perplexity API client (async batch, retries)
      scoring.py                 # OpenAI scoring engine (deterministic + LLM hybrid)
      contact_enrichment.py      # Contact extraction (provider-based, extensible)
      enricher.py                # Orchestrator (DB ↔ all engines)
      cli.py                     # CLI: ingest, research, score, contacts, status
    api/
      schemas.py                 # Pydantic request/response models (11 schemas)
      leads.py                   # GET /api/leads, /api/leads/{id}, /api/stats
      pipeline.py                # POST /api/pipeline/scrape, /enrich; GET /status
    services/
      lead_service.py            # DB query helpers: filtering, sorting, pagination, stats
  tests/
    conftest.py                  # Shared fixtures: in-memory SQLite, session rollback
    test_lead_service.py         # 25 tests for lead_service query functions
    test_api.py                  # 19 tests for FastAPI endpoints (TestClient + StaticPool)
  data/
    leads.db                     # SQLite database (created on first run)
    sample_contractors.json      # Sample data for testing without the scraper
  .env                           # API keys (PERPLEXITY_API_KEY, OPENAI_API_KEY)
  .env.example                   # Template for .env
  pyproject.toml                 # Dependencies
```

---

## Quick Start

```bash
cd backend

# 1. Set up environment
cp .env.example .env
# Edit .env with your PERPLEXITY_API_KEY and OPENAI_API_KEY

# 2. Run the scraper (requires Playwright browsers installed)
uv run python -m app.pipeline.scraper

# 3. Run the full enrichment pipeline
uv run python -m app.pipeline.cli research      # Stage 2: Perplexity research
uv run python -m app.pipeline.cli score          # Stage 3: OpenAI scoring
uv run python -m app.pipeline.cli contacts       # Stage 4: Contact extraction

# 4. Check status
uv run python -m app.pipeline.cli status

# 5. Start the API server
uv run python main.py
# Server runs at http://localhost:8000
# Interactive docs at http://localhost:8000/docs

# Alternative: skip scraper, ingest sample data and run research
uv run python -m app.pipeline.cli ingest data/sample_contractors.json --research
```

### CLI Commands Reference

| Command | Description | Key Flags |
|---|---|---|
| `ingest <file>` | Import contractors from JSON | `--research` (auto-run research after), `--concurrency N` |
| `research` | Perplexity research on unenriched contractors | `--force` (re-research all), `--limit N`, `--concurrency N` (default 3) |
| `score` | OpenAI scoring on researched contractors | `--force` (re-score all), `--limit N`, `--concurrency N` (default 5) |
| `contacts` | Extract decision-maker contacts from research | `--force` (re-extract all), `--limit N`, `--concurrency N` (default 5) |
| `status` | Show pipeline progress summary | — |

The CLI and REST API share the same database — you can use the CLI to run pipeline stages and the API to query/display results. The API also exposes `POST /api/pipeline/scrape` and `POST /api/pipeline/enrich` endpoints as alternatives to the CLI commands.
