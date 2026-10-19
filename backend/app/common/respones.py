from pydantic import BaseModel
from typing import Any, Type


class Respones(BaseModel):
    code: int
    message: str
    data: Any

    @classmethod
    def success(cls, message: str = "请求成功", data: Any = None):
        return cls(code=200, message=message, data=data)

    @classmethod
    def error(cls, code: int = 500, message: str = "请求失败", data: Any = None):
        return cls(code=code, message=message,data=data)


def success_response(data_type: Type = dict):
    """生成成功响应类型"""
    class SuccessResponse(BaseModel):
        code: int = 200
        message: str
        data: data_type
    return SuccessResponse
