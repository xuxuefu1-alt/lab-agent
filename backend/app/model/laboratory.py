from sqlalchemy import String, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Laboratory(Base):
    __tablename__ = "laboratory"
    __table_args__ = {"comment": "实验室信息表"}

    name: Mapped[str] = mapped_column(
        String(100), comment="实验室名称", nullable=False
    )
    description: Mapped[str | None] = mapped_column(
        Text, comment="实验室描述"
    )
    location: Mapped[str] = mapped_column(
        String(255), comment="实验室位置", nullable=False
    )
    capacity: Mapped[int] = mapped_column(
        Integer, default=0, comment="实验室容纳人数", nullable=False
    )
    manager_id: Mapped[int] = mapped_column(
        comment="管理员ID", nullable=False
    )
    status: Mapped[int] = mapped_column(
        default=1, comment="状态 1正常 0禁用", nullable=False
    )
