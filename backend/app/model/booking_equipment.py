from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BookingEquipment(Base):
    __tablename__ = "booking_equipment"
    __table_args__ = (
        UniqueConstraint("booking_id", "equipment_id", name="uq_booking_equipment"),
    )

    booking_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("booking.id", ondelete="CASCADE"),
        nullable=False,
    )
    equipment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("equipment.id"),
        nullable=False,
    )
    booking: Mapped["Booking"] = relationship(back_populates="equipment_links")
