"""
OpenAI scoring engine — Stage 2 of the enrichment pipeline.

Takes contractor structured data + Perplexity research text and produces:
  - Hybrid lead score (deterministic base + LLM-scored qualitative factors)
  - Actionable sales intelligence (talking points, buying signals, etc.)

Design:
  - Deterministic scoring (60/100 pts) from structured fields: certification,
    review volume, rating quality. Reproducible, free, auditable.
  - LLM scoring (40/100 pts) from unstructured research text: business signals,
    why-now urgency. Requires reading comprehension over Perplexity output.
  - LLM generates all qualitative outputs: talking points, buying signals,
    pain points, recommended pitch, why-now narrative, draft email.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from openai import AsyncOpenAI, APIConnectionError, APIStatusError, RateLimitError

from app.config import (
    ENRICHMENT_DELAY_SECONDS,
    MAX_RETRIES,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_SCORING_MAX_TOKENS,
    OPENAI_SCORING_TEMPERATURE,
    RETRY_BACKOFF_BASE,
)
from app.pipeline.prompts import OPENAI_SCORING_SYSTEM, build_scoring_prompt

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Deterministic scoring functions
# ---------------------------------------------------------------------------

def score_certification(cert: str) -> int:
    """Score GAF certification tier. Max 30 points."""
    tiers = {
        "President's Club": 30,
        "Master Elite": 25,
        "Certified Plus": 20,
        "Certified": 15,
        "Uncertified": 5,
    }
    if not cert:
        return 5
    # Check for partial matches (e.g., "Master Elite Weather Stopper")
    cert_lower = cert.lower()
    for tier_name, score in tiers.items():
        if tier_name.lower() in cert_lower:
            return score
    return 5


def score_review_volume(review_count: int) -> int:
    """Score review count as a proxy for job volume. Max 20 points.

    Uses log scale: a contractor with 10 reviews scores ~7,
    100 reviews scores ~13, 500+ reviews scores 18-20.
    """
    if not review_count or review_count <= 0:
        return 0
    raw = math.log10(review_count + 1) / math.log10(1001) * 20
    return min(20, round(raw))


def score_rating(rating: float, review_count: int) -> int:
    """Score star rating weighted by review confidence. Max 10 points.

    A 5.0 rating with 2 reviews is less meaningful than 4.7 with 400.
    Confidence reaches full weight at 50+ reviews.
    """
    if not review_count or review_count <= 0 or not rating or rating <= 0:
        return 0
    confidence = min(1.0, review_count / 50)
    raw = (rating / 5.0) * 10 * confidence
    return round(raw)


def compute_deterministic_scores(contractor: dict) -> dict:
    """Compute the deterministic (structured-data) portion of the lead score.

    Returns dict with certification_tier, review_volume, rating_quality, subtotal.
    """
    cert = score_certification(contractor.get("certification", ""))
    reviews = score_review_volume(contractor.get("review_count", 0) or 0)
    rating = score_rating(
        contractor.get("rating", 0) or 0,
        contractor.get("review_count", 0) or 0,
    )
    return {
        "certification_tier": cert,
        "review_volume": reviews,
        "rating_quality": rating,
        "subtotal": cert + reviews + rating,
    }


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ScoringResult:
    """Output from scoring a single contractor."""
    contractor_id: int
    contractor_name: str
    lead_score: int = 0
    score_breakdown: dict = field(default_factory=dict)
    talking_points: list[str] = field(default_factory=list)
    buying_signals: list[str] = field(default_factory=list)
    pain_points: list[str] = field(default_factory=list)
    recommended_pitch: str = ""
    why_now: str = ""
    draft_email: str = ""
    success: bool = True
    error: str | None = None
    duration_seconds: float = 0.0


@dataclass
class BatchScoringReport:
    """Summary of a full batch scoring run."""
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    results: list[ScoringResult] = field(default_factory=list)
    total_duration_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

def _build_client() -> AsyncOpenAI:
    """Build an async OpenAI client for scoring."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set. Add it to backend/.env")
    return AsyncOpenAI(api_key=OPENAI_API_KEY)


# ---------------------------------------------------------------------------
# Single contractor scoring
# ---------------------------------------------------------------------------

async def score_contractor(
    client: AsyncOpenAI,
    contractor: dict,
    research_summary: str,
) -> ScoringResult:
    """Score a single contractor using deterministic + LLM hybrid approach.

    Args:
        client: AsyncOpenAI client.
        contractor: dict from Contractor.to_dict().
        research_summary: Perplexity research text for this contractor.

    Returns:
        ScoringResult with lead score, breakdown, and all qualitative outputs.
    """
    name = contractor.get("name", "Unknown")
    contractor_id = contractor.get("id", 0)
    start = time.monotonic()

    # Step 1: Compute deterministic scores
    det_scores = compute_deterministic_scores(contractor)

    # Step 2: Build prompt and call OpenAI
    prompt = build_scoring_prompt(contractor, det_scores, research_summary)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": OPENAI_SCORING_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=OPENAI_SCORING_MAX_TOKENS,
                temperature=OPENAI_SCORING_TEMPERATURE,
                response_format={"type": "json_object"},
            )

            raw_text = response.choices[0].message.content or ""
            parsed = json.loads(raw_text)

            # Validate and extract
            result = _parse_scoring_response(parsed, det_scores, contractor_id, name)
            result.duration_seconds = time.monotonic() - start

            logger.info(
                f"Scored '{name}': {result.lead_score}/100 "
                f"(det={det_scores['subtotal']}, biz={parsed.get('business_signals_score', '?')}, "
                f"urgency={parsed.get('why_now_urgency_score', '?')}) "
                f"in {result.duration_seconds:.1f}s"
            )
            return result

        except json.JSONDecodeError as e:
            duration = time.monotonic() - start
            logger.error(f"JSON parse error for '{name}': {e}")
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_BASE ** attempt
                logger.warning(f"Retrying in {wait:.1f}s...")
                await asyncio.sleep(wait)
            else:
                return ScoringResult(
                    contractor_id=contractor_id,
                    contractor_name=name,
                    success=False,
                    error=f"JSON parse error after {MAX_RETRIES} attempts: {e}",
                    duration_seconds=duration,
                )

        except (RateLimitError, APIConnectionError) as e:
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_BASE ** attempt
                logger.warning(
                    f"Transient error for '{name}' (attempt {attempt}/{MAX_RETRIES}), "
                    f"retrying in {wait:.1f}s: {e}"
                )
                await asyncio.sleep(wait)
            else:
                duration = time.monotonic() - start
                logger.error(f"Failed to score '{name}' after {MAX_RETRIES} attempts: {e}")
                return ScoringResult(
                    contractor_id=contractor_id,
                    contractor_name=name,
                    success=False,
                    error=str(e),
                    duration_seconds=duration,
                )

        except APIStatusError as e:
            duration = time.monotonic() - start
            logger.error(f"API error for '{name}': {e.status_code} {e.message}")
            return ScoringResult(
                contractor_id=contractor_id,
                contractor_name=name,
                success=False,
                error=f"API {e.status_code}: {e.message}",
                duration_seconds=duration,
            )

        except Exception as e:
            duration = time.monotonic() - start
            logger.error(f"Unexpected error scoring '{name}': {e}")
            return ScoringResult(
                contractor_id=contractor_id,
                contractor_name=name,
                success=False,
                error=str(e),
                duration_seconds=duration,
            )

    # Should not reach here
    duration = time.monotonic() - start
    return ScoringResult(
        contractor_id=contractor_id,
        contractor_name=name,
        success=False,
        error="Exhausted retries",
        duration_seconds=duration,
    )


def _parse_scoring_response(
    parsed: dict,
    det_scores: dict,
    contractor_id: int,
    contractor_name: str,
) -> ScoringResult:
    """Parse and validate OpenAI's JSON response into a ScoringResult.

    Enforces that lead_score = deterministic_subtotal + LLM components.
    Clamps LLM scores to valid ranges.
    """
    subtotal = det_scores["subtotal"]

    # Extract and clamp LLM scores
    biz_score = max(0, min(20, int(parsed.get("business_signals_score", 0))))
    urgency_score = max(0, min(20, int(parsed.get("why_now_urgency_score", 0))))

    # Enforce correct arithmetic (don't trust the LLM's addition)
    lead_score = subtotal + biz_score + urgency_score

    # Build the full breakdown
    score_breakdown = {
        "certification_tier": det_scores["certification_tier"],
        "review_volume": det_scores["review_volume"],
        "rating_quality": det_scores["rating_quality"],
        "business_signals": biz_score,
        "why_now_urgency": urgency_score,
    }

    # Extract qualitative outputs with safe defaults
    talking_points = parsed.get("talking_points", [])
    if not isinstance(talking_points, list):
        talking_points = []

    buying_signals = parsed.get("buying_signals", [])
    if not isinstance(buying_signals, list):
        buying_signals = []

    pain_points = parsed.get("pain_points", [])
    if not isinstance(pain_points, list):
        pain_points = []

    return ScoringResult(
        contractor_id=contractor_id,
        contractor_name=contractor_name,
        lead_score=lead_score,
        score_breakdown=score_breakdown,
        talking_points=talking_points,
        buying_signals=buying_signals,
        pain_points=pain_points,
        recommended_pitch=str(parsed.get("recommended_pitch", "")),
        why_now=str(parsed.get("why_now", "")),
        draft_email=str(parsed.get("draft_email", "")),
        success=True,
    )


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

async def score_batch(
    contractors: list[dict],
    research_map: dict[int, str],
    concurrency: int = 5,
    on_progress: Optional[Callable] = None,
) -> BatchScoringReport:
    """Score a batch of contractors with controlled concurrency.

    Args:
        contractors: list of dicts from Contractor.to_dict().
        research_map: {contractor_id: research_summary_text} for each contractor.
        concurrency: max parallel OpenAI API calls.
        on_progress: optional callback(result, completed, total).

    Returns:
        BatchScoringReport with all results and summary stats.
    """
    if not contractors:
        return BatchScoringReport()

    client = _build_client()
    report = BatchScoringReport(total=len(contractors))
    semaphore = asyncio.Semaphore(concurrency)
    start = time.monotonic()

    async def _process_one(contractor: dict, index: int) -> ScoringResult:
        async with semaphore:
            if index > 0:
                await asyncio.sleep(ENRICHMENT_DELAY_SECONDS)

            contractor_id = contractor.get("id", index)
            research_text = research_map.get(contractor_id, "")

            result = await score_contractor(client, contractor, research_text)

            if result.success:
                report.succeeded += 1
            else:
                report.failed += 1

            if on_progress:
                completed = report.succeeded + report.failed + report.skipped
                on_progress(result, completed, report.total)

            return result

    tasks = [
        _process_one(contractor, i)
        for i, contractor in enumerate(contractors)
    ]
    report.results = await asyncio.gather(*tasks)
    report.total_duration_seconds = time.monotonic() - start

    logger.info(
        f"Batch scoring complete: {report.succeeded}/{report.total} succeeded, "
        f"{report.failed} failed in {report.total_duration_seconds:.1f}s"
    )

    return report


# ---------------------------------------------------------------------------
# Synchronous entry point
# ---------------------------------------------------------------------------

def score_batch_sync(
    contractors: list[dict],
    research_map: dict[int, str],
    concurrency: int = 5,
    on_progress: Optional[Callable] = None,
) -> BatchScoringReport:
    """Synchronous wrapper around score_batch for CLI usage."""
    return asyncio.run(
        score_batch(contractors, research_map, concurrency, on_progress)
    )
