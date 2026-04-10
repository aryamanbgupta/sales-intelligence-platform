# Pipeline Documentation

## Overview

The data pipeline collects and enriches roofing contractor leads in three stages:

1. **Scrape** — Pull contractor listings from GAF's public directory via Coveo API interception, then visit each profile page for additional details
2. **Research** — Query Perplexity (sonar-pro) for web-sourced intelligence on each contractor: reputation, growth signals, supplier relationships, market context
3. **Score** — *(next stage)* Feed scraped data + research into OpenAI to produce structured lead scores, talking points, and outreach drafts

Stages are decoupled. Each can be re-run independently — re-scrape without losing research, re-research without re-scraping, re-score without re-researching. All data is stored in SQLite at `backend/data/leads.db`.

```
  GAF Website                   Perplexity API                  OpenAI API
      │                              │                              │
      ▼                              ▼                              ▼
  ┌────────┐    contractors    ┌──────────┐    lead_insights   ┌──────────┐
  │Scraper │───────────────▶   │Research  │───────────────▶    │ Scoring  │
  │        │    table          │ Engine   │    table            │ (TBD)   │
  └────────┘                   └──────────┘                    └──────────┘
  Playwright +                  Async batch                     Structured
  Coveo API                     w/ retries                      JSON output
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
| Online Reputation | Google review themes, BBB rating, Angi/HomeAdvisor/Yelp/Houzz ratings, press coverage |
| Business Health & Growth | Company size, hiring activity, expansion signals, social media trends |
| Website Analysis | Services featured, material brands mentioned, careers page, site quality (only when website URL available) |
| Market & Weather Context | Recent severe weather in service area, local roofing demand, seasonal patterns |
| Supplier & Material Intelligence | Current material suppliers, product lines used, delivery complaints, job volume, buying groups |
| Competitive Positioning | Market position, differentiators, competitors, unique selling proposition |

The prompt adapts based on data availability — if we already know years in business, it doesn't ask; if no website is available, it asks Perplexity to search for one.

### Architecture

```
app/pipeline/
  prompts.py     # Prompt templates — system prompt + dynamic research prompt builder
  research.py    # Perplexity API client — async batch processing, retries, rate limiting
  enricher.py    # Orchestrator — connects research engine to the database
  cli.py         # CLI entry point for all pipeline operations
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

Populated by the research engine (and later, the scoring stage). One row per contractor (FK to `contractors.id`, UNIQUE constraint).

| Column | Type | Populated By | Description |
|---|---|---|---|
| `id` | INTEGER PK | DB | Auto-increment |
| `contractor_id` | INTEGER FK UNIQUE | Research | References `contractors.id` |
| `research_summary` | TEXT | Research | Perplexity research output (full text) |
| `citations` | TEXT (JSON) | Research | Array of source URLs from Perplexity |
| `lead_score` | INTEGER | Scoring | 0–100 composite score |
| `score_breakdown` | TEXT (JSON) | Scoring | `{certification: 25, reviews: 18, ...}` |
| `talking_points` | TEXT (JSON) | Scoring | Array of sales talking points |
| `buying_signals` | TEXT (JSON) | Scoring | Array of buying signals |
| `pain_points` | TEXT (JSON) | Scoring | Array of pain points |
| `recommended_pitch` | TEXT | Scoring | Suggested pitch text |
| `why_now` | TEXT | Scoring | Time-sensitive signal |
| `draft_email` | TEXT | Scoring | Generated outreach email |
| `enriched_at` | DATETIME | Research | When enrichment last ran |
| `created_at` | DATETIME | DB | Row creation time |
| `updated_at` | DATETIME | DB | Last update time |

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
    → Worker 1: scrape("10013", 50) → store → scrape profiles → research
    → Worker 2: scrape("90210", 50) → store → scrape profiles → research
    → ...
  → All results land in shared Postgres
  → Scoring pipeline picks up newly researched contractors
```

---

## File Structure

```
backend/
  app/
    config.py                    # All settings: API keys, URLs, rate limits
    db/
      database.py                # SQLAlchemy engine, session factory, init_db()
      models.py                  # Contractor + LeadInsight ORM models
    pipeline/
      scraper.py                 # GAF scraper (Coveo interception + profile pages)
      prompts.py                 # Perplexity prompt templates
      research.py                # Perplexity API client (async batch, retries)
      enricher.py                # Orchestrator (DB ↔ research engine)
      cli.py                     # CLI: ingest, research, status commands
    api/                         # (placeholder for FastAPI endpoints)
    services/                    # (placeholder for query helpers)
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
# Edit .env with your API keys

# 2. Run the scraper (requires Playwright browsers installed)
uv run python -m app.pipeline.scraper

# 3. Run Perplexity research on all scraped contractors
uv run python -m app.pipeline.cli research

# 4. Check status
uv run python -m app.pipeline.cli status

# Alternative: skip scraper, ingest sample data and research it
uv run python -m app.pipeline.cli ingest data/sample_contractors.json --research
```
