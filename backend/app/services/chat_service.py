"""Agentic chat service — natural language interface to the leads database.

Uses OpenAI function calling to let sales reps query leads conversationally.
The LLM decides which tools to call, executes them against the DB, and
iterates until it produces a final text answer.
"""

import json
import logging
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy.orm import Session

from app.config import OPENAI_API_KEY, OPENAI_MODEL
from app.services.lead_service import get_lead_detail, get_leads, get_stats

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 5

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

CHAT_SYSTEM_PROMPT = """\
You are a sales intelligence assistant for a roofing materials distributor. \
You help sales reps explore and analyze their leads database of roofing contractors.

## Your Knowledge
- GAF certification tiers (highest to lowest): President's Club > Master Elite > Certified Plus > Certified > Uncertified
- Higher-tier contractors do more job volume and purchase more premium materials
- Lead scores range 0-100, composed of: certification tier (30pts), review volume (20pts), \
rating quality (10pts), business signals (20pts), why-now urgency (20pts)
- Scores 60+ are "Hot" leads, 40-59 are "Warm", below 40 are "Cold"
- Distributors sell shingles, underlayment, ventilation, accessories, and related roofing products
- Review count is a proxy for job volume — more completed jobs means more materials purchased

## Your Behavior
- Use the available tools to look up real data before answering. Never guess or fabricate data.
- Be specific — reference actual contractor names, scores, and data points.
- When listing leads, include their ID, name, score, certification, and location.
- For strategy questions, ground your advice in actual data you retrieve.
- Keep responses concise but actionable. Use bullet points and markdown formatting.
- If the user asks about a contractor by name, search for them first.
- When comparing leads, use the compare tool rather than fetching one at a time.
- Suggest next actions when appropriate.
"""

# ---------------------------------------------------------------------------
# Tool definitions (OpenAI function-calling format)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_leads",
            "description": (
                "Search and filter the leads database. Returns a paginated list "
                "of contractors with basic info and lead scores."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "search": {
                        "type": "string",
                        "description": "Search contractor name (partial match)",
                    },
                    "min_score": {
                        "type": "integer",
                        "description": "Minimum lead score (0-100)",
                    },
                    "max_score": {
                        "type": "integer",
                        "description": "Maximum lead score (0-100)",
                    },
                    "certification": {
                        "type": "string",
                        "enum": [
                            "President's Club",
                            "Master Elite",
                            "Certified",
                        ],
                        "description": "Filter by GAF certification tier",
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": [
                            "lead_score",
                            "name",
                            "rating",
                            "review_count",
                            "distance_miles",
                        ],
                        "description": "Sort field (default: lead_score)",
                    },
                    "sort_order": {
                        "type": "string",
                        "enum": ["asc", "desc"],
                        "description": "Sort direction (default: desc)",
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number (default: 1)",
                    },
                    "per_page": {
                        "type": "integer",
                        "description": "Results per page (default: 10, max: 20)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_lead_detail",
            "description": (
                "Get full detail for a specific contractor, including AI-generated "
                "insights, score breakdown, talking points, buying signals, pain "
                "points, recommended pitch, why-now signal, draft email, and contacts."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_id": {
                        "type": "integer",
                        "description": "The contractor's ID",
                    },
                },
                "required": ["lead_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_stats",
            "description": (
                "Get aggregate dashboard statistics: total leads, average score, "
                "high-priority count, certification breakdown, and score distribution."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_leads",
            "description": (
                "Compare 2-3 leads side by side. Returns full detail for each "
                "lead so they can be compared on score, certification, insights, "
                "and signals."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "minItems": 2,
                        "maxItems": 3,
                        "description": "List of 2-3 contractor IDs to compare",
                    },
                },
                "required": ["lead_ids"],
            },
        },
    },
]

# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------


def _execute_tool(name: str, args: dict, session: Session) -> Any:
    """Execute a tool call and return the result as a serializable dict."""
    if name == "search_leads":
        leads, total = get_leads(
            session,
            search=args.get("search"),
            min_score=args.get("min_score"),
            max_score=args.get("max_score"),
            certification=args.get("certification"),
            sort_by=args.get("sort_by", "lead_score"),
            sort_order=args.get("sort_order", "desc"),
            page=args.get("page", 1),
            per_page=min(args.get("per_page", 10), 20),
        )
        return {"leads": leads, "total": total}

    elif name == "get_lead_detail":
        detail = get_lead_detail(session, args["lead_id"])
        if not detail:
            return {"error": f"Lead with ID {args['lead_id']} not found"}
        return detail

    elif name == "get_stats":
        return get_stats(session)

    elif name == "compare_leads":
        results = []
        for lid in args["lead_ids"]:
            detail = get_lead_detail(session, lid)
            if detail:
                results.append(detail)
            else:
                results.append({"error": f"Lead {lid} not found"})
        return {"leads": results}

    return {"error": f"Unknown tool: {name}"}


# ---------------------------------------------------------------------------
# Agentic chat loop
# ---------------------------------------------------------------------------


async def run_chat(messages: list[dict], session: Session) -> str:
    """Run the agentic chat loop.

    Calls OpenAI with tool definitions, executes any requested tools,
    feeds results back, and iterates until a final text response is
    produced. Returns the assistant's final text.
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set. Add it to backend/.env")

    client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    full_messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}] + messages

    for round_num in range(MAX_TOOL_ROUNDS):
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=full_messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.3,
            max_tokens=1024,
        )

        msg = response.choices[0].message

        # No tool calls — we have the final answer
        if not msg.tool_calls:
            return msg.content or ""

        # Append the assistant message (with tool_calls) to history
        full_messages.append(msg.model_dump(exclude_none=True))

        # Execute each tool call and append results
        for tool_call in msg.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)

            logger.info(
                "Chat tool call [round %d]: %s(%s)",
                round_num + 1,
                fn_name,
                fn_args,
            )

            result = _execute_tool(fn_name, fn_args, session)

            full_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, default=str),
                }
            )

    # Hit the loop cap — return whatever text we have
    return (
        msg.content
        or "I wasn't able to complete the analysis. Please try rephrasing your question."
    )
