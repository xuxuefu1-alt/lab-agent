from sqlalchemy.orm import Session

from app.model.user import User
from app.schemas.user import UpdateUserRequest, UserResponse
from app.common.respones import Respones
from app.dependencies.auth import get_current_user


# 获取用户信息
def get_user_info(user: User):
    return UserResponse.model_validate(user)


# 更新用户信息
def update_user_info(db: Session, user: User, data: UpdateUserRequest):
    user_dir = data.model_dump(exclude_none=True)
    for field, value in user_dir.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)
