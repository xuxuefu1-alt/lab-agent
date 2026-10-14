from fastapi import APIRouter, Depends
from app.dependencies.auth import get_current_user
from app.model.user import User
from app.schemas.user import UserResponse
from app.common.respones import Respones

router = APIRouter(prefix="/user", tags=["用户信息"])


@router.get("/info")
def get_user_info(current_user: User = Depends(get_current_user)):
    return Respones.success(
        message="请求成功", data=UserResponse.model_validate(current_user)
    )
