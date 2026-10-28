from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "student", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1, max_length=20)


class ChatResponse(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str
    tool_calls: list[dict] = Field(default_factory=list)
    blocks: list[dict] = Field(default_factory=list)
