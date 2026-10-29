from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.respones import success_response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.schemas.laboratory import LaboratoryCreate, LaboratoryResponse, LaboratoryUpdate
from app.services.laboratory_services import LaboratoryService
from app.services.resource_availability import get_laboratory_availability


router = APIRouter(prefix="/laboratories", tags=["laboratories"])


@router.post("", response_model=success_response(LaboratoryResponse))
async def create_laboratory(
    laboratory: LaboratoryCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    db_laboratory = LaboratoryService.create_laboratory(db, laboratory)
    return {"code": 200, "data": db_laboratory, "message": "实验室创建成功"}


@router.get("/{laboratory_id}", response_model=success_response(LaboratoryResponse))
async def get_laboratory(
    laboratory_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    laboratory = LaboratoryService.get_laboratory_by_id(db, laboratory_id)
    data = LaboratoryResponse.model_validate(laboratory).model_dump()
    data.update(get_laboratory_availability(db, [laboratory_id]).get(laboratory_id, {}))
    return {"code": 200, "data": data, "message": "获取成功"}


@router.get("", response_model=success_response(dict))
async def get_laboratories(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=1000),
    keyword: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if keyword:
        laboratories = LaboratoryService.search_laboratories(db, keyword, skip, limit)
    else:
        laboratories = LaboratoryService.get_all_laboratories(db, skip, limit)

    total = LaboratoryService.get_laboratories_count(db)
    availability = get_laboratory_availability(db, [lab.id for lab in laboratories])
    items = []
    for lab in laboratories:
        item = LaboratoryResponse.model_validate(lab).model_dump()
        item.update(availability.get(lab.id, {}))
        items.append(item)

    return {
        "code": 200,
        "data": {"items": items, "total": total, "skip": skip, "limit": limit},
        "message": "获取成功",
    }


@router.put("/{laboratory_id}", response_model=success_response(LaboratoryResponse))
async def update_laboratory(
    laboratory_id: int,
    laboratory: LaboratoryUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    db_laboratory = LaboratoryService.update_laboratory(db, laboratory_id, laboratory)
    return {"code": 200, "data": db_laboratory, "message": "实验室更新成功"}


@router.delete("/{laboratory_id}", response_model=success_response(dict))
async def delete_laboratory(
    laboratory_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = LaboratoryService.delete_laboratory(db, laboratory_id)
    return {"code": 200, "data": result, "message": result["message"]}
