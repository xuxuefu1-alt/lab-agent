from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.schemas.booking import (
    BookingCreate,
    BookingUpdate,
    BookingApprove,
    BookingResponse,
)
from app.services.booking_services import BookingService
from app.common.respones import success_response
from app.model.user import User
from app.model.laboratory import Laboratory

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=success_response(BookingResponse))
async def create_booking(
    booking: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建预约"""
    db_booking = BookingService.create_booking(db, current_user.id, booking)
    return {
        "code": 200,
        "data": BookingResponse.model_validate(db_booking),
        "message": "预约创建成功，等待审批",
    }


@router.get("/{booking_id}", response_model=success_response(BookingResponse))
async def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取预约详情"""
    booking = BookingService.get_booking_by_id(db, booking_id)

    # 权限检查
    if booking.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="权限不足")

    return {
        "code": 200,
        "data": BookingResponse.model_validate(booking),
        "message": "获取成功",
    }


@router.get("", response_model=success_response(dict))
async def get_bookings(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: str | None = Query(None),
    laboratory_id: int | None = Query(None),
    user_keyword: str | None = Query(None, max_length=100),
    time_from: str | None = Query(None, max_length=16),
    time_to: str | None = Query(None, max_length=16),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取预约列表"""
    if current_user.role == "admin":
        bookings, total = BookingService.list_bookings(
            db,
            skip=skip,
            limit=limit,
            status=status,
            laboratory_id=laboratory_id,
            user_keyword=user_keyword,
            time_from=time_from,
            time_to=time_to,
        )
    else:
        # 学生只能查看自己的预约
        bookings, total = BookingService.list_bookings(
            db,
            skip=skip,
            limit=limit,
            status=status,
            laboratory_id=laboratory_id,
            time_from=time_from,
            time_to=time_to,
            user_id=current_user.id,
        )

    items = []
    for booking in bookings:
        item = BookingResponse.model_validate(booking).model_dump()
        user = db.query(User).filter(User.id == booking.user_id).first()
        laboratory = db.query(Laboratory).filter(Laboratory.id == booking.laboratory_id).first()
        item.update({
            "user_name": user.name if user else None,
            "username": user.username if user else None,
            "laboratory_name": laboratory.name if laboratory else None,
        })
        items.append(item)

    return {
        "code": 200,
        "data": {
            "items": items,
            "total": total,
            "skip": skip,
            "limit": limit,
        },
        "message": "获取成功",
    }


@router.put("/{booking_id}", response_model=success_response(BookingResponse))
async def update_booking(
    booking_id: int,
    booking: BookingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新预约"""
    db_booking = BookingService.get_booking_by_id(db, booking_id)

    # 权限检查
    if db_booking.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="权限不足")

    updated_booking = BookingService.update_booking(db, booking_id, booking)
    return {
        "code": 200,
        "data": BookingResponse.model_validate(updated_booking),
        "message": "预约更新成功",
    }


@router.post("/{booking_id}/approve", response_model=success_response(BookingResponse))
async def approve_booking(
    booking_id: int,
    approve_data: BookingApprove,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """审批预约"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以审批预约")

    approved_booking = BookingService.approve_booking(
        db, booking_id, approve_data, current_user.id
    )
    return {
        "code": 200,
        "data": BookingResponse.model_validate(approved_booking),
        "message": f"预约已{approve_data.status}",
    }


@router.post("/{booking_id}/cancel", response_model=success_response(dict))
async def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """取消预约"""
    db_booking = BookingService.get_booking_by_id(db, booking_id)

    # 权限检查
    if db_booking.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="权限不足")

    result = BookingService.cancel_booking(db, booking_id)
    return {
        "code": 200,
        "data": result,
        "message": result["message"],
    }


@router.delete("/{booking_id}", response_model=success_response(dict))
async def delete_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除预约"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以删除预约")

    result = BookingService.delete_booking(db, booking_id)
    return {
        "code": 200,
        "data": result,
        "message": result["message"],
    }
