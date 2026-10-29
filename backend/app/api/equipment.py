from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.respones import success_response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.model.laboratory import Laboratory
from app.schemas.equipment import EquipmentCreate, EquipmentResponse, EquipmentUpdate
from app.services.equipment_services import EquipmentService
from app.services.resource_availability import get_equipment_availability


router = APIRouter(prefix="/equipment", tags=["equipment"])


@router.post("", response_model=success_response(EquipmentResponse))
async def create_equipment(
    equipment: EquipmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    db_equipment = EquipmentService.create_equipment(db, equipment)
    return {"code": 200, "data": db_equipment, "message": "设备创建成功"}


@router.get("/{equipment_id}", response_model=success_response(EquipmentResponse))
async def get_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    equipment = EquipmentService.get_equipment_by_id(db, equipment_id)
    data = EquipmentResponse.model_validate(equipment).model_dump()
    laboratory = db.query(Laboratory).filter(Laboratory.id == equipment.laboratory_id).first()
    data.update({
        "laboratory_name": laboratory.name if laboratory else None,
        "laboratory_location": laboratory.location if laboratory else None,
    })
    data.update(get_equipment_availability(db, [equipment_id]).get(equipment_id, {}))
    return {"code": 200, "data": data, "message": "获取成功"}


@router.get("", response_model=success_response(dict))
async def get_equipment_list(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=1000),
    keyword: str | None = Query(None),
    laboratory_id: int | None = Query(None),
    maintenance_status: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if keyword:
        equipment_list = EquipmentService.search_equipment(db, keyword, skip, limit)
    elif laboratory_id:
        equipment_list = EquipmentService.get_equipment_by_laboratory(db, laboratory_id, skip, limit)
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
        total = len(EquipmentService.get_equipment_by_maintenance_status(db, maintenance_status, 0, 1000000))
    else:
        total = EquipmentService.get_equipment_count(db)

    availability = get_equipment_availability(db, [item.id for item in equipment_list])
    laboratory_ids = {item.laboratory_id for item in equipment_list}
    laboratories = {
        item.id: item
        for item in db.query(Laboratory).filter(Laboratory.id.in_(laboratory_ids)).all()
    } if laboratory_ids else {}
    items = []
    for item in equipment_list:
        row = EquipmentResponse.model_validate(item).model_dump()
        laboratory = laboratories.get(item.laboratory_id)
        row.update({
            "laboratory_name": laboratory.name if laboratory else None,
            "laboratory_location": laboratory.location if laboratory else None,
        })
        row.update(availability.get(item.id, {}))
        items.append(row)

    return {
        "code": 200,
        "data": {"items": items, "total": total, "skip": skip, "limit": limit},
        "message": "获取成功",
    }


@router.put("/{equipment_id}", response_model=success_response(EquipmentResponse))
async def update_equipment(
    equipment_id: int,
    equipment: EquipmentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    db_equipment = EquipmentService.update_equipment(db, equipment_id, equipment)
    return {"code": 200, "data": db_equipment, "message": "设备更新成功"}


@router.delete("/{equipment_id}", response_model=success_response(dict))
async def delete_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = EquipmentService.delete_equipment(db, equipment_id)
    return {"code": 200, "data": result, "message": result["message"]}
