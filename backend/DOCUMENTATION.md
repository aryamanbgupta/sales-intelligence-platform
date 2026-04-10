# GAF Contractor Scraper — Documentation

## Overview

The scraper pulls residential roofing contractor data from GAF's public directory ([gaf.com/en-us/roofing-contractors/residential](https://www.gaf.com/en-us/roofing-contractors/residential)) for a given ZIP code and radius. It runs in two phases:

1. **Listing scrape** — Fetches all contractors from the search results via Coveo API interception
2. **Profile scrape** — Visits each contractor's profile page to extract website URL, years in business, and company description

Results are stored in a SQLite database at `backend/data/leads.db`.

---

## How It Works

### Phase 1: Listing Scrape (Coveo API Interception)

GAF's website is JS-rendered and protected by Akamai bot detection (returns 403 to plain HTTP requests). Under the hood, the contractor search is powered by **Coveo** (a search-as-a-service platform). We exploit this:

1. **Playwright** launches headless Chromium with stealth settings (spoofed `navigator.webdriver`, realistic user-agent, etc.) to bypass Akamai
2. The browser navigates to `https://www.gaf.com/en-us/roofing-contractors/residential?postalCode={zip}&countryCode=us&user=true&distance={miles}`
3. The page fires a POST request to `https://platform.cloud.coveo.com/rest/search/v2` — we **intercept** this request to capture:
   - The Bearer token (Coveo API key)
   - The full request body (includes resolved lat/lng coordinates, field list, facets)
   - The first page of results (10 contractors)
4. We then make **direct HTTP calls** to the Coveo API (no browser needed) to paginate through all results, using `firstResult` offset and `numberOfResults=50`

This hybrid approach is fast (~15 seconds for 76 contractors) and returns clean, structured JSON.

### Phase 2: Profile Scrape

The Coveo listing API doesn't include website URLs, years in business, or company descriptions. These live on individual profile pages. For each contractor:

1. Playwright visits the profile page (e.g. `/roofing-contractors/residential/usa/ny/new-hyde-park/preferred-exterior-corp-1004859`)
2. Extracts the **website URL** from the "Visit Website" link (preferred) or JSON-LD `sameAs` field (filtered to exclude social media)
3. Extracts **years in business** from the "In business since YYYY" text in the details section
4. Extracts the **about text** from the company description section

Profile pages are scraped 3 at a time (configurable concurrency) to be polite. The full run takes ~2-3 minutes for 76 contractors.

---

## How to Run

```bash
cd backend
uv run python -m app.pipeline.scraper
```

This runs both phases and stores everything in the database. Output:

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

# Phase 1: Scrape listings
contractors = await scrape_contractors(zip_code="10013", distance=25)
store_contractors(contractors)

# Phase 2: Scrape profile details
profile_entries = [
    {"gaf_id": c["gaf_id"], "profile_url": c["profile_url"]}
    for c in contractors if c.get("profile_url")
]
details = await scrape_profile_details(profile_entries, concurrency=3)
update_profile_details(details)
```

---

## Database Schema

### Table: `contractors`

This is the primary table that the enrichment pipeline (Perplexity research + OpenAI scoring) should use as input.

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
| `rating` | REAL | Google star rating (0-5). Null for ~7 contractors with no reviews | Coveo API |
| `review_count` | INTEGER | Number of Google reviews. Null for ~7 contractors | Coveo API |
| `services` | TEXT (JSON) | JSON array of specialties (e.g. "Solar", "Metal", "FORTIFIED Roof") | Coveo API |
| `latitude` | REAL | Geo latitude | Coveo API |
| `longitude` | REAL | Geo longitude | Coveo API |
| `distance_miles` | REAL | Distance from search ZIP in miles | Coveo API |
| `years_in_business` | INTEGER | Calculated from "In business since YYYY". Null if not listed | Profile page |
| `about` | TEXT | Company description from profile. Empty if not listed | Profile page |
| `profile_url` | TEXT | Full GAF profile page URL | Coveo API |
| `image_url` | TEXT | Profile image/logo URL | Coveo API |
| `scraped_at` | DATETIME | When this record was last scraped | Auto |
| `created_at` | DATETIME | Row creation time | Auto |
| `updated_at` | DATETIME | Last update time | Auto |

### Table: `lead_insights`

Stores AI-generated enrichment data. One row per contractor (FK to `contractors.id`). Initially empty — populated by the enrichment pipeline.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `contractor_id` | INTEGER FK UNIQUE | References `contractors.id` |
| `research_summary` | TEXT | Perplexity research output |
| `citations` | TEXT (JSON) | Array of source URLs from Perplexity |
| `lead_score` | INTEGER | 0-100 score from OpenAI |
| `score_breakdown` | TEXT (JSON) | `{certification: 25, reviews: 18, ...}` |
| `talking_points` | TEXT (JSON) | Array of sales talking points |
| `buying_signals` | TEXT (JSON) | Array of buying signals |
| `pain_points` | TEXT (JSON) | Array of pain points |
| `recommended_pitch` | TEXT | Suggested pitch text |
| `why_now` | TEXT | Time-sensitive signal |
| `draft_email` | TEXT | Generated outreach email |
| `enriched_at` | DATETIME | When enrichment ran |

---

## Data Coverage (ZIP 10013, 25mi radius)

| Field | Coverage | Notes |
|---|---|---|
| gaf_id, name, city, state, zip, phone | 76/76 (100%) | Always present |
| certification | 76/76 (100%) | 68 Master Elite, 11 President's Club |
| rating + review_count | 69/76 (91%) | 7 contractors have no Google reviews |
| website | 44/76 (58%) | ~30 contractors don't list a website on GAF |
| years_in_business | 46/76 (61%) | ~30 contractors don't list founding year |
| about (description) | 48/76 (63%) | Some profiles have no description |
| lat/lng, distance, profile_url | 76/76 (100%) | Always present |

---

## Using Scraped Data for Enrichment (Perplexity Research)

The enrichment pipeline should query contractors that **don't yet have insights**:

```python
from app.db.database import SessionLocal
from app.db.models import Contractor, LeadInsight

session = SessionLocal()

# Get contractors without enrichment data
unenriched = (
    session.query(Contractor)
    .outerjoin(LeadInsight)
    .filter(LeadInsight.id == None)
    .all()
)

for contractor in unenriched:
    # Build the Perplexity research prompt using scraped data
    prompt = f'''
    Research "{contractor.name}" roofing contractor located at {contractor.address}.
    Phone: {contractor.phone}
    Website: {contractor.website or "unknown"}
    GAF Certification: {contractor.certification}
    Google Rating: {contractor.rating} ({contractor.review_count} reviews)
    Years in Business: {contractor.years_in_business or "unknown"}

    Find: company overview, Google review sentiment, recent projects,
    news mentions, storm activity in area, growth signals, BBB rating.
    '''
    # ... send to Perplexity API ...
```

Key fields for enrichment quality:
- **`name` + `address`** — primary identifiers for web research
- **`website`** — if available, Perplexity can analyze the contractor's site
- **`certification`** — context for scoring (Master Elite = top tier)
- **`rating` + `review_count`** — proxies for business volume
- **`years_in_business`** — business maturity signal

---

## What We Don't Scrape

| Field | Why | Where to get it |
|---|---|---|
| State license ID | Not on GAF's site | State licensing board databases, or Perplexity can research it |
| Full street address | GAF only shows city/state/ZIP | Google Places API or Perplexity research |
| Revenue / employee count | Not public | Perplexity research, LinkedIn, or Crunchbase |
| Google review text | On GAF profile but not worth the scraping time | Google Places API or Perplexity |

---

## Architecture Notes

- **Stealth**: Playwright injects JS to override `navigator.webdriver`, `chrome.runtime`, and `navigator.plugins` to appear as a real browser
- **Upsert**: Re-running the scraper updates existing records (matched by `gaf_id`) without creating duplicates
- **Pagination**: The Coveo API returns 10 results per page by default; we request 50 per page for efficiency
- **Concurrency**: Profile pages are scraped 3 at a time to avoid overwhelming GAF's servers
- **Error isolation**: A single profile page failure doesn't stop the batch — errors are logged and skipped

### File Locations

```
backend/
  app/
    config.py                  # GAF/Coveo URLs, scraper settings
    pipeline/
      scraper.py               # Main scraper module (listings + profiles)
    db/
      database.py              # SQLAlchemy engine, session, init_db()
      models.py                # Contractor + LeadInsight ORM models
  data/
    leads.db                   # SQLite database (created on first run)
```
