from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.model.booking import Booking
from app.model.equipment import Equipment
from app.model.user import User


ACTIVE_BOOKING_STATUSES = ("待审核", "已批准")


# 负责 empty state 相关逻辑，并返回处理结果。
def _empty_state() -> dict:
    return {
        "availability_status": "available",
        "availability_label": "可预约",
        "reservation": None,
        "reservations": [],
        "current_booking_id": None,
        "current_booking_start": None,
        "current_booking_end": None,
        "current_booking_status": None,
        "next_booking_id": None,
        "next_booking_start": None,
        "next_booking_end": None,
        "next_booking_status": None,
    }


# 负责 parse 相关逻辑，并返回处理结果。
def _parse(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return None


# 构建state相关数据或业务逻辑。
def _build_state(rows: list[Booking], now: datetime, users: dict[int, User]) -> dict:
    state = _empty_state()
    parsed_rows = []
    for row in rows:
        start = _parse(row.start_time)
        end = _parse(row.end_time)
        if start is None or end is None or start >= end:
            continue
        parsed_rows.append((row, start, end))

    current = [item for item in parsed_rows if item[1] <= now < item[2]]
    upcoming = [item for item in parsed_rows if item[1] > now]
    current.sort(key=lambda item: (item[0].status != "已批准", item[1]))
    upcoming.sort(key=lambda item: item[1])
    visible = sorted(current + upcoming, key=lambda item: item[1])
    reservation_details = [_reservation_detail(item[0], users) for item in visible]

    if current:
        row, _, _ = current[0]
        reservation = _reservation_detail(row, users)
        state.update(
            availability_status="occupied" if row.status == "已批准" else "pending",
            availability_label="存在预约",
            reservation=reservation,
            reservations=reservation_details,
            current_booking_id=row.id,
            current_booking_start=row.start_time,
            current_booking_end=row.end_time,
            current_booking_status=row.status,
        )
    elif upcoming:
        row, _, _ = upcoming[0]
        reservation = _reservation_detail(row, users)
        state.update(
            availability_status="reserved" if row.status == "已批准" else "pending",
            availability_label="存在预约",
            reservation=reservation,
            reservations=reservation_details,
            next_booking_id=row.id,
            next_booking_start=row.start_time,
            next_booking_end=row.end_time,
            next_booking_status=row.status,
        )
    return state


# 负责 reservation detail 相关逻辑，并返回处理结果。
def _reservation_detail(row: Booking, users: dict[int, User]) -> dict:
    applicant = users.get(row.user_id)
    approver = users.get(row.approved_by) if row.approved_by else None
    return {
        "id": row.id,
        "start_time": row.start_time,
        "end_time": row.end_time,
        "status": row.status,
        "user_name": applicant.name if applicant else None,
        "username": applicant.username if applicant else None,
        "approved_by_name": approver.name if approver else None,
        "approved_by_username": approver.username if approver else None,
    }


# 获取laboratory availability相关数据或业务逻辑。
def get_laboratory_availability(db: Session, laboratory_ids: list[int]) -> dict[int, dict]:
    if not laboratory_ids:
        return {}
    rows = (
        db.query(Booking)
        .filter(
            Booking.laboratory_id.in_(laboratory_ids),
            Booking.status.in_(ACTIVE_BOOKING_STATUSES),
        )
        .order_by(Booking.start_time.asc())
        .all()
    )
    grouped = {laboratory_id: [] for laboratory_id in laboratory_ids}
    for row in rows:
        grouped.setdefault(row.laboratory_id, []).append(row)
    user_ids = {row.user_id for row in rows}
    user_ids.update(row.approved_by for row in rows if row.approved_by)
    users = {user.id: user for user in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    now = datetime.now()
    return {laboratory_id: _build_state(items, now, users) for laboratory_id, items in grouped.items()}


# 获取equipment availability相关数据或业务逻辑。
def get_equipment_availability(db: Session, equipment_ids: list[int]) -> dict[int, dict]:
    if not equipment_ids:
        return {}
    equipment_rows = (
        db.query(Equipment)
        .filter(Equipment.id.in_(equipment_ids))
        .all()
    )
    laboratory_ids = list({item.laboratory_id for item in equipment_rows})
    laboratory_states = get_laboratory_availability(db, laboratory_ids)
    return {
        item.id: dict(laboratory_states.get(item.laboratory_id, _empty_state()))
        for item in equipment_rows
    }
