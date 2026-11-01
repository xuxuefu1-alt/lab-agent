from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.respones import Respones
from app.database import get_db
from app.schemas.auth import LoginRequest, registerRquest
from app.services import auth_services


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
# 负责 login 相关逻辑，并返回处理结果。
def login(data: LoginRequest, db: Session = Depends(get_db)):
    result = auth_services.login(db, data)
    return Respones.success(message="登录成功", data=result)


@router.post("/register")
# 负责 register 相关逻辑，并返回处理结果。
def register(data: registerRquest, db: Session = Depends(get_db)):
    result = auth_services.register(db, data)
    return Respones.success(message="注册成功", data=result)
