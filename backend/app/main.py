from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError

from app.model.user import User
from app.model.laboratory import Laboratory
from app.model.equipment import Equipment
from app.database import Base, engine
from app.api import api
# 跨域中间件
from starlette.middleware.cors import CORSMiddleware

# 导入异常处理器
from app.common.exceptions import (
    BusinessExceptions,
    bussiness_exceptions_hadler,
    http_exceptions_hadler,
    validation_exceptions_hadler,
    global_exceptions_hadler,
)

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI()
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173"
]
# 允许跨域中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.include_router(api)
# 注册异常处理器
app.add_exception_handler(BusinessExceptions,bussiness_exceptions_hadler)
app.add_exception_handler(HTTPException,http_exceptions_hadler)
app.add_exception_handler(RequestValidationError,validation_exceptions_hadler)
app.add_exception_handler(Exception,global_exceptions_hadler)


@app.get("/")
def root():
    return {"message": "fastapi正在运行"}
