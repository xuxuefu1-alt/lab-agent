from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.model.user import User
from app.database import get_db
from app.schemas.ai import ChatRequest, ChatResponse
from app.services import ai_services
from app.common.respones import Respones

router = APIRouter(prefix="/ai", tags=["AI聊天"])


@router.post("/chat")
def chat(
    data: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = ai_services.chat_llm(data, db, current_user)
    payload = ChatResponse(
        content=result["content"],
        tool_calls=result["tool_calls"],
        blocks=result.get("blocks", []),
    )
    return Respones.success(data=payload.model_dump())
