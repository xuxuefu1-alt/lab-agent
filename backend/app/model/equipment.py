from sqlalchemy import String, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Equipment(Base):
    __tablename__ = "equipment"
    __table_args__ = {"comment": "设备信息表"}

    name: Mapped[str] = mapped_column(
        String(100), comment="设备名称", nullable=False
    )
    equipment_type: Mapped[str] = mapped_column(
        String(50), comment="设备类型", nullable=False
    )
    laboratory_id: Mapped[int] = mapped_column(
        comment="所属实验室ID", nullable=False
    )
    model: Mapped[str | None] = mapped_column(
        String(100), comment="设备型号"
    )
    serial_number: Mapped[str | None] = mapped_column(
        String(100), comment="序列号", unique=True
    )
    description: Mapped[str | None] = mapped_column(
        Text, comment="设备描述"
    )
    purchase_date: Mapped[str | None] = mapped_column(
        String(20), comment="购入日期"
    )
    maintenance_status: Mapped[str] = mapped_column(
        String(20), default="正常", comment="维护状态 正常/维修中/停用", nullable=False
    )
    status: Mapped[int] = mapped_column(
        default=1, comment="状态 1正常 0禁用", nullable=False
    )
