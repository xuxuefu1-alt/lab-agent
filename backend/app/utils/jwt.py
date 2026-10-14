import jwt
from  datetime import datetime,timedelta
from app.config import settings


# 创建token
def create_access_token(user_id: int) -> str:
    # 过期时间
    expire = datetime.now() + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    # 参数
    pyload = {"user_id": user_id, "exp": expire}
    return jwt.encode(pyload, settings.JWT_SECRT_KEY, algorithm=settings.JWT_ALGORITHM)


# 解析token
def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRT_KEY, algorithms=[settings.JWT_ALGORITHM])
