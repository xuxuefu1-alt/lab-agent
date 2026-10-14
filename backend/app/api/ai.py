from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user
from app.model.user import User
from app.schemas.ai import ChatMessage, ChatRequest
from app.services import ai_services
from app.common.respones import Respones

router = APIRouter(prefix="/ai", tags=["AI聊天"])


@router.post("/chat")
def chat(data: ChatRequest, current_user: User = Depends(get_current_user)):
    content = ai_services.chat_llm(data)
    return Respones.success(data=ChatMessage(role="assistant", content=content).model_dump())
