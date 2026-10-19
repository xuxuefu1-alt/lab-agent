from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies.auth import get_current_user
from app.model.user import User
from app.schemas.user import UpdateUserRequest
from app.common.respones import Respones
from app.services.user_services import get_user_info
from app.services import user_services
from app.database import get_db

router = APIRouter(prefix="/user", tags=["用户信息"])


# 获取用户信息
@router.get("/info")
def get_user_info(current_user: User = Depends(get_current_user)):
    return Respones.success(data=user_services.get_user_info(current_user))


# 更新用户信息
@router.put("/update")
def update_user_info(
    data: UpdateUserRequest,
    current_user:User=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    res = user_services.update_user_info(db, current_user, data)
    return Respones.success(data=res)
