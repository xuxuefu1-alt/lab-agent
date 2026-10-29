from datetime import datetime

from sqlalchemy.orm import Session

from app.common.exceptions import BusinessExceptions
from app.model.booking import Booking
from app.model.booking_equipment import BookingEquipment
from app.model.equipment import Equipment
from app.model.laboratory import Laboratory
from app.model.user import User
from app.schemas.booking import BookingApprove, BookingCreate, BookingUpdate
from app.services.booking_policy import (
    format_standard_booking_slots,
    is_standard_booking_slot,
)


PENDING = "待审核"
APPROVED = "已批准"
REJECTED = "已拒绝"
CANCELLED = "已取消"
NORMAL_MAINTENANCE_STATUSES = {"正常", "Normal", "姝ｅ父"}


class BookingService:
    @staticmethod
    def _parse_time(value: str) -> datetime:
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M")
        except (TypeError, ValueError) as exc:
            raise BusinessExceptions("时间格式不正确，请使用 YYYY-MM-DD HH:mm 格式。") from exc

    @staticmethod
    def _validate_resources(db: Session, laboratory_id: int, equipment_ids: list[int]) -> list[int]:
        laboratory = db.query(Laboratory).filter(
            Laboratory.id == laboratory_id,
            Laboratory.status == 1,
        ).first()
        if laboratory is None:
            raise BusinessExceptions("所选实验室当前不可预约。")

        normalized_ids = list(dict.fromkeys(equipment_ids or []))
        if len(normalized_ids) > 20:
            raise BusinessExceptions("最多只能选择 20 件设备。")
        if not normalized_ids:
            return []

        equipment_rows = db.query(Equipment).filter(Equipment.id.in_(normalized_ids)).all()
        by_id = {row.id: row for row in equipment_rows}
        if any(item_id not in by_id for item_id in normalized_ids):
            raise BusinessExceptions("所选设备不存在。")

        for item_id in normalized_ids:
            equipment = by_id[item_id]
            if equipment.laboratory_id != laboratory_id:
                raise BusinessExceptions("所选设备不属于当前实验室。")
            if equipment.status != 1:
                raise BusinessExceptions("所选设备已停用。")
            if equipment.maintenance_status not in NORMAL_MAINTENANCE_STATUSES:
                raise BusinessExceptions("所选设备当前不可预约，可能处于维护状态。")
        return normalized_ids

    @staticmethod
    def _ensure_no_conflict(
        db: Session,
        laboratory_id: int,
        equipment_ids: list[int],
        start: datetime,
        end: datetime,
        exclude_booking_id: int | None = None,
    ) -> None:
        lab_query = db.query(Booking).filter(
            Booking.laboratory_id == laboratory_id,
            Booking.status.in_([PENDING, APPROVED]),
        )
        if exclude_booking_id is not None:
            lab_query = lab_query.filter(Booking.id != exclude_booking_id)
        for existing in lab_query.all():
            existing_start = BookingService._parse_time(existing.start_time)
            existing_end = BookingService._parse_time(existing.end_time)
            if existing_start < end and existing_end > start:
                raise BusinessExceptions("所选实验室在该时间段已被预约，请更换时间。")

        if not equipment_ids:
            return
        equipment_query = (
            db.query(Booking)
            .join(BookingEquipment, BookingEquipment.booking_id == Booking.id)
            .filter(
                BookingEquipment.equipment_id.in_(equipment_ids),
                Booking.status.in_([PENDING, APPROVED]),
            )
        )
        if exclude_booking_id is not None:
            equipment_query = equipment_query.filter(Booking.id != exclude_booking_id)
        for existing in equipment_query.all():
            existing_start = BookingService._parse_time(existing.start_time)
            existing_end = BookingService._parse_time(existing.end_time)
            if existing_start < end and existing_end > start:
                raise BusinessExceptions("所选设备中有一件或多件在该时间段已被预约，请更换时间或设备。")

    @staticmethod
    def _replace_equipment_links(db: Session, booking: Booking, equipment_ids: list[int]) -> None:
        booking.equipment_links.clear()
        booking.equipment_links.extend(
            BookingEquipment(equipment_id=equipment_id) for equipment_id in equipment_ids
        )
        db.add(booking)

    @staticmethod
    def create_booking(db: Session, user_id: int, booking: BookingCreate) -> Booking:
        start = BookingService._parse_time(booking.start_time)
        end = BookingService._parse_time(booking.end_time)
        if start >= end:
            raise BusinessExceptions("结束时间必须晚于开始时间。")
        if not is_standard_booking_slot((start.hour, start.minute, end.hour, end.minute)):
            raise BusinessExceptions(
                f"该时间段不属于可预约时段，请选择：{format_standard_booking_slots()}。"
            )

        # Serialize booking checks for the same laboratory.
        locked_laboratory = (
            db.query(Laboratory)
            .filter(
                Laboratory.id == booking.laboratory_id,
                Laboratory.status == 1,
            )
            .with_for_update()
            .first()
        )
        if locked_laboratory is None:
            raise BusinessExceptions("所选实验室当前不可预约。")

        equipment_ids = BookingService._validate_resources(db, booking.laboratory_id, booking.equipment_ids)
        BookingService._ensure_no_conflict(db, booking.laboratory_id, equipment_ids, start, end)

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
        db.flush()
        BookingService._replace_equipment_links(db, db_booking, equipment_ids)
        db.commit()
        db.refresh(db_booking)
        return db_booking

    @staticmethod
    def get_booking_by_id(db: Session, booking_id: int) -> Booking:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise BusinessExceptions("未找到对应预约。")
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
    def list_bookings(
        db: Session,
        skip: int = 0,
        limit: int = 10,
        status: str | None = None,
        laboratory_id: int | None = None,
        user_keyword: str | None = None,
        time_from: str | None = None,
        time_to: str | None = None,
        user_id: int | None = None,
    ) -> tuple[list[Booking], int]:
        query = db.query(Booking)
        if user_keyword:
            like = f"%{user_keyword}%"
            query = query.join(User, User.id == Booking.user_id).filter(
                (User.username.like(like)) | (User.name.like(like))
            )
        if user_id is not None:
            query = query.filter(Booking.user_id == user_id)
        if status:
            query = query.filter(Booking.status == status)
        if laboratory_id is not None:
            query = query.filter(Booking.laboratory_id == laboratory_id)
        if time_from:
            query = query.filter(Booking.end_time >= time_from)
        if time_to:
            query = query.filter(Booking.start_time <= time_to)
        total = query.count()
        rows = query.order_by(Booking.id.desc()).offset(skip).limit(limit).all()
        return rows, total

    @staticmethod
    def update_booking(db: Session, booking_id: int, booking: BookingUpdate) -> Booking:
        db_booking = BookingService.get_booking_by_id(db, booking_id)
        if db_booking.status != PENDING:
            raise BusinessExceptions("只有待审核状态的预约可以修改。")

        update_data = booking.model_dump(exclude_unset=True)
        next_laboratory_id = update_data.pop("laboratory_id", db_booking.laboratory_id)
        next_start = update_data.get("start_time", db_booking.start_time)
        next_end = update_data.get("end_time", db_booking.end_time)
        start = BookingService._parse_time(next_start)
        end = BookingService._parse_time(next_end)
        if start >= end:
            raise BusinessExceptions("结束时间必须晚于开始时间。")
        if not is_standard_booking_slot((start.hour, start.minute, end.hour, end.minute)):
            raise BusinessExceptions(
                f"该时间段不属于可预约时段，请选择：{format_standard_booking_slots()}。"
            )

        equipment_was_sent = "equipment_ids" in update_data
        next_equipment_ids = update_data.pop("equipment_ids", None)
        if next_equipment_ids is None:
            next_equipment_ids = db_booking.equipment_ids
        next_equipment_ids = BookingService._validate_resources(
            db, next_laboratory_id, next_equipment_ids
        )
        BookingService._ensure_no_conflict(
            db, next_laboratory_id, next_equipment_ids, start, end, exclude_booking_id=booking_id
        )
        db_booking.laboratory_id = next_laboratory_id
        for field, value in update_data.items():
            setattr(db_booking, field, value)
        if equipment_was_sent:
            BookingService._replace_equipment_links(db, db_booking, next_equipment_ids)
        db.commit()
        db.refresh(db_booking)
        return db_booking

    @staticmethod
    def approve_booking(db: Session, booking_id: int, approve_data: BookingApprove, approved_by: int) -> Booking:
        db_booking = BookingService.get_booking_by_id(db, booking_id)
        if db_booking.status != PENDING:
            raise BusinessExceptions("只有待审核状态的预约可以审批。")
        if approve_data.status not in [APPROVED, REJECTED]:
            raise BusinessExceptions("审批状态不正确。")
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
    def cancel_booking(
        db: Session,
        booking_id: int,
        actor_user_id: int | None = None,
        actor_role: str | None = None,
    ) -> dict:
        db_booking = (
            db.query(Booking)
            .filter(Booking.id == booking_id)
            .with_for_update()
            .first()
        )
        if db_booking is None:
            raise BusinessExceptions("未找到对应预约。")
        if actor_user_id is not None and db_booking.user_id != actor_user_id and actor_role != "admin":
            raise BusinessExceptions("你只能取消自己的预约。")
        if db_booking.status in [REJECTED, CANCELLED]:
            raise BusinessExceptions("这条预约当前不可取消。")
        db_booking.status = CANCELLED
        db.add(db_booking)
        db.commit()
        return {"message": "预约已取消。"}

    @staticmethod
    def delete_booking(db: Session, booking_id: int) -> dict:
        db_booking = BookingService.get_booking_by_id(db, booking_id)
        db.delete(db_booking)
        db.commit()
        return {"message": "预约已删除。"}
