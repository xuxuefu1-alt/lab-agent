from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.schemas.laboratory import (
    LaboratoryCreate,
    LaboratoryUpdate,
    LaboratoryResponse,
)
from app.services.laboratory_services import LaboratoryService
from app.common.respones import success_response

router = APIRouter(prefix="/laboratories", tags=["laboratories"])


@router.post("", response_model=success_response(LaboratoryResponse))
async def create_laboratory(
    laboratory: LaboratoryCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """创建实验室"""
    db_laboratory = LaboratoryService.create_laboratory(db, laboratory)
    return {"code": 200, "data": db_laboratory, "message": "实验室创建成功"}


@router.get("/{laboratory_id}", response_model=success_response(LaboratoryResponse))
async def get_laboratory(
    laboratory_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """获取实验室详情"""
    laboratory = LaboratoryService.get_laboratory_by_id(db, laboratory_id)
    return {"code": 200, "data": laboratory, "message": "获取成功"}


@router.get("", response_model=success_response(dict))
async def get_laboratories(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=1000),
    keyword: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """获取实验室列表"""
    if keyword:
        laboratories = LaboratoryService.search_laboratories(db, keyword, skip, limit)
    else:
        laboratories = LaboratoryService.get_all_laboratories(db, skip, limit)

    total = LaboratoryService.get_laboratories_count(db)

    # 转换为 Pydantic 模型
    items = [LaboratoryResponse.model_validate(lab) for lab in laboratories]

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


@router.put("/{laboratory_id}", response_model=success_response(LaboratoryResponse))
async def update_laboratory(
    laboratory_id: int,
    laboratory: LaboratoryUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """更新实验室"""
    db_laboratory = LaboratoryService.update_laboratory(db, laboratory_id, laboratory)
    return {"code": 200, "data": db_laboratory, "message": "实验室更新成功"}


@router.delete("/{laboratory_id}", response_model=success_response(dict))
async def delete_laboratory(
    laboratory_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """删除实验室"""
    result = LaboratoryService.delete_laboratory(db, laboratory_id)
    return {"code": 200, "data": result, "message": result["message"]}
