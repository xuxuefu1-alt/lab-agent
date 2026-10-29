from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AiConversation(Base):
    __tablename__ = "ai_conversation"
    __table_args__ = (
        UniqueConstraint("user_id", "client_key", name="uq_ai_conversation_user_key"),
    )

    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    client_key: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str | None] = mapped_column(String(200))
    summary: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
