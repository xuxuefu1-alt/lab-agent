from fastapi import APIRouter
from app.api.auth import router as auth_router
from app.api.user import router as user_router
from app.api.upload import router as file_router
from app.api.ai import router as ai_router
from app.api.laboratory import router as laboratory_router
from app.api.equipment import router as equipment_router

api = APIRouter(prefix="/api")

api.include_router(auth_router)
api.include_router(user_router)
api.include_router(file_router)
api.include_router(ai_router)
api.include_router(laboratory_router)
api.include_router(equipment_router)
