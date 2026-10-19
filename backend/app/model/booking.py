from sqlalchemy import String, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from app.database import Base


class Booking(Base):
    __tablename__ = "booking"
    __table_args__ = {"comment": "实验室预约表"}

    laboratory_id: Mapped[int] = mapped_column(
        Integer, comment="实验室ID", nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, comment="用户ID", nullable=False
    )
    start_time: Mapped[str] = mapped_column(
        String(20), comment="开始时间 (YYYY-MM-DD HH:mm)", nullable=False
    )
    end_time: Mapped[str] = mapped_column(
        String(20), comment="结束时间 (YYYY-MM-DD HH:mm)", nullable=False
    )
    purpose: Mapped[str] = mapped_column(
        Text, comment="预约目的", nullable=False
    )
    student_count: Mapped[int] = mapped_column(
        Integer, default=1, comment="学生数量", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default="待审核", comment="状态 待审核/已批准/已拒绝/已取消", nullable=False
    )
    reject_reason: Mapped[str | None] = mapped_column(
        Text, comment="拒绝原因"
    )
    remarks: Mapped[str | None] = mapped_column(
        Text, comment="备注"
    )
    approved_by: Mapped[int | None] = mapped_column(
        Integer, comment="审批人ID"
    )
    approved_time: Mapped[datetime | None] = mapped_column(
        DateTime, comment="审批时间"
    )
