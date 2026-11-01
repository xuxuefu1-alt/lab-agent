from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError

from app.model.user import User
from app.model.laboratory import Laboratory
from app.model.equipment import Equipment
from app.model.booking import Booking
from app.model.ai_conversation import AiConversation
from app.model.ai_message import AiMessage
from app.model.ai_workflow_state import AiWorkflowState
from app.model.ai_audit_log import AiAuditLog
from app.database import Base, engine, SessionLocal
from app.config import settings
from app.services.ai_memory_service import cleanup_expired_state
from app.services.ai_checkpoint import initialize_checkpointer
from app.api import api
from app.observability import install_observability
# 跨域中间件
from starlette.middleware.cors import CORSMiddleware

# 导入异常处理器
from app.common.exceptions import (
    BusinessExceptions,
    bussiness_exceptions_hadler,
    http_exceptions_hadler,
    validation_exceptions_hadler,
    global_exceptions_hadler,
)

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI()
install_observability(
    app,
    settings.OTEL_SERVICE_NAME,
    settings.OTEL_EXPORTER_OTLP_ENDPOINT,
)


@app.on_event("startup")
# 清理ai state on startup相关数据或业务逻辑。
def cleanup_ai_state_on_startup():
    initialize_checkpointer()
    db = SessionLocal()
    try:
        cleanup_expired_state(db)
    finally:
        db.close()
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173"
]
# 允许跨域中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.include_router(api)
# 注册异常处理器
app.add_exception_handler(BusinessExceptions,bussiness_exceptions_hadler)
app.add_exception_handler(HTTPException,http_exceptions_hadler)
app.add_exception_handler(RequestValidationError,validation_exceptions_hadler)
app.add_exception_handler(Exception,global_exceptions_hadler)


@app.get("/")
# 提供根路径响应并返回服务基础状态。
def root():
    return {"message": "fastapi正在运行"}
