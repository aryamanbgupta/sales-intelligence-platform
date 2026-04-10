"""
GAF Contractor Directory Scraper

Scrapes contractor data from GAF's public directory. The site is JS-rendered
and protected by Akamai bot detection, so we use Playwright to load the page.
Under the hood, GAF uses Coveo search-as-a-service — we intercept the Coveo
API calls to get clean, structured JSON instead of parsing DOM elements.

Flow:
  1. Launch headless Chromium with stealth settings
  2. Navigate to GAF search URL with postalCode & distance params
  3. Intercept the Coveo REST API response (contractor data as JSON)
  4. Extract the Bearer token and geo-coordinates from the first request
  5. Make additional paginated API calls directly to Coveo to fetch all results
  6. Parse each result into a flat contractor dict
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx
from playwright.async_api import async_playwright, Response

from app.config import (
    COVEO_API_URL,
    COVEO_ORG_ID,
    COVEO_PIPELINE,
    GAF_BASE_URL,
    SCRAPER_RESULTS_PER_PAGE,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stealth JS — injected before every page load to avoid bot detection
# ---------------------------------------------------------------------------
_STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.chrome = { runtime: {} };
const _origQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (p) =>
    p.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : _origQuery(p);
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
"""


# ---------------------------------------------------------------------------
# Data container for the intercepted Coveo first-call context
# ---------------------------------------------------------------------------
@dataclass
class _CoveoContext:
    """Captures auth + query context from the first Coveo call the page makes."""
    bearer_token: str = ""
    request_body: dict = field(default_factory=dict)
    first_results: list[dict] = field(default_factory=list)
    total_count: int = 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
async def scrape_contractors(
    zip_code: str = "10013",
    distance: int = 25,
) -> list[dict[str, Any]]:
    """
    Scrape all residential contractors from GAF's directory for a given ZIP code.

    Returns a list of dicts, one per contractor, with these keys:
        gaf_id, name, address, city, state, zip_code, phone, website,
        certification, certifications_raw, rating, review_count,
        latitude, longitude, distance_miles, profile_url, image_url
    """
    logger.info("Starting GAF scrape for ZIP %s, distance %d mi", zip_code, distance)

    ctx = await _load_initial_page(zip_code, distance)
    if not ctx.bearer_token:
        raise RuntimeError("Failed to capture Coveo API credentials from GAF page")

    logger.info(
        "Coveo context captured: %d total contractors, token=...%s",
        ctx.total_count, ctx.bearer_token[-8:],
    )

    # Fetch remaining pages via direct Coveo API calls
    all_raw = list(ctx.first_results)
    fetched = len(all_raw)

    async with httpx.AsyncClient(timeout=30.0) as client:
        while fetched < ctx.total_count:
            page_results = await _fetch_coveo_page(
                client, ctx.bearer_token, ctx.request_body, first_result=fetched,
            )
            if not page_results:
                break
            all_raw.extend(page_results)
            fetched = len(all_raw)
            logger.info("Fetched %d / %d contractors", fetched, ctx.total_count)
            await asyncio.sleep(0.5)  # polite delay

    # Parse into clean dicts
    contractors = [_parse_contractor(r) for r in all_raw]
    logger.info("Scraping complete: %d contractors parsed", len(contractors))
    return contractors


# ---------------------------------------------------------------------------
# Step 1: Playwright loads the page and intercepts the Coveo call
# ---------------------------------------------------------------------------
async def _load_initial_page(zip_code: str, distance: int) -> _CoveoContext:
    ctx = _CoveoContext()

    async def _on_request(request):
        if "platform.cloud.coveo.com/rest/search" in request.url and request.method == "POST":
            ctx.bearer_token = request.headers.get("authorization", "").replace("Bearer ", "")
            post = request.post_data
            if post:
                try:
                    ctx.request_body = json.loads(post)
                except json.JSONDecodeError:
                    pass

    async def _on_response(response: Response):
        if "platform.cloud.coveo.com/rest/search" in response.url and response.status == 200:
            try:
                body = await response.json()
                if "results" in body and not ctx.first_results:
                    ctx.first_results = body["results"]
                    ctx.total_count = body.get("totalCount", 0)
            except Exception:
                pass

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        browser_ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1440, "height": 900},
            locale="en-US",
            timezone_id="America/New_York",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Sec-CH-UA": '"Google Chrome";v="131", "Chromium";v="131"',
                "Sec-CH-UA-Mobile": "?0",
                "Sec-CH-UA-Platform": '"macOS"',
            },
        )
        await browser_ctx.add_init_script(_STEALTH_JS)
        page = await browser_ctx.new_page()
        page.on("request", _on_request)
        page.on("response", _on_response)

        url = f"{GAF_BASE_URL}?postalCode={zip_code}&countryCode=us&user=true&distance={distance}"
        logger.info("Loading %s", url)
        await page.goto(url, wait_until="networkidle", timeout=60_000)

        # Give Coveo a moment to fire its search request
        await asyncio.sleep(3)
        await browser.close()

    return ctx


# ---------------------------------------------------------------------------
# Step 2: Paginated Coveo API calls (direct HTTP, no browser)
# ---------------------------------------------------------------------------
async def _fetch_coveo_page(
    client: httpx.AsyncClient,
    bearer_token: str,
    base_body: dict,
    first_result: int,
) -> list[dict]:
    body = {**base_body}
    body["firstResult"] = first_result
    body["numberOfResults"] = SCRAPER_RESULTS_PER_PAGE
    # Remove analytics to avoid noise
    body.pop("analytics", None)

    resp = await client.post(
        f"{COVEO_API_URL}?organizationId={COVEO_ORG_ID}",
        json=body,
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("results", [])


# ---------------------------------------------------------------------------
# Step 3: Parse a Coveo result into a clean contractor dict
# ---------------------------------------------------------------------------
def _parse_contractor(result: dict) -> dict[str, Any]:
    raw = result.get("raw", {})

    # Extract the highest-tier certification label
    certs_raw = raw.get("gaf_f_contractor_certifications_and_awards_residential", [])
    certification = _pick_top_certification(certs_raw)

    # Build a readable address from components
    city = raw.get("gaf_f_city", "")
    state = raw.get("gaf_f_state_code", "")
    zip_code = raw.get("gaf_postal_code", "")
    address = ", ".join(filter(None, [city, state, zip_code]))

    return {
        "gaf_id": str(raw.get("gaf_contractor_id", "")),
        "name": raw.get("gaf_navigation_title", result.get("title", "")),
        "address": address,
        "city": city,
        "state": state,
        "zip_code": zip_code,
        "phone": raw.get("gaf_phone", ""),
        "website": "",  # Not in Coveo results; enrichment will find this
        "certification": certification,
        "certifications_raw": json.dumps(certs_raw),
        "rating": raw.get("gaf_rating", 0.0),
        "review_count": raw.get("gaf_number_of_reviews", 0),
        "services": json.dumps(
            raw.get("gaf_f_contractor_specialties_residential", [])
            + raw.get("gaf_f_contractor_technologies_residential", [])
        ),
        "latitude": raw.get("gaf_latitude"),
        "longitude": raw.get("gaf_longitude"),
        "distance_miles": round(raw.get("distanceinmiles", 0), 2),
        "profile_url": raw.get("uri", ""),
        "image_url": raw.get("gaf_featured_image_src", ""),
    }


def _pick_top_certification(certs: list[str]) -> str:
    """Return the highest-tier GAF certification from a list."""
    # Priority order (highest to lowest)
    tiers = [
        ("President's Club", "President's Club"),
        ("Master Elite", "Master Elite"),
        ("Certified Plus", "Certified Plus"),
        ("Certified", "Certified"),
    ]
    for keyword, label in tiers:
        for cert in certs:
            if keyword.lower() in cert.lower():
                return label
    return certs[0] if certs else "Uncertified"


# ---------------------------------------------------------------------------
# Step 4: Upsert scraped data into the database
# ---------------------------------------------------------------------------
def store_contractors(contractors: list[dict[str, Any]]) -> dict[str, int]:
    """
    Upsert scraped contractors into the database.
    Uses gaf_id as the dedupe key — existing rows are updated, new ones inserted.

    Returns: {"new": N, "updated": M, "total": N+M}
    """
    from app.db.database import SessionLocal, init_db
    from app.db.models import Contractor

    init_db()
    session = SessionLocal()
    new_count = 0
    updated_count = 0

    try:
        for data in contractors:
            existing = session.query(Contractor).filter_by(gaf_id=data["gaf_id"]).first()
            if existing:
                # Update mutable fields
                for key in [
                    "name", "address", "city", "state", "zip_code", "phone",
                    "website", "certification", "certifications_raw", "rating",
                    "review_count", "services", "latitude", "longitude",
                    "distance_miles", "profile_url", "image_url",
                ]:
                    setattr(existing, key, data.get(key))
                existing.scraped_at = _utcnow()
                updated_count += 1
            else:
                contractor = Contractor(
                    gaf_id=data["gaf_id"],
                    name=data["name"],
                    address=data.get("address", ""),
                    city=data.get("city", ""),
                    state=data.get("state", ""),
                    zip_code=data.get("zip_code", ""),
                    phone=data.get("phone", ""),
                    website=data.get("website", ""),
                    certification=data.get("certification", ""),
                    certifications_raw=data.get("certifications_raw", "[]"),
                    rating=data.get("rating"),
                    review_count=data.get("review_count"),
                    services=data.get("services", "[]"),
                    latitude=data.get("latitude"),
                    longitude=data.get("longitude"),
                    distance_miles=data.get("distance_miles"),
                    profile_url=data.get("profile_url", ""),
                    image_url=data.get("image_url", ""),
                )
                session.add(contractor)
                new_count += 1

        session.commit()
        logger.info("Stored contractors: %d new, %d updated", new_count, updated_count)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    return {"new": new_count, "updated": updated_count, "total": new_count + updated_count}


def _utcnow():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Step 5: Scrape individual profile pages for website + details
# ---------------------------------------------------------------------------
async def scrape_profile_details(
    profile_urls: list[dict[str, str]],
    concurrency: int = 3,
) -> list[dict[str, Any]]:
    """
    Visit each contractor's GAF profile page to extract:
      - website URL (from JSON-LD sameAs or "Visit Website" link)
      - years in business (from "In business since YYYY")
      - about text (company description)

    Args:
        profile_urls: list of {"gaf_id": "...", "profile_url": "https://..."} dicts
        concurrency: max pages to scrape in parallel

    Returns:
        list of {"gaf_id", "website", "years_in_business", "about"} dicts
    """
    if not profile_urls:
        return []

    logger.info("Scraping %d profile pages (concurrency=%d)", len(profile_urls), concurrency)
    results = []
    sem = asyncio.Semaphore(concurrency)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1440, "height": 900},
            locale="en-US",
            timezone_id="America/New_York",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Sec-CH-UA": '"Google Chrome";v="131", "Chromium";v="131"',
                "Sec-CH-UA-Mobile": "?0",
                "Sec-CH-UA-Platform": '"macOS"',
            },
        )
        await context.add_init_script(_STEALTH_JS)

        async def _scrape_one(entry: dict) -> dict | None:
            async with sem:
                gaf_id = entry["gaf_id"]
                url = entry["profile_url"]
                try:
                    page = await context.new_page()
                    resp = await page.goto(url, wait_until="networkidle", timeout=30_000)
                    if resp.status != 200:
                        logger.warning("Profile %s returned %d", gaf_id, resp.status)
                        await page.close()
                        return None

                    detail = {"gaf_id": gaf_id, "website": "", "years_in_business": None, "about": ""}

                    # --- Extract website ---
                    # Priority 1: "Visit Website" link (most reliable — it's the actual website)
                    visit_link = await page.query_selector('a:has-text("Visit Website")')
                    if visit_link:
                        detail["website"] = await visit_link.get_attribute("href") or ""

                    # Priority 2: JSON-LD sameAs, filtering out social media
                    if not detail["website"]:
                        social_domains = [
                            "facebook.com", "instagram.com", "twitter.com", "x.com",
                            "youtube.com", "linkedin.com", "pinterest.com", "yelp.com",
                            "tiktok.com", "nextdoor.com",
                        ]
                        json_ld_scripts = await page.query_selector_all('script[type="application/ld+json"]')
                        for script in json_ld_scripts:
                            try:
                                text = await script.inner_text()
                                data = json.loads(text)
                                if data.get("@type") == "Organization":
                                    same_as = data.get("sameAs", [])
                                    if isinstance(same_as, str):
                                        same_as = [same_as]
                                    for url in same_as:
                                        if not any(d in url.lower() for d in social_domains):
                                            detail["website"] = url
                                            break
                            except (json.JSONDecodeError, Exception):
                                pass

                    # --- Extract years in business ---
                    details_section = await page.query_selector('[data-module="contractor-details"]')
                    if details_section:
                        details_text = await details_section.inner_text()
                        since_match = re.search(r"(?:since|Since)\s+(\d{4})", details_text)
                        if since_match:
                            founded_year = int(since_match.group(1))
                            detail["years_in_business"] = datetime.now().year - founded_year

                    # --- Extract about text ---
                    about_section = await page.query_selector('.contractor-about__description, [class*="about"] p')
                    if about_section:
                        detail["about"] = (await about_section.inner_text()).strip()
                    if not detail["about"]:
                        # Try the broader approach
                        about_el = await page.query_selector('section:has(h2:has-text("About")) p')
                        if about_el:
                            detail["about"] = (await about_el.inner_text()).strip()

                    await page.close()
                    logger.info(
                        "Profile %s: website=%s, years=%s",
                        gaf_id,
                        detail["website"][:40] if detail["website"] else "(none)",
                        detail["years_in_business"],
                    )
                    return detail
                except Exception as e:
                    logger.warning("Error scraping profile %s: %s", gaf_id, e)
                    return None

        tasks = [_scrape_one(entry) for entry in profile_urls]
        raw_results = await asyncio.gather(*tasks)
        results = [r for r in raw_results if r is not None]

        await browser.close()

    logger.info("Profile scraping complete: %d/%d succeeded", len(results), len(profile_urls))
    return results


def update_profile_details(details: list[dict[str, Any]]) -> int:
    """Update contractors in the database with profile page details."""
    from app.db.database import SessionLocal, init_db
    from app.db.models import Contractor

    init_db()
    session = SessionLocal()
    updated = 0

    try:
        for d in details:
            contractor = session.query(Contractor).filter_by(gaf_id=d["gaf_id"]).first()
            if contractor:
                if d.get("website"):
                    contractor.website = d["website"]
                if d.get("years_in_business") is not None:
                    contractor.years_in_business = d["years_in_business"]
                if d.get("about"):
                    contractor.about = d["about"]
                contractor.updated_at = _utcnow()
                updated += 1
        session.commit()
        logger.info("Updated %d contractors with profile details", updated)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    return updated


# ---------------------------------------------------------------------------
# CLI entrypoint for standalone testing
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    async def _main():
        # Step 1: Scrape contractor listings from Coveo
        contractors = await scrape_contractors(zip_code="10013", distance=25)
        print(f"\n{'='*60}")
        print(f"Scraped {len(contractors)} contractors from listings")
        print(f"{'='*60}\n")

        # Step 2: Store in database
        result = store_contractors(contractors)
        print(f"Database: {result['new']} new, {result['updated']} updated")

        # Step 3: Scrape profile pages for website + years in business
        profile_entries = [
            {"gaf_id": c["gaf_id"], "profile_url": c["profile_url"]}
            for c in contractors if c.get("profile_url")
        ]
        print(f"\nScraping {len(profile_entries)} profile pages for details...")
        details = await scrape_profile_details(profile_entries, concurrency=3)
        updated = update_profile_details(details)
        print(f"Updated {updated} contractors with website/years/about")

        # Summary
        websites = sum(1 for d in details if d.get("website"))
        years = sum(1 for d in details if d.get("years_in_business") is not None)
        abouts = sum(1 for d in details if d.get("about"))
        print(f"\nProfile data: {websites} websites, {years} years-in-business, {abouts} about texts")

        # Print sample
        for c in contractors[:3]:
            d = next((x for x in details if x["gaf_id"] == c["gaf_id"]), {})
            print(f"\n  {c['name']}")
            print(f"    Website: {d.get('website', '(none)')}")
            print(f"    Years: {d.get('years_in_business', '(none)')}")

    asyncio.run(_main())
