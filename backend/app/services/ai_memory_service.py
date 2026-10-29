import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.model.ai_audit_log import AiAuditLog
from app.model.ai_conversation import AiConversation
from app.model.ai_message import AiMessage
from app.model.ai_workflow_state import AiWorkflowState
from app.model.user import User


logger = logging.getLogger(__name__)


def _redis_client():
    if not settings.REDIS_URL:
        return None
    try:
        import redis

        return redis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception:
        logger.exception("Redis is configured but unavailable; using database fallback")
        return None


def acquire_idempotency_lock(key: str, ttl_seconds: int = 600) -> bool:
    client = _redis_client()
    if client is None:
        return True
    lock_key = "ai:idempotency:" + hashlib.sha256(key.encode("utf-8")).hexdigest()
    try:
        return bool(client.set(lock_key, "1", nx=True, ex=ttl_seconds))
    except Exception:
        logger.exception("Redis idempotency lock failed; using database fallback")
        return True


def release_idempotency_lock(key: str) -> None:
    client = _redis_client()
    if client is None:
        return
    lock_key = "ai:idempotency:" + hashlib.sha256(key.encode("utf-8")).hexdigest()
    try:
        client.delete(lock_key)
    except Exception:
        logger.exception("Redis idempotency lock release failed")


def get_or_create_conversation(
    db: Session,
    current_user: User,
    client_key: str | None,
) -> AiConversation:
    key = (client_key or "default")[:100]
    conversation = (
        db.query(AiConversation)
        .filter(
            AiConversation.user_id == current_user.id,
            AiConversation.client_key == key,
        )
        .first()
    )
    if conversation:
        return conversation
    conversation = AiConversation(
        user_id=current_user.id,
        client_key=key,
        title=None,
        status="active",
        last_message_at=datetime.now(),
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def load_recent_messages(db: Session, conversation_id: int) -> list[AiMessage]:
    limit = max(2, settings.AI_CONTEXT_MESSAGE_LIMIT)
    rows = (
        db.query(AiMessage)
        .filter(AiMessage.conversation_id == conversation_id)
        .order_by(AiMessage.sequence.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(rows))


def append_message(
    db: Session,
    conversation: AiConversation,
    user_id: int,
    role: str,
    content: str,
    blocks: list[dict[str, Any]] | None = None,
    tool_calls: list[dict[str, Any]] | None = None,
) -> AiMessage:
    last_sequence = (
        db.query(AiMessage.sequence)
        .filter(AiMessage.conversation_id == conversation.id)
        .order_by(AiMessage.sequence.desc())
        .first()
    )
    next_sequence = (last_sequence[0] if last_sequence else 0) + 1
    message = AiMessage(
        conversation_id=conversation.id,
        user_id=user_id,
        sequence=next_sequence,
        role=role,
        content=content,
        blocks_json=json.dumps(blocks or [], ensure_ascii=False),
        tool_calls_json=json.dumps(tool_calls or [], ensure_ascii=False),
    )
    db.add(message)
    conversation.last_message_at = datetime.now()
    db.add(conversation)
    return message


def save_summary(db: Session, conversation: AiConversation, summary: str | None) -> None:
    if summary:
        conversation.summary = summary[:4000]
        db.add(conversation)


def save_audit(
    db: Session,
    current_user: User,
    conversation_id: int | None,
    action: str,
    status: str,
    tool_name: str | None = None,
    request: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
    error_code: str | None = None,
) -> None:
    db.add(
        AiAuditLog(
            user_id=current_user.id,
            conversation_id=conversation_id,
            action=action,
            tool_name=tool_name,
            status=status,
            request_json=json.dumps(request or {}, ensure_ascii=False),
            result_json=json.dumps(result or {}, ensure_ascii=False),
            error_code=error_code,
        )
    )


def save_workflow_state(
    db: Session,
    conversation: AiConversation,
    current_user: User,
    workflow_type: str,
    state: dict[str, Any],
    status: str = "pending",
    expires_at: datetime | None = None,
) -> AiWorkflowState:
    workflow = (
        db.query(AiWorkflowState)
        .filter(
            AiWorkflowState.conversation_id == conversation.id,
            AiWorkflowState.workflow_type == workflow_type,
        )
        .first()
    )
    if workflow is None:
        workflow = AiWorkflowState(
            conversation_id=conversation.id,
            user_id=current_user.id,
            workflow_type=workflow_type,
            status=status,
            state_json=json.dumps(state, ensure_ascii=False),
            expires_at=expires_at or datetime.now() + timedelta(minutes=10),
        )
        db.add(workflow)
    else:
        workflow.status = status
        workflow.state_json = json.dumps(state, ensure_ascii=False)
        workflow.version += 1
        workflow.expires_at = expires_at or datetime.now() + timedelta(minutes=10)
        workflow.consumed_at = None
    return workflow


def consume_workflow_state(
    db: Session,
    current_user: User,
    conversation_id: int,
    workflow_type: str,
) -> AiWorkflowState | None:
    workflow = (
        db.query(AiWorkflowState)
        .filter(
            AiWorkflowState.conversation_id == conversation_id,
            AiWorkflowState.user_id == current_user.id,
            AiWorkflowState.workflow_type == workflow_type,
            AiWorkflowState.status == "pending",
            AiWorkflowState.consumed_at.is_(None),
        )
        .with_for_update()
        .first()
    )
    if workflow is None:
        return None
    if workflow.expires_at and workflow.expires_at < datetime.now():
        workflow.status = "expired"
        db.add(workflow)
        db.commit()
        return None
    workflow.status = "consumed"
    workflow.consumed_at = datetime.now()
    db.add(workflow)
    return workflow


def cleanup_expired_state(db: Session, retention_days: int = 30) -> int:
    cutoff = datetime.now() - timedelta(days=retention_days)
    deleted = (
        db.query(AiWorkflowState)
        .filter(
            AiWorkflowState.expires_at < datetime.now(),
            AiWorkflowState.create_time < cutoff,
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    return deleted

