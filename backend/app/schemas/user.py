import email
from turtle import st

from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    id: int
    role: str
    username: str
    name: str
    email: str | None = None
    phone: str | None = None
    status: int = 1
    avatar: str | None = None
    model_config = ConfigDict(from_attributes=True)  # 转化为json对象


class UpdateUserRequest(BaseModel):
    name: str | None = None
    avatar: str | None = None
    email: str | None = None
    phone: str | None = None
