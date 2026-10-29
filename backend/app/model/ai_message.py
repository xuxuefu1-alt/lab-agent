from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AiMessage(Base):
    __tablename__ = "ai_message"

    conversation_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    blocks_json: Mapped[str | None] = mapped_column(Text)
    tool_calls_json: Mapped[str | None] = mapped_column(Text)
    token_usage_json: Mapped[str | None] = mapped_column(Text)
