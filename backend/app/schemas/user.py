import email
from turtle import st

from pydantic import BaseModel, ConfigDict, Field


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


class AdminUserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=50)
    name: str = Field(..., min_length=1, max_length=50)
    email: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=30)
    role: str = Field(default="student", pattern="^(student|admin)$")


class AdminUserUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=50)
    email: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=30)
    role: str | None = Field(None, pattern="^(student|admin)$")
    status: int | None = Field(None, ge=0, le=1)
