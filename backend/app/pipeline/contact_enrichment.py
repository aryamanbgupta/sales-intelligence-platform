"""
Contact enrichment — extract and enrich decision-maker contacts.

This module provides a provider-based architecture for finding contacts:

  1. PerplexityExtractor (implemented) — Parses the research text that
     Perplexity already generated to extract structured contact data using
     a lightweight OpenAI call.

  2. HunterIOProvider (stub) — Looks up email addresses by domain via
     the Hunter.io API. Ready to plug in with an API key.

  3. Custom providers — Add new providers by implementing `find_contacts()`
     and registering in PROVIDER_REGISTRY.

Usage:
    from app.pipeline.contact_enrichment import run_contact_extraction

    # Extract contacts from existing research for all contractors
    results = run_contact_extraction_sync(contractors, research_map)

    # With additional providers enabled
    results = run_contact_extraction_sync(
        contractors, research_map,
        providers=["perplexity_extract", "hunter_io"],
    )
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from openai import AsyncOpenAI, APIConnectionError, APIStatusError, RateLimitError

from app.config import (
    ENRICHMENT_DELAY_SECONDS,
    MAX_RETRIES,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    RETRY_BACKOFF_BASE,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ContactInfo:
    """A single extracted contact."""
    full_name: str
    title: str = ""
    email: str = ""
    phone: str = ""
    linkedin_url: str = ""
    source: str = ""       # which provider found this contact
    confidence: str = ""   # "high", "medium", "low"


@dataclass
class ContactExtractionResult:
    """Result from extracting contacts for one contractor."""
    contractor_id: int
    contractor_name: str
    contacts: list[ContactInfo] = field(default_factory=list)
    success: bool = True
    error: str | None = None
    duration_seconds: float = 0.0


@dataclass
class BatchContactReport:
    """Summary of a batch contact extraction run."""
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    total_contacts_found: int = 0
    results: list[ContactExtractionResult] = field(default_factory=list)
    total_duration_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Provider: Perplexity research text extraction (via OpenAI)
# ---------------------------------------------------------------------------

CONTACT_EXTRACTION_PROMPT = """\
Extract decision-maker contact information from the research text below.

Company: {company_name}
Location: {city}, {state}

Research text:
{research_text}

Extract ALL people mentioned who could be decision-makers at this company \
(owners, presidents, VPs, managers, principals, registered agents, etc.)

For each person, extract whatever is available:
- full_name: their full name
- title: their role/title at the company
- email: their email address (only if explicitly stated)
- phone: their direct phone (only if explicitly stated and different from company phone)
- linkedin_url: their LinkedIn profile URL (only if explicitly stated)
- source: where in the research this info was found (e.g., "D&B listing", "BBB profile", "NY Secretary of State")
- confidence: "high" if name + title from authoritative source (state records, BBB, D&B), \
"medium" if from reviews or website, "low" if inferred or uncertain

Respond with ONLY valid JSON — no markdown fences, no extra text:
{{"contacts": [
  {{"full_name": "...", "title": "...", "email": "...", "phone": "...", "linkedin_url": "...", "source": "...", "confidence": "..."}},
  ...
]}}

If NO contacts were found in the research text, respond with:
{{"contacts": []}}"""


async def extract_contacts_from_research(
    client: AsyncOpenAI,
    contractor: dict,
    research_text: str,
) -> ContactExtractionResult:
    """Extract structured contacts from Perplexity research text using OpenAI.

    This is a lightweight call — the research already contains the info,
    we just need OpenAI to parse it into structured JSON.
    """
    name = contractor.get("name", "Unknown")
    contractor_id = contractor.get("id", 0)
    start = time.monotonic()

    if not research_text or not research_text.strip():
        return ContactExtractionResult(
            contractor_id=contractor_id,
            contractor_name=name,
            contacts=[],
            success=True,
            duration_seconds=0.0,
        )

    prompt = CONTACT_EXTRACTION_PROMPT.format(
        company_name=name,
        city=contractor.get("city", ""),
        state=contractor.get("state", ""),
        research_text=research_text,
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content or ""
            parsed = json.loads(raw)
            raw_contacts = parsed.get("contacts", [])

            contacts = []
            for c in raw_contacts:
                full_name = (c.get("full_name") or "").strip()
                if not full_name:
                    continue
                contacts.append(ContactInfo(
                    full_name=full_name,
                    title=(c.get("title") or "").strip(),
                    email=(c.get("email") or "").strip(),
                    phone=(c.get("phone") or "").strip(),
                    linkedin_url=(c.get("linkedin_url") or "").strip(),
                    source=(c.get("source") or "perplexity_research").strip(),
                    confidence=(c.get("confidence") or "medium").strip(),
                ))

            duration = time.monotonic() - start
            logger.info(
                "Extracted %d contacts for '%s' in %.1fs",
                len(contacts), name, duration,
            )

            return ContactExtractionResult(
                contractor_id=contractor_id,
                contractor_name=name,
                contacts=contacts,
                success=True,
                duration_seconds=duration,
            )

        except json.JSONDecodeError as e:
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF_BASE ** attempt)
            else:
                duration = time.monotonic() - start
                return ContactExtractionResult(
                    contractor_id=contractor_id,
                    contractor_name=name,
                    success=False,
                    error=f"JSON parse error: {e}",
                    duration_seconds=duration,
                )

        except (RateLimitError, APIConnectionError) as e:
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF_BASE ** attempt)
            else:
                duration = time.monotonic() - start
                return ContactExtractionResult(
                    contractor_id=contractor_id,
                    contractor_name=name,
                    success=False,
                    error=str(e),
                    duration_seconds=duration,
                )

        except (APIStatusError, Exception) as e:
            duration = time.monotonic() - start
            return ContactExtractionResult(
                contractor_id=contractor_id,
                contractor_name=name,
                success=False,
                error=str(e),
                duration_seconds=duration,
            )

    duration = time.monotonic() - start
    return ContactExtractionResult(
        contractor_id=contractor_id,
        contractor_name=name,
        success=False,
        error="Exhausted retries",
        duration_seconds=duration,
    )


# ---------------------------------------------------------------------------
# Provider: Hunter.io (stub — ready to plug in)
# ---------------------------------------------------------------------------

# To enable Hunter.io:
#   1. Add HUNTER_API_KEY to config.py and .env
#   2. `uv add hunter-io` or use httpx directly
#   3. Implement the function below
#   4. Add "hunter_io" to PROVIDER_REGISTRY
#
# Hunter.io free tier: 25 searches/month
# Paid: starts at $49/mo for 500 searches
#
# API docs: https://hunter.io/api-documentation/v2
#
# Example implementation:
#
#   async def find_contacts_hunter(
#       client: httpx.AsyncClient,
#       contractor: dict,
#   ) -> ContactExtractionResult:
#       domain = _extract_domain(contractor.get("website", ""))
#       if not domain:
#           return ContactExtractionResult(...)  # skip, no website
#
#       resp = await client.get(
#           "https://api.hunter.io/v2/domain-search",
#           params={"domain": domain, "api_key": HUNTER_API_KEY},
#       )
#       data = resp.json()
#
#       contacts = []
#       for email_entry in data.get("data", {}).get("emails", []):
#           contacts.append(ContactInfo(
#               full_name=f"{email_entry.get('first_name', '')} {email_entry.get('last_name', '')}".strip(),
#               title=email_entry.get("position", ""),
#               email=email_entry.get("value", ""),
#               source="hunter_io",
#               confidence="high" if email_entry.get("confidence", 0) > 80 else "medium",
#           ))
#       return ContactExtractionResult(
#           contractor_id=contractor["id"],
#           contractor_name=contractor["name"],
#           contacts=contacts,
#           success=True,
#       )


def _extract_domain(url: str) -> str:
    """Extract bare domain from a URL. Utility for email lookup providers."""
    if not url:
        return ""
    url = url.strip().rstrip("/")
    # Remove protocol
    for prefix in ("https://www.", "http://www.", "https://", "http://"):
        if url.lower().startswith(prefix):
            url = url[len(prefix):]
            break
    # Remove path
    url = url.split("/")[0]
    return url.lower()


# ---------------------------------------------------------------------------
# Provider registry — add new providers here
# ---------------------------------------------------------------------------

# Each provider is a string key mapped to a callable that takes
# (AsyncOpenAI_client, contractor_dict, research_text) -> ContactExtractionResult
#
# To add a new provider:
#   1. Write an async function matching the signature above
#   2. Add it to this dict
#   3. Pass its key in the `providers` list when calling run_contact_extraction

PROVIDER_REGISTRY: Dict[str, str] = {
    "perplexity_extract": "extract_contacts_from_research",
    # "hunter_io": "find_contacts_hunter",      # uncomment when implemented
    # "apollo": "find_contacts_apollo",          # future
    # "rocketreach": "find_contacts_rocketreach", # future
}


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

async def run_contact_extraction(
    contractors: list[dict],
    research_map: dict[int, str],
    concurrency: int = 5,
    on_progress: Optional[Callable] = None,
) -> BatchContactReport:
    """Extract contacts for a batch of contractors.

    Args:
        contractors: list of dicts from Contractor.to_dict().
        research_map: {contractor_id: research_text} from lead_insights.
        concurrency: max parallel OpenAI calls.
        on_progress: optional callback(result, completed, total).
    """
    if not contractors:
        return BatchContactReport()

    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set. Add it to backend/.env")

    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    report = BatchContactReport(total=len(contractors))
    semaphore = asyncio.Semaphore(concurrency)
    start = time.monotonic()

    async def _process_one(contractor: dict, index: int) -> ContactExtractionResult:
        async with semaphore:
            if index > 0:
                await asyncio.sleep(ENRICHMENT_DELAY_SECONDS * 0.5)  # lighter delay for extraction

            contractor_id = contractor.get("id", index)
            research_text = research_map.get(contractor_id, "")

            result = await extract_contacts_from_research(
                client, contractor, research_text,
            )

            if result.success:
                report.succeeded += 1
                report.total_contacts_found += len(result.contacts)
            else:
                report.failed += 1

            if on_progress:
                completed = report.succeeded + report.failed
                on_progress(result, completed, report.total)

            return result

    tasks = [_process_one(c, i) for i, c in enumerate(contractors)]
    report.results = await asyncio.gather(*tasks)
    report.total_duration_seconds = time.monotonic() - start

    logger.info(
        "Contact extraction complete: %d/%d succeeded, %d contacts found in %.1fs",
        report.succeeded, report.total, report.total_contacts_found,
        report.total_duration_seconds,
    )

    return report


def run_contact_extraction_sync(
    contractors: list[dict],
    research_map: dict[int, str],
    concurrency: int = 5,
    on_progress: Optional[Callable] = None,
) -> BatchContactReport:
    """Synchronous wrapper for CLI usage."""
    return asyncio.run(
        run_contact_extraction(contractors, research_map, concurrency, on_progress)
    )
