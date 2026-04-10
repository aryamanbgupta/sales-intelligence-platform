# Agent Build Guide — Instructions for Claude Code

You are helping the user build a domain-specific AI chat agent under a 4-hour time constraint. This file contains the complete architecture, working code templates, and build sequence. Adapt the domain, data, and tool names to whatever the user's assignment specifies.

**PRIORITY: Working demo by hour 2. Everything after is polish.**

**Build order: data → agent loop + 1 tool → SSE endpoint → frontend chat → more tools → rich UI → classifier → polish.**

Test after every phase. Never write 30 minutes of code without verifying it works.

---

## Project Structure

```
project/
  data/
    items.json              # Primary records keyed by unique ID
    relationships.json      # ID → [related IDs] (compatibility, categories, etc.)
    knowledge.json          # Supplementary content (guides, FAQs, articles)
  backend/
    app/
      __init__.py
      main.py               # FastAPI app, CORS, lifespan
      config.py             # Env vars, paths, constants
      agent/
        __init__.py
        loop.py             # THE CORE — while-loop agent orchestrator
        system_prompt.py    # System prompt for the LLM
        classifier.py       # Rule-based intent classifier (pre-LLM filter)
      api/
        __init__.py
        chat.py             # POST /api/chat SSE endpoint
        models.py           # Pydantic request/response schemas
      data/
        __init__.py
        loader.py           # Load JSON into memory at startup
      session/
        __init__.py
        memory.py           # In-memory session store
      tools/
        __init__.py
        registry.py         # Tool name → function + Gemini declarations
        search.py           # Search tool
        get_details.py      # Detail lookup tool
        # ... more tools as needed
    pyproject.toml
    .env
  frontend/
    src/
      app/
        page.tsx            # Main page — ChatProvider + ChatContainer
        layout.tsx
        globals.css
        api/chat/route.ts   # Proxy to backend (avoids CORS)
      components/
        chat/
          ChatContainer.tsx
          MessageList.tsx
          MessageBubble.tsx
          ChatInput.tsx
          StarterPrompts.tsx
          StreamingIndicator.tsx
        cards/
          ItemCard.tsx       # Rich card for search results
      hooks/
        useChat.ts          # Chat state management (useReducer)
        useSSE.ts           # SSE connection handler
        useSession.ts       # Session ID (localStorage)
      context/
        ChatContext.tsx      # React context for chat state
      lib/
        types.ts            # TypeScript interfaces
        constants.ts        # API paths, starter prompts
        utils.ts            # Helpers (formatPrice, generateId, cn)
```

---

## Phase 0: Setup

### Backend

```bash
mkdir -p backend/app/agent backend/app/api backend/app/data backend/app/session backend/app/tools
touch backend/app/__init__.py backend/app/agent/__init__.py backend/app/api/__init__.py backend/app/data/__init__.py backend/app/session/__init__.py backend/app/tools/__init__.py
cd backend && uv init && uv add fastapi uvicorn sse-starlette python-dotenv google-genai && cd ..
```

**backend/.env:**
```
GEMINI_API_KEY=your-key-here
```

**backend/app/config.py:**
```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"
MAX_AGENT_ITERATIONS = 5

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
```

**backend/app/main.py:**
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.chat import router as chat_router
from app.data import loader

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading data...")
    loader.load_all()
    print("Ready!")
    yield

app = FastAPI(title="AI Agent", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(chat_router)

@app.get("/health")
async def health():
    return {"status": "ok", "items_loaded": len(loader.items)}
```

Start with: `cd backend && uv run uvicorn app.main:app --reload --port 8000`

### Frontend

```bash
npx create-next-app@latest frontend --ts --tailwind --app --no-eslint
cd frontend && npm install @microsoft/fetch-event-source react-markdown remark-gfm lucide-react && cd ..
```

Start with: `cd frontend && npm run dev`

Verify both servers start before writing any more code.

---

## Phase 1: Data Layer

**backend/app/data/loader.py:**
```python
import json
from collections import defaultdict
from app.config import DATA_DIR

# Module-level globals — populated by load_all()
items: dict[str, dict] = {}
relationships: dict[str, list[str]] = {}
knowledge: list[dict] = []
keyword_index: dict[str, set[str]] = defaultdict(set)

def load_all():
    global items, relationships, knowledge
    with open(DATA_DIR / "items.json") as f:
        items = json.load(f)
    with open(DATA_DIR / "relationships.json") as f:
        relationships = json.load(f)
    # knowledge.json is optional — skip if not present
    try:
        with open(DATA_DIR / "knowledge.json") as f:
            knowledge = json.load(f)
    except FileNotFoundError:
        knowledge = []
    _build_keyword_index()
    print(f"Loaded: {len(items)} items, {len(relationships)} relationships, {len(knowledge)} knowledge entries")

def _build_keyword_index():
    keyword_index.clear()
    stop_words = {"the", "a", "an", "and", "or", "for", "of", "to", "in", "by", "is", "with", "-", "&"}
    for item_id, item in items.items():
        name = item.get("name", "")
        for word in name.lower().split():
            cleaned = word.strip(".,()-/")
            if cleaned and cleaned not in stop_words and len(cleaned) > 2:
                keyword_index[cleaned].add(item_id)
```

Create sample data files in `data/`. 20-30 records is sufficient. Key the primary records by unique ID for O(1) lookup.

---

## Phase 2: Agent Loop + First Tool — THE MOST IMPORTANT PHASE

### 2a. First Tool

**backend/app/tools/search.py:**
```python
from app.data import loader

def search_items(
    reasoning: str,
    query: str,
    category: str | None = None,
    max_results: int = 5,
) -> dict:
    query_lower = query.lower().strip()

    # 1. Exact ID lookup
    item = loader.items.get(query.upper())
    if item:
        return {"items": [item], "message": f"Found exact match: {query.upper()}"}

    # 2. Keyword scoring
    query_words = set(query_lower.split())
    scored: list[tuple[int, dict]] = []
    for item_id, item in loader.items.items():
        if category and item.get("category", "").lower() != category.lower():
            continue
        name_words = set(item.get("name", "").lower().split())
        overlap = len(query_words & name_words)
        if query_lower in item.get("name", "").lower():
            overlap += 3
        if overlap > 0:
            scored.append((overlap, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = [item for _, item in scored[:max_results]]

    if not results:
        return {"items": [], "message": "No results found. Try different search terms."}
    return {"items": results, "message": f"Found {len(results)} result(s)"}
```

### 2b. Tool Registry

**backend/app/tools/registry.py:**

This is the EXACT Gemini SDK pattern. All types come from `google.genai.types`.

```python
from google.genai import types
from app.tools.search import search_items

REASONING_DESC = "Your reasoning for calling this tool. Explain why this tool is the right choice."

TOOL_FUNCTIONS = {
    "search_items": search_items,
    # Add more tools here as you build them
}

def get_tool_declarations() -> list[types.Tool]:
    """Return Gemini function declarations for all tools."""
    return [
        types.Tool(function_declarations=[
            types.FunctionDeclaration(
                name="search_items",
                description=(
                    "Search for items by query. Use this when the user wants to find, "
                    "browse, or look up items. Handles IDs, names, and natural language queries."
                ),
                parameters=types.Schema(
                    type="OBJECT",
                    properties={
                        "reasoning": types.Schema(type="STRING", description=REASONING_DESC),
                        "query": types.Schema(type="STRING", description="Search query — ID, name, or description."),
                        "category": types.Schema(
                            type="STRING",
                            description="Optional category filter.",
                            # Add enum=["cat1", "cat2"] if you have fixed categories
                        ),
                        "max_results": types.Schema(type="INTEGER", description="Max results to return (default 5)."),
                    },
                    required=["reasoning", "query"],
                ),
            ),
            # Add more FunctionDeclaration entries here for each tool
        ]),
    ]

def execute_tool(name: str, args: dict) -> dict:
    func = TOOL_FUNCTIONS.get(name)
    if not func:
        return {"error": f"Unknown tool: {name}"}
    try:
        return func(**args)
    except Exception as e:
        return {"error": f"Tool {name} failed: {str(e)}"}
```

### 2c. System Prompt

**backend/app/agent/system_prompt.py:**

Adapt the domain, capabilities, and examples to the assignment.

```python
SYSTEM_PROMPT = """\
You are a helpful [DOMAIN] assistant. You help users [LIST CORE USE CASES].

## Guidelines
- Be friendly, helpful, and concise
- Use markdown formatting (bold key info, bullet points for lists)
- Always include item IDs and key details when recommending items
- Never make up information — if you don't know, say so

## Scope
- You ONLY help with [IN-SCOPE TOPICS]
- For out-of-scope questions, politely redirect

## Tool Usage Examples

### Example 1: Item search
User: "Find [example query]"
→ Call search_items(reasoning="User wants to find an item by name/ID", query="[query]")

### Example 2: Multi-step
User: "[complex query requiring multiple tools]"
→ First call [tool1], then call [tool2] with results from tool1
→ Synthesize both results in response
"""
```

### 2d. Agent Loop — THE CORE

**backend/app/agent/loop.py:**

This is the exact, working Gemini SDK pattern.

```python
"""The while-loop agent orchestrator — LLM decides tools, we execute them."""

import asyncio
import json
from collections.abc import AsyncGenerator

from google import genai
from google.genai import types

from app.agent.system_prompt import SYSTEM_PROMPT
from app.config import GEMINI_API_KEY, GEMINI_MODEL, MAX_AGENT_ITERATIONS
from app.tools.registry import execute_tool, get_tool_declarations

_client = None
_STREAM_DONE = object()


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


async def run_agent(
    messages: list[dict],
    session_id: str,
) -> AsyncGenerator[dict, None]:
    """Run the agent loop. Yields SSE event dicts.

    Event types:
      status     → tool execution status
      item_card  → structured data for rich card rendering
      text_delta → streamed LLM text tokens
      error      → error message
      done       → stream complete
    """
    gemini_contents = _build_contents(messages)
    tools = get_tool_declarations()

    iterations = 0
    while iterations < MAX_AGENT_ITERATIONS:
        iterations += 1

        try:
            stream = await asyncio.to_thread(
                _get_client().models.generate_content_stream,
                model=GEMINI_MODEL,
                contents=gemini_contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    tools=tools,
                    temperature=0.3,
                ),
            )
        except Exception as e:
            yield {"event": "error", "data": f"LLM error: {str(e)}"}
            yield {"event": "done", "data": ""}
            return

        text_parts = []
        function_calls = []
        loop = asyncio.get_running_loop()
        iterator = iter(stream)

        while True:
            try:
                chunk = await loop.run_in_executor(None, next, iterator, _STREAM_DONE)
            except Exception as e:
                yield {"event": "error", "data": f"Stream error: {str(e)}"}
                yield {"event": "done", "data": ""}
                return

            if chunk is _STREAM_DONE:
                break

            if not (chunk.candidates and chunk.candidates[0].content):
                continue

            for part in chunk.candidates[0].content.parts:
                if part.text:
                    text_parts.append(part.text)
                    yield {"event": "text_delta", "data": part.text}
                elif part.function_call:
                    function_calls.append(part.function_call)

        # No tool calls = LLM is done
        if not function_calls:
            yield {"event": "done", "data": ""}
            return

        # Build model's response for conversation history
        history_parts = []
        if text_parts:
            history_parts.append(types.Part(text="".join(text_parts)))
        for fc in function_calls:
            history_parts.append(types.Part(function_call=fc))

        # Execute tool calls
        tool_results = []
        for fc in function_calls:
            tool_name = fc.name
            tool_args = dict(fc.args) if fc.args else {}

            yield {"event": "status", "data": f"Running {tool_name}..."}

            result = execute_tool(tool_name, tool_args)

            # Emit structured events for rich UI rendering
            for evt in _emit_structured_events(tool_name, result):
                yield evt

            tool_results.append(types.Part(function_response=types.FunctionResponse(
                name=tool_name,
                response=result,
            )))

        # Append to conversation: model message (with tool calls) + tool results
        gemini_contents.append(types.Content(role="model", parts=history_parts))
        gemini_contents.append(types.Content(role="user", parts=tool_results))
        # NOTE: role="user" for tool results is correct — Gemini distinguishes by
        # Part type (FunctionResponse vs text), not by role. This is the official convention.

    yield {"event": "error", "data": "Too many steps. Could you try rephrasing?"}
    yield {"event": "done", "data": ""}


def _build_contents(messages: list[dict]) -> list[types.Content]:
    """Convert our message format to Gemini Content objects."""
    contents = []
    for msg in messages:
        role = "model" if msg.get("role") == "assistant" else "user"
        contents.append(types.Content(
            role=role,
            parts=[types.Part(text=msg.get("content", ""))],
        ))
    return contents


def _emit_structured_events(tool_name: str, result: dict) -> list[dict]:
    """Emit structured SSE events for rich frontend cards.

    After a tool executes, check if the result should trigger a UI card.
    The frontend receives these as separate SSE events and renders
    the appropriate component (ItemCard, CompatibilityBadge, etc.).
    """
    events = []
    if tool_name == "search_items":
        for item in result.get("items", [])[:3]:
            events.append({"event": "item_card", "data": json.dumps(item)})
    # Add more event types here as you add tools:
    # elif tool_name == "check_compatibility":
    #     events.append({"event": "compatibility_result", "data": json.dumps(result)})
    return events
```

### 2e. Session Store

**backend/app/session/memory.py:**
```python
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

### 2f. Chat Endpoint

**backend/app/api/models.py:**
```python
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(description="The user's latest message")
    session_id: str = Field(description="Session UUID for conversation continuity")
```

**backend/app/api/chat.py:**
```python
import json
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
from app.agent.loop import run_agent
from app.api.models import ChatRequest
from app.session.memory import store

router = APIRouter()

@router.post("/api/chat")
async def chat(request: ChatRequest):
    session_id = request.session_id
    user_message = request.message.strip()

    if not user_message:
        return EventSourceResponse(_error_stream("Please enter a message."))

    store.add_message(session_id, "user", user_message)
    messages = store.get_messages(session_id)

    async def event_generator():
        assistant_text = ""
        async for event in run_agent(messages, session_id):
            if event.get("event") == "text_delta":
                assistant_text += event.get("data", "")
            yield {
                "event": event.get("event", "text_delta"),
                "data": event.get("data", "") if isinstance(event.get("data"), str) else json.dumps(event.get("data")),
            }
        if assistant_text:
            store.add_message(session_id, "assistant", assistant_text)

    return EventSourceResponse(event_generator())

async def _error_stream(message: str):
    yield {"event": "error", "data": message}
    yield {"event": "done", "data": ""}
```

**TEST NOW:**
```bash
curl -N -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{"message": "find something", "session_id": "test1"}'
```
You should see SSE events streaming. If not, debug before moving to frontend.

---

## Phase 3: Frontend

### 3a. Types

**frontend/src/lib/types.ts:**
```typescript
export interface ItemCardData {
  id: string;
  name: string;
  // Add fields matching your domain's item structure
  [key: string]: unknown;
}

export type ContentBlock =
  | { type: "text"; text: string }
  | { type: "item_card"; data: ItemCardData };
  // Add more block types as you add tools:
  // | { type: "compatibility_result"; data: CompatibilityData }

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

export type ChatAction =
  | { type: "ADD_USER_MESSAGE"; message: Message }
  | { type: "ADD_ASSISTANT_MESSAGE"; message: Message }
  | { type: "APPEND_TEXT_DELTA"; text: string }
  | { type: "ADD_CONTENT_BLOCK"; block: ContentBlock }
  | { type: "SET_STATUS"; text: string }
  | { type: "SET_ERROR"; error: string }
  | { type: "FINALIZE_STREAM" }
  | { type: "CLEAR_MESSAGES" };
```

**frontend/src/lib/utils.ts:**
```typescript
export function generateId(): string {
  return crypto.randomUUID();
}

export function formatPrice(price: string | number): string {
  const num = typeof price === "string" ? parseFloat(price) : price;
  if (isNaN(num)) return String(price);
  return `$${num.toFixed(2)}`;
}
```

**frontend/src/lib/constants.ts:**
```typescript
export const API_PATHS = {
  chat: "/api/chat",
} as const;

export const STARTER_PROMPTS = [
  { label: "Example Query 1", message: "your example query here" },
  { label: "Example Query 2", message: "your example query here" },
  { label: "Example Query 3", message: "your example query here" },
];
```

### 3b. SSE Hook

**frontend/src/hooks/useSSE.ts:**
```typescript
"use client";

import { useRef, useCallback } from "react";
import { fetchEventSource } from "@microsoft/fetch-event-source";

export interface SSEHandlers {
  onTextDelta: (text: string) => void;
  onItemCard: (data: unknown) => void;
  onStatus: (text: string) => void;
  onError: (error: string) => void;
  onDone: () => void;
}

export function useSSE() {
  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(
    async (
      url: string,
      body: { message: string; session_id: string },
      handlers: SSEHandlers
    ) => {
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;

      await fetchEventSource(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: ctrl.signal,
        openWhenHidden: true,
        onmessage(ev) {
          switch (ev.event) {
            case "text_delta":
              handlers.onTextDelta(ev.data);
              break;
            case "item_card":
              try { handlers.onItemCard(JSON.parse(ev.data)); } catch { /* skip */ }
              break;
            // Add more event types here as you add tools
            case "status":
              handlers.onStatus(ev.data);
              break;
            case "error":
              handlers.onError(ev.data);
              break;
            case "done":
              handlers.onDone();
              break;
          }
        },
        onclose() { handlers.onDone(); },
        onerror(err) {
          if (ctrl.signal.aborted) return;
          handlers.onError(err instanceof Error ? err.message : "Connection error");
          throw err;
        },
      });
    },
    []
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  return { send, abort };
}
```

### 3c. Session Hook

**frontend/src/hooks/useSession.ts:**
```typescript
"use client";

import { useState, useEffect, useCallback } from "react";
import { generateId } from "@/lib/utils";

const SESSION_KEY = "chat_session_id";

export function useSession() {
  const [sessionId, setSessionId] = useState("");

  useEffect(() => {
    const stored = localStorage.getItem(SESSION_KEY);
    if (stored) {
      setSessionId(stored);
    } else {
      const newId = generateId();
      localStorage.setItem(SESSION_KEY, newId);
      setSessionId(newId);
    }
  }, []);

  const resetSession = useCallback(() => {
    const newId = generateId();
    localStorage.setItem(SESSION_KEY, newId);
    setSessionId(newId);
  }, []);

  return { sessionId, resetSession };
}
```

### 3d. Chat Hook

**frontend/src/hooks/useChat.ts:**
```typescript
"use client";

import { useReducer, useCallback, useRef } from "react";
import { useSSE } from "./useSSE";
import { useSession } from "./useSession";
import type { ChatState, ChatAction, Message, ContentBlock } from "@/lib/types";
import { generateId } from "@/lib/utils";
import { API_PATHS } from "@/lib/constants";

const initialState: ChatState = {
  messages: [],
  isStreaming: false,
  error: null,
  statusText: null,
};

function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case "ADD_USER_MESSAGE":
      return { ...state, messages: [...state.messages, action.message], isStreaming: true, error: null, statusText: null };
    case "ADD_ASSISTANT_MESSAGE":
      return { ...state, messages: [...state.messages, action.message] };
    case "APPEND_TEXT_DELTA": {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (!last || last.role !== "assistant") return state;
      const content = [...last.content];
      const lastBlock = content[content.length - 1];
      if (lastBlock && lastBlock.type === "text") {
        content[content.length - 1] = { type: "text", text: lastBlock.text + action.text };
      } else {
        content.push({ type: "text", text: action.text });
      }
      msgs[msgs.length - 1] = { ...last, content };
      return { ...state, messages: msgs, statusText: null };
    }
    case "ADD_CONTENT_BLOCK": {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (!last || last.role !== "assistant") return state;
      msgs[msgs.length - 1] = { ...last, content: [...last.content, action.block] };
      return { ...state, messages: msgs };
    }
    case "SET_STATUS":
      return { ...state, statusText: action.text };
    case "SET_ERROR":
      return { ...state, error: action.error, isStreaming: false, statusText: null };
    case "FINALIZE_STREAM": {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, isStreaming: false };
      }
      return { ...state, messages: msgs, isStreaming: false, statusText: null };
    }
    case "CLEAR_MESSAGES":
      return { ...initialState };
    default:
      return state;
  }
}

export function useChat() {
  const [state, dispatch] = useReducer(chatReducer, initialState);
  const { send, abort } = useSSE();
  const { sessionId, resetSession } = useSession();
  const dispatchRef = useRef(dispatch);
  dispatchRef.current = dispatch;
  const pendingBlocksRef = useRef<ContentBlock[]>([]);

  const flushPendingBlocks = useCallback(() => {
    for (const block of pendingBlocksRef.current) {
      dispatchRef.current({ type: "ADD_CONTENT_BLOCK", block });
    }
    pendingBlocksRef.current = [];
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || !sessionId) return;
      pendingBlocksRef.current = [];

      const userMsg: Message = {
        id: generateId(), role: "user",
        content: [{ type: "text", text: text.trim() }], timestamp: Date.now(),
      };
      dispatch({ type: "ADD_USER_MESSAGE", message: userMsg });

      const assistantMsg: Message = {
        id: generateId(), role: "assistant",
        content: [], timestamp: Date.now(), isStreaming: true,
      };
      dispatch({ type: "ADD_ASSISTANT_MESSAGE", message: assistantMsg });

      try {
        await send(API_PATHS.chat, { message: text.trim(), session_id: sessionId }, {
          onTextDelta: (t) => dispatchRef.current({ type: "APPEND_TEXT_DELTA", text: t }),
          onItemCard: (data) => pendingBlocksRef.current.push({ type: "item_card", data: data as any }),
          onStatus: (t) => dispatchRef.current({ type: "SET_STATUS", text: t }),
          onError: (e) => dispatchRef.current({ type: "SET_ERROR", error: e }),
          onDone: () => {
            flushPendingBlocks();
            dispatchRef.current({ type: "FINALIZE_STREAM" });
          },
        });
      } catch {
        flushPendingBlocks();
        dispatchRef.current({ type: "FINALIZE_STREAM" });
      }
    },
    [sessionId, send, flushPendingBlocks]
  );

  const stopStreaming = useCallback(() => {
    abort();
    flushPendingBlocks();
    dispatch({ type: "FINALIZE_STREAM" });
  }, [abort, flushPendingBlocks]);

  const clearMessages = useCallback(() => {
    abort();
    pendingBlocksRef.current = [];
    dispatch({ type: "CLEAR_MESSAGES" });
    resetSession();
  }, [abort, resetSession]);

  return {
    messages: state.messages, isStreaming: state.isStreaming,
    error: state.error, statusText: state.statusText,
    sendMessage, stopStreaming, clearMessages,
  };
}
```

### 3e. Context

**frontend/src/context/ChatContext.tsx:**
```typescript
"use client";

import { createContext, useContext } from "react";
import { useChat } from "@/hooks/useChat";

type ChatContextType = ReturnType<typeof useChat>;
const ChatContext = createContext<ChatContextType | null>(null);

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const chat = useChat();
  return <ChatContext.Provider value={chat}>{children}</ChatContext.Provider>;
}

export function useChatContext(): ChatContextType {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChatContext must be used within ChatProvider");
  return ctx;
}
```

### 3f. API Proxy

**frontend/src/app/api/chat/route.ts:**
```typescript
export const runtime = "edge";

export async function POST(req: Request) {
  const body = await req.json();
  const backendUrl = process.env.BACKEND_API_URL || "http://localhost:8000";

  const response = await fetch(`${backendUrl}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    return new Response(JSON.stringify({ error: "Backend request failed" }), {
      status: response.status,
      headers: { "Content-Type": "application/json" },
    });
  }

  return new Response(response.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
```

### 3g. Components

Build these in order. Ask Claude to create: ChatInput, MessageBubble, MessageList, ChatContainer, then wire into page.tsx.

**Key rendering logic for MessageBubble — switch on block type:**
```typescript
{message.content.map((block, i) => {
  switch (block.type) {
    case "text":
      return <Markdown key={i} remarkPlugins={[remarkGfm]}>{block.text}</Markdown>;
    case "item_card":
      return <ItemCard key={i} data={block.data} />;
    default:
      return null;
  }
})}
```

**page.tsx:**
```typescript
"use client";
import { ChatProvider } from "@/context/ChatContext";
import { ChatContainer } from "@/components/chat/ChatContainer";

export default function Home() {
  return (
    <ChatProvider>
      <ChatContainer />
    </ChatProvider>
  );
}
```

**TEST NOW:** Type a message in the browser. See streamed response. This is your minimum viable demo.

---

## Phase 4: Add More Tools

For each new tool, you need to:
1. Create the function in `backend/app/tools/`
2. Add it to `TOOL_FUNCTIONS` dict in `registry.py`
3. Add a `FunctionDeclaration` to `get_tool_declarations()` in `registry.py`
4. Add a few-shot example to `system_prompt.py`
5. Test via the chat UI

Common tool patterns:

**Detail lookup** — get full info for a specific item by ID:
```python
def get_details(reasoning: str, item_id: str) -> dict:
    item = loader.items.get(item_id.upper())
    if not item:
        return {"found": False, "message": f"Item {item_id} not found."}
    return {"found": True, **item}
```

**Relationship check** — verify if two things are related:
```python
def check_relationship(reasoning: str, item_id: str, target_id: str) -> dict:
    related = loader.relationships.get(item_id.upper(), [])
    is_related = target_id.upper() in related
    return {
        "related": is_related,
        "confidence": "verified" if is_related else "not_in_data",
        "message": f"{item_id} {'is' if is_related else 'is not'} related to {target_id}.",
    }
```

**Diagnosis** — map a problem to solutions:
```python
def diagnose(reasoning: str, description: str, category: str) -> dict:
    # Fuzzy match against known problems, return causes + recommended items
    ...
```

---

## Phase 5: Rich UI Cards

In loop.py `_emit_structured_events`, emit typed SSE events after tool execution.
In useSSE.ts, add cases for new event types.
In useChat.ts, buffer new card types in pendingBlocksRef.
In types.ts, add to ContentBlock union.
In MessageBubble.tsx, add to the switch statement.
Create the card component.

---

## Phase 6: Intent Classifier (Guardrails)

**backend/app/agent/classifier.py:**
```python
import re
from enum import Enum

class Intent(Enum):
    ON_TOPIC = "on_topic"
    GREETING = "greeting"
    OUT_OF_SCOPE = "out_of_scope"
    OFF_TOPIC = "off_topic"

# Define regex patterns for your domain
DOMAIN_KEYWORDS = re.compile(r"\b(keyword1|keyword2|keyword3)\b", re.IGNORECASE)
OUT_OF_SCOPE_KEYWORDS = re.compile(r"\b(adjacent_topic1|adjacent_topic2)\b", re.IGNORECASE)
GREETING_PATTERNS = re.compile(r"^\s*(hi|hello|hey|thanks|help)\s*[!.?]?\s*$", re.IGNORECASE)

OFF_TOPIC_MESSAGE = "I'm a [DOMAIN] assistant. I can help you with [CAPABILITIES]. How can I help?"
OUT_OF_SCOPE_MESSAGE = "I specialize in [SCOPE]. For [OUT_OF_SCOPE], please visit [REDIRECT]."

def classify(message: str) -> Intent:
    text = message.strip()
    if GREETING_PATTERNS.match(text):
        return Intent.GREETING
    if DOMAIN_KEYWORDS.search(text):
        return Intent.ON_TOPIC
    if OUT_OF_SCOPE_KEYWORDS.search(text):
        return Intent.OUT_OF_SCOPE
    if len(text.split()) <= 4:
        return Intent.ON_TOPIC  # short follow-ups pass through
    return Intent.OFF_TOPIC
```

Wire into loop.py at the top of `run_agent`:
```python
from app.agent.classifier import Intent, classify, OFF_TOPIC_MESSAGE, OUT_OF_SCOPE_MESSAGE

intent = classify(latest_message)
if intent == Intent.OFF_TOPIC:
    yield {"event": "text_delta", "data": OFF_TOPIC_MESSAGE}
    yield {"event": "done", "data": ""}
    return
if intent == Intent.OUT_OF_SCOPE:
    yield {"event": "text_delta", "data": OUT_OF_SCOPE_MESSAGE}
    yield {"event": "done", "data": ""}
    return
```
