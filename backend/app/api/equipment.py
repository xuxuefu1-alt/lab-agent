from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.schemas.equipment import (
    EquipmentCreate,
    EquipmentUpdate,
    EquipmentResponse,
)
from app.services.equipment_services import EquipmentService
from app.common.respones import success_response

router = APIRouter(prefix="/equipment", tags=["equipment"])


@router.post("", response_model=success_response(EquipmentResponse))
async def create_equipment(
    equipment: EquipmentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """创建设备"""
    db_equipment = EquipmentService.create_equipment(db, equipment)
    return {"code": 200, "data": db_equipment, "message": "设备创建成功"}


@router.get("/{equipment_id}", response_model=success_response(EquipmentResponse))
async def get_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """获取设备详情"""
    equipment = EquipmentService.get_equipment_by_id(db, equipment_id)
    return {"code": 200, "data": equipment, "message": "获取成功"}


@router.get("", response_model=success_response(dict))
async def get_equipment_list(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    keyword: str | None = Query(None),
    laboratory_id: int | None = Query(None),
    maintenance_status: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """获取设备列表"""
    if keyword:
        equipment_list = EquipmentService.search_equipment(db, keyword, skip, limit)
    elif laboratory_id:
        equipment_list = EquipmentService.get_equipment_by_laboratory(
            db, laboratory_id, skip, limit
        )
    elif maintenance_status:
        equipment_list = EquipmentService.get_equipment_by_maintenance_status(
            db, maintenance_status, skip, limit
        )
    else:
        equipment_list = EquipmentService.get_all_equipment(db, skip, limit)

    if keyword:
        total = len(EquipmentService.search_equipment(db, keyword, 0, 1000000))
    elif laboratory_id is not None:
        total = EquipmentService.get_equipment_count_by_laboratory(db, laboratory_id)
    elif maintenance_status:
        total = len(
            EquipmentService.get_equipment_by_maintenance_status(
                db, maintenance_status, 0, 1000000
            )
        )
    else:
        total = EquipmentService.get_equipment_count(db)

    items = [EquipmentResponse.model_validate(item) for item in equipment_list]
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


@router.put("/{equipment_id}", response_model=success_response(EquipmentResponse))
async def update_equipment(
    equipment_id: int,
    equipment: EquipmentUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """更新设备"""
    db_equipment = EquipmentService.update_equipment(db, equipment_id, equipment)
    return {"code": 200, "data": db_equipment, "message": "设备更新成功"}


@router.delete("/{equipment_id}", response_model=success_response(dict))
async def delete_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """删除设备"""
    result = EquipmentService.delete_equipment(db, equipment_id)
    return {"code": 200, "data": result, "message": result["message"]}
