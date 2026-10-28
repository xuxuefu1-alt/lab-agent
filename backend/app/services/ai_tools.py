import json
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.model.equipment import Equipment
from app.model.laboratory import Laboratory
from app.model.user import User
from app.model.booking import Booking
from app.services.booking_services import BookingService


NORMAL_MAINTENANCE_STATUSES = {"正常", "Normal", "姝ｅ父"}


class LaboratoryToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    keyword: str | None = Field(default=None, max_length=100)
    limit: int = Field(default=20, ge=1, le=50)


class EquipmentToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    laboratory_id: int | None = Field(default=None, ge=1)
    keyword: str | None = Field(default=None, max_length=100)
    limit: int = Field(default=20, ge=1, le=50)


class LaboratoryEquipmentToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    keyword: str | None = Field(default=None, max_length=100)
    limit: int = Field(default=20, ge=1, le=50)


class UserListToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    keyword: str | None = Field(default=None, max_length=100)
    role: str | None = Field(default=None, pattern="^(student|admin)$")
    status: int | None = Field(default=None, ge=0, le=1)
    skip: int = Field(default=0, ge=0, le=10000)
    limit: int = Field(default=20, ge=1, le=50)


class UserProfileToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: int = Field(..., ge=1)


class MyBookingsToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str | None = Field(default=None, max_length=20)
    limit: int = Field(default=20, ge=1, le=50)


def _laboratory_item(item: Laboratory) -> dict[str, Any]:
    return {
        "id": item.id,
        "name": item.name,
        "location": item.location,
        "capacity": item.capacity,
        "description": item.description,
        "status": item.status,
    }


def _equipment_item(item: Equipment) -> dict[str, Any]:
    reservable = item.status == 1 and item.maintenance_status in NORMAL_MAINTENANCE_STATUSES
    return {
        "id": item.id,
        "name": item.name,
        "equipment_type": item.equipment_type,
        "laboratory_id": item.laboratory_id,
        "model": item.model,
        "serial_number": item.serial_number,
        "maintenance_status": item.maintenance_status,
        "status": item.status,
        "reservable": reservable,
    }


def _user_item(item: User) -> dict[str, Any]:
    return {
        "id": item.id,
        "username": item.username,
        "name": item.name,
        "role": item.role,
        "email": item.email,
        "phone": item.phone,
        "status": item.status,
    }


def _permission_summary(user: User) -> dict[str, Any]:
    is_admin = user.role == "admin"
    return {
        "role": user.role,
        "role_label": "\u7ba1\u7406\u5458" if is_admin else "\u5b66\u751f",
        "status": user.status,
        "permissions": {
            "query_own_profile": True,
            "query_own_bookings": True,
            "manage_users": is_admin,
            "query_all_users": is_admin,
            "query_all_bookings": is_admin,
            "approve_bookings": is_admin,
        },
    }


def _booking_item(db: Session, item: Booking) -> dict[str, Any]:
    laboratory = db.query(Laboratory).filter(Laboratory.id == item.laboratory_id).first()
    equipment_ids = item.equipment_ids
    equipment_rows = []
    if equipment_ids:
        equipment_rows = db.query(Equipment).filter(Equipment.id.in_(equipment_ids)).all()
    equipment_by_id = {row.id: row for row in equipment_rows}
    return {
        "id": item.id,
        "laboratory_id": item.laboratory_id,
        "laboratory_name": laboratory.name if laboratory else None,
        "equipment": [
            {"id": equipment_id, "name": equipment_by_id[equipment_id].name}
            for equipment_id in equipment_ids
            if equipment_id in equipment_by_id
        ],
        "start_time": item.start_time,
        "end_time": item.end_time,
        "purpose": item.purpose,
        "student_count": item.student_count,
        "status": item.status,
        "reject_reason": item.reject_reason,
        "remarks": item.remarks,
    }


def _active_laboratories(db: Session, keyword: str | None, limit: int) -> list[Laboratory]:
    query = db.query(Laboratory).filter(Laboratory.status == 1)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter((Laboratory.name.like(like)) | (Laboratory.location.like(like)))
    return query.order_by(Laboratory.id).limit(limit).all()


def _equipment_query(db: Session, laboratory_id: int | None, keyword: str | None, limit: int):
    query = db.query(Equipment)
    if laboratory_id is not None:
        query = query.filter(Equipment.laboratory_id == laboratory_id)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            (Equipment.name.like(like))
            | (Equipment.equipment_type.like(like))
            | (Equipment.model.like(like))
            | (Equipment.serial_number.like(like))
        )
    return query.order_by(Equipment.id).limit(limit)


def _list_open_laboratories(db: Session, keyword: str | None, limit: int) -> dict[str, Any]:
    rows = _active_laboratories(db, keyword, limit)
    return {"items": [_laboratory_item(row) for row in rows], "count": len(rows)}


def _list_laboratory_equipment(
    db: Session,
    laboratory_id: int | None,
    keyword: str | None,
    limit: int,
) -> dict[str, Any]:
    rows = _equipment_query(db, laboratory_id, keyword, limit).all()
    return {"items": [_equipment_item(row) for row in rows], "count": len(rows)}


def _list_open_laboratories_with_equipment(
    db: Session, keyword: str | None, limit: int
) -> dict[str, Any]:
    laboratories = _active_laboratories(db, keyword, limit)
    if not laboratories:
        return {"items": [], "count": 0}
    laboratory_ids = [item.id for item in laboratories]
    equipment_rows = (
        db.query(Equipment)
        .filter(
            Equipment.laboratory_id.in_(laboratory_ids),
            Equipment.status == 1,
            Equipment.maintenance_status.in_(NORMAL_MAINTENANCE_STATUSES),
        )
        .order_by(Equipment.id)
        .all()
    )
    by_laboratory: dict[int, list[dict[str, Any]]] = {item.id: [] for item in laboratories}
    for equipment in equipment_rows:
        by_laboratory[equipment.laboratory_id].append(_equipment_item(equipment))
    items = [
        {"laboratory": _laboratory_item(laboratory), "equipment": by_laboratory[laboratory.id]}
        for laboratory in laboratories
    ]
    return {"items": items, "count": len(items)}


def _list_users(
    db: Session,
    keyword: str | None,
    role: str | None,
    status: int | None,
    skip: int,
    limit: int,
) -> dict[str, Any]:
    query = db.query(User)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            (User.username.like(like))
            | (User.name.like(like))
            | (User.email.like(like))
        )
    if role is not None:
        query = query.filter(User.role == role)
    if status is not None:
        query = query.filter(User.status == status)
    total = query.count()
    rows = query.order_by(User.id).offset(skip).limit(limit).all()
    return {"items": [_user_item(row) for row in rows], "count": len(rows), "total": total}


def _list_my_bookings(
    db: Session,
    user_id: int,
    status: str | None,
    limit: int,
) -> dict[str, Any]:
    query = db.query(Booking).filter(Booking.user_id == user_id)
    if status:
        query = query.filter(Booking.status == status)
    rows = query.order_by(Booking.id.desc()).limit(limit).all()
    return {"items": [_booking_item(db, row) for row in rows], "count": len(rows)}


def build_tools(db: Session, current_user: User) -> list[StructuredTool]:
    """Build request-scoped read-only tools; identity and DB access stay server-side."""

    def account_is_enabled() -> bool:
        return current_user.status == 1

    def list_open_laboratories(keyword: str | None = None, limit: int = 20) -> str:
        if not account_is_enabled():
            return json.dumps({"ok": False, "error": "Current account is disabled."})
        try:
            return json.dumps({"ok": True, "data": _list_open_laboratories(db, keyword, limit)}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)[:300]}, ensure_ascii=False)

    def list_laboratory_equipment(
        laboratory_id: int | None = None,
        keyword: str | None = None,
        limit: int = 20,
    ) -> str:
        if not account_is_enabled():
            return json.dumps({"ok": False, "error": "Current account is disabled."})
        try:
            return json.dumps(
                {"ok": True, "data": _list_laboratory_equipment(db, laboratory_id, keyword, limit)},
                ensure_ascii=False,
            )
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)[:300]}, ensure_ascii=False)

    def list_open_laboratories_with_equipment(keyword: str | None = None, limit: int = 20) -> str:
        if not account_is_enabled():
            return json.dumps({"ok": False, "error": "Current account is disabled."})
        try:
            return json.dumps(
                {"ok": True, "data": _list_open_laboratories_with_equipment(db, keyword, limit)},
                ensure_ascii=False,
            )
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)[:300]}, ensure_ascii=False)

    def get_current_user_profile() -> str:
        if not account_is_enabled():
            return json.dumps({"ok": False, "error": "Current account is disabled."})
        return json.dumps(
            {"ok": True, "data": {"access": _permission_summary(current_user)}},
            ensure_ascii=False,
        )

    def get_user_profile(user_id: int) -> str:
        if not account_is_enabled():
            return json.dumps({"ok": False, "error": "Current account is disabled."})
        if current_user.role != "admin" and user_id != current_user.id:
            return json.dumps({"ok": False, "error": "You can only access your own profile."}, ensure_ascii=False)
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user is None:
                return json.dumps({"ok": False, "error": "User not found."}, ensure_ascii=False)
            return json.dumps(
                {"ok": True, "data": {"access": _permission_summary(user)}},
                ensure_ascii=False,
            )
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)[:300]}, ensure_ascii=False)

    def list_users(
        keyword: str | None = None,
        role: str | None = None,
        status: int | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> str:
        if not account_is_enabled():
            return json.dumps({"ok": False, "error": "Current account is disabled."})
        if current_user.role != "admin":
            return json.dumps({"ok": False, "error": "Only administrators can list users."}, ensure_ascii=False)
        try:
            return json.dumps(
                {"ok": True, "data": _list_users(db, keyword, role, status, skip, limit)},
                ensure_ascii=False,
            )
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)[:300]}, ensure_ascii=False)

    def list_my_bookings(status: str | None = None, limit: int = 20) -> str:
        if not account_is_enabled():
            return json.dumps({"ok": False, "error": "Current account is disabled."})
        try:
            return json.dumps(
                {"ok": True, "data": _list_my_bookings(db, current_user.id, status, limit)},
                ensure_ascii=False,
            )
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)[:300]}, ensure_ascii=False)

    return [
        StructuredTool.from_function(
            func=list_open_laboratories,
            name="list_open_laboratories",
            description="List active laboratories, optionally filtered by name or location.",
            args_schema=LaboratoryToolArgs,
        ),
        StructuredTool.from_function(
            func=list_laboratory_equipment,
            name="list_laboratory_equipment",
            description="List equipment, optionally filtered by laboratory or keyword.",
            args_schema=EquipmentToolArgs,
        ),
        StructuredTool.from_function(
            func=list_open_laboratories_with_equipment,
            name="list_open_laboratories_with_equipment",
            description="List active laboratories with reservable equipment grouped under each laboratory.",
            args_schema=LaboratoryEquipmentToolArgs,
        ),
        StructuredTool.from_function(
            func=get_current_user_profile,
            name="get_current_user_profile",
            description="Get only the authenticated user's role and permission summary. Never expose personal profile fields.",
        ),
        StructuredTool.from_function(
            func=get_user_profile,
            name="get_user_profile",
            description="Get only a user's role and permission summary. Personal profile fields are never returned.",
            args_schema=UserProfileToolArgs,
        ),
        StructuredTool.from_function(
            func=list_users,
            name="list_users",
            description="List users with filters. Administrators only; never returns passwords or password hashes.",
            args_schema=UserListToolArgs,
        ),
        StructuredTool.from_function(
            func=list_my_bookings,
            name="list_my_bookings",
            description="List bookings belonging to the authenticated user, including laboratory and equipment names.",
            args_schema=MyBookingsToolArgs,
        ),
    ]
