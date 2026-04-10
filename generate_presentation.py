"""
Generate a PowerPoint presentation for the Roofing Lead Intelligence Platform.
Styled to match the PartSelect case study reference deck.
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# ── Constants ──────────────────────────────────────────────────────────────
SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)

# Colors
BLACK = RGBColor(0x17, 0x17, 0x17)
DARK_GRAY = RGBColor(0x40, 0x40, 0x40)
MED_GRAY = RGBColor(0x6B, 0x6B, 0x6B)
LIGHT_GRAY = RGBColor(0xA0, 0xA0, 0xA0)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
OFF_WHITE = RGBColor(0xFE, 0xFF, 0xF7)
ORANGE = RGBColor(0xEA, 0x88, 0x0E)
TEAL = RGBColor(0x0D, 0x9B, 0x8C)
GREEN = RGBColor(0x16, 0x83, 0x5E)
RED = RGBColor(0xAA, 0x1E, 0x00)
BLUE = RGBColor(0x1E, 0x40, 0xAF)

FONT_BODY = "Calibri"
FONT_MONO = "Consolas"


def set_slide_bg(slide, color):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_textbox(slide, left, top, width, height, text, font_size=18,
                bold=False, color=BLACK, font_name=FONT_BODY, alignment=PP_ALIGN.LEFT,
                line_spacing=1.2):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.font.name = font_name
    p.alignment = alignment
    p.space_after = Pt(0)
    return txBox


def add_para(text_frame, text, font_size=18, bold=False, color=BLACK,
             font_name=FONT_BODY, alignment=PP_ALIGN.LEFT, space_before=0, space_after=4):
    p = text_frame.add_paragraph()
    p.text = text
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.font.name = font_name
    p.alignment = alignment
    p.space_before = Pt(space_before)
    p.space_after = Pt(space_after)
    return p


def add_subtitle_line(slide, text, top=Inches(0.35)):
    add_textbox(slide, Inches(0.8), top, Inches(11.7), Inches(0.35),
                text, font_size=11, color=MED_GRAY, font_name=FONT_BODY)


def add_section_title(slide, text, top=Inches(0.9)):
    add_textbox(slide, Inches(0.8), top, Inches(11.7), Inches(0.6),
                text, font_size=36, bold=True, color=BLACK)


def add_colored_rect(slide, left, top, width, height, fill_color, border_color=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    if border_color:
        shape.line.color.rgb = border_color
        shape.line.width = Pt(1)
    else:
        shape.line.fill.background()
    return shape


def add_card(slide, left, top, width, height, fill_color=WHITE, border_color=None):
    return add_colored_rect(slide, left, top, width, height, fill_color, border_color)


def add_bullet_list(slide, left, top, width, height, items, font_size=16,
                    color=BLACK, bullet="", spacing=6):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = f"{bullet}{item}" if bullet else item
        p.font.size = Pt(font_size)
        p.font.color.rgb = color
        p.font.name = FONT_BODY
        p.space_after = Pt(spacing)
    return txBox


# ══════════════════════════════════════════════════════════════════════════
# BUILD SLIDES
# ══════════════════════════════════════════════════════════════════════════
prs = Presentation()
prs.slide_width = SLIDE_WIDTH
prs.slide_height = SLIDE_HEIGHT
blank_layout = prs.slide_layouts[6]  # Blank

# ── SLIDE 1: Title ────────────────────────────────────────────────────────
slide = prs.slides.add_slide(blank_layout)
set_slide_bg(slide, BLACK)

add_textbox(slide, Inches(0.8), Inches(2.0), Inches(11.7), Inches(1.2),
            "Roofing Lead Intelligence Platform",
            font_size=44, bold=True, color=WHITE)

add_textbox(slide, Inches(0.8), Inches(3.3), Inches(11.7), Inches(0.8),
            "AI-powered sales intelligence for roofing distributors",
            font_size=24, color=LIGHT_GRAY)

add_textbox(slide, Inches(0.8), Inches(5.5), Inches(11.7), Inches(0.6),
            "Aryaman Gupta  \u00b7  Onsite Project  \u00b7  Instalily AI",
            font_size=16, color=MED_GRAY)


# ── SLIDE 2: The Problem ──────────────────────────────────────────────────
slide = prs.slides.add_slide(blank_layout)
set_slide_bg(slide, OFF_WHITE)
add_subtitle_line(slide, "Roofing Lead Intelligence Platform \u2014 Aryaman Gupta | Instalily")
add_section_title(slide, "The Problem")

problems = [
    "Roofing distributors have no systematic way to identify and prioritize contractor leads",
    "Sales reps spend hours manually researching contractors \u2014 Googling names, checking reviews, guessing who to call first",
    "GAF\u2019s public directory has rich contractor data, but it\u2019s locked inside a JS-rendered, bot-protected website",
    "No existing tool combines scraping + AI enrichment + actionable sales intelligence in one workflow",
    "Without lead scoring, reps waste time on low-potential contractors while high-value leads go untouched",
]
add_bullet_list(slide, Inches(0.8), Inches(1.8), Inches(11.7), Inches(4.5),
                problems, font_size=20, bullet="\u2022  ", spacing=14)


# ── SLIDE 3: The Solution ─────────────────────────────────────────────────
slide = prs.slides.add_slide(blank_layout)
set_slide_bg(slide, OFF_WHITE)
add_subtitle_line(slide, "Roofing Lead Intelligence Platform \u2014 Aryaman Gupta | Instalily")
add_section_title(slide, "The Solution")

add_textbox(slide, Inches(0.8), Inches(1.7), Inches(11.7), Inches(0.7),
            "An end-to-end platform that scrapes, enriches, scores, and presents contractor leads \u2014 turning raw directory data into actionable sales intelligence.",
            font_size=18, color=DARK_GRAY)

# 4 solution cards
card_data = [
    ("Scrape", "Playwright + Coveo API\ninterception", "78 contractors from\nGAF directory"),
    ("Research", "Perplexity sonar-pro\nweb research engine", "Grounded insights with\ncitations per lead"),
    ("Score", "Hybrid deterministic +\nLLM scoring (0\u2013100)", "Explainable 5-factor\nbreakdown"),
    ("Serve", "Next.js dashboard +\nFastAPI REST API", "Filter, sort, drill into\nevery lead"),
]
card_w = Inches(2.7)
card_h = Inches(3.0)
gap = Inches(0.35)
start_x = Inches(0.8)
card_top = Inches(2.8)

for i, (title, desc, detail) in enumerate(card_data):
    x = start_x + i * (card_w + gap)
    add_card(slide, x, card_top, card_w, card_h, fill_color=WHITE, border_color=BLACK)
    add_textbox(slide, x + Inches(0.25), card_top + Inches(0.25), card_w - Inches(0.5), Inches(0.5),
                title, font_size=22, bold=True, color=BLACK)
    add_textbox(slide, x + Inches(0.25), card_top + Inches(0.9), card_w - Inches(0.5), Inches(0.9),
                desc, font_size=15, color=DARK_GRAY)
    add_textbox(slide, x + Inches(0.25), card_top + Inches(1.9), card_w - Inches(0.5), Inches(0.9),
                detail, font_size=14, color=MED_GRAY, font_name=FONT_MONO)


# ── SLIDE 4: Architecture ─────────────────────────────────────────────────
slide = prs.slides.add_slide(blank_layout)
set_slide_bg(slide, OFF_WHITE)
add_subtitle_line(slide, "Roofing Lead Intelligence Platform \u2014 Aryaman Gupta | Instalily")
add_section_title(slide, "Architecture: Pipeline + API + Dashboard")

# Pipeline flow diagram using shapes
flow_items = [
    ("GAF\nWebsite", DARK_GRAY),
    ("Playwright\nScraper", TEAL),
    ("Perplexity\nResearch", BLUE),
    ("OpenAI\nScoring", ORANGE),
    ("SQLite\nDatabase", GREEN),
    ("FastAPI\nREST API", DARK_GRAY),
    ("Next.js\nDashboard", BLACK),
]

box_w = Inches(1.45)
box_h = Inches(1.1)
arrow_w = Inches(0.35)
start_x = Inches(0.5)
flow_top = Inches(2.3)

for i, (label, color) in enumerate(flow_items):
    x = start_x + i * (box_w + arrow_w)
    shape = add_colored_rect(slide, x, flow_top, box_w, box_h, color)
    shape.text_frame.paragraphs[0].text = label
    shape.text_frame.paragraphs[0].font.size = Pt(13)
    shape.text_frame.paragraphs[0].font.color.rgb = WHITE
    shape.text_frame.paragraphs[0].font.bold = True
    shape.text_frame.paragraphs[0].font.name = FONT_BODY
    shape.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
    shape.text_frame.word_wrap = True

    # Arrow
    if i < len(flow_items) - 1:
        add_textbox(slide, x + box_w, flow_top + Inches(0.25), arrow_w, Inches(0.6),
                    "\u2192", font_size=28, bold=True, color=MED_GRAY, alignment=PP_ALIGN.CENTER)

# Key architecture notes below
arch_notes = [
    "Pipeline runs offline \u2014 scrape, research, score, extract contacts, store. Dashboard never waits on LLM calls.",
    "Each stage is independently runnable: re-score without re-researching, re-research without re-scraping.",
    "Three DB tables: contractors (raw data), lead_insights (AI enrichments), contacts (decision-makers).",
    "Clean separation: CLI for pipeline ops, REST API for reads, Next.js for presentation.",
]
add_bullet_list(slide, Inches(0.8), Inches(4.0), Inches(11.7), Inches(3.0),
                arch_notes, font_size=16, bullet="\u2022  ", spacing=10)


# ── SLIDE 5: Scraping ─────────────────────────────────────────────────────
slide = prs.slides.add_slide(blank_layout)
set_slide_bg(slide, OFF_WHITE)
add_subtitle_line(slide, "Roofing Lead Intelligence Platform \u2014 Aryaman Gupta | Instalily")
add_section_title(slide, "Stage 0: Scraping \u2014 Playwright + Coveo API Interception")

scraping_points = [
    "GAF\u2019s site is JS-rendered and protected by Akamai bot detection \u2014 can\u2019t use simple HTTP requests",
    "Playwright launches headless Chromium with stealth settings (spoofed webdriver, plugins, permissions)",
    "Instead of parsing DOM elements, we intercept the Coveo search API calls for clean structured JSON",
    "Extract Bearer token from the first request, then paginate directly against Coveo\u2019s REST API",
    "Profile page scraping runs with configurable concurrency for website URLs, years in business, about text",
    "Parameterized: zip_code and distance are inputs, not hardcoded \u2014 works for any territory",
    "Result: 78 contractors with name, address, phone, certification, rating, reviews, services, lat/lng, distance",
]
add_bullet_list(slide, Inches(0.8), Inches(1.8), Inches(11.7), Inches(5.0),
                scraping_points, font_size=17, bullet="\u2022  ", spacing=10)


# ── SLIDE 6: Three-Stage AI Enrichment ─────────────────────────────────────
slide = prs.slides.add_slide(blank_layout)
set_slide_bg(slide, OFF_WHITE)
add_subtitle_line(slide, "Roofing Lead Intelligence Platform \u2014 Aryaman Gupta | Instalily")
add_section_title(slide, "Three-Stage AI Enrichment Pipeline")

add_textbox(slide, Inches(0.8), Inches(1.7), Inches(11.7), Inches(0.5),
            "Multiple LLMs, each doing what they\u2019re best at.",
            font_size=17, color=DARK_GRAY)

stages = [
    ("Stage 1: Perplexity \u2014 Web Research", BLUE,
     ["Sends structured research queries to Perplexity sonar-pro for each contractor",
      "Returns: company overview, decision-makers, Google review sentiment, recent projects, storm activity, growth signals, BBB rating, supplier intel",
      "Grounded citations (URLs) stored alongside research text \u2014 reps can verify"]),
    ("Stage 2: OpenAI \u2014 Hybrid Scoring", ORANGE,
     ["Deterministic scoring (60/100 pts): certification tier, review volume (log-scaled), rating quality",
      "LLM scoring (40/100 pts): business signals + why-now urgency extracted from research text",
      "Also generates: talking points, buying signals, pain points, recommended pitch, draft email"]),
    ("Stage 3: OpenAI \u2014 Contact Extraction", GREEN,
     ["Extracts decision-maker contacts from research text: names, titles, emails, LinkedIn URLs",
      "Provider-based architecture: PerplexityExtractor (implemented), Hunter.io (ready to plug in)",
      "Deduplicated by name + contractor_id \u2014 re-running enriches, doesn\u2019t duplicate"]),
]

stage_top = Inches(2.3)
stage_h = Inches(1.5)
stage_gap = Inches(0.15)

for i, (title, color, bullets) in enumerate(stages):
    y = stage_top + i * (stage_h + stage_gap)
    # Color bar on left
    add_colored_rect(slide, Inches(0.8), y, Inches(0.08), stage_h, color)
    add_textbox(slide, Inches(1.1), y + Inches(0.05), Inches(11.0), Inches(0.35),
                title, font_size=18, bold=True, color=BLACK)
    for j, bullet in enumerate(bullets):
        add_textbox(slide, Inches(1.3), y + Inches(0.4) + j * Inches(0.33), Inches(10.8), Inches(0.35),
                    f"\u2022  {bullet}", font_size=14, color=DARK_GRAY)


# ── SLIDE 7: Hybrid Scoring Deep Dive ──────────────────────────────────────
slide = prs.slides.add_slide(blank_layout)
set_slide_bg(slide, OFF_WHITE)
add_subtitle_line(slide, "Roofing Lead Intelligence Platform \u2014 Aryaman Gupta | Instalily")
add_section_title(slide, "Hybrid Scoring: Why Not Fully LLM or Fully Deterministic?")

# Two columns
col_w = Inches(5.5)

# Left column - Deterministic
add_textbox(slide, Inches(0.8), Inches(1.9), col_w, Inches(0.4),
            "Deterministic (60 pts \u2014 Python)", font_size=20, bold=True, color=TEAL)
det_items = [
    "certification_tier (0\u201330): President\u2019s Club=30, Master Elite=25, Certified=15",
    "review_volume (0\u201320): log-scaled from review count",
    "rating_quality (0\u201310): star rating weighted by review confidence",
    "Same input = same score. Costs $0. Auditable.",
]
add_bullet_list(slide, Inches(0.8), Inches(2.5), col_w, Inches(2.5),
                det_items, font_size=15, bullet="\u2022  ", spacing=10)

# Right column - LLM
add_textbox(slide, Inches(7.0), Inches(1.9), col_w, Inches(0.4),
            "LLM-Scored (40 pts \u2014 gpt-4o-mini)", font_size=20, bold=True, color=ORANGE)
llm_items = [
    "business_signals (0\u201320): growth, hiring, expansion from research text",
    "why_now_urgency (0\u201320): storms, seasonal demand, supplier issues",
    "Only an LLM can extract these from 3000 chars of unstructured research",
    "~$0.001 per contractor. All 78 leads scored for ~$0.05 total.",
]
add_bullet_list(slide, Inches(7.0), Inches(2.5), col_w, Inches(2.5),
                llm_items, font_size=15, bullet="\u2022  ", spacing=10)

# Bottom benefits
add_textbox(slide, Inches(0.8), Inches(5.0), Inches(11.7), Inches(0.4),
            "Key Benefits:", font_size=18, bold=True, color=BLACK)
benefits = [
    "Graceful degradation: if OpenAI is down, deterministic subtotal (60/100) still provides usable ranking",
    "Pre-computed deterministic scores passed to LLM as \u201clocked \u2014 do not modify\u201d context",
    "LLM scores clamped to valid ranges; arithmetic enforced in Python (don\u2019t trust the LLM\u2019s addition)",
    "response_format={\"type\": \"json_object\"} for guaranteed parseable output",
]
add_bullet_list(slide, Inches(0.8), Inches(5.5), Inches(11.7), Inches(1.8),
                benefits, font_size=15, bullet="\u2022  ", spacing=8)


# ── SLIDE 8: Database Design ──────────────────────────────────────────────
slide = prs.slides.add_slide(blank_layout)
set_slide_bg(slide, OFF_WHITE)
add_subtitle_line(slide, "Roofing Lead Intelligence Platform \u2014 Aryaman Gupta | Instalily")
add_section_title(slide, "Data Management: Three-Table Schema")

# Three table cards
tables = [
    ("contractors", "23 columns", [
        "Raw scraped data from GAF",
        "gaf_id as dedupe key (upserts)",
        "Name, address, phone, website",
        "Certification, rating, reviews",
        "Lat/lng, distance, services",
        "Years in business, about text",
    ]),
    ("lead_insights", "15 columns", [
        "AI-generated enrichments",
        "1:1 with contractor (UNIQUE FK)",
        "lead_score (0\u2013100)",
        "score_breakdown (5-factor JSON)",
        "Talking points, buying signals",
        "Why now, draft email, pitch",
    ]),
    ("contacts", "10 columns", [
        "Decision-maker contacts",
        "Many-to-one with contractor",
        "Name, title, email, phone",
        "LinkedIn URL",
        "Source + confidence level",
        "Deduped by name + contractor",
    ]),
]

table_w = Inches(3.6)
table_h = Inches(3.5)
table_gap = Inches(0.4)
table_start_x = Inches(0.8)
table_top = Inches(1.9)

for i, (name, cols, fields) in enumerate(tables):
    x = table_start_x + i * (table_w + table_gap)
    add_card(slide, x, table_top, table_w, table_h, fill_color=WHITE, border_color=BLACK)
    add_textbox(slide, x + Inches(0.2), table_top + Inches(0.15), table_w - Inches(0.4), Inches(0.35),
                f"{name}", font_size=18, bold=True, color=BLACK, font_name=FONT_MONO)
    add_textbox(slide, x + Inches(0.2), table_top + Inches(0.5), table_w - Inches(0.4), Inches(0.25),
                cols, font_size=12, color=MED_GRAY, font_name=FONT_MONO)
    for j, field in enumerate(fields):
        add_textbox(slide, x + Inches(0.2), table_top + Inches(0.85) + j * Inches(0.38),
                    table_w - Inches(0.4), Inches(0.35),
                    f"\u2022  {field}", font_size=13, color=DARK_GRAY)

# Key decisions below
db_notes = [
    "SQLAlchemy ORM \u2014 swap SQLite for Postgres by changing one connection string",
    "JSON fields stored as TEXT (SQLite-compatible), become native JSONB with GIN indexes in Postgres",
    "Three tables enable independent re-processing: re-score without re-researching, re-research without re-scraping",
]
add_bullet_list(slide, Inches(0.8), Inches(5.7), Inches(11.7), Inches(1.5),
                db_notes, font_size=15, bullet="\u2022  ", spacing=8)


# ── SLIDE 9: REST API ─────────────────────────────────────────────────────
slide = prs.slides.add_slide(blank_layout)
set_slide_bg(slide, OFF_WHITE)
add_subtitle_line(slide, "Roofing Lead Intelligence Platform \u2014 Aryaman Gupta | Instalily")
add_section_title(slide, "REST API: 6 Endpoints, 11 Schemas, 3-Tier Architecture")

# Endpoint table
endpoints = [
    ("GET", "/api/leads", "Paginated list with filters (score, cert, search), sorting, URL-synced"),
    ("GET", "/api/leads/{id}", "Full detail: contractor + insights + contacts (eager-loaded)"),
    ("GET", "/api/stats", "Dashboard metrics: totals, averages, cert breakdown, score distribution"),
    ("POST", "/api/pipeline/scrape", "Trigger scraping for any zip_code + distance"),
    ("POST", "/api/pipeline/enrich", "Run all 3 enrichment stages sequentially"),
    ("GET", "/api/pipeline/status", "Pipeline health: how many awaiting research/scoring/contacts"),
]

ep_top = Inches(1.9)
for i, (method, path, desc) in enumerate(endpoints):
    y = ep_top + i * Inches(0.55)
    method_color = GREEN if method == "GET" else ORANGE
    add_textbox(slide, Inches(0.8), y, Inches(0.7), Inches(0.4),
                method, font_size=14, bold=True, color=method_color, font_name=FONT_MONO)
    add_textbox(slide, Inches(1.5), y, Inches(2.5), Inches(0.4),
                path, font_size=14, color=BLACK, font_name=FONT_MONO)
    add_textbox(slide, Inches(4.2), y, Inches(8.5), Inches(0.4),
                desc, font_size=14, color=DARK_GRAY)

# Architecture notes
api_arch = [
    "Schemas (schemas.py): 11 Pydantic models enforce type safety. Separate list vs. detail schemas avoid serializing multi-KB fields for table rows.",
    "Service layer (lead_service.py): Isolates SQLAlchemy query logic. NULL-safe ordering, CASE WHEN bucketing for stats.",
    "Routers (leads.py, pipeline.py): Thin handlers. Column whitelist prevents SQL injection. per_page capped at 100.",
    "All handlers are sync def \u2014 enricher uses asyncio.run() internally; FastAPI runs sync handlers in a thread pool.",
]
add_bullet_list(slide, Inches(0.8), Inches(5.3), Inches(11.7), Inches(2.0),
                api_arch, font_size=14, bullet="\u2022  ", spacing=8)


# ── SLIDE 10: UI Dashboard ────────────────────────────────────────────────
slide = prs.slides.add_slide(blank_layout)
set_slide_bg(slide, OFF_WHITE)
add_subtitle_line(slide, "Roofing Lead Intelligence Platform \u2014 Aryaman Gupta | Instalily")
add_section_title(slide, "Dashboard UI: Instalily-Branded Design")

ui_features = [
    "Instalily design language: IBM Plex Sans/Mono, off-white #FEFFF7, sharp black borders, monospace uppercase eyebrows",
    "Floating dark gradient pill navigation with backdrop blur",
    "StatsBar: 4 metric cells (Total Leads, Top Leads, Avg Score, Enriched) in sharp-bordered grid",
    "FilterBar: Inline score tier pills (Hot 60+ / Warm / Cold) + certification filter pills + debounced search",
    "LeadTable: Sortable columns (score, name, volume, distance), paginated, ScorePill + CertBadge inline",
    "All filter/sort/page state synced to URL query params \u2014 every view is bookmarkable and shareable",
    "25 components total, zero external UI libraries \u2014 pure Tailwind CSS v4",
]
add_bullet_list(slide, Inches(0.8), Inches(1.8), Inches(11.7), Inches(5.0),
                ui_features, font_size=17, bullet="\u2022  ", spacing=12)


# ── SLIDE 11: UI Lead Detail ──────────────────────────────────────────────
slide = prs.slides.add_slide(blank_layout)
set_slide_bg(slide, OFF_WHITE)
add_subtitle_line(slide, "Roofing Lead Intelligence Platform \u2014 Aryaman Gupta | Instalily")
add_section_title(slide, "Lead Detail Page: 8 Insight Sections")

# Layout the 8 sections as cards
sections = [
    ("LeadHeader", "Name, score pill, cert badge,\nmeta (location, phone, website, yrs)"),
    ("ContactCard", "Decision-maker cards with\nemail / call / LinkedIn buttons"),
    ("WhyNowBanner", "Time-sensitive urgency signal\n(orange left-border accent)"),
    ("TalkingPoints", "Numbered list (01, 02, 03)\nmonospace formatting"),
    ("ScoreBreakdown", "5 labeled progress bars\nshowing each scoring factor"),
    ("InsightsGrid", "Buying signals (green) +\npain points (red) two-column"),
    ("DraftEmail", "Dark #171717 card with\none-click copy button"),
    ("ResearchSummary", "Collapsible text + citation\nsource pills (clickable)"),
]

card_w = Inches(2.7)
card_h = Inches(1.8)
gap_x = Inches(0.3)
gap_y = Inches(0.25)
start_x = Inches(0.6)
start_y = Inches(1.9)

for i, (name, desc) in enumerate(sections):
    col = i % 4
    row = i // 4
    x = start_x + col * (card_w + gap_x)
    y = start_y + row * (card_h + gap_y)
    add_card(slide, x, y, card_w, card_h, fill_color=WHITE, border_color=BLACK)
    add_textbox(slide, x + Inches(0.15), y + Inches(0.15), card_w - Inches(0.3), Inches(0.35),
                name, font_size=16, bold=True, color=BLACK, font_name=FONT_MONO)
    add_textbox(slide, x + Inches(0.15), y + Inches(0.55), card_w - Inches(0.3), Inches(1.0),
                desc, font_size=13, color=DARK_GRAY)

add_textbox(slide, Inches(0.8), Inches(6.2), Inches(11.7), Inches(0.5),
            "Lead detail is a server component \u2014 single fetch, data passed as props. Only CopyButton and ResearchSummary are client components.",
            font_size=14, color=MED_GRAY)


# ── SLIDE 12: Sales Intelligence Output ───────────────────────────────────
slide = prs.slides.add_slide(blank_layout)
set_slide_bg(slide, OFF_WHITE)
add_subtitle_line(slide, "Roofing Lead Intelligence Platform \u2014 Aryaman Gupta | Instalily")
add_section_title(slide, "What Sales Reps Actually Get")

add_textbox(slide, Inches(0.8), Inches(1.7), Inches(11.7), Inches(0.4),
            "Example: Grapevine Pro \u2014 Score 67 (Hot), President\u2019s Club, 449 reviews, Iselin NJ",
            font_size=17, bold=True, color=DARK_GRAY)

output_items = [
    'Score Breakdown: Certification 30/30 | Reviews 18/20 | Rating 9/10 | Biz Signals 10/20 | Why Now 0/20',
    'Talking Point: "Mention their 449 Google reviews \u2014 they clearly value reputation"',
    'Talking Point: "Ask about their storm restoration pipeline and material lead times"',
    'Buying Signal: "High volume of storm damage repair work"',
    'Buying Signal: "Recently expanded service area"',
    'Pain Point: "Current supplier has inconsistent delivery times (per Google reviews)"',
    'Why Now: "Major hailstorm hit their primary service area 3 weeks ago"',
    'Recommended Pitch: "Position as reliable, high-volume supplier for storm season..."',
    'Draft Email: Personalized outreach ready to copy and send',
    'Key Contact: Frank N. \u2014 Owner \u2014 email, phone, LinkedIn',
]
add_bullet_list(slide, Inches(0.8), Inches(2.3), Inches(11.7), Inches(4.5),
                output_items, font_size=16, bullet="\u2022  ", spacing=9)


# ── SLIDE 13: Testing ─────────────────────────────────────────────────────
slide = prs.slides.add_slide(blank_layout)
set_slide_bg(slide, OFF_WHITE)
add_subtitle_line(slide, "Roofing Lead Intelligence Platform \u2014 Aryaman Gupta | Instalily")
add_section_title(slide, "Testing: 119 Tests Across the Full Backend")

# Test categories
test_cats = [
    ("Service Layer (25 tests)", [
        "Pagination, all filter combinations, sort ordering",
        "NULL score handling, stats aggregation, score distribution bucketing",
    ]),
    ("API Endpoints (19 tests)", [
        "Full HTTP round-trip via FastAPI TestClient with in-memory SQLite (StaticPool)",
        "Response shapes, pagination metadata, 404 handling, input validation (422)",
    ]),
    ("Pipeline (75 tests)", [
        "Scraper parsing, research engine (async mocking), scoring deterministic functions",
        "Enricher orchestration, ORM model methods, certification tiers, citation extraction",
    ]),
]

cat_top = Inches(1.9)
for i, (category, items) in enumerate(test_cats):
    y = cat_top + i * Inches(1.5)
    add_textbox(slide, Inches(0.8), y, Inches(11.7), Inches(0.4),
                category, font_size=19, bold=True, color=BLACK)
    for j, item in enumerate(items):
        add_textbox(slide, Inches(1.1), y + Inches(0.45) + j * Inches(0.35),
                    Inches(11.0), Inches(0.35),
                    f"\u2022  {item}", font_size=15, color=DARK_GRAY)

add_textbox(slide, Inches(0.8), Inches(5.8), Inches(11.7), Inches(0.4),
            "Run with:  cd backend && uv run pytest -v",
            font_size=15, color=MED_GRAY, font_name=FONT_MONO)


# ── SLIDE 14: Tech Stack ──────────────────────────────────────────────────
slide = prs.slides.add_slide(blank_layout)
set_slide_bg(slide, OFF_WHITE)
add_subtitle_line(slide, "Roofing Lead Intelligence Platform \u2014 Aryaman Gupta | Instalily")
add_section_title(slide, "Tech Stack")

stack = [
    ("Layer", "Technology", "Why"),
    ("Frontend", "Next.js 16 + React 19 + Tailwind 4", "App Router, server components, brand styling"),
    ("Backend", "FastAPI + Python 3.9", "Async-native, auto-generated OpenAPI docs"),
    ("Research LLM", "Perplexity sonar-pro", "Web search with grounded citations"),
    ("Scoring LLM", "OpenAI gpt-4o-mini", "Structured JSON output, lowest cost"),
    ("Database", "SQLite (SQLAlchemy ORM)", "Zero-config, swap to Postgres with one line"),
    ("Scraping", "Playwright (Chromium)", "Bypasses Akamai bot detection, Coveo API interception"),
    ("CLI", "argparse + async", "Independent stage execution with --force, --limit, --concurrency"),
    ("Testing", "pytest (119 tests)", "In-memory SQLite, async mocking, TestClient"),
]

header_top = Inches(1.9)
col_widths = [Inches(1.5), Inches(4.0), Inches(6.0)]
col_starts = [Inches(0.8), Inches(2.3), Inches(6.3)]

for i, (layer, tech, why) in enumerate(stack):
    y = header_top + i * Inches(0.52)
    is_header = i == 0
    for j, (text, col_start, col_width) in enumerate(zip([layer, tech, why], col_starts, col_widths)):
        add_textbox(slide, col_start, y, col_width, Inches(0.45),
                    text, font_size=15 if not is_header else 14,
                    bold=is_header, color=BLACK if not is_header else MED_GRAY,
                    font_name=FONT_MONO if is_header else FONT_BODY)


# ── SLIDE 15: Scalability & Future ────────────────────────────────────────
slide = prs.slides.add_slide(blank_layout)
set_slide_bg(slide, OFF_WHITE)
add_subtitle_line(slide, "Roofing Lead Intelligence Platform \u2014 Aryaman Gupta | Instalily")
add_section_title(slide, "Scalability: Built to Grow")

scale_items = [
    ("Database \u2192 Postgres", "One connection string change. Add Alembic migrations, JSONB with GIN indexes, pgBouncer pooling."),
    ("Pipeline \u2192 Celery + Redis", "Async task queue for pipeline execution. Fan out scraping across ZIP codes in parallel workers."),
    ("Search \u2192 Full-Text + Semantic", "Postgres tsvector for name/address lookup. pgvector for semantic search over research summaries."),
    ("Auth \u2192 Multi-Tenant", "JWT authentication. Territory assignment \u2014 each rep sees leads in their region. Row-level security."),
    ("Observability", "Structured logging, LLM token/latency tracking, pipeline health dashboard with alerting."),
    ("Integrations", "CRM export (Salesforce, HubSpot). Email integration \u2014 send drafted emails from the platform."),
]

item_top = Inches(1.9)
for i, (title, desc) in enumerate(scale_items):
    y = item_top + i * Inches(0.85)
    add_textbox(slide, Inches(0.8), y, Inches(3.2), Inches(0.35),
                title, font_size=17, bold=True, color=BLACK)
    add_textbox(slide, Inches(4.2), y, Inches(8.5), Inches(0.7),
                desc, font_size=15, color=DARK_GRAY)


# ── SLIDE 16: Key Design Decisions (Q&A Prep) ─────────────────────────────
slide = prs.slides.add_slide(blank_layout)
set_slide_bg(slide, OFF_WHITE)
add_subtitle_line(slide, "Roofing Lead Intelligence Platform \u2014 Aryaman Gupta | Instalily")
add_section_title(slide, "Key Design Decisions")

decisions = [
    "Why Coveo API interception instead of DOM scraping?\n\u2192  Structured JSON is more reliable, faster, and survives UI redesigns. DOM parsing is fragile.",
    "Why Perplexity + OpenAI instead of one model?\n\u2192  Perplexity excels at grounded web search with citations. OpenAI excels at structured JSON output. Each does what it\u2019s best at.",
    "Why hybrid scoring instead of fully LLM?\n\u2192  Deterministic where objectively knowable (certifications, reviews). LLM where reading comprehension is required (growth signals, urgency). Reproducible + intelligent.",
    "Why SQLite instead of Postgres?\n\u2192  Zero-config for the demo. SQLAlchemy ORM makes the swap a one-line change. Schema is already Postgres-ready (JSONB, indexes).",
    "Why sync API handlers?\n\u2192  Enricher uses asyncio.run() internally. Async handlers would crash (nested event loops). FastAPI\u2019s thread pool handles this transparently.",
    "Why separate list vs. detail schemas?\n\u2192  List endpoint returns ~12 fields per row. Detail returns multi-KB text fields. Separate schemas avoid serializing research_summary for every table row.",
]
add_bullet_list(slide, Inches(0.8), Inches(1.8), Inches(11.7), Inches(5.2),
                decisions, font_size=15, bullet="", spacing=10)


# ── SLIDE 17: Numbers at a Glance ─────────────────────────────────────────
slide = prs.slides.add_slide(blank_layout)
set_slide_bg(slide, OFF_WHITE)
add_subtitle_line(slide, "Roofing Lead Intelligence Platform \u2014 Aryaman Gupta | Instalily")
add_section_title(slide, "By the Numbers")

metrics = [
    ("78", "Contractors scraped\nand enriched"),
    ("119", "Backend tests\npassing"),
    ("25", "Frontend\ncomponents"),
    ("~$0.05", "Total cost to score\nall 78 leads"),
    ("3", "AI enrichment\nstages"),
    ("6", "REST API\nendpoints"),
    ("11", "Pydantic\nschemas"),
    ("5", "Score breakdown\nfactors"),
]

metric_w = Inches(2.6)
metric_h = Inches(1.6)
metric_gap = Inches(0.3)
metric_start_x = Inches(0.6)
metric_top = Inches(1.9)

for i, (number, label) in enumerate(metrics):
    col = i % 4
    row = i // 4
    x = metric_start_x + col * (metric_w + metric_gap)
    y = metric_top + row * (metric_h + metric_gap)
    add_card(slide, x, y, metric_w, metric_h, fill_color=WHITE, border_color=BLACK)
    add_textbox(slide, x + Inches(0.15), y + Inches(0.15), metric_w - Inches(0.3), Inches(0.7),
                number, font_size=36, bold=True, color=BLACK, font_name=FONT_MONO,
                alignment=PP_ALIGN.CENTER)
    add_textbox(slide, x + Inches(0.15), y + Inches(0.9), metric_w - Inches(0.3), Inches(0.6),
                label, font_size=14, color=DARK_GRAY, alignment=PP_ALIGN.CENTER)


# ── SLIDE 18: Closing ─────────────────────────────────────────────────────
slide = prs.slides.add_slide(blank_layout)
set_slide_bg(slide, BLACK)

add_textbox(slide, Inches(0.8), Inches(1.8), Inches(11.7), Inches(1.0),
            "Roofing Lead Intelligence Platform",
            font_size=40, bold=True, color=WHITE)

closing_points = [
    "End-to-End Pipeline \u2014 Scrape, research, score, extract contacts, serve via API, display in dashboard",
    "Hybrid AI Scoring \u2014 Deterministic + LLM for reproducibility and intelligence",
    "Actionable Intelligence \u2014 Talking points, buying signals, pain points, draft emails, decision-maker contacts",
    "Production-Ready Architecture \u2014 119 tests, clean separation, scales to Postgres/Celery with minimal changes",
]
add_bullet_list(slide, Inches(0.8), Inches(3.2), Inches(11.7), Inches(2.8),
                closing_points, font_size=18, color=LIGHT_GRAY, bullet="\u2022  ", spacing=14)

add_textbox(slide, Inches(0.8), Inches(6.3), Inches(11.7), Inches(0.5),
            "Built by Aryaman Gupta for Instalily AI",
            font_size=16, color=MED_GRAY)


# ══════════════════════════════════════════════════════════════════════════
# SAVE
# ══════════════════════════════════════════════════════════════════════════
output_path = "/Users/aryamangupta/projects-github/instalily-onsite/RoofLeads_Presentation.pptx"
prs.save(output_path)
print(f"Saved to {output_path}")
print(f"Total slides: {len(prs.slides)}")
