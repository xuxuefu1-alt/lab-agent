from sqlalchemy.orm import Session
from datetime import datetime
from app.model.booking import Booking
from app.schemas.booking import BookingCreate, BookingUpdate, BookingApprove
from app.common.exceptions import BusinessExceptions


class BookingService:
    @staticmethod
    def create_booking(db: Session, user_id: int, booking: BookingCreate) -> Booking:
        """创建预约"""
        # 验证时间格式
        try:
            start = datetime.strptime(booking.start_time, "%Y-%m-%d %H:%M")
            end = datetime.strptime(booking.end_time, "%Y-%m-%d %H:%M")
            if start >= end:
                raise BusinessExceptions("结束时间必须晚于开始时间")
        except ValueError:
            raise BusinessExceptions("时间格式错误，应为 YYYY-MM-DD HH:mm")

        # 检查时间冲突
        conflicted = db.query(Booking).filter(
            Booking.laboratory_id == booking.laboratory_id,
            Booking.status.in_(["待审核", "已批准"]),
            Booking.start_time < booking.end_time,
            Booking.end_time > booking.start_time,
        ).first()

        if conflicted:
            raise BusinessExceptions("该时间段已被预约")

        db_booking = Booking(
            laboratory_id=booking.laboratory_id,
            user_id=user_id,
            start_time=booking.start_time,
            end_time=booking.end_time,
            purpose=booking.purpose,
            student_count=booking.student_count,
            remarks=booking.remarks,
            status="待审核",
        )

        db.add(db_booking)
        db.commit()
        db.refresh(db_booking)
        return db_booking

    @staticmethod
    def get_booking_by_id(db: Session, booking_id: int) -> Booking:
        """根据ID获取预约"""
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise BusinessExceptions("预约不存在")
        return booking

    @staticmethod
    def get_all_bookings(db: Session, skip: int = 0, limit: int = 10) -> list[Booking]:
        """获取所有预约"""
        return db.query(Booking).offset(skip).limit(limit).all()

    @staticmethod
    def get_bookings_count(db: Session) -> int:
        """获取预约总数"""
        return db.query(Booking).count()

    @staticmethod
    def get_user_bookings(db: Session, user_id: int, skip: int = 0, limit: int = 10) -> list[Booking]:
        """获取用户的预约列表"""
        return db.query(Booking).filter(Booking.user_id == user_id).offset(skip).limit(limit).all()

    @staticmethod
    def get_user_bookings_count(db: Session, user_id: int) -> int:
        """获取用户预约总数"""
        return db.query(Booking).filter(Booking.user_id == user_id).count()

    @staticmethod
    def get_bookings_by_status(db: Session, status: str, skip: int = 0, limit: int = 10) -> list[Booking]:
        """根据状态获取预约"""
        return db.query(Booking).filter(Booking.status == status).offset(skip).limit(limit).all()

    @staticmethod
    def get_bookings_by_laboratory(db: Session, laboratory_id: int, skip: int = 0, limit: int = 10) -> list[Booking]:
        """根据实验室获取预约"""
        return db.query(Booking).filter(Booking.laboratory_id == laboratory_id).offset(skip).limit(limit).all()

    @staticmethod
    def update_booking(db: Session, booking_id: int, booking: BookingUpdate) -> Booking:
        """更新预约"""
        db_booking = BookingService.get_booking_by_id(db, booking_id)

        # 只能修改待审核状态的预约
        if db_booking.status != "待审核":
            raise BusinessExceptions("只能修改待审核状态的预约")

        update_data = booking.model_dump(exclude_unset=True)
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
        """审批预约"""
        db_booking = BookingService.get_booking_by_id(db, booking_id)

        if db_booking.status != "待审核":
            raise BusinessExceptions("只能审批待审核状态的预约")

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
        """取消预约"""
        db_booking = BookingService.get_booking_by_id(db, booking_id)

        if db_booking.status in ["已拒绝", "已取消"]:
            raise BusinessExceptions("该预约无法取消")

        db_booking.status = "已取消"
        db.add(db_booking)
        db.commit()
        return {"message": "预约已取消"}

    @staticmethod
    def delete_booking(db: Session, booking_id: int) -> dict:
        """删除预约"""
        db_booking = BookingService.get_booking_by_id(db, booking_id)
        db.delete(db_booking)
        db.commit()
        return {"message": "预约已删除"}
