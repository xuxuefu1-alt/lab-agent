from pydantic import BaseModel
from app.schemas.user import UserResponse


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: UserResponse


class registerRquest(BaseModel):
    username: str
    password: str
    name: str | None = None
    email: str | None = None
    phone: str | None = None
