from datetime import datetime

from sqlalchemy.orm import Session

from app.common.exceptions import BusinessExceptions
from app.model.booking import Booking
from app.schemas.booking import BookingApprove, BookingCreate, BookingUpdate


PENDING = "\u5f85\u5ba1\u6838"
APPROVED = "\u5df2\u6279\u51c6"
REJECTED = "\u5df2\u62d2\u7edd"
CANCELLED = "\u5df2\u53d6\u6d88"


class BookingService:
    @staticmethod
    def _parse_time(value: str) -> datetime:
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M")
        except ValueError as exc:
            raise BusinessExceptions("Invalid time format; expected YYYY-MM-DD HH:mm") from exc

    @staticmethod
    def _ensure_no_conflict(
        db: Session,
        laboratory_id: int,
        start: datetime,
        end: datetime,
        exclude_booking_id: int | None = None,
    ) -> None:
        query = db.query(Booking).filter(
            Booking.laboratory_id == laboratory_id,
            Booking.status.in_([PENDING, APPROVED]),
        )
        if exclude_booking_id is not None:
            query = query.filter(Booking.id != exclude_booking_id)

        for existing in query.all():
            existing_start = BookingService._parse_time(existing.start_time)
            existing_end = BookingService._parse_time(existing.end_time)
            if existing_start < end and existing_end > start:
                raise BusinessExceptions("The selected time slot is already booked")

    @staticmethod
    def create_booking(db: Session, user_id: int, booking: BookingCreate) -> Booking:
        start = BookingService._parse_time(booking.start_time)
        end = BookingService._parse_time(booking.end_time)
        if start >= end:
            raise BusinessExceptions("End time must be later than start time")

        BookingService._ensure_no_conflict(db, booking.laboratory_id, start, end)

        db_booking = Booking(
            laboratory_id=booking.laboratory_id,
            user_id=user_id,
            start_time=booking.start_time,
            end_time=booking.end_time,
            purpose=booking.purpose,
            student_count=booking.student_count,
            remarks=booking.remarks,
            status=PENDING,
        )
        db.add(db_booking)
        db.commit()
        db.refresh(db_booking)
        return db_booking

    @staticmethod
    def get_booking_by_id(db: Session, booking_id: int) -> Booking:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise BusinessExceptions("Booking not found")
        return booking

    @staticmethod
    def get_all_bookings(db: Session, skip: int = 0, limit: int = 10) -> list[Booking]:
        return db.query(Booking).offset(skip).limit(limit).all()

    @staticmethod
    def get_bookings_count(db: Session) -> int:
        return db.query(Booking).count()

    @staticmethod
    def get_user_bookings(db: Session, user_id: int, skip: int = 0, limit: int = 10) -> list[Booking]:
        return db.query(Booking).filter(Booking.user_id == user_id).offset(skip).limit(limit).all()

    @staticmethod
    def get_user_bookings_count(db: Session, user_id: int) -> int:
        return db.query(Booking).filter(Booking.user_id == user_id).count()

    @staticmethod
    def get_bookings_by_status(db: Session, status: str, skip: int = 0, limit: int = 10) -> list[Booking]:
        return db.query(Booking).filter(Booking.status == status).offset(skip).limit(limit).all()

    @staticmethod
    def get_bookings_by_laboratory(db: Session, laboratory_id: int, skip: int = 0, limit: int = 10) -> list[Booking]:
        return db.query(Booking).filter(Booking.laboratory_id == laboratory_id).offset(skip).limit(limit).all()

    @staticmethod
    def update_booking(db: Session, booking_id: int, booking: BookingUpdate) -> Booking:
        db_booking = BookingService.get_booking_by_id(db, booking_id)
        if db_booking.status != PENDING:
            raise BusinessExceptions("Only pending bookings can be modified")

        update_data = booking.model_dump(exclude_unset=True)
        next_start = update_data.get("start_time", db_booking.start_time)
        next_end = update_data.get("end_time", db_booking.end_time)
        start = BookingService._parse_time(next_start)
        end = BookingService._parse_time(next_end)
        if start >= end:
            raise BusinessExceptions("End time must be later than start time")

        BookingService._ensure_no_conflict(
            db,
            db_booking.laboratory_id,
            start,
            end,
            exclude_booking_id=booking_id,
        )
        for field, value in update_data.items():
            setattr(db_booking, field, value)

        db.add(db_booking)
        db.commit()
        db.refresh(db_booking)
        return db_booking

    @staticmethod
    def approve_booking(
        db: Session, booking_id: int, approve_data: BookingApprove, approved_by: int
    ) -> Booking:
        db_booking = BookingService.get_booking_by_id(db, booking_id)
        if db_booking.status != PENDING:
            raise BusinessExceptions("Only pending bookings can be approved")
        if approve_data.status not in [APPROVED, REJECTED]:
            raise BusinessExceptions("Invalid approval status")

        db_booking.status = approve_data.status
        db_booking.reject_reason = approve_data.reject_reason
        db_booking.remarks = approve_data.remarks
        db_booking.approved_by = approved_by
        db_booking.approved_time = datetime.now()
        db.add(db_booking)
        db.commit()
        db.refresh(db_booking)
        return db_booking

    @staticmethod
    def cancel_booking(db: Session, booking_id: int) -> dict:
        db_booking = BookingService.get_booking_by_id(db, booking_id)
        if db_booking.status in [REJECTED, CANCELLED]:
            raise BusinessExceptions("This booking cannot be cancelled")
        db_booking.status = CANCELLED
        db.add(db_booking)
        db.commit()
        return {"message": "Booking cancelled"}

    @staticmethod
    def delete_booking(db: Session, booking_id: int) -> dict:
        db_booking = BookingService.get_booking_by_id(db, booking_id)
        db.delete(db_booking)
        db.commit()
        return {"message": "Booking deleted"}
