from http import HTTPStatus

from sqlalchemy.orm import Session
from app.schemas.auth import LoginRequest, registerRquest
from app.model.user import User
from app.common.exceptions import BusinessExceptions
from app.utils.password import verify_password, hash_password
from app.utils.jwt import create_access_token
from app.schemas.auth import LoginResponse
from app.schemas.user import UserResponse


def login(db: Session, data: LoginRequest):
    user = db.query(User).filter(User.username == data.username).first()
    if not user:
        raise BusinessExceptions(message="账号不存在", code=HTTPStatus.UNAUTHORIZED)
    # 验证密码跟密文
    if not verify_password(data.password, user.password):
        raise BusinessExceptions(message="密码错误", code=HTTPStatus.UNAUTHORIZED)
    if user.status != 1:
        raise BusinessExceptions(message="账号已经禁用", code=HTTPStatus.FORBIDDEN)
    # 账号密码通过 创建token
    token = create_access_token(user.id)
    # 登录成功 返回对应用户数据 状态码
    return LoginResponse(token=token, user=UserResponse.model_validate(user))


def register(db: Session, data: registerRquest):
    user = db.query(User).filter(User.username == data.username).first()
    if user:
        raise BusinessExceptions(message="该账户已经存在", code=HTTPStatus.CONFLICT)
    # 注册成功 存入数据库 更新数据库
    user_model = User(
        username=data.username,
        password=hash_password(data.password),
        name=data.name or data.username,
        role="student",
        email=data.email,
        phone=data.phone,
        status=1,
    )
    db.add(user_model)
    db.commit()
    db.refresh(user_model)
    return UserResponse.model_validate(user_model)
