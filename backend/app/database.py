# 创建数据库连接工程
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import create_engine, DateTime
from app.config import settings
from datetime import datetime

engine_kwargs = {}
if settings.mysql_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
engine = create_engine(settings.mysql_url, **engine_kwargs)

# 数据库session会话连接工厂
SessionLocal = sessionmaker(bind=engine, autoflush=False)


# 获取db相关数据或业务逻辑。
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, comment="主键ID"
    )
    create_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, comment="创建时间"
    )
    update_time: Mapped[datetime] = mapped_column(
            DateTime, default=datetime.now,onupdate=datetime.now, comment="更新时间"
        )
