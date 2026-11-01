import base64
import hashlib
import hmac
import json
import logging
import time
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessExceptions
from app.model.equipment import Equipment
from app.model.laboratory import Laboratory
from app.model.user import User
from app.model.booking import Booking
from app.schemas.booking import BookingCreate
from app.config import settings
from app.services.booking_services import BookingService
from app.services.booking_policy import is_standard_booking_slot

logger = logging.getLogger(__name__)


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
    laboratory_keyword: str | None = Field(default=None, max_length=100)
    equipment_keyword: str | None = Field(default=None, max_length=100)
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


class PendingBookingsToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str = Field(default="待审核", pattern="^待审核$")
    time_from: str | None = Field(default=None, max_length=16)
    time_to: str | None = Field(default=None, max_length=16)
    limit: int = Field(default=20, ge=1, le=50)


class CreateBookingToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    laboratory_id: int = Field(..., ge=1)
    equipment_ids: list[int] = Field(default_factory=list, max_length=20)
    start_time: str = Field(..., min_length=16, max_length=16)
    end_time: str = Field(..., min_length=16, max_length=16)
    purpose: str = Field(default="实验室/设备预约", min_length=1, max_length=500)
    student_count: int = Field(default=1, ge=1, le=100)
    remarks: str | None = Field(default=None, max_length=500)


class CancelBookingToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    booking_id: int = Field(..., ge=1)


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


def _encode_confirmation(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    body = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    signature = hmac.new(settings.JWT_SECRT_KEY.encode("utf-8"), body.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def verify_booking_confirmation(token: str, current_user: User) -> dict[str, Any]:
    try:
        body, signature = token.split(".", 1)
        expected = hmac.new(
            settings.JWT_SECRT_KEY.encode("utf-8"), body.encode("ascii"), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid signature")
        padding = "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode((body + padding).encode("ascii")))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError, TypeError) as exc:
        raise ValueError("invalid confirmation token") from exc
    if payload.get("action") != "create_booking":
        raise ValueError("invalid confirmation action")
    if payload.get("user_id") != current_user.id:
        raise ValueError("confirmation token belongs to another user")
    if payload.get("expires_at", 0) < int(time.time()):
        raise ValueError("confirmation token expired")
    return payload


def verify_cancel_booking_confirmation(token: str, current_user: User) -> dict[str, Any]:
    try:
        body, signature = token.split(".", 1)
        expected = hmac.new(
            settings.JWT_SECRT_KEY.encode("utf-8"), body.encode("ascii"), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid signature")
        padding = "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode((body + padding).encode("ascii")))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError, TypeError) as exc:
        raise ValueError("invalid cancellation token") from exc
    if payload.get("action") != "cancel_booking":
        raise ValueError("invalid cancellation action")
    if payload.get("user_id") != current_user.id:
        raise ValueError("cancellation token belongs to another user")
    if payload.get("expires_at", 0) < int(time.time()):
        raise ValueError("cancellation token expired")
    if not isinstance(payload.get("booking_id"), int):
        raise ValueError("invalid booking id")
    return payload


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
    laboratory_ids = {row.laboratory_id for row in rows}
    laboratories = (
        db.query(Laboratory)
        .filter(Laboratory.id.in_(laboratory_ids))
        .all()
        if laboratory_ids
        else []
    )
    laboratory_by_id = {row.id: row for row in laboratories}
    items = []
    for row in rows:
        item = _equipment_item(row)
        laboratory = laboratory_by_id.get(row.laboratory_id)
        item["laboratory_name"] = laboratory.name if laboratory else None
        item["laboratory_location"] = laboratory.location if laboratory else None
        items.append(item)
    return {"items": items, "count": len(items)}


def _list_open_laboratories_with_equipment(
    db: Session,
    laboratory_keyword: str | None,
    equipment_keyword: str | None,
    limit: int,
) -> dict[str, Any]:
    query = db.query(Laboratory).filter(Laboratory.status == 1)
    if laboratory_keyword:
        like = f"%{laboratory_keyword}%"
        query = query.filter((Laboratory.name.like(like)) | (Laboratory.location.like(like)))
    if equipment_keyword:
        like = f"%{equipment_keyword}%"
        matching_laboratory_ids = (
            db.query(Equipment.laboratory_id)
            .filter(
                Equipment.status == 1,
                Equipment.maintenance_status.in_(NORMAL_MAINTENANCE_STATUSES),
                (Equipment.name.like(like))
                | (Equipment.equipment_type.like(like))
                | (Equipment.model.like(like))
                | (Equipment.serial_number.like(like)),
            )
        )
        query = query.filter(Laboratory.id.in_(matching_laboratory_ids))
    laboratories = query.order_by(Laboratory.id).limit(limit).all()
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
    )
    if equipment_keyword:
        like = f"%{equipment_keyword}%"
        equipment_rows = equipment_rows.filter(
            (Equipment.name.like(like))
            | (Equipment.equipment_type.like(like))
            | (Equipment.model.like(like))
            | (Equipment.serial_number.like(like))
        )
    equipment_rows = equipment_rows.order_by(Equipment.id).all()
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
    if status == "active":
        query = query.filter(Booking.status.in_(["待审核", "已批准"]))
    elif status:
        query = query.filter(Booking.status == status)
    rows = query.order_by(Booking.id.desc()).limit(limit).all()
    return {"items": [_booking_item(db, row) for row in rows], "count": len(rows)}


def _list_pending_bookings(
    db: Session,
    status: str,
    time_from: str | None,
    time_to: str | None,
    limit: int,
) -> dict[str, Any]:
    query = db.query(Booking).filter(Booking.status == status)
    if time_from:
        query = query.filter(Booking.start_time >= time_from)
    if time_to:
        query = query.filter(Booking.start_time < time_to)
    rows = query.order_by(Booking.id.desc()).limit(limit).all()
    items = []
    for row in rows:
        item = _booking_item(db, row)
        user = db.query(User).filter(User.id == row.user_id).first()
        item.update({
            "user_id": row.user_id,
            "user_name": user.name if user else None,
            "username": user.username if user else None,
        })
        items.append(item)
    return {"items": items, "count": len(items)}


def _tool_failure(db: Session, exc: Exception) -> str:
    try:
        db.rollback()
    except Exception:
        logger.exception("Failed to rollback AI tool transaction")
    if isinstance(exc, BusinessExceptions):
        return json.dumps(
            {
                "ok": False,
                "error": str(exc),
                "retryable": False,
                "error_type": "business_rule",
            },
            ensure_ascii=False,
        )
    logger.exception("AI tool database operation failed")
    return json.dumps(
        {"ok": False, "error": "数据查询暂时失败，请稍后重试。", "retryable": True},
        ensure_ascii=False,
    )


def build_tools(db: Session, current_user: User) -> list[StructuredTool]:
    """Build request-scoped read-only tools; identity and DB access stay server-side."""

    def account_is_enabled() -> bool:
        return current_user.status == 1

    def list_open_laboratories(keyword: str | None = None, limit: int = 20) -> str:
        if not account_is_enabled():
            return json.dumps({"ok": False, "error": "当前账户已停用。"}, ensure_ascii=False)
        try:
            return json.dumps({"ok": True, "data": _list_open_laboratories(db, keyword, limit)}, ensure_ascii=False)
        except Exception as exc:
            return _tool_failure(db, exc)

    def list_laboratory_equipment(
        laboratory_id: int | None = None,
        keyword: str | None = None,
        limit: int = 20,
    ) -> str:
        if not account_is_enabled():
            return json.dumps({"ok": False, "error": "当前账户已停用。"}, ensure_ascii=False)
        try:
            return json.dumps(
                {"ok": True, "data": _list_laboratory_equipment(db, laboratory_id, keyword, limit)},
                ensure_ascii=False,
            )
        except Exception as exc:
            return _tool_failure(db, exc)

    def list_open_laboratories_with_equipment(
        laboratory_keyword: str | None = None,
        equipment_keyword: str | None = None,
        limit: int = 20,
    ) -> str:
        if not account_is_enabled():
            return json.dumps({"ok": False, "error": "当前账户已停用。"}, ensure_ascii=False)
        try:
            return json.dumps(
                {
                    "ok": True,
                    "data": _list_open_laboratories_with_equipment(
                        db, laboratory_keyword, equipment_keyword, limit
                    ),
                },
                ensure_ascii=False,
            )
        except Exception as exc:
            return _tool_failure(db, exc)

    def get_current_user_profile() -> str:
        if not account_is_enabled():
            return json.dumps({"ok": False, "error": "当前账户已停用。"}, ensure_ascii=False)
        return json.dumps(
            {"ok": True, "data": {"access": _permission_summary(current_user)}},
            ensure_ascii=False,
        )

    def get_user_profile(user_id: int) -> str:
        if not account_is_enabled():
            return json.dumps({"ok": False, "error": "当前账户已停用。"}, ensure_ascii=False)
        if current_user.role != "admin" and user_id != current_user.id:
            return json.dumps({"ok": False, "error": "你只能查看自己的账户权限摘要。"}, ensure_ascii=False)
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user is None:
                return json.dumps({"ok": False, "error": "未找到对应用户。"}, ensure_ascii=False)
            return json.dumps(
                {"ok": True, "data": {"access": _permission_summary(user)}},
                ensure_ascii=False,
            )
        except Exception as exc:
            return _tool_failure(db, exc)

    def list_users(
        keyword: str | None = None,
        role: str | None = None,
        status: int | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> str:
        if not account_is_enabled():
            return json.dumps({"ok": False, "error": "当前账户已停用。"}, ensure_ascii=False)
        if current_user.role != "admin":
            return json.dumps({"ok": False, "error": "只有管理员可以查询用户列表。"}, ensure_ascii=False)
        try:
            return json.dumps(
                {"ok": True, "data": _list_users(db, keyword, role, status, skip, limit)},
                ensure_ascii=False,
            )
        except Exception as exc:
            return _tool_failure(db, exc)

    def list_my_bookings(status: str | None = None, limit: int = 20) -> str:
        if not account_is_enabled():
            return json.dumps({"ok": False, "error": "当前账户已停用。"}, ensure_ascii=False)
        try:
            return json.dumps(
                {"ok": True, "data": _list_my_bookings(db, current_user.id, status, limit)},
                ensure_ascii=False,
            )
        except Exception as exc:
            return _tool_failure(db, exc)

    def list_pending_bookings(
        status: str = "待审核",
        time_from: str | None = None,
        time_to: str | None = None,
        limit: int = 20,
    ) -> str:
        if not account_is_enabled():
            return json.dumps({"ok": False, "error": "当前账户已停用。"}, ensure_ascii=False)
        if current_user.role != "admin":
            return json.dumps({"ok": False, "error": "只有管理员可以查询其他用户的待审批预约。"}, ensure_ascii=False)
        try:
            return json.dumps(
                {
                    "ok": True,
                    "data": _list_pending_bookings(db, status, time_from, time_to, limit),
                },
                ensure_ascii=False,
            )
        except Exception as exc:
            return _tool_failure(db, exc)

    def prepare_create_booking(
        laboratory_id: int,
        equipment_ids: list[int] | None = None,
        start_time: str = "",
        end_time: str = "",
        purpose: str = "实验室/设备预约",
        student_count: int = 1,
        remarks: str | None = None,
    ) -> str:
        if not account_is_enabled():
            return json.dumps({"ok": False, "error": "当前账户已停用。"}, ensure_ascii=False)
        try:
            request = BookingCreate(
                laboratory_id=laboratory_id,
                equipment_ids=equipment_ids or [],
                start_time=start_time,
                end_time=end_time,
                purpose=purpose,
                student_count=student_count,
                remarks=remarks,
            )
            start = BookingService._parse_time(request.start_time)
            end = BookingService._parse_time(request.end_time)
            if start >= end:
                return json.dumps({"ok": False, "error": "结束时间必须晚于开始时间。"}, ensure_ascii=False)
            if not is_standard_booking_slot((start.hour, start.minute, end.hour, end.minute)):
                return json.dumps(
                    {
                        "ok": False,
                        "error": "该时间段不属于可预约时段，请选择 08:00–10:00、10:00–12:00、14:00–16:00、16:00–18:00 或 19:00–21:00。",
                        "error_code": "invalid_standard_slot",
                    },
                    ensure_ascii=False,
                )
            normalized_ids = BookingService._validate_resources(db, request.laboratory_id, request.equipment_ids)
            BookingService._ensure_no_conflict(db, request.laboratory_id, normalized_ids, start, end)
            laboratory = db.query(Laboratory).filter(Laboratory.id == request.laboratory_id).first()
            equipment_rows = db.query(Equipment).filter(Equipment.id.in_(normalized_ids)).all() if normalized_ids else []
            booking = {
                "laboratory_id": request.laboratory_id,
                "laboratory_name": laboratory.name if laboratory else None,
                "equipment_ids": normalized_ids,
                "equipment": [{"id": item.id, "name": item.name} for item in equipment_rows],
                "start_time": request.start_time,
                "end_time": request.end_time,
                "purpose": request.purpose,
                "student_count": request.student_count,
                "remarks": request.remarks,
            }
            token = _encode_confirmation({
                "action": "create_booking",
                "user_id": current_user.id,
                "expires_at": int(time.time()) + 600,
                "booking": booking,
            })
            return json.dumps(
                {"ok": True, "data": {"status": "pending_confirmation", "booking": booking, "confirmation_token": token}},
                ensure_ascii=False,
            )
        except Exception as exc:
            return _tool_failure(db, exc)

    def prepare_cancel_booking(booking_id: int) -> str:
        if not account_is_enabled():
            return json.dumps({"ok": False, "error": "当前账户已停用。"}, ensure_ascii=False)
        try:
            booking = (
                db.query(Booking)
                .filter(Booking.id == booking_id, Booking.user_id == current_user.id)
                .first()
            )
            if booking is None:
                return json.dumps({"ok": False, "error": "未找到属于当前账户的预约。"}, ensure_ascii=False)
            if booking.status in {"已取消", "已拒绝"}:
                return json.dumps({"ok": False, "error": "该预约当前不可取消。"}, ensure_ascii=False)
            summary = _booking_item(db, booking)
            token = _encode_confirmation(
                {
                    "action": "cancel_booking",
                    "user_id": current_user.id,
                    "booking_id": booking.id,
                    "expires_at": int(time.time()) + 600,
                }
            )
            return json.dumps(
                {
                    "ok": True,
                    "data": {
                        "status": "pending_confirmation",
                        "booking": summary,
                        "confirmation_token": token,
                    },
                },
                ensure_ascii=False,
            )
        except Exception as exc:
            return _tool_failure(db, exc)

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
            description="List equipment with its owning laboratory name and location. Use this when the user asks which laboratory contains a specific equipment item, type, model, or keyword.",
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
            description="List bookings belonging to the authenticated user. Use status=active for current pending or approved bookings; use no status only when the user explicitly asks for booking history.",
            args_schema=MyBookingsToolArgs,
        ),
        StructuredTool.from_function(
            func=list_pending_bookings,
            name="list_pending_bookings",
            description="查询所有用户的待审核预约。仅管理员可用，不执行审批写入。",
            args_schema=PendingBookingsToolArgs,
        ),
        StructuredTool.from_function(
            func=prepare_create_booking,
            name="prepare_create_booking",
            description="准备实验室和设备预约。仅在实验室、设备、开始时间和结束时间都已明确后调用；用途默认是“实验室/设备预约”，使用人数默认是 1；返回待确认的预约信息，不代表预约已经创建。",
            args_schema=CreateBookingToolArgs,
        ),
        StructuredTool.from_function(
            func=prepare_cancel_booking,
            name="prepare_cancel_booking",
            description="准备取消当前登录用户自己的预约。只生成待确认信息，不会直接取消；必须先获得用户明确确认。",
            args_schema=CancelBookingToolArgs,
        ),
    ]
