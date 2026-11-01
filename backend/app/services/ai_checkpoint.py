from __future__ import annotations

import logging
from threading import Lock

from app.config import settings


logger = logging.getLogger(__name__)
_checkpointer = None
_checkpointer_lock = Lock()


# 初始化checkpointer相关数据或业务逻辑。
def initialize_checkpointer():
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer
    with _checkpointer_lock:
        if _checkpointer is not None:
            return _checkpointer
        if settings.REDIS_URL:
            from langgraph.checkpoint.redis import RedisSaver

            saver = RedisSaver(
                settings.REDIS_URL,
                ttl={"default_ttl": settings.AI_CHECKPOINT_TTL_MINUTES, "refresh_on_read": True},
                checkpoint_prefix=settings.AI_CHECKPOINT_PREFIX,
                checkpoint_write_prefix=f"{settings.AI_CHECKPOINT_PREFIX}_write",
            )
            # RedisSaver requires Redis Stack search indexes. Fail fast when
            # production is pointed at a plain Redis instance.
            saver.setup()
            _checkpointer = saver
            logger.info("LangGraph Redis checkpointer initialized")
            return _checkpointer

        if settings.APP_ENV == "production":
            raise RuntimeError("REDIS_URL is required for production LangGraph checkpoints")

        from langgraph.checkpoint.memory import InMemorySaver

        logger.warning("Using in-memory LangGraph checkpoints outside production")
        _checkpointer = InMemorySaver()
        return _checkpointer


# 获取checkpointer相关数据或业务逻辑。
def get_checkpointer():
    return initialize_checkpointer()


# 负责 thread id 相关逻辑，并返回处理结果。
def thread_id(user_id: int, conversation_key: str, workflow: str) -> str:
    return f"ai:{workflow}:user:{user_id}:conversation:{conversation_key}"


# 清理thread相关数据或业务逻辑。
def clear_thread(checkpointer, checkpoint_thread_id: str) -> None:
    delete_thread = getattr(checkpointer, "delete_thread", None)
    if delete_thread is not None:
        delete_thread(checkpoint_thread_id)


# 判断是否存在thread相关数据或业务逻辑。
def has_thread(checkpointer, checkpoint_thread_id: str) -> bool:
    get_tuple = getattr(checkpointer, "get_tuple", None)
    if get_tuple is None:
        return False
    return get_tuple({"configurable": {"thread_id": checkpoint_thread_id}}) is not None
