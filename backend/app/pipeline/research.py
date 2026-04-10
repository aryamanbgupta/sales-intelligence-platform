"""
Perplexity research engine — Stage 1 of the enrichment pipeline.

Queries the Perplexity API (OpenAI-compatible) to gather web-sourced
intelligence about each roofing contractor. Designed for scalability:
    - Batch processing with configurable concurrency
    - Per-contractor error isolation (one failure doesn't stop the batch)
    - Exponential backoff on transient failures
    - Rate limiting between requests
    - Structured output: research text + citation URLs
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from openai import AsyncOpenAI, APIConnectionError, RateLimitError, APIStatusError

from app.config import (
    ENRICHMENT_DELAY_SECONDS,
    MAX_RETRIES,
    PERPLEXITY_API_KEY,
    PERPLEXITY_BASE_URL,
    PERPLEXITY_MAX_TOKENS,
    PERPLEXITY_MODEL,
    PERPLEXITY_TEMPERATURE,
    RETRY_BACKOFF_BASE,
)
from app.pipeline.prompts import PERPLEXITY_RESEARCH_SYSTEM, build_research_prompt

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ResearchResult:
    """Output from a single contractor research query."""
    contractor_id: int
    contractor_name: str
    research_summary: str
    citations: list[str] = field(default_factory=list)
    success: bool = True
    error: str | None = None
    duration_seconds: float = 0.0


@dataclass
class BatchResearchReport:
    """Summary of a full batch research run."""
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    results: list[ResearchResult] = field(default_factory=list)
    total_duration_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

def _build_client() -> AsyncOpenAI:
    """Build an async OpenAI-compatible client pointed at Perplexity."""
    if not PERPLEXITY_API_KEY:
        raise ValueError(
            "PERPLEXITY_API_KEY is not set. Add it to backend/.env"
        )
    return AsyncOpenAI(
        api_key=PERPLEXITY_API_KEY,
        base_url=PERPLEXITY_BASE_URL,
    )


# ---------------------------------------------------------------------------
# Single contractor research
# ---------------------------------------------------------------------------

async def research_contractor(
    client: AsyncOpenAI,
    contractor: dict,
    contractor_id: int,
) -> ResearchResult:
    """Run Perplexity research for a single contractor with retry logic.

    Args:
        client: AsyncOpenAI client configured for Perplexity.
        contractor: dict with contractor fields (name, address, etc.)
        contractor_id: database ID for tracking.

    Returns:
        ResearchResult with research text and citations.
    """
    name = contractor.get("name", "Unknown")
    prompt = build_research_prompt(contractor)
    start = time.monotonic()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                model=PERPLEXITY_MODEL,
                messages=[
                    {"role": "system", "content": PERPLEXITY_RESEARCH_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=PERPLEXITY_MAX_TOKENS,
                temperature=PERPLEXITY_TEMPERATURE,
            )

            # Extract research text
            research_text = response.choices[0].message.content or ""

            # Extract citations from Perplexity's response metadata.
            # Perplexity returns citations in the response object.
            citations = _extract_citations(response)

            duration = time.monotonic() - start
            logger.info(
                f"Researched '{name}' in {duration:.1f}s "
                f"({len(citations)} citations, {len(research_text)} chars)"
            )

            return ResearchResult(
                contractor_id=contractor_id,
                contractor_name=name,
                research_summary=research_text,
                citations=citations,
                success=True,
                duration_seconds=duration,
            )

        except (RateLimitError, APIConnectionError) as e:
            # Transient — retry with backoff
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_BASE ** attempt
                logger.warning(
                    f"Transient error for '{name}' (attempt {attempt}/{MAX_RETRIES}), "
                    f"retrying in {wait:.1f}s: {e}"
                )
                await asyncio.sleep(wait)
            else:
                duration = time.monotonic() - start
                logger.error(f"Failed to research '{name}' after {MAX_RETRIES} attempts: {e}")
                return ResearchResult(
                    contractor_id=contractor_id,
                    contractor_name=name,
                    research_summary="",
                    success=False,
                    error=str(e),
                    duration_seconds=duration,
                )

        except APIStatusError as e:
            # Non-transient API error (400, 401, etc.) — don't retry
            duration = time.monotonic() - start
            logger.error(f"API error for '{name}': {e.status_code} {e.message}")
            return ResearchResult(
                contractor_id=contractor_id,
                contractor_name=name,
                research_summary="",
                success=False,
                error=f"API {e.status_code}: {e.message}",
                duration_seconds=duration,
            )

        except Exception as e:
            duration = time.monotonic() - start
            logger.error(f"Unexpected error researching '{name}': {e}")
            return ResearchResult(
                contractor_id=contractor_id,
                contractor_name=name,
                research_summary="",
                success=False,
                error=str(e),
                duration_seconds=duration,
            )

    # Should never reach here due to the return in the retry loop,
    # but satisfy the type checker
    duration = time.monotonic() - start
    return ResearchResult(
        contractor_id=contractor_id,
        contractor_name=name,
        research_summary="",
        success=False,
        error="Exhausted retries",
        duration_seconds=duration,
    )


def _extract_citations(response) -> list[str]:
    """Extract citation URLs from Perplexity's response.

    Perplexity returns citations in the response object under `citations`
    at the top level of the response. The OpenAI SDK exposes this via
    the model's extra fields.
    """
    citations = []

    # Perplexity includes citations as a top-level field in the response
    raw = getattr(response, "citations", None)
    if raw and isinstance(raw, list):
        citations.extend(str(url) for url in raw if url)
        return citations

    # Fallback: check model_extra on the response object
    if hasattr(response, "model_extra") and response.model_extra:
        raw = response.model_extra.get("citations", [])
        if raw and isinstance(raw, list):
            citations.extend(str(url) for url in raw if url)
            return citations

    # Fallback: try to parse from raw JSON if available
    try:
        raw_dict = response.model_dump() if hasattr(response, "model_dump") else {}
        raw = raw_dict.get("citations", [])
        if raw and isinstance(raw, list):
            citations.extend(str(url) for url in raw if url)
    except Exception:
        pass

    return citations


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

async def research_batch(
    contractors: list[dict],
    concurrency: int = 3,
    on_progress: Optional[Callable] = None,
) -> BatchResearchReport:
    """Research a batch of contractors with controlled concurrency.

    Args:
        contractors: list of dicts, each must have at minimum 'id' and 'name'.
        concurrency: max parallel Perplexity API calls. Keep low (2-5) to
                     respect rate limits and avoid getting throttled.
        on_progress: optional callback(result: ResearchResult, completed: int, total: int)
                     called after each contractor is processed.

    Returns:
        BatchResearchReport with all results and summary stats.
    """
    if not contractors:
        return BatchResearchReport()

    client = _build_client()
    report = BatchResearchReport(total=len(contractors))
    semaphore = asyncio.Semaphore(concurrency)
    start = time.monotonic()

    async def _process_one(contractor: dict, index: int) -> ResearchResult:
        async with semaphore:
            # Rate limiting: space out requests
            if index > 0:
                await asyncio.sleep(ENRICHMENT_DELAY_SECONDS)

            contractor_id = contractor.get("id", index)
            result = await research_contractor(client, contractor, contractor_id)

            if result.success:
                report.succeeded += 1
            else:
                report.failed += 1

            if on_progress:
                completed = report.succeeded + report.failed + report.skipped
                on_progress(result, completed, report.total)

            return result

    # Run with controlled concurrency
    tasks = [
        _process_one(contractor, i)
        for i, contractor in enumerate(contractors)
    ]
    report.results = await asyncio.gather(*tasks)
    report.total_duration_seconds = time.monotonic() - start

    logger.info(
        f"Batch research complete: {report.succeeded}/{report.total} succeeded, "
        f"{report.failed} failed in {report.total_duration_seconds:.1f}s"
    )

    return report


# ---------------------------------------------------------------------------
# Synchronous entry point (for scripts / non-async callers)
# ---------------------------------------------------------------------------

def research_batch_sync(
    contractors: list[dict],
    concurrency: int = 3,
    on_progress: Optional[Callable] = None,
) -> BatchResearchReport:
    """Synchronous wrapper around research_batch for CLI usage."""
    return asyncio.run(research_batch(contractors, concurrency, on_progress))
