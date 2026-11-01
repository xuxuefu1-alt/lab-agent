from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ChatMessage(BaseModel):
    role: Literal["user", "student", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    conversation_id: str | None = Field(None, max_length=100)
    message: str | None = Field(None, min_length=1, max_length=4000)
    messages: list[ChatMessage] | None = Field(None, max_length=20)
    confirmation_token: str | None = Field(None, max_length=4096)

    @model_validator(mode="after")
    # 校验input相关数据或业务逻辑。
    def validate_input(self):
        if not self.message and not self.messages:
            raise ValueError("message or messages is required")
        return self


class ChatResponse(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str
    tool_calls: list[dict] = Field(default_factory=list)
    blocks: list[dict] = Field(default_factory=list)
    confirmation_token: str | None = None
    conversation_id: str | None = None
