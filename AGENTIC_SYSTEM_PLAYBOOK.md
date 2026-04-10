# Agentic System Build Playbook

A step-by-step guide for building a domain-specific AI agent with tool-calling, streaming, and a polished chat UI — optimized for a 3–4 hour time constraint.

---

## Philosophy

**Build the thinnest working vertical first, then layer polish.**

The goal is a working demo as early as possible (ideally by the halfway mark), then spend the remaining time adding features and UI polish. Every phase should end with something testable. Never write 30 minutes of code without verifying it works.

**Architecture over data volume.** 30 well-structured records demonstrate the same engineering as 3,000. Don't waste time on data scale — spend it on clean tool design and a good agent loop.

**Custom loop over frameworks.** A hand-written `while` loop with tool-calling is ~50 lines, fully debuggable, and easy to explain. LangChain/LlamaIndex add complexity without value for a system with <10 tools.

---

## Phase 0: Setup (15 min)

### Backend (Python + FastAPI)

```bash
mkdir backend && cd backend
uv init
uv add fastapi uvicorn sse-starlette python-dotenv

# Add your LLM SDK — pick ONE:
uv add google-genai        # Gemini (recommended — fast, cheap, good function calling)
# OR
uv add openai              # OpenAI
# OR
uv add anthropic           # Claude
```

Create `.env`:
```
LLM_API_KEY=your-key-here
```

Create `backend/app/__init__.py` (empty) and `backend/app/main.py`:
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load data into memory here
    print("Loading data...")
    # loader.load_all()
    print("Ready!")
    yield

app = FastAPI(title="Agent", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten for production
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

Verify: `uv run uvicorn app.main:app --reload --port 8000`

### Frontend (Next.js + Tailwind)

```bash
npx create-next-app@latest frontend --ts --tailwind --app --no-eslint
cd frontend && npm run dev
```

Verify: opens on `localhost:3000`.

**Don't write any real code yet.** Just confirm both services start.

---

## Phase 1: Data Layer (15 min)

### Structure Your Data

Whatever domain you're given, normalize it into a **keyed JSON dictionary** where each record has a unique ID. This is the single most important data decision — it enables O(1) lookups.

```
data/
  items.json          # Primary records keyed by unique ID
  relationships.json  # ID → [related IDs] mappings (e.g., compatibility, categories)
  knowledge.json      # Supplementary content (guides, articles, FAQs)
```

Example `items.json` structure (adapt fields to your domain):
```json
{
  "ITEM_001": {
    "id": "ITEM_001",
    "name": "...",
    "category": "...",
    "price": "...",
    "description": "...",
    "metadata_field_1": "...",
    "metadata_field_2": "...",
    "related_ids": ["ITEM_002", "ITEM_003"]
  }
}
```

### Write the Loader

```
backend/app/data/
  __init__.py
  loader.py
```

`loader.py` — Load JSON into module-level globals at startup:
```python
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"

items: dict[str, dict] = {}
relationships: dict[str, list[str]] = {}
knowledge: list[dict] = []

def load_all():
    global items, relationships, knowledge
    with open(DATA_DIR / "items.json") as f:
        items = json.load(f)
    with open(DATA_DIR / "relationships.json") as f:
        relationships = json.load(f)
    with open(DATA_DIR / "knowledge.json") as f:
        knowledge = json.load(f)
    print(f"Loaded: {len(items)} items, {len(relationships)} relationships, {len(knowledge)} knowledge entries")
```

Wire it into `main.py` lifespan. **Test now** — start the server, confirm data loads.

### Search (Keep It Simple)

Don't build vector search yet. Start with:
1. **Exact ID lookup** — `items.get(id)`
2. **Keyword search** — match query words against item name/description fields
3. **Category filter** — filter items by a category/type field

```python
def search_items(query: str, category: str | None = None, max_results: int = 5) -> list[dict]:
    query_lower = query.lower()
    
    # 1. Exact ID match
    item = items.get(query.upper())
    if item:
        return [item]
    
    # 2. Keyword scoring
    scored = []
    query_words = set(query_lower.split())
    for item_id, item in items.items():
        if category and item.get("category") != category:
            continue
        name_words = set(item.get("name", "").lower().split())
        overlap = len(query_words & name_words)
        if overlap > 0:
            scored.append((overlap, item))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:max_results]]
```

This is good enough for a demo. Mention vector search as a known improvement.

---

## Phase 2: Agent Loop + First Tool (30 min)

This is the most important phase. Everything else is layered on top of this.

### File Structure

```
backend/app/
  agent/
    __init__.py
    loop.py           # The core while-loop orchestrator
    system_prompt.py  # System prompt for the LLM
  tools/
    __init__.py
    registry.py       # Tool name → function mapping + LLM declarations
    search.py         # First tool: search items
```

### Build Order

**1. Write one tool function (5 min)**

`tools/search.py`:
```python
from app.data import loader
from app.data.search import search_items

def search(reasoning: str, query: str, category: str | None = None, max_results: int = 5) -> dict:
    results = search_items(query, category, max_results)
    if not results:
        return {"items": [], "message": "No results found. Try different search terms."}
    return {
        "items": results[:max_results],
        "message": f"Found {len(results)} result(s)",
    }
```

**2. Register it with LLM-compatible declarations (10 min)**

`tools/registry.py`:
```python
# Map tool names to functions
TOOL_FUNCTIONS = {
    "search": search,
}

# Return LLM-specific tool declarations (adapt to your LLM SDK)
def get_tool_declarations():
    ...

# Execute a tool by name
def execute_tool(name: str, args: dict) -> dict:
    func = TOOL_FUNCTIONS.get(name)
    if not func:
        return {"error": f"Unknown tool: {name}"}
    try:
        return func(**args)
    except Exception as e:
        return {"error": f"Tool {name} failed: {str(e)}"}
```

Key design decisions for tool declarations:
- Add a **`reasoning`** parameter to every tool (required). The LLM must explain why it's calling this tool. This improves routing accuracy via chain-of-thought and gives you a debug trail. The tool function ignores it.
- Write **detailed descriptions** in the declaration — the LLM reads these to decide which tool to call. Be specific about when to use each tool and what it returns.
- Use **enums** for constrained parameters (e.g., category types).

**3. Write the agent loop (15 min)**

`agent/loop.py` — this is the core:

```python
async def run_agent(messages: list[dict], session_id: str) -> AsyncGenerator[dict, None]:
    """The while-loop agent. Yields SSE event dicts."""
    
    # Optional: run a fast classifier BEFORE the LLM to filter/redirect
    # intent = classify(latest_message)
    # if intent == "off_topic": yield redirect message; return
    
    contents = convert_to_llm_format(messages)
    tools = get_tool_declarations()
    max_iterations = 5
    
    for i in range(max_iterations):
        # Call LLM with streaming
        stream = call_llm_stream(contents, tools)
        
        text_parts = []
        function_calls = []
        
        for chunk in stream:
            if chunk.has_text:
                text_parts.append(chunk.text)
                yield {"event": "text_delta", "data": chunk.text}
            if chunk.has_function_call:
                function_calls.append(chunk.function_call)
        
        # No tool calls = LLM is done, stream is complete
        if not function_calls:
            yield {"event": "done", "data": ""}
            return
        
        # Execute tool calls, emit status events
        for fc in function_calls:
            yield {"event": "status", "data": f"Running {fc.name}..."}
            result = execute_tool(fc.name, fc.args)
            
            # Emit structured events for UI rendering (product cards, etc.)
            for evt in emit_structured_events(fc.name, result):
                yield evt
        
        # Append tool call + results to conversation, loop again
        contents.append(model_response_with_tool_calls)
        contents.append(tool_results)
    
    yield {"event": "error", "data": "Too many steps. Try rephrasing."}
    yield {"event": "done", "data": ""}
```

The key insight: **the LLM decides the control flow, not you.** It reads the user message, picks a tool, reads the result, and either calls another tool or writes a final answer. Multi-intent queries ("find X and check if it's compatible with Y") work naturally because the LLM chains tool calls within a single turn.

**Test now** — call `run_agent` directly or via a quick script. Verify the LLM calls `search` when you ask "find [item]" and produces a response using the tool results.

---

## Phase 3: Chat Endpoint + Session Memory (15 min)

### Session Store

```python
# app/session/memory.py
class SessionStore:
    def __init__(self):
        self._sessions: dict[str, list[dict]] = {}
    
    def add_message(self, session_id: str, role: str, content: str):
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        self._sessions[session_id].append({"role": role, "content": content})
    
    def get_messages(self, session_id: str) -> list[dict]:
        return self._sessions.get(session_id, [])

store = SessionStore()
```

### SSE Endpoint

```python
# app/api/chat.py
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

router = APIRouter()

@router.post("/api/chat")
async def chat(request: ChatRequest):
    session_id = request.session_id
    store.add_message(session_id, "user", request.message)
    messages = store.get_messages(session_id)
    
    async def event_generator():
        assistant_text = ""
        async for event in run_agent(messages, session_id):
            if event["event"] == "text_delta":
                assistant_text += event["data"]
            yield event
        if assistant_text:
            store.add_message(session_id, "assistant", assistant_text)
    
    return EventSourceResponse(event_generator())
```

**Test now** — `curl -X POST localhost:8000/api/chat -H "Content-Type: application/json" -d '{"message": "find something", "session_id": "test1"}'`. Verify you get SSE events.

---

## Phase 4: Frontend Chat UI (45 min)

### Architecture

```
frontend/src/
  app/
    page.tsx              # Main chat page
    api/chat/route.ts     # Proxy to backend (avoids CORS issues)
    layout.tsx
    globals.css
  components/
    chat/
      ChatContainer.tsx   # Outer shell: header + message list + input
      MessageList.tsx      # Scrollable message area
      MessageBubble.tsx    # Single message (user or assistant)
      ChatInput.tsx        # Text input + send button
  hooks/
    useChat.ts            # Chat state management (useReducer)
    useSSE.ts             # SSE connection handler
    useSession.ts         # Session ID management
  lib/
    types.ts              # TypeScript interfaces
    constants.ts          # API paths, config
```

### Build Order

**1. Types + Constants (5 min)**

```typescript
// lib/types.ts
export type ContentBlock =
  | { type: "text"; text: string }
  | { type: "product_card"; data: Record<string, unknown> }  // extend later

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: ContentBlock[];
  timestamp: number;
  isStreaming?: boolean;
}

export interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  error: string | null;
  statusText: string | null;
}
```

**2. SSE Hook (10 min)**

```typescript
// hooks/useSSE.ts — handles the EventSource connection
// Parse SSE events: text_delta, status, done, error, and any structured events
// Call corresponding callbacks passed in by useChat
```

**3. Chat Hook with useReducer (10 min)**

```typescript
// hooks/useChat.ts
// Actions: ADD_USER_MESSAGE, ADD_ASSISTANT_MESSAGE, APPEND_TEXT_DELTA,
//          SET_STATUS, SET_ERROR, FINALIZE_STREAM, CLEAR_MESSAGES
// sendMessage() creates user + empty assistant messages, opens SSE stream
// Text deltas append to the last assistant message's last text block
```

**4. Components (20 min)**

Build in this order — each should be testable visually as you go:

1. **ChatInput** — text field + send button. Disable while streaming.
2. **MessageBubble** — render user (right-aligned, colored) vs assistant (left-aligned, neutral). Render markdown if time allows (`react-markdown`).
3. **MessageList** — map messages to bubbles, auto-scroll to bottom.
4. **ChatContainer** — header bar with title + "New Chat" button, wraps MessageList + ChatInput.

**5. API Proxy Route (5 min)**

```typescript
// app/api/chat/route.ts
export async function POST(req: Request) {
  const body = await req.json();
  const response = await fetch(`${BACKEND_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return new Response(response.body, {
    headers: { "Content-Type": "text/event-stream" },
  });
}
```

**Test now** — full round-trip. Type a message in the browser, see the agent stream a response. **This is your minimum viable demo.**

---

## Phase 5: Add Remaining Tools (30–45 min)

Now that the core works, add tools one at a time. For each:
1. Write the tool function
2. Add the function declaration to the registry
3. Test via the chat UI
4. Optionally emit a structured SSE event for rich UI rendering

### Common Tool Patterns

**Lookup tool** — retrieve full details for a specific item by ID:
```python
def get_details(reasoning: str, item_id: str) -> dict:
    item = loader.items.get(item_id.upper())
    if not item:
        return {"found": False, "message": "Item not found"}
    return {"found": True, **item}
```

**Relationship/compatibility tool** — check if two things are related:
```python
def check_relationship(reasoning: str, item_id: str, target_id: str) -> dict:
    related = loader.relationships.get(item_id, [])
    is_related = target_id in related
    return {
        "related": is_related,
        "confidence": "verified" if is_related else "not_in_data",
        "message": "..." 
    }
```

**Diagnosis/recommendation tool** — map a problem description to solutions:
```python
def diagnose(reasoning: str, description: str, category: str) -> dict:
    # Fuzzy match description against known problem → solution mappings
    # Return ranked causes + recommended items
    ...
```

**Guidance/how-to tool** — return step-by-step instructions:
```python
def get_guide(reasoning: str, item_id: str = None, topic: str = None) -> dict:
    # Look up by item ID or fuzzy-match topic against knowledge base
    ...
```

### Adding a Tool Checklist
- [ ] Write the function in `tools/`
- [ ] Add to `TOOL_FUNCTIONS` dict in `registry.py`
- [ ] Add `FunctionDeclaration` with detailed description
- [ ] Add examples to system prompt showing when to use it
- [ ] Test: ask a question that should trigger it, verify it does
- [ ] Optional: emit structured SSE event + add UI card component

---

## Phase 6: Guardrails / Classifier (15 min)

Add a **rule-based intent classifier** that runs BEFORE the LLM. This is zero-latency, zero-cost, and a strong architectural talking point.

```python
# agent/classifier.py
import re
from enum import Enum

class Intent(Enum):
    ON_TOPIC = "on_topic"
    GREETING = "greeting"
    OUT_OF_SCOPE = "out_of_scope"
    OFF_TOPIC = "off_topic"

def classify(message: str) -> Intent:
    text = message.strip()
    
    # Greeting (short standalone messages)
    if re.match(r"^\s*(hi|hello|hey|thanks|help)\s*[!.?]?\s*$", text, re.IGNORECASE):
        return Intent.GREETING
    
    # Domain-specific keywords → on-topic
    if DOMAIN_KEYWORDS.search(text):
        return Intent.ON_TOPIC
    
    # Adjacent-but-out-of-scope keywords → redirect with helpful message
    if OUT_OF_SCOPE_KEYWORDS.search(text):
        return Intent.OUT_OF_SCOPE
    
    # Short follow-ups in conversation context should pass through
    if len(text.split()) <= 4:
        return Intent.ON_TOPIC
    
    return Intent.OFF_TOPIC
```

Wire it into the agent loop:
```python
intent = classify(latest_message)
if intent == Intent.OFF_TOPIC:
    yield {"event": "text_delta", "data": OFF_TOPIC_REDIRECT}
    yield {"event": "done", "data": ""}
    return
```

**Three-layer defense:**
1. Classifier (regex, before LLM) — catches obvious off-topic
2. System prompt — instructs LLM to stay in scope
3. LLM's own judgment — handles edge cases

---

## Phase 7: Rich UI Components (30 min)

Structured SSE events enable rich cards instead of plain text. The backend emits typed events, the frontend renders matching components.

### Backend: Emit Structured Events

In the agent loop, after executing a tool, check the result and emit typed events:

```python
def emit_structured_events(tool_name: str, result: dict) -> list[dict]:
    events = []
    if tool_name == "search" and result.get("items"):
        for item in result["items"][:3]:
            events.append({"event": "item_card", "data": json.dumps(item)})
    elif tool_name == "check_relationship":
        events.append({"event": "relationship_result", "data": json.dumps(result)})
    return events
```

### Frontend: Render Content Blocks

Extend `ContentBlock` type:
```typescript
export type ContentBlock =
  | { type: "text"; text: string }
  | { type: "item_card"; data: ItemCardData }
  | { type: "relationship_result"; data: RelationshipData }
  | { type: "diagnosis"; data: DiagnosisData }
```

In `MessageBubble`, switch on block type and render the appropriate component. Buffer card blocks during streaming and flush them after text is done — this prevents cards from appearing mid-sentence.

### High-Impact UI Components (in priority order)

1. **Item/Product Card** — image, name, price/key-metric, link. This is the single biggest visual differentiator.
2. **Status indicator** — "Running search..." while tools execute.
3. **Starter prompts** — 3–4 clickable buttons on the empty chat state.
4. **Relationship/compatibility badge** — green check / red X / yellow question mark.
5. **Quick-reply suggestion buttons** — follow-up actions after the assistant responds.

---

## Phase 8: Polish (remaining time)

### System Prompt Refinement

The system prompt is the most underrated lever. Invest 10 minutes here:

```
You are a [domain] assistant. You help users [core use cases].

## Guidelines
- Be friendly, concise, and use markdown formatting
- Always include [key identifiers] when mentioning items
- When uncertain, say so — never fabricate information
- [Domain-specific safety/scope rules]

## Tool Usage Examples
### Example 1: [Common query type]
User: "[example message]"
→ Call [tool_name](reasoning="...", param="...")
→ [What to do with the result]

### Example 2: [Multi-step query]
User: "[example message]"
→ First call [tool_1], then call [tool_2] with results
→ Synthesize both results in response
```

Few-shot examples in the system prompt are the most reliable way to steer tool selection. Include 3–4 covering your main query types.

### Error Handling

- LLM API timeout → yield an error event with a friendly message
- Tool execution failure → return `{"error": "..."}` (the LLM reads this and explains it to the user)
- Empty user input → reject at the endpoint level
- Max iterations reached → "That's a complex question. Could you try rephrasing?"

### Visual Polish (if time remains)

- Typing / streaming indicator (animated dots)
- Smooth auto-scroll with `scrollIntoView({ behavior: "smooth" })`
- Responsive layout (chat should work on narrow widths)
- Header with app branding
- Timestamps on messages

---

## Architecture Talking Points

Have these ready to explain verbally:

**"Why a custom while-loop instead of LangChain?"**
> Our use case is N tools + 1 LLM — not complex enough to justify the abstraction tax. The custom loop is ~50 lines, fully debuggable, and handles multi-intent queries naturally by letting the LLM chain tool calls.

**"Why a regex classifier before the LLM?"**
> It filters off-topic queries at zero latency and zero cost. The LLM never sees "what's the weather?" — we catch it in microseconds with regex. This is a three-layer defense: classifier, system prompt, and LLM judgment.

**"Why the reasoning parameter on every tool?"**
> It forces chain-of-thought before tool selection, which measurably improves routing accuracy. It's also a free debug trail — I can see exactly why the LLM chose each tool.

**"How would you add a new domain/category?"**
> Three steps: (1) add the data file, (2) add keywords to the classifier, (3) update the system prompt scope. The tools and agent loop are domain-agnostic — they just operate on the data layer.

**"What would you improve with more time?"**
> (1) Vector search for semantic queries — the keyword search misses synonyms. (2) Async tool execution — sync calls block the event loop under concurrency. (3) Session eviction — the in-memory store is a memory leak. (4) Test suite for the classifier and tools.

---

## Quick Reference: SSE Event Types

| Event | When | Frontend Action |
|---|---|---|
| `text_delta` | LLM streams a text chunk | Append to current assistant message |
| `status` | Tool is being executed | Show "Running [tool]..." indicator |
| `item_card` | Tool returned an item to display | Render rich card component |
| `relationship_result` | Relationship/compatibility checked | Render badge (check/X/unknown) |
| `diagnosis` | Problem diagnosed with causes | Render diagnosis card with ranked causes |
| `suggestions` | LLM suggests follow-up actions | Render clickable quick-reply buttons |
| `error` | Something went wrong | Show error message in chat |
| `done` | Stream complete | Finalize assistant message, re-enable input |

---

## Checklist: Minimum Viable Demo

Before anything else, get these working end-to-end:

- [ ] Backend starts, data loads into memory
- [ ] One tool works (search/lookup)
- [ ] Agent loop calls the tool when appropriate and streams a response
- [ ] SSE endpoint returns events
- [ ] Frontend sends a message and displays streamed response
- [ ] Multi-turn conversation works (session memory)

Everything after this is additive value. If you hit this checklist by the halfway mark, you're in great shape.

---
---

# Appendix A: Data Scraping Reference

If the task requires scraping a website to build your dataset, this appendix covers the three main approaches — from fastest to most robust — with reusable patterns and code.

## Choosing a Scraping Approach

| Approach | Speed | Anti-Bot Handling | Cost | Best For |
|---|---|---|---|---|
| **BeautifulSoup + requests** | Fast (2-5 pages/sec) | None | Free | Server-rendered HTML, no JS needed |
| **Firecrawl API** | Medium (1 page/sec) | Built-in | Paid (credits) | Anti-bot sites, quick setup, markdown output |
| **Playwright (headless browser)** | Slow (0.3-1 page/sec) | Full (real browser) | Free | AJAX content, anti-bot bypass, model expansion |

**Decision flow:**
1. Try `requests` + BeautifulSoup first — it's instant to set up
2. If blocked (403, Cloudflare, Akamai) → use Firecrawl for speed or Playwright for free
3. If content loads via JavaScript (AJAX, "Load More" buttons) → Playwright

## Approach 1: BeautifulSoup + Requests (Fastest)

Works for server-rendered sites with no anti-bot protection.

```bash
uv add requests beautifulsoup4
```

```python
import requests
from bs4 import BeautifulSoup
import time
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}
DELAY = 1.0  # Be polite

def scrape_page(url: str) -> dict | None:
    """Fetch a page and extract structured data."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  ERROR: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Extract structured data — adapt selectors to target site
    title = soup.select_one("h1")
    price = soup.select_one(".price, [data-price], .product-price")
    description = soup.select_one(".description, .product-description, [itemprop='description']")
    image = soup.select_one("img.product-image, .gallery img, [itemprop='image']")

    return {
        "title": title.get_text(strip=True) if title else "",
        "price": price.get_text(strip=True) if price else "",
        "description": description.get_text(strip=True) if description else "",
        "image_url": image.get("src", "") if image else "",
        "source_url": url,
    }


def scrape_batch(urls: list[str], output_path: str):
    """Scrape a list of URLs with delay and checkpoint saves."""
    results = []
    for i, url in enumerate(urls):
        print(f"  [{i+1}/{len(urls)}] {url[:80]}...")
        data = scrape_page(url)
        if data:
            results.append(data)

        # Checkpoint every 50
        if len(results) % 50 == 0 and results:
            with open(output_path, "w") as f:
                json.dump(results, f, indent=2)

        time.sleep(DELAY)

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved {len(results)} items to {output_path}")
```

### Extracting JSON-LD (Structured Data Goldmine)

Many e-commerce sites embed structured data in `<script type="application/ld+json">` tags. This is the cleanest data source — no CSS selector guessing.

```python
import json
import re

def extract_jsonld(html: str) -> list[dict]:
    """Extract all JSON-LD structured data from a page."""
    pattern = r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>'
    matches = re.findall(pattern, html, re.S)

    results = []
    for match in matches:
        try:
            data = json.loads(match)
            if isinstance(data, list):
                results.extend(data)
            else:
                results.append(data)
        except json.JSONDecodeError:
            continue
    return results


def parse_product_jsonld(jsonld: dict) -> dict | None:
    """Extract product fields from a Product JSON-LD object."""
    if jsonld.get("@type") != "Product":
        return None

    offers = jsonld.get("offers", {})
    if isinstance(offers, list):
        offers = offers[0] if offers else {}

    rating = jsonld.get("aggregateRating", {})

    return {
        "name": jsonld.get("name", ""),
        "brand": jsonld.get("brand", {}).get("name", ""),
        "description": jsonld.get("description", ""),
        "price": offers.get("price", ""),
        "currency": offers.get("priceCurrency", "USD"),
        "in_stock": offers.get("availability", "").endswith("InStock"),
        "rating": rating.get("ratingValue", ""),
        "review_count": rating.get("reviewCount", ""),
        "image_url": jsonld.get("image", ""),
        "sku": jsonld.get("sku", ""),
    }
```

## Approach 2: Firecrawl API (Anti-Bot, Markdown Output)

Firecrawl handles JavaScript rendering and anti-bot protection. Returns clean markdown — ideal for LLM consumption and embedding.

```bash
uv add firecrawl-py python-dotenv
# Get API key from https://firecrawl.dev
```

```python
import os
from firecrawl import FirecrawlApp
from dotenv import load_dotenv

load_dotenv()
app = FirecrawlApp(api_key=os.environ["FIRECRAWL_API_KEY"])

# --- Single page scrape ---
result = app.scrape("https://example.com/product/123", formats=["markdown", "html"])
markdown = result.markdown    # Clean markdown text
html = result.html            # Raw HTML (for JSON-LD extraction)
metadata = result.metadata    # Page title, description, etc.

# --- Discover URLs via site map ---
urls = app.map("https://example.com", search="products", limit=500)
# Returns list of URLs matching the search query

# --- Batch scrape with resume support ---
import json
import time

OUTPUT = "data/items.json"
DELAY = 1.5

def scrape_with_firecrawl(urls: list[str]):
    # Load existing results for resume support
    existing = {}
    if os.path.exists(OUTPUT):
        with open(OUTPUT) as f:
            for item in json.load(f):
                existing[item["url"]] = item

    results = list(existing.values())

    for i, url in enumerate(urls):
        if url in existing:
            print(f"  [{i+1}/{len(urls)}] SKIP (cached)")
            continue

        print(f"  [{i+1}/{len(urls)}] Scraping...")
        try:
            result = app.scrape(url, formats=["markdown"])
            md = result.markdown or ""

            if md and "Page Not Found" not in md:
                parsed = parse_markdown(md, url)  # Your parsing function
                results.append(parsed)
        except Exception as e:
            print(f"    ERROR: {e}")

        # Checkpoint every 10
        if i % 10 == 0:
            with open(OUTPUT, "w") as f:
                json.dump(results, f, indent=2)

        time.sleep(DELAY)

    with open(OUTPUT, "w") as f:
        json.dump(results, f, indent=2)
```

### Parsing Firecrawl Markdown

Firecrawl returns the full page as markdown. You need regex patterns to extract structured fields from it.

```python
import re

def parse_markdown(md: str, url: str) -> dict:
    """Extract structured data from Firecrawl markdown output.
    Adapt these patterns to the target site's markdown structure.
    Run a 'recon' scrape of 1 page first to see the actual format."""

    data = {"source_url": url, "raw_markdown": md[:8000]}

    # Title (H1)
    h1 = re.search(r"^#\s+(.+)", md, re.M)
    if h1:
        data["name"] = h1.group(1).strip()

    # Price — look for dollar amounts near stock status
    price = re.search(r"\$(\d{1,4}\.\d{2})", md)
    if price:
        data["price"] = price.group(1)

    # Stock status
    data["in_stock"] = bool(re.search(r"In Stock", md[:2000]))

    # Rating — e.g. "4.9" near "Reviews"
    rating = re.search(r"(\d\.\d)\s*(?:out of 5|stars?|\n)", md)
    if rating:
        data["rating"] = rating.group(1)

    # Review count
    reviews = re.search(r"(\d+)\s+Reviews?", md)
    if reviews:
        data["review_count"] = reviews.group(1)

    # Linked items — URLs in markdown links
    links = re.findall(r'\[([^\]]+)\]\((https?://[^)]+)\)', md)
    data["related_links"] = [{"text": t, "url": u} for t, u in links[:20]]

    # Images — first product image URL
    images = re.findall(r'!\[.*?\]\((https?://[^)]+\.(?:jpg|png|webp))\)', md)
    if images:
        data["image_url"] = images[0]

    return data
```

**Key tip:** Always run a **recon scrape** first — scrape 1 page, save the raw markdown, and study its structure before writing your parser. Every site's markdown looks different.

## Approach 3: Playwright (Headless Browser)

For sites with AJAX-loaded content, "Load More" buttons, or aggressive anti-bot protection.

```bash
uv add playwright playwright-stealth html2text
uv run playwright install chromium
```

```python
import asyncio
import random
import html2text
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

class BrowserScraper:
    """Scrapes pages using a real headless Chromium browser."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._browser = None
        self._context = None
        self._stealth = Stealth()
        self._converter = html2text.HTML2Text()
        self._converter.body_width = 0
        self._converter.ignore_images = False

    async def start(self):
        """Launch browser with stealth settings."""
        pw = await async_playwright().start()
        self._browser = await pw.chromium.launch(headless=self.headless)
        self._context = await self._browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )

    async def stop(self):
        if self._browser:
            await self._browser.close()

    async def scrape_page(self, url: str) -> dict | None:
        """Navigate to a URL and extract page content."""
        page = await self._context.new_page()
        await self._stealth.apply_stealth(page)

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)

            # Optional: click "Load More" / "Show All" buttons
            # try:
            #     await page.click("button:text('Show All')", timeout=3000)
            #     await page.wait_for_timeout(2000)
            # except:
            #     pass

            # Get page content
            html = await page.content()

            # Strip boilerplate (nav, footer, scripts)
            html = await page.evaluate("""
                () => {
                    for (const sel of ['header', 'footer', 'nav', 'script', 'style']) {
                        document.querySelectorAll(sel).forEach(el => el.remove());
                    }
                    const main = document.querySelector('main, [role="main"], .main-content');
                    return (main || document.body).innerHTML;
                }
            """)

            # Convert to markdown
            markdown = self._converter.handle(html)

            return {"markdown": markdown, "html": html, "url": url}

        except Exception as e:
            print(f"  Browser error: {e}")
            return None
        finally:
            await page.close()
            # Random delay to avoid detection
            await asyncio.sleep(random.uniform(1.0, 3.0))


# Usage
async def main():
    scraper = BrowserScraper(headless=True)
    await scraper.start()

    urls = ["https://example.com/page1", "https://example.com/page2"]
    for url in urls:
        data = await scraper.scrape_page(url)
        if data:
            print(f"Got {len(data['markdown'])} chars from {url}")

    await scraper.stop()

asyncio.run(main())
```

### Parallel Scraping with Slices

For large scrapes, split URLs across multiple terminal processes:

```python
# Usage: python scraper.py --slice 1/4   (runs in terminal 1)
#        python scraper.py --slice 2/4   (runs in terminal 2)
#        python scraper.py --slice 3/4   (runs in terminal 3)
#        python scraper.py --slice 4/4   (runs in terminal 4)

def get_slice(items: list, slice_spec: str) -> list:
    """Split items for parallel processing. '2/4' = 2nd of 4 slices."""
    current, total = map(int, slice_spec.split("/"))
    chunk_size = len(items) // total
    start = (current - 1) * chunk_size
    end = start + chunk_size if current < total else len(items)
    return items[start:end]
```

After all slices finish, merge results:
```python
def merge_slices(output_dir: str, final_path: str):
    """Combine slice output files into one."""
    import glob
    all_items = {}
    for path in sorted(glob.glob(f"{output_dir}/items_slice_*.json")):
        with open(path) as f:
            for item in json.load(f):
                all_items[item["id"]] = item  # Deduplicate by ID
    with open(final_path, "w") as f:
        json.dump(list(all_items.values()), f, indent=2)
    print(f"Merged {len(all_items)} items into {final_path}")
```

## Post-Scrape: Building Indexes

After scraping, transform raw data into the structures your agent needs.

```python
def build_indexes(items: list[dict], output_dir: str):
    """Build derived indexes from scraped items."""

    # 1. Primary lookup: ID → full item
    items_by_id = {}
    for item in items:
        items_by_id[item["id"]] = item

    # 2. Relationship index: target_id → [item_ids]
    # e.g., model_number → [compatible part IDs]
    relationships = {}
    for item in items:
        for related_id in item.get("compatible_with", []):
            relationships.setdefault(related_id, []).append(item["id"])

    # 3. Category index: category → [item_ids]
    categories = {}
    for item in items:
        cat = item.get("category", "other")
        categories.setdefault(cat, []).append(item["id"])

    # 4. Symptom/problem index: symptom → [item_ids]
    symptoms = {}
    for item in items:
        for symptom in item.get("symptoms_fixed", []):
            symptoms.setdefault(symptom.lower(), []).append(item["id"])

    # Save all
    for name, data in [
        ("items_by_id.json", items_by_id),
        ("relationships.json", relationships),
        ("categories.json", categories),
        ("symptoms_index.json", symptoms),
    ]:
        with open(f"{output_dir}/{name}", "w") as f:
            json.dump(data, f, indent=2)
        print(f"  Saved {name}: {len(data)} entries")
```

---

# Appendix B: Vector Embedding Reference

If time allows and you want semantic search (improves natural language queries significantly), here's the pattern.

## When to Add Embeddings

**Skip if:** your data has strong identifiers (IDs, model numbers) and keyword search covers most queries. Keyword search is good enough for a demo.

**Add if:** users will ask things like "the thing that makes ice" or "my fridge is dripping water from the bottom" — natural language that doesn't match exact field values.

## Setup: ChromaDB + Gemini Embeddings

```bash
uv add chromadb google-genai
```

```python
# app/data/embeddings.py
from google import genai
from app.config import LLM_API_KEY, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=LLM_API_KEY)
    return _client

def embed_query(text: str) -> list[float]:
    """Embed a single search query."""
    result = _get_client().models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config={"task_type": "RETRIEVAL_QUERY", "output_dimensionality": EMBEDDING_DIMENSIONS},
    )
    return result.embeddings[0].values

def embed_texts(texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    """Batch embed documents (max 100 per call for Gemini)."""
    result = _get_client().models.embed_content(
        model=EMBEDDING_MODEL,
        contents=texts,
        config={"task_type": task_type, "output_dimensionality": EMBEDDING_DIMENSIONS},
    )
    return [e.values for e in result.embeddings]
```

```python
# app/data/chroma_store.py
import chromadb
from app.config import CHROMA_DIR

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return _client

def get_items_collection():
    return _get_client().get_or_create_collection("items", metadata={"hnsw:space": "cosine"})

def get_knowledge_collection():
    return _get_client().get_or_create_collection("knowledge", metadata={"hnsw:space": "cosine"})

def query_items(embedding: list[float], n_results: int = 5, where: dict = None) -> dict:
    kwargs = {"query_embeddings": [embedding], "n_results": n_results}
    if where:
        kwargs["where"] = where
    return get_items_collection().query(**kwargs)
```

## One-Time Embedding Script

Run once after scraping to populate ChromaDB:

```python
# scripts/embed_items.py
"""Embed all items into ChromaDB. Run once after scraping."""

import json
from app.data.chroma_store import get_items_collection
from app.data.embeddings import embed_texts

BATCH_SIZE = 50  # Gemini API batch limit

def build_search_document(item: dict) -> str:
    """Build a text document optimized for embedding search.
    Combine the fields a user would naturally search for."""
    lines = []
    lines.append(f"{item.get('name', '')} by {item.get('brand', '')}.")
    if item.get("category"):
        lines.append(f"Category: {item['category']}.")
    if item.get("description"):
        lines.append(item["description"][:500])
    if item.get("symptoms_fixed"):
        lines.append(f"Fixes: {', '.join(item['symptoms_fixed'])}.")
    return "\n".join(lines)

def main():
    with open("data/items_by_id.json") as f:
        items = json.load(f)

    ids = list(items.keys())
    documents = [build_search_document(items[id]) for id in ids]
    metadatas = [{"category": items[id].get("category", ""), "brand": items[id].get("brand", "")} for id in ids]

    collection = get_items_collection()

    for i in range(0, len(documents), BATCH_SIZE):
        batch_docs = documents[i:i+BATCH_SIZE]
        batch_ids = ids[i:i+BATCH_SIZE]
        batch_meta = metadatas[i:i+BATCH_SIZE]

        embeddings = embed_texts(batch_docs, task_type="RETRIEVAL_DOCUMENT")
        collection.upsert(ids=batch_ids, documents=batch_docs, embeddings=embeddings, metadatas=batch_meta)

        print(f"  Batch {i//BATCH_SIZE + 1}: {len(batch_docs)} items embedded")

    print(f"Done: {collection.count()} items in ChromaDB")

if __name__ == "__main__":
    main()
```

## Using Embeddings in Search

Upgrade your keyword search to hybrid:

```python
def search_hybrid(query: str, category: str = None, max_results: int = 5) -> list[dict]:
    """Hybrid search: exact ID → semantic → keyword → merge with RRF."""

    # 1. Exact ID match (fastest)
    if is_id_pattern(query):
        item = items.get(query.upper())
        if item:
            return [item]

    # 2. Semantic search via ChromaDB
    embedding = embed_query(query)
    where = {"category": category} if category else None
    chroma_results = query_items(embedding, n_results=max_results, where=where)
    semantic_items = [items[id] for id in chroma_results["ids"][0] if id in items]

    # 3. Keyword fallback
    keyword_items = keyword_search(query, max_results)

    # 4. Merge with Reciprocal Rank Fusion
    return reciprocal_rank_fusion([semantic_items, keyword_items])[:max_results]


def reciprocal_rank_fusion(result_lists: list[list[dict]], k: int = 60) -> list[dict]:
    """Merge ranked lists. RRF score = sum(1 / (k + rank)) across lists."""
    scores = {}
    item_map = {}
    for results in result_lists:
        for rank, item in enumerate(results):
            item_id = item.get("id", "")
            scores[item_id] = scores.get(item_id, 0) + 1.0 / (k + rank + 1)
            item_map[item_id] = item
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [item_map[id] for id, _ in ranked]
```

## Embedding Knowledge (Guides, Articles, FAQs)

For longer documents, chunk by heading before embedding:

```python
import re

def chunk_by_heading(markdown: str, title: str) -> list[tuple[str, str]]:
    """Split markdown into (heading, content) chunks at ## boundaries."""
    splits = re.split(r"(?:^|\n)## (.+)", markdown)
    chunks = []

    # Content before first heading
    if splits[0].strip():
        chunks.append((title, splits[0].strip()))

    # Pair headings with content
    for i in range(1, len(splits), 2):
        heading = splits[i].strip()
        content = splits[i+1].strip() if i+1 < len(splits) else ""
        if content:
            chunks.append((heading, content))

    return chunks if chunks else [(title, markdown.strip())]
```

---

# Appendix C: Scraping Best Practices

1. **Always start with a recon scrape.** Scrape 1 page, save the raw output, and study its structure before writing parsers. This saves hours of blind regex debugging.

2. **Respect rate limits.** Use 1-2 second delays between requests. Set a polite User-Agent. Check `robots.txt`.

3. **Build in resume support.** Save checkpoints every N items. On restart, skip already-scraped URLs. Long scrapes will fail partway through — plan for it.

4. **Deduplicate by unique ID.** Use `dict[id] = item` rather than a list to naturally prevent duplicates when merging or resuming.

5. **Separate scraping from parsing.** Save raw HTML/markdown first, then parse. This lets you re-parse without re-scraping when you fix regex patterns.

6. **Prefer JSON-LD over CSS selectors.** Many sites embed `<script type="application/ld+json">` with structured product data. This is more stable than CSS selectors which break on redesigns.

7. **Validate after scraping.** Count records, check for empty fields, verify key fields (prices, IDs) are populated. Print summary stats.

8. **Keep raw data.** Store the raw markdown/HTML (truncated to ~8KB) alongside parsed fields. This lets you re-extract fields later without re-scraping.

9. **Use parallel slices for large scrapes.** Split URLs across N terminal processes. Merge results afterward. This turns a 4-hour scrape into a 1-hour scrape.

10. **Time budget:** For an interview, scraping should take at most 15-20 minutes. Aim for 30-50 records with clean structure rather than thousands of messy ones.
