"""Chat endpoint — natural language interface to the leads database."""

import asyncio
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_session
from app.services.chat_service import run_chat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    response: str


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, session: Session = Depends(get_session)):
    """Send a message to the sales intelligence assistant."""
    messages = [{"role": m.role, "content": m.content} for m in req.history]
    messages.append({"role": "user", "content": req.message})

    try:
        result = asyncio.run(run_chat(messages, session))
        return ChatResponse(response=result)
    except Exception as e:
        logger.error("Chat error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to process chat message"
        )
