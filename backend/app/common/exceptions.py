# 异常捕获
from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.common.respones import Respones


class BusinessExceptions(Exception):
    def __init__(self, message: str, code: int = 200):
        self.message = message
        self.code = code
        super().__init__(message)
        pass

    # 自定义业务异常


async def bussiness_exceptions_hadler(request: Request, exc: BusinessExceptions):
    return JSONResponse(
        status_code=200,
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
    print('='*50)
    print('参数验证错误详情:')
    print('错误信息:', exc.errors())
    print('请求体:', await request.body())
    print('='*50)

    # 获取详细的错误信息
    errors = exc.errors()
    error_messages = []
    for error in errors:
        field = '.'.join(str(loc) for loc in error['loc'])
        msg = error['msg']
        error_messages.append(f"{field}: {msg}")

    detailed_message = "请求参数错误: " + "; ".join(error_messages)

    return JSONResponse(
        status_code=422,
        content=Respones.error(code=422, message=detailed_message).model_dump(),
    )


# 全局兜底错误捕获
async def global_exceptions_hadler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=Respones.error(code=500, message="服务器内部异常").model_dump(),
    )
