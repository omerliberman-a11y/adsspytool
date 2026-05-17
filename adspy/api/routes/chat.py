from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from adspy.ai.agent import chat as agent_chat

router = APIRouter(prefix="/chat", tags=["chat"])


class Message(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    messages: list[Message] = Field(min_length=1)
    max_steps: int = Field(default=4, ge=1, le=8)


@router.post("")
def chat(req: ChatRequest) -> dict[str, Any]:
    try:
        reply = agent_chat(
            [m.model_dump() for m in req.messages],
            max_steps=req.max_steps,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {
        "reply": reply.text,
        "tool_calls": reply.tool_calls,
        "latency_ms": reply.latency_ms,
    }
