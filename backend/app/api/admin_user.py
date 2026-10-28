from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.schemas.user import UserResponse, AdminUserCreate, AdminUserUpdate
from app.schemas.password import ChangePasswordRequest, ChangePasswordResponse
from app.services.user_services import UserService
from app.common.respones import success_response
from app.model.user import User

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=success_response(dict))
async def get_users_list(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    keyword: str | None = Query(None),
    role: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户列表 (管理员功能)"""
    # 检查是否为管理员
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以访问")

    if keyword:
        users = UserService.search_users(db, keyword, skip, limit)
    elif role:
        users = UserService.get_users_by_role(db, role, skip, limit)
    else:
        users = UserService.get_all_users(db, skip, limit)

    total = UserService.get_users_count(db)

    return {
        "code": 200,
        "data": {
            "items": [UserResponse.model_validate(user) for user in users],
            "total": total,
            "skip": skip,
            "limit": limit,
        },
        "message": "获取成功",
    }


@router.get("/{user_id}", response_model=success_response(UserResponse))
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户详情"""
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="权限不足")

    user = UserService.get_user_by_id(db, user_id)
    return {
        "code": 200,
        "data": UserResponse.model_validate(user),
        "message": "获取成功",
    }


@router.post("", response_model=success_response(UserResponse))
async def create_user(
    user_data: AdminUserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建用户 (管理员功能)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以创建用户")

    user = UserService.create_user(
        db,
        username=user_data.username,
        password=user_data.password,
        name=user_data.name,
        role=user_data.role,
        email=user_data.email,
        phone=user_data.phone,
    )

    return {
        "code": 200,
        "data": UserResponse.model_validate(user),
        "message": "用户创建成功",
    }


@router.put("/{user_id}", response_model=success_response(UserResponse))
async def update_user(
    user_id: int,
    user_data: AdminUserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新用户信息"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="权限不足")

    user = UserService.update_user(db, user_id, user_data)
    return {
        "code": 200,
        "data": UserResponse.model_validate(user),
        "message": "用户更新成功",
    }


@router.delete("/{user_id}", response_model=success_response(dict))
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除用户 (管理员功能)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以删除用户")

    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="不能删除自己")

    result = UserService.delete_user(db, user_id)
    return {
        "code": 200,
        "data": result,
        "message": result["message"],
    }


@router.post("/{user_id}/change-password", response_model=success_response(ChangePasswordResponse))
async def change_password(
    user_id: int,
    password_data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """修改密码"""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="只能修改自己的密码")

    # 验证密码一致性
    password_data.validate_passwords()

    password_data.validate_passwords()
    result = UserService.change_password(
        db, user_id, password_data.old_password, password_data.new_password
    )

    return {
        "code": 200,
        "data": ChangePasswordResponse(),
        "message": result["message"],
    }


@router.put("/{user_id}/toggle-status", response_model=success_response(UserResponse))
async def toggle_user_status(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """切换用户状态"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以操作用户状态")

    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="不能切换自己的状态")

    user = UserService.toggle_user_status(db, user_id)
    return {
        "code": 200,
        "data": UserResponse.model_validate(user),
        "message": "用户状态已切换",
    }
