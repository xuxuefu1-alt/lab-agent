import json
import queue
import threading
from collections.abc import Iterator
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.model.user import User
from app.database import get_db
from app.database import SessionLocal
from app.schemas.ai import ChatRequest, ChatResponse
from app.services import ai_services
from app.observability import REQUEST_ID
from app.common.respones import Respones

router = APIRouter(prefix="/ai", tags=["AI聊天"])


# 负责 sse event 相关逻辑，并返回处理结果。
def _sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


# 负责 stream chat events 相关逻辑，并返回处理结果。
def _stream_chat_events(data: ChatRequest, user_id: int, request_id: str | None = None) -> Iterator[str]:
    events: queue.Queue[dict] = queue.Queue()
    finished = threading.Event()
    run_id = uuid4().hex

    # 向调用方发送事件或增量结果。
    def emit(payload: dict) -> None:
        events.put(payload)

    # 在后台执行当前请求的异步处理。
    def worker() -> None:
        request_token = REQUEST_ID.set(request_id or run_id)
        db = None
        try:
            db = SessionLocal()
            user = db.query(User).filter(User.id == user_id).first()
            if user is None:
                raise ValueError("当前用户不存在")
            result = ai_services.chat_llm(
                data,
                db,
                user,
                progress_callback=emit,
                token_callback=emit,
            )
            events.put({
                "type": "final",
                "status": "completed",
                "message": result["content"],
                "content": result["content"],
                "tool_calls": result["tool_calls"],
                "blocks": result.get("blocks", []),
                "confirmation_token": result.get("confirmation_token"),
                "conversation_id": result.get("conversation_id"),
            })
        except Exception as exc:
            events.put({
                "type": "error",
                "status": "failed",
                "message": getattr(exc, "message", None) or str(exc) or "AI 服务暂时不可用，请稍后重试",
            })
        finally:
            try:
                if db is not None:
                    db.close()
            finally:
                REQUEST_ID.reset(request_token)
                finished.set()

    threading.Thread(target=worker, daemon=True).start()
    sequence = 0
    while not finished.is_set() or not events.empty():
        try:
            event = events.get(timeout=0.5)
        except queue.Empty:
            continue
        sequence += 1
        event["sequence"] = sequence
        event.setdefault("run_id", run_id)
        yield _sse_event(event)


@router.post("/chat")
# 负责 chat 相关逻辑，并返回处理结果。
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
        confirmation_token=result.get("confirmation_token"),
        conversation_id=result.get("conversation_id"),
    )
    return Respones.success(data=payload.model_dump())


@router.post("/chat/stream")
# 负责 chat stream 相关逻辑，并返回处理结果。
def chat_stream(
    data: ChatRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    return StreamingResponse(
        _stream_chat_events(
            data,
            current_user.id,
            getattr(request.state, "request_id", None),
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/conversations/{conversation_id}/reset")
# 重置conversation相关数据或业务逻辑。
def reset_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = ai_services.reset_conversation(conversation_id, db, current_user)
    return Respones.success(data=result)


@router.delete("/conversations/{conversation_id}")
# 删除conversation相关数据或业务逻辑。
def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = ai_services.delete_conversation(conversation_id, db, current_user)
    return Respones.success(data=result)
