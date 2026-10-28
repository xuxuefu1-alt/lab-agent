from sqlalchemy.orm import Session

from app.model.user import User
from app.schemas.user import UpdateUserRequest, UserResponse
from app.common.respones import Respones
from app.common.exceptions import BusinessExceptions
from app.dependencies.auth import get_current_user
from app.utils.password import verify_password, hash_password


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


class UserService:
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User:
        """根据ID获取用户"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise BusinessExceptions("用户不存在")
        return user

    @staticmethod
    def get_all_users(db: Session, skip: int = 0, limit: int = 10) -> list[User]:
        """获取所有用户列表 (分页)"""
        return db.query(User).offset(skip).limit(limit).all()

    @staticmethod
    def get_users_count(db: Session) -> int:
        """获取用户总数"""
        return db.query(User).count()

    @staticmethod
    def get_user_by_username(db: Session, username: str) -> User:
        """根据用户名获取用户"""
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise BusinessExceptions("用户不存在")
        return user

    @staticmethod
    def change_password(db: Session, user_id: int, old_password: str, new_password: str) -> dict:
        """修改用户密码"""
        user = UserService.get_user_by_id(db, user_id)

        # 验证旧密码
        if not verify_password(old_password, user.password):
            raise BusinessExceptions("原密码错误")

        # 更新密码
        user.password = hash_password(new_password)
        db.add(user)
        db.commit()

        return {"message": "密码修改成功"}

    @staticmethod
    def update_user(db: Session, user_id: int, user_data: UpdateUserRequest) -> User:
        """更新用户信息"""
        user = UserService.get_user_by_id(db, user_id)

        update_data = (
            user_data.model_dump(exclude_unset=True)
            if hasattr(user_data, "model_dump")
            else dict(user_data)
        )
        for field, value in update_data.items():
            setattr(user, field, value)

        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def delete_user(db: Session, user_id: int) -> dict:
        """删除用户"""
        user = UserService.get_user_by_id(db, user_id)
        db.delete(user)
        db.commit()
        return {"message": "用户已删除"}

    @staticmethod
    def create_user(
        db: Session,
        username: str,
        password: str,
        name: str,
        role: str,
        email: str | None = None,
        phone: str | None = None,
    ) -> User:
        """创建用户"""
        # 检查用户名是否已存在
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            raise BusinessExceptions("用户名已存在")

        user = User(
            username=username,
            password=hash_password(password),
            name=name,
            role=role,
            email=email,
            phone=phone,
            status=1
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def search_users(db: Session, keyword: str, skip: int = 0, limit: int = 10) -> list[User]:
        """搜索用户"""
        query = db.query(User)
        if keyword:
            query = query.filter(
                User.username.like(f"%{keyword}%") |
                User.name.like(f"%{keyword}%") |
                User.email.like(f"%{keyword}%")
            )
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def get_users_by_role(db: Session, role: str, skip: int = 0, limit: int = 10) -> list[User]:
        """根据角色获取用户列表"""
        return db.query(User).filter(User.role == role).offset(skip).limit(limit).all()

    @staticmethod
    def toggle_user_status(db: Session, user_id: int) -> User:
        """切换用户状态"""
        user = UserService.get_user_by_id(db, user_id)
        user.status = 1 if user.status == 0 else 0
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
