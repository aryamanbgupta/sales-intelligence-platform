import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- Paths ---
PROJECT_ROOT = Path(__file__).parent.parent.parent  # instalily-onsite/
BACKEND_ROOT = Path(__file__).parent.parent          # backend/
DB_PATH = BACKEND_ROOT / "data" / "leads.db"

# --- API Keys ---
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# --- Perplexity Config ---
PERPLEXITY_BASE_URL = "https://api.perplexity.ai"
PERPLEXITY_MODEL = "sonar-pro"
PERPLEXITY_MAX_TOKENS = 4096
PERPLEXITY_TEMPERATURE = 0.2

# --- GAF Scraper Config ---
GAF_BASE_URLS = {
    "residential": "https://www.gaf.com/en-us/roofing-contractors/residential",
    "commercial": "https://www.gaf.com/en-us/roofing-contractors/commercial",
}
GAF_BASE_URL = GAF_BASE_URLS["residential"]  # default
COVEO_API_URL = "https://platform.cloud.coveo.com/rest/search/v2"
COVEO_ORG_ID = "gafmaterialscorporationproduction3yalqk12"
SCRAPER_RESULTS_PER_PAGE = 50           # max results per Coveo API call

# --- OpenAI Scoring Config ---
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_SCORING_MAX_TOKENS = 2048
OPENAI_SCORING_TEMPERATURE = 0.3

# --- Pipeline Config ---
ENRICHMENT_BATCH_SIZE = 10              # contractors per batch
ENRICHMENT_DELAY_SECONDS = 1.0          # delay between API calls (rate limiting)
MAX_RETRIES = 3                         # retries per contractor on transient failure
RETRY_BACKOFF_BASE = 2.0                # exponential backoff base (seconds)

# --- Database ---
DATABASE_URL = f"sqlite:///{DB_PATH}"
