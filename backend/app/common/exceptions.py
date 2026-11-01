# 异常捕获
import logging

from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.common.respones import Respones

logger = logging.getLogger(__name__)


class BusinessExceptions(Exception):
    # 初始化对象状态和依赖。
    def __init__(self, message: str, code: int = 400):
        if not 400 <= code <= 599:
            raise ValueError("Business exception code must be an HTTP 4xx or 5xx status")
        self.message = message
        self.code = code
        self.status_code = code
        super().__init__(message)

    # 自定义业务异常


async def bussiness_exceptions_hadler(request: Request, exc: BusinessExceptions):
    return JSONResponse(
        status_code=exc.status_code,
        content=Respones.error(code=exc.code, message=exc.message).model_dump(),
    )
    # http异常


async def http_exceptions_hadler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=Respones.error(code=exc.status_code, message=exc.detail).model_dump(),
    )


# 参数异常


async def validation_exceptions_hadler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    error_messages = []
    for error in errors:
        field = '.'.join(str(loc) for loc in error['loc'])
        msg = error['msg']
        error_messages.append(f"{field}: {msg}")

    logger.warning(
        "Request validation failed",
        extra={
            "path": request.url.path,
            "validation_errors": [
                {
                    "location": [str(part) for part in error["loc"]],
                    "type": error.get("type"),
                }
                for error in errors
            ],
        },
    )

    detailed_message = "请求参数错误: " + "; ".join(error_messages)

    return JSONResponse(
        status_code=422,
        content=Respones.error(code=422, message=detailed_message).model_dump(),
    )


# 全局兜底错误捕获
async def global_exceptions_hadler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=500,
        content=Respones.error(code=500, message="服务器内部异常").model_dump(),
        headers={"X-Request-ID": request_id} if request_id else None,
    )
