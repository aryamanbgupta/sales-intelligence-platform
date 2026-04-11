# Demo + Presentation Script

**Format:** ~15-20 min presentation/demo, ~40 min Q&A
**Approach:** Slides for context, then live demo to prove it works. Keep slides moving fast — the demo is the star.

---

## PRE-DEMO SETUP (do before the call)

```bash
# Terminal 1 — Backend
cd backend && uv run python main.py
# Verify: http://localhost:8000/docs

# Terminal 2 — Frontend
cd frontend && npm run dev
# Verify: http://localhost:3000

# Browser tabs ready:
# 1. Dashboard: http://localhost:3000
# 2. Lead detail: http://localhost:3000/leads/8
# 3. FastAPI docs: http://localhost:8000/docs
```

- Have the chat panel closed (you'll open it live)
- Have the dashboard unfiltered (show the full 78 leads on load)
- Clear your terminal scrollback so it's clean

---

## PART 1: SLIDES (~8 min)

Move through slides quickly. The goal is context, not reading bullets.

### Slide 1 — Title (10 sec)
> "I built an AI-powered sales intelligence platform for roofing distributors. It scrapes contractor data, enriches it with multiple LLMs, scores leads, extracts decision-maker contacts, and presents everything in a dashboard with an agentic chat interface. Let me walk you through how it works, then I'll do a live demo."

### Slide 2 — The Problem (45 sec)
> "The core problem: a roofing distributor's sales reps have no systematic way to find and prioritize contractor leads. They're manually Googling names, checking reviews, guessing who to call. GAF — the largest roofing manufacturer — has a public contractor directory with rich data, but it's locked behind a JS-rendered, bot-protected website. There's nothing that combines scraping that data with AI enrichment to produce actionable intelligence."

### Slide 3 — The Solution (45 sec)
> "So I built an end-to-end pipeline. Five stages: First, scrape contractor data from GAF's directory using Playwright. Second, research each contractor using Perplexity's web search. Third, score and enrich using a hybrid deterministic plus LLM approach with OpenAI. Fourth, serve it through a dashboard where reps can filter, sort, and drill into leads. And fifth — an agentic chat interface where reps can ask questions in natural language. I'll show all of this live."

### Slide 4 — Architecture (60 sec)
> "Here's the architecture. The pipeline runs offline — scrape, research, score, extract contacts, store to SQLite. The dashboard and chat agent read from the database through a FastAPI REST API. Clean separation — the dashboard never waits on scraping or LLM calls. Each pipeline stage is independently runnable: I can re-score without re-researching, re-research without re-scraping. The chat agent sits on the same API, same service layer, same data — just a different interface."

### Slide 6 — Three-Stage Enrichment (60 sec)
> "The enrichment pipeline is three stages, each using the right LLM for the job. Stage 1: Perplexity sonar-pro does web research — company overview, review sentiment, storm activity, growth signals — and returns grounded citations. Stage 2: OpenAI does hybrid scoring — I'll come back to this. Stage 3: OpenAI extracts decision-maker contacts from the research text. Each stage runs independently with force, limit, and concurrency flags."

### Slide 7 — Hybrid Scoring (60 sec)
> "This is the key architectural decision. Scoring is hybrid: 60 points are deterministic — Python computes certification tier, review volume on a log scale, and rating quality. These are objective facts, not judgment calls. The other 40 points are LLM-scored — business signals and why-now urgency, extracted from the unstructured research text. Only an LLM can read '3 new crews hired' or 'hailstorm last week' and quantify it. The benefit: if OpenAI goes down, the deterministic subtotal still provides a usable ranking. Total cost to score all 78 leads was about 5 cents."

### Slide 8 — Agentic Chat (60 sec)
> "The chat agent gives reps a natural language interface over the database. It uses OpenAI function calling with four tools: search and filter leads, get full detail on one lead, get dashboard stats, and compare leads side by side. The agent loop runs up to 5 rounds — the LLM decides which tools to call, executes them, reads the results, and decides whether it needs more data or can answer. The system prompt is domain-aware: it knows GAF certification tiers, score components, and what 'Hot' vs 'Warm' means. Let me show you this live."

**[TRANSITION]**
> "That's the architecture. Let me switch to the live demo."

---

## PART 2: LIVE DEMO (~10 min)

### Demo 1 — Dashboard Overview (2 min)

**Switch to browser — Dashboard tab**

> "This is the dashboard. 78 contractors scraped from GAF's directory within 25 miles of Manhattan. You can see the stats at the top: 78 total leads, 8 hot leads scoring 60 or above, average score of 48.3, and 76 out of 78 enriched."

**Point out the design:**
> "The design mirrors Instalily's brand aesthetic — IBM Plex fonts, monospace section labels, sharp black borders, editorial layout. No external UI libraries, just Tailwind."

**Click "Hot 60+" filter pill:**
> "I can filter by score tier. These are the 8 highest-priority leads — all President's Club or Master Elite certified. Scores range from 61 to 67."

**Click "President's Club" cert filter:**
> "I can also filter by certification. These are the 11 President's Club contractors — GAF's highest tier, top 2% of contractors nationally. They do the most volume and buy the most premium products."

**Click the "Score" column header to sort:**
> "All columns are sortable. And notice — every filter, sort, and page state is synced to the URL. This view is bookmarkable and shareable."

**Clear filters, type "Jersey" in search:**
> "And there's a text search with 300ms debounce."

### Demo 2 — Lead Detail Page (3 min)

**Showcase lead: The Great American Roofing Company (ID 8)**

> "Let me drill into one of our top leads."

**Click on The Great American Roofing Company (or navigate to /leads/8):**

> "This is The Great American Roofing Company — score 65, President's Club certified, 4.9 stars from 150 reviews, based in Ramsey, New Jersey."

**Walk through each section top to bottom:**

> **Contacts:** "First, we have key contacts extracted from the research. Three decision-makers found: Lawrence Ferrari, the President — sourced from their BBB profile with high confidence. Plus Stephen and Andrea Ferrari in management."

> **Talking Points:** "The system generated specific talking points for a sales rep. 'Highlight their 4.9 rating from 150 reviews.' 'Mention their President's Club certification, indicating high-volume work.' These aren't generic — they reference this contractor's actual data."

> **Score Breakdown:** "Here's the explainability. You can see exactly why they scored 65: certification tier maxed at 30 out of 30, review volume at 15 out of 20, rating quality at 10 out of 10, business signals at 10 out of 20. The rep can see precisely what's driving the score."

> **Buying Signals and Pain Points:** "Buying signals: 'High review volume suggests actively taking jobs.' Pain points: 'May face supply chain challenges with high job volume.' These are sourced from the Perplexity research."

> **Draft Email:** "And here's a ready-to-send outreach email. Personalized with their name, rating, certification, and positioning. One click to copy."

> **Research Summary:** "Finally, the collapsible research summary with citation links — BBB, HomeAdvisor, Houzz, GAF. The rep can verify any claim."

### Demo 3 — Agentic Chat (3 min)

**Click the chat bubble in the bottom-right corner.**

> "Now let me show you the chat agent. This is a natural language interface over the same database."

**Type this query:**

```
Who are the top 3 President's Club contractors and why should I prioritize them?
```

> "I'm asking a strategic question. Watch — the agent will call the search_leads tool to find President's Club contractors sorted by score, then synthesize an answer."

**Wait for response, then narrate what happened:**
> "It searched the database, found the top 3, and gave me a prioritized breakdown with specific data points — scores, ratings, review counts, and a reason to prioritize each one. This isn't canned — the agent decided which tool to call and how to structure the answer."

**Type a follow-up:**

```
Compare lead 2 and lead 8 — which one should I call first?
```

> "Now I'm asking it to compare two specific leads. It'll use the compare_leads tool to fetch both, then make a recommendation grounded in the actual data."

**Wait for response:**
> "It pulled both leads, compared them across score, reviews, certification, and signals, and made a specific recommendation. A sales rep could have this conversation without ever touching the dashboard filters."

**Optional third query (if time allows):**

```
Give me a quick summary of the overall pipeline — how many leads do we have and what's the breakdown?
```

> "And it can also pull aggregate stats. This is the same data powering the StatsBar at the top of the dashboard, but accessible through conversation."

### Demo 4 — API Docs (1 min)

**Switch to FastAPI docs tab (localhost:8000/docs):**

> "Under the hood, the FastAPI server auto-generates these interactive API docs. 7 endpoints total — leads list with pagination and filtering, lead detail, stats, the chat endpoint, and pipeline management endpoints for scraping and enrichment. Everything is typed with Pydantic schemas."

---

## PART 3: WRAP-UP SLIDES (~2 min)

### Slide 14 — Testing (30 sec)
> "119 backend tests passing — service layer, API endpoints, and pipeline. All run against an in-memory SQLite database with async mocking for LLM calls."

### Slide 16 — Scalability (45 sec)
> "For production: swap SQLite for Postgres with one connection string change — the ORM handles everything. Pipeline moves to Celery plus Redis for async task execution. Add JWT auth with territory assignment so each rep sees their region. The chat agent gets SSE streaming for real-time token delivery. The architecture is designed for these changes, not locked into the demo stack."

### Slide 18 — By the Numbers (30 sec)
> "Quick recap: 78 contractors scraped and enriched, 119 tests, 26 frontend components, total enrichment cost about 5 cents, 7 API endpoints, 4 chat agent tools. All built within the time constraint."

### Slide 19 — Closing (15 sec)
> "That's the platform. Happy to dive into any part — architecture decisions, the scraping approach, the scoring model, the agent implementation, or anything else."

---

## Q&A CHEAT SHEET

Likely questions and concise answers:

**"Why Coveo API interception instead of DOM scraping?"**
> Coveo returns structured JSON — more reliable, faster, survives UI redesigns. DOM parsing breaks when they change a CSS class.

**"Why two different LLMs (Perplexity + OpenAI)?"**
> Perplexity is built for web search with grounded citations — you can't get that from OpenAI. OpenAI is better at structured JSON output. Best tool for each job.

**"Why hybrid scoring instead of letting the LLM score everything?"**
> Deterministic where objectively knowable — Master Elite > Certified is a lookup table, not a judgment call. Same input always produces the same score, costs nothing, fully auditable. LLM only where reading comprehension is required.

**"Why SQLite?"**
> Zero-config for the demo. SQLAlchemy ORM makes Postgres a one-line change. Schema is already production-ready — JSON fields become JSONB with GIN indexes.

**"How does the chat agent work?"**
> OpenAI function calling. I define 4 tools as JSON schemas. The LLM decides which to call, I execute them against the DB, feed results back, and iterate up to 5 rounds. It uses the same service layer as the REST API — one source of truth.

**"What about rate limiting / cost control on the chat?"**
> Right now there's a 5-round cap per request and max_tokens=1024. For production: add per-user rate limiting, conversation token budgets, and potentially cache common queries.

**"How would you handle scale — hundreds of reps?"**
> Postgres with connection pooling (pgBouncer). Celery + Redis for async pipeline execution. JWT auth with territory-based row-level security. The pipeline already supports concurrency flags and batch processing.

**"What if the Perplexity research is wrong?"**
> Citations are stored and displayed — reps can verify. Research is a stage, not the whole pipeline. Deterministic scoring (60/100) doesn't depend on research quality. The system degrades gracefully.

**"Why sync API handlers?"**
> The enricher pipeline calls asyncio.run() internally. If the handler is async, you get a nested event loop crash. FastAPI runs sync handlers in a thread pool automatically — cleanest solution.

**"How long did this take?"**
> Built within the time constraint. Prioritized working demo with real data first, then polish and documentation.

**"What would you do differently with more time?"**
> SSE streaming for the chat. Postgres with full-text search. A proper eval set for scoring quality — run a batch, have a human review a sample, iterate on prompts. Hunter.io integration for verified email addresses. Territory-based multi-tenant auth.

**"How do you ensure scoring consistency?"**
> Deterministic scores are fully reproducible — same input, same output. LLM scores use temperature 0.3 with JSON mode and range clamping. Pre-computed deterministic scores are passed as "locked — do not modify" context. Final arithmetic is enforced in Python, not trusted from the LLM.
