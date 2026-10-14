import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, UploadFile

from app.common.exceptions import BusinessExceptions
from app.config import ALLOWED_FILE, MAX_FILE_SIZE, UPLOAD_DIR


router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise BusinessExceptions(message="文件名不能为空")

    original_name = os.path.basename(file.filename)
    extension = Path(original_name).suffix.lower()
    if extension not in ALLOWED_FILE:
        raise BusinessExceptions(message=f"不支持上传{extension}的文件后缀")

    if file.size and file.size > MAX_FILE_SIZE:
        raise BusinessExceptions(
            message=f"文件大小不能超过{MAX_FILE_SIZE // 1024 // 1024}MB"
        )

    stored_name = f"{uuid4().hex}{extension}"
    target = UPLOAD_DIR / stored_name
    size = 0
    try:
        with target.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    target.unlink(missing_ok=True)
                    raise BusinessExceptions(
                        message=f"文件大小不能超过{MAX_FILE_SIZE // 1024 // 1024}MB"
                    )
                output.write(chunk)
    finally:
        await file.close()

    return {
        "filename": original_name,
        "stored_name": stored_name,
        "size": size,
    }
