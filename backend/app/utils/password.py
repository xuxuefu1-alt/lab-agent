import bcrypt

 # 密码加密
def hash_password(password: str) -> str:
   
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

 # 验证密码 password：明文  hashed_password：密文
def verify_password(password:str,hashed_password:str)->bool:
    return bcrypt.checkpw(
        password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )
