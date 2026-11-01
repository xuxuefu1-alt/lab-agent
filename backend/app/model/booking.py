from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Booking(Base):
    __tablename__ = "booking"
    __table_args__ = {"comment": "实验室预约表"}

    laboratory_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[str] = mapped_column(String(20), nullable=False)
    end_time: Mapped[str] = mapped_column(String(20), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    student_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="待审核", nullable=False)
    reject_reason: Mapped[str | None] = mapped_column(Text)
    remarks: Mapped[str | None] = mapped_column(Text)
    approved_by: Mapped[int | None] = mapped_column(Integer)
    approved_time: Mapped[datetime | None] = mapped_column(DateTime)

    equipment_links: Mapped[list["BookingEquipment"]] = relationship(
        "BookingEquipment",
        back_populates="booking",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    # 解析并校验设备 ID 列表。
    def equipment_ids(self) -> list[int]:
        return [link.equipment_id for link in self.equipment_links]
