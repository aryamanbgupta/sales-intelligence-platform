"""
Prompt templates for the enrichment pipeline.

Separated from the engine logic so they can be iterated on independently.
"""

import json

PERPLEXITY_RESEARCH_SYSTEM = """\
You are a B2B sales research analyst specializing in the roofing industry. \
Your job is to gather actionable intelligence about roofing contractors that \
a roofing materials distributor can use to prioritize and engage leads.

You will be given a dossier of what we already know about the contractor from \
their GAF directory listing. DO NOT repeat this information back. Instead, \
use it as context to find NEW information from other web sources.

Focus on facts that signal purchasing behavior, business health, and \
sales readiness. Always cite your sources. Be specific — names, dates, \
numbers are more valuable than vague statements."""


def build_research_prompt(contractor: dict) -> str:
    """Build a comprehensive research query for a single contractor.

    Leverages all available scraped data to give Perplexity strong anchors
    and avoid wasting tokens on information we already have.

    Args:
        contractor: dict with keys from Contractor.to_dict() — includes
                    name, address, city, state, zip_code, phone, website,
                    certification, certifications_raw, rating, review_count,
                    services, years_in_business, about, profile_url.
    """
    name = contractor.get("name", "Unknown")
    city = contractor.get("city", "")
    state = contractor.get("state", "")
    zip_code = contractor.get("zip_code", "")
    phone = contractor.get("phone", "")
    website = contractor.get("website", "")
    certification = contractor.get("certification", "")
    certifications_raw = contractor.get("certifications_raw", [])
    rating = contractor.get("rating")
    review_count = contractor.get("review_count")
    services = contractor.get("services", [])
    years_in_business = contractor.get("years_in_business")
    about = contractor.get("about", "")
    profile_url = contractor.get("profile_url", "")

    # --- Build the "what we already know" dossier ---
    location = f"{city}, {state} {zip_code}".strip() if city else "unknown location"

    known_lines = []
    known_lines.append(f"- Location: {location}")
    if phone:
        known_lines.append(f"- Phone: {phone}")
    if website:
        known_lines.append(f"- Website: {website}")
    if certification:
        cert_detail = certification
        if certifications_raw and len(certifications_raw) > 1:
            cert_detail += f" (all certs: {', '.join(certifications_raw)})"
        known_lines.append(f"- GAF certification tier: {cert_detail}")
    if rating is not None:
        review_str = f" ({review_count} Google reviews)" if review_count else ""
        known_lines.append(f"- Google rating: {rating}/5{review_str}")
    if services:
        known_lines.append(f"- Listed specialties: {', '.join(services)}")
    if years_in_business is not None:
        known_lines.append(f"- Years in business: {years_in_business}")
    if about:
        # Truncate very long descriptions to keep the prompt focused
        about_text = about if len(about) <= 500 else about[:500] + "..."
        known_lines.append(f"- Company self-description: \"{about_text}\"")
    if profile_url:
        known_lines.append(f"- GAF profile: {profile_url}")

    known_block = "\n".join(known_lines)

    # --- Build targeted research directives ---
    # Adapt what we ask Perplexity to find based on what we already know

    website_directive = ""
    if website:
        website_directive = f"""
## Website Analysis
Visit {website} and report:
- What services/products do they prominently feature?
- Do they mention any material brands or supplier partnerships?
- Do they have a careers/hiring page? Are there open positions?
- Is the site modern and professional, or dated?
- Any mention of service area, number of crews, or capacity?"""
    else:
        website_directive = """
## Web Presence
- Can you find a website for this contractor? (Search their name + city)
- Do they have an active social media presence (Facebook, Instagram, LinkedIn)?"""

    years_directive = ""
    if years_in_business is None:
        years_directive = "- How long have they been in business? (check state business registrations, LinkedIn, etc.)"

    return f"""\
Research the roofing contractor "{name}" based in {location}.

## What We Already Know (from GAF directory — DO NOT repeat this)
{known_block}

We need you to find ADDITIONAL intelligence from other web sources. \
Focus on the sections below.

## 1. Decision Makers & Key Contacts (HIGH PRIORITY)
Our sales team needs to know WHO to contact. Find names, titles, and any \
direct contact info for people who make purchasing decisions at this company.

Search these sources:
- **State business registrations**: Check {state} Secretary of State / Division \
of Corporations for registered agent, officers, or principals (e.g., \
NY DOS entity search, NJ DARA business records)
- **BBB profile**: Often lists owner/principal name
- **D&B / Dun & Bradstreet**: Business lookup for company officers
- **LinkedIn**: Search for people who list "{name}" as their employer — \
look for Owner, President, VP, Operations Manager, Purchasing Manager
- **Company website**: Check "About Us", "Our Team", or "Contact" pages
- **Google**: Search "{name} owner" or "{name} president" + city

For each person found, report:
- Full name
- Title / role
- Source where you found them
- Any direct email or phone if publicly listed
- LinkedIn profile URL if found

Even partial info is valuable — a name + title with no email is still \
useful for the sales team. List EVERY person you can find.

## 2. Online Reputation Deep Dive
- Google Reviews: What are the top 3 recurring themes in positive reviews? \
Any recurring complaints? Quote specific review snippets if possible.
- BBB: What is their rating? Any filed complaints or resolved disputes?
- Presence on Angi, HomeAdvisor, Yelp, Houzz — and ratings on each.
- Any notable press coverage, awards, or public complaints?

## 3. Business Health & Growth Signals
{years_directive}
- Estimated company size (employees, trucks, crews) — check LinkedIn, \
job boards, fleet registrations
- Any recent hiring activity (Indeed, ZipRecruiter, LinkedIn job postings)?
- Signs of expansion: new office, new service area, new equipment
- Social media activity trends — growing engagement or dormant?
- Any recent awards, recognitions, or new certifications?
{website_directive}

## 4. Market & Weather Context
- Any severe weather events (hail, storms, wind damage) in the \
{city}, {state} area in the last 6 months?
- Current roofing demand conditions in the NYC metro / tri-state market
- Upcoming seasonal demand patterns

## 5. Supplier & Material Intelligence (MOST IMPORTANT FOR OUR PURPOSES)
- Do they mention ANY current material suppliers or distributor \
relationships (on their site, in reviews, in press)?
- Do Google reviews or complaints mention material quality, delivery \
delays, or product availability issues?
- What product lines do they appear to use or promote? \
(GAF, Owens Corning, CertainTeed, IKO, Atlas, etc.)
- Any indication of their monthly/annual job volume?
- Are they part of any buying groups or co-ops?

## 6. Competitive Positioning
- How do they position themselves? (premium quality, low price, fast \
turnaround, customer service, etc.)
- Who are their main competitors in the {city} area?
- What appears to be their unique selling proposition?

Prioritize concrete, verifiable facts over speculation. Include dates \
where available. Every claim should be traceable to a source. \
If you cannot find information for a section, say so briefly and move on — \
don't pad with generic industry observations."""


# ---------------------------------------------------------------------------
# Stage 2: OpenAI Scoring & Insights
# ---------------------------------------------------------------------------

OPENAI_SCORING_SYSTEM = """\
You are a B2B sales intelligence analyst for a roofing materials distributor. \
You analyze roofing contractors and produce structured sales intelligence \
that helps distribution reps prioritize and engage leads.

You will receive:
1. Structured contractor data from the GAF directory (certification, rating, reviews, etc.)
2. Pre-computed deterministic scores for objective data fields (DO NOT modify these)
3. Web research from Perplexity about the contractor

Your job:
- Score two qualitative factors by reading the research text
- Generate actionable sales intelligence (talking points, buying signals, pain points, pitch, email)

DOMAIN KNOWLEDGE:
- GAF certification tiers (highest to lowest): President's Club > Master Elite > Certified Plus > Certified > Uncertified
- Higher-tier contractors do more volume and buy more premium products
- Review count is a proxy for job volume — more jobs = more materials purchased
- Distributors sell shingles, underlayment, accessories, ventilation, and related products
- Sales reps need concrete, specific insights — not generic industry platitudes

OUTPUT: You must respond with ONLY valid JSON matching the schema provided. No markdown, no commentary."""


def build_scoring_prompt(
    contractor: dict,
    deterministic_scores: dict,
    research_summary: str,
) -> str:
    """Build the per-contractor scoring prompt for OpenAI.

    Args:
        contractor: dict from Contractor.to_dict()
        deterministic_scores: dict from compute_deterministic_scores()
            with keys: certification_tier, review_volume, rating_quality, subtotal
        research_summary: Perplexity research text from lead_insights
    """
    name = contractor.get("name", "Unknown")
    city = contractor.get("city", "")
    state = contractor.get("state", "")
    certification = contractor.get("certification", "Uncertified")
    rating = contractor.get("rating", 0)
    review_count = contractor.get("review_count", 0)
    distance_miles = contractor.get("distance_miles")
    years_in_business = contractor.get("years_in_business")
    services = contractor.get("services", [])
    website = contractor.get("website", "")
    about = contractor.get("about", "")

    cert_score = deterministic_scores["certification_tier"]
    review_score = deterministic_scores["review_volume"]
    rating_score = deterministic_scores["rating_quality"]
    subtotal = deterministic_scores["subtotal"]

    # Build services string
    if isinstance(services, list):
        services_str = ", ".join(services) if services else "Not listed"
    else:
        services_str = str(services) if services else "Not listed"

    distance_str = f"{distance_miles:.1f} miles" if distance_miles else "Unknown"
    years_str = str(years_in_business) if years_in_business else "Unknown"

    return f"""\
## Contractor Profile
- Name: {name}
- Location: {city}, {state}
- GAF Certification: {certification}
- Rating: {rating}/5.0 ({review_count} reviews)
- Distance from distributor: {distance_str}
- Years in business: {years_str}
- Services: {services_str}
- Website: {website or "Not found"}

## Pre-Computed Scores (LOCKED — do not modify these)
- certification_tier: {cert_score}/30
- review_volume: {review_score}/20
- rating_quality: {rating_score}/10
- deterministic_subtotal: {subtotal}/60

## YOUR SCORING TASK
Score these two factors based ONLY on the research text below. \
Cite specific evidence from the research for each score.

**business_signals** (0-20):
  Evidence of growth, hiring, expansion, new equipment, rising revenue, \
  positive business trajectory. Award 0 if no evidence found. \
  Award 5-10 for moderate signals. Award 15+ only with strong, concrete evidence \
  (e.g., "hiring 3 new crews", "opened second location", "revenue up 40%").

**why_now_urgency** (0-20):
  Time-sensitive triggers that create an immediate sales opportunity: \
  recent storms/hail in service area, seasonal demand surge approaching, \
  supplier problems mentioned in reviews, contract expirations, rapid growth \
  outpacing current supply chain. Award 0 if no urgency signals. \
  Award 15+ only for imminent, documented triggers.

**lead_score** = deterministic_subtotal ({subtotal}) + business_signals + why_now_urgency

## Research Text
{research_summary or "No research available for this contractor."}

## Required JSON Output
Respond with ONLY this JSON structure (no markdown fences, no extra text):
{{
  "business_signals_score": <int 0-20>,
  "business_signals_reasoning": "<1-2 sentence justification citing research>",
  "why_now_urgency_score": <int 0-20>,
  "why_now_urgency_reasoning": "<1-2 sentence justification citing research>",
  "lead_score": <int = {subtotal} + business_signals_score + why_now_urgency_score>,
  "score_breakdown": {{
    "certification_tier": {cert_score},
    "review_volume": {review_score},
    "rating_quality": {rating_score},
    "business_signals": <your business_signals_score>,
    "why_now_urgency": <your why_now_urgency_score>
  }},
  "talking_points": [
    "<3-5 specific, actionable conversation starters for the sales rep>",
    "<reference concrete data from profile or research — not generic advice>",
    "<e.g., 'Mention their 449 Google reviews — they clearly value reputation, position our premium shingles as matching that standard'>"
  ],
  "buying_signals": [
    "<2-4 indicators this contractor may need a new/better materials supplier>",
    "<e.g., 'High volume of storm damage repairs suggests surge in shingle demand'>"
  ],
  "pain_points": [
    "<2-4 problems the distributor could solve for this contractor>",
    "<e.g., 'Google reviews mention delays — likely experiencing supply chain issues'>"
  ],
  "recommended_pitch": "<2-3 sentences: how should the rep position the distributor's value prop for THIS specific contractor>",
  "why_now": "<1-2 sentences: the time-sensitive reason to call THIS WEEK, or 'No immediate urgency signal identified' if none found>",
  "draft_email": "<Complete cold outreach email, 150-200 words. Include Subject: line. Personalize with contractor name, certification, and specific findings. Professional tone, not pushy. End with clear CTA for a brief call.>"
}}"""
