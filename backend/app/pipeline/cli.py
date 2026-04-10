"""
CLI entry point for the enrichment pipeline.

Usage:
    # Ingest contractors from a JSON file
    uv run python -m app.pipeline.cli ingest data/sample_contractors.json

    # Ingest and immediately run research
    uv run python -m app.pipeline.cli ingest data/sample_contractors.json --research

    # Stage 1: Run Perplexity research on unenriched contractors
    uv run python -m app.pipeline.cli research
    uv run python -m app.pipeline.cli research --force        # re-research all
    uv run python -m app.pipeline.cli research --limit 10     # first 10 only

    # Stage 2: Run OpenAI scoring on researched contractors
    uv run python -m app.pipeline.cli score
    uv run python -m app.pipeline.cli score --force           # re-score all
    uv run python -m app.pipeline.cli score --limit 5         # first 5 only

    # Stage 3: Extract decision-maker contacts from research text
    uv run python -m app.pipeline.cli contacts
    uv run python -m app.pipeline.cli contacts --force        # re-extract all

    # Show current pipeline status
    uv run python -m app.pipeline.cli status
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from app.db.database import SessionLocal, init_db
from app.db.models import Contact, Contractor, LeadInsight
from app.pipeline.enricher import (
    ingest_contractors,
    run_contact_enrichment,
    run_research_enrichment,
    run_scoring_enrichment,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def cmd_ingest(args):
    """Ingest contractors from a JSON file."""
    path = Path(args.file)
    if not path.exists():
        logger.error(f"File not found: {path}")
        sys.exit(1)

    with open(path) as f:
        data = json.load(f)

    # Accept either a list or a dict keyed by ID
    if isinstance(data, dict):
        contractors_list = list(data.values())
    elif isinstance(data, list):
        contractors_list = data
    else:
        logger.error("JSON must be a list of contractors or a dict keyed by ID")
        sys.exit(1)

    logger.info(f"Ingesting {len(contractors_list)} contractors from {path}...")
    results = ingest_contractors(contractors_list)
    logger.info(f"Done. {len(results)} contractors in database.")

    if args.research:
        logger.info("Starting research enrichment...")
        report = run_research_enrichment(concurrency=args.concurrency)
        _print_report(report)


def cmd_research(args):
    """Run Perplexity research on unenriched (or all) contractors."""
    logger.info("Starting research enrichment...")
    report = run_research_enrichment(
        force=args.force,
        limit=args.limit,
        concurrency=args.concurrency,
    )
    _print_report(report)


def cmd_score(args):
    """Run OpenAI scoring on researched contractors."""
    logger.info("Starting scoring enrichment...")
    report = run_scoring_enrichment(
        force=args.force,
        limit=args.limit,
        concurrency=args.concurrency,
    )
    _print_scoring_report(report)


def cmd_contacts(args):
    """Extract decision-maker contacts from research text."""
    logger.info("Starting contact extraction...")
    report = run_contact_enrichment(
        force=args.force,
        limit=args.limit,
        concurrency=args.concurrency,
    )
    _print_contacts_report(report)


def cmd_status(args):
    """Show current database status."""
    init_db()
    session = SessionLocal()
    try:
        total_contractors = session.query(Contractor).count()
        total_insights = session.query(LeadInsight).count()
        researched = (
            session.query(LeadInsight)
            .filter(LeadInsight.research_summary.isnot(None))
            .filter(LeadInsight.research_summary != "")
            .count()
        )
        scored = (
            session.query(LeadInsight)
            .filter(LeadInsight.lead_score.isnot(None))
            .count()
        )
        total_contacts = session.query(Contact).count()
        contractors_with_contacts = (
            session.query(Contact.contractor_id)
            .distinct()
            .count()
        )

        print(f"\n{'='*50}")
        print(f"  Pipeline Status")
        print(f"{'='*50}")
        print(f"  Contractors in DB:     {total_contractors}")
        print(f"  With research:         {researched}")
        print(f"  With lead scores:      {scored}")
        print(f"  With contacts:         {contractors_with_contacts} ({total_contacts} total contacts)")
        print(f"  Awaiting research:     {total_contractors - researched}")
        print(f"  Awaiting scoring:      {researched - scored}")
        print(f"  Awaiting contacts:     {researched - contractors_with_contacts}")
        print(f"{'='*50}\n")

        # Show a few contractors
        if total_contractors > 0:
            print("  Recent contractors:")
            contractors = session.query(Contractor).order_by(Contractor.id.desc()).limit(5).all()
            for c in contractors:
                has_research = "R" if c.insights and c.insights.research_summary else "-"
                has_score = "S" if c.insights and c.insights.lead_score else "-"
                print(f"    [{has_research}{has_score}] {c.name} ({c.certification or 'uncertified'}) - {c.city}, {c.state}")
            print()

    finally:
        session.close()


def _print_report(report):
    """Pretty-print a BatchResearchReport."""
    print(f"\n{'='*50}")
    print(f"  Research Report")
    print(f"{'='*50}")
    print(f"  Total contractors:   {report.total}")
    print(f"  Succeeded:           {report.succeeded}")
    print(f"  Failed:              {report.failed}")
    print(f"  Duration:            {report.total_duration_seconds:.1f}s")
    print(f"{'='*50}")

    if report.results:
        print("\n  Details:")
        for r in report.results:
            status = "OK" if r.success else f"FAIL: {r.error}"
            citations = f" ({len(r.citations)} citations)" if r.citations else ""
            print(f"    {r.contractor_name}: {status}{citations} [{r.duration_seconds:.1f}s]")
    print()


def _print_scoring_report(report):
    """Pretty-print a BatchScoringReport."""
    print(f"\n{'='*50}")
    print(f"  Scoring Report")
    print(f"{'='*50}")
    print(f"  Total contractors:   {report.total}")
    print(f"  Succeeded:           {report.succeeded}")
    print(f"  Failed:              {report.failed}")
    print(f"  Duration:            {report.total_duration_seconds:.1f}s")
    print(f"{'='*50}")

    if report.results:
        print("\n  Details:")
        for r in report.results:
            if r.success:
                biz = r.score_breakdown.get("business_signals", "?")
                urg = r.score_breakdown.get("why_now_urgency", "?")
                print(f"    {r.contractor_name}: score={r.lead_score} (biz={biz}, urgency={urg}) [{r.duration_seconds:.1f}s]")
            else:
                print(f"    {r.contractor_name}: FAIL: {r.error} [{r.duration_seconds:.1f}s]")
    print()


def _print_contacts_report(report):
    """Pretty-print a BatchContactReport."""
    print(f"\n{'='*50}")
    print(f"  Contact Extraction Report")
    print(f"{'='*50}")
    print(f"  Total contractors:   {report.total}")
    print(f"  Succeeded:           {report.succeeded}")
    print(f"  Failed:              {report.failed}")
    print(f"  Contacts found:      {report.total_contacts_found}")
    print(f"  Duration:            {report.total_duration_seconds:.1f}s")
    print(f"{'='*50}")

    if report.results:
        print("\n  Details:")
        for r in report.results:
            if r.success and r.contacts:
                names = ", ".join(f"{c.full_name} ({c.title})" if c.title else c.full_name for c in r.contacts)
                print(f"    {r.contractor_name}: {len(r.contacts)} contacts — {names}")
            elif r.success:
                print(f"    {r.contractor_name}: no contacts found")
            else:
                print(f"    {r.contractor_name}: FAIL: {r.error}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Roofing Lead Intelligence Pipeline CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ingest
    ingest_parser = subparsers.add_parser("ingest", help="Ingest contractors from JSON file")
    ingest_parser.add_argument("file", help="Path to JSON file with contractor data")
    ingest_parser.add_argument("--research", action="store_true", help="Run research after ingesting")
    ingest_parser.add_argument("--concurrency", type=int, default=3, help="Parallel API calls (default: 3)")

    # research
    research_parser = subparsers.add_parser("research", help="Run Perplexity research on contractors")
    research_parser.add_argument("--force", action="store_true", help="Re-research all contractors")
    research_parser.add_argument("--limit", type=int, default=None, help="Max contractors to process")
    research_parser.add_argument("--concurrency", type=int, default=3, help="Parallel API calls (default: 3)")

    # score
    score_parser = subparsers.add_parser("score", help="Run OpenAI scoring on researched contractors")
    score_parser.add_argument("--force", action="store_true", help="Re-score all researched contractors")
    score_parser.add_argument("--limit", type=int, default=None, help="Max contractors to process")
    score_parser.add_argument("--concurrency", type=int, default=5, help="Parallel API calls (default: 5)")

    # contacts
    contacts_parser = subparsers.add_parser("contacts", help="Extract decision-maker contacts from research")
    contacts_parser.add_argument("--force", action="store_true", help="Re-extract for all researched contractors")
    contacts_parser.add_argument("--limit", type=int, default=None, help="Max contractors to process")
    contacts_parser.add_argument("--concurrency", type=int, default=5, help="Parallel API calls (default: 5)")

    # status
    subparsers.add_parser("status", help="Show pipeline status")

    args = parser.parse_args()

    if args.command == "ingest":
        cmd_ingest(args)
    elif args.command == "research":
        cmd_research(args)
    elif args.command == "score":
        cmd_score(args)
    elif args.command == "contacts":
        cmd_contacts(args)
    elif args.command == "status":
        cmd_status(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
