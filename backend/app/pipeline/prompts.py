"""
Prompt templates for the enrichment pipeline.

Separated from the engine logic so they can be iterated on independently.
"""

PERPLEXITY_RESEARCH_SYSTEM = """\
You are a B2B sales research analyst specializing in the roofing industry. \
Your job is to gather actionable intelligence about roofing contractors that \
a roofing materials distributor can use to prioritize and engage leads.

Focus on facts that signal purchasing behavior, business health, and \
sales readiness. Always cite your sources. Be specific — names, dates, \
numbers are more valuable than vague statements."""


def build_research_prompt(contractor: dict) -> str:
    """Build a comprehensive research query for a single contractor.

    Args:
        contractor: dict with keys from the Contractor model (name, address,
                    city, state, zip_code, phone, website, certification,
                    rating, review_count, services).
    """
    name = contractor.get("name", "Unknown")
    city = contractor.get("city", "")
    state = contractor.get("state", "")
    address = contractor.get("address", "")
    website = contractor.get("website", "")
    certification = contractor.get("certification", "")
    rating = contractor.get("rating", "")
    review_count = contractor.get("review_count", "")

    location = f"{city}, {state}" if city and state else address or "unknown location"
    website_line = f"- Known website: {website}" if website else ""
    cert_line = f"- GAF certification: {certification}" if certification else ""
    rating_line = f"- Google/GAF rating: {rating} stars ({review_count} reviews)" if rating else ""

    return f"""\
Research the roofing contractor "{name}" based in {location}.

Known details:
- Full address: {address}
{cert_line}
{rating_line}
{website_line}

Please investigate and report on ALL of the following areas. If you cannot \
find information for a section, explicitly say so rather than guessing.

## 1. Company Overview
- How long have they been in business?
- Estimated company size (employees, trucks, crews)
- Ownership structure if known (family-owned, franchise, private equity-backed)
- Service area / territories covered

## 2. Online Reputation & Reviews
- Google Reviews summary: overall sentiment, common praise, common complaints
- BBB rating and any filed complaints
- Yelp, Angi, or HomeAdvisor presence and ratings
- Any notable positive or negative press

## 3. Services & Specialization
- Residential vs. commercial split
- Specific services offered (new roofs, repairs, gutters, siding, solar)
- Any manufacturer certifications beyond GAF (Owens Corning, CertainTeed, etc.)
- Premium product lines they promote (designer shingles, metal roofing, etc.)

## 4. Business Growth Signals
- Any recent hiring activity (job postings, new crew members)
- Fleet or equipment expansions
- New office locations or expanded service area
- Website or branding updates
- Social media activity and engagement trends

## 5. Recent Projects & Activity
- Notable recent projects or customer testimonials
- Involvement in community projects or sponsorships
- Awards or recognitions

## 6. Market & Weather Context
- Recent severe weather events (hail, storms, hurricanes) in their service area
- Current roofing demand conditions in their market
- Seasonal considerations for their region

## 7. Competitive Positioning
- How do they position themselves vs. competitors? (price, quality, speed)
- What differentiates them in their market?
- Any weaknesses or gaps in their offering?

## 8. Distributor Relevance Signals
- Any mentions of current material suppliers
- Complaints about material availability or delivery
- Volume indicators (how many jobs per month/year)
- Signs they might be open to a new supplier relationship

Prioritize concrete, verifiable facts over speculation. Include dates where \
possible. Every claim should be traceable to a source."""
