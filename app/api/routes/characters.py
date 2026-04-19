"""字符 API 路由"""
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.api.models import CharacterOut
from app.config import PROJECTS_DIR
from app.services.preprocessor import preprocess_single_char, save_processed_char
from app.services.project_service import get_project, update_meta

router = APIRouter(prefix="/api/projects/{project_id}", tags=["characters"])


@router.post("/characters", status_code=status.HTTP_201_CREATED)
async def upload_character(
    project_id: str,
    file: UploadFile = File(...),
    label: str = Form(...),
) -> dict:
    """上传单字图片"""
    # 验证项目存在
    project = get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 {project_id} 不存在",
        )

    # 验证标签
    if len(label) != 1 or not (0x4E00 <= ord(label) <= 0x9FFF):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="标签必须是单个 CJK 字符",
        )

    # 检查是否已存在
    unicode_hex = f"{ord(label):04X}"
    chars_dir = PROJECTS_DIR / project_id / "chars"
    char_file = chars_dir / f"{unicode_hex}.png"

    if char_file.exists():
        # 覆盖
        char_file.unlink()

    # 处理图片
    image_bytes = await file.read()
    processed = preprocess_single_char(image_bytes)
    save_processed_char(processed, project_id, label)

    # 更新元数据
    confirmed_chars = project.get("confirmed_chars", [])
    if label not in confirmed_chars:
        confirmed_chars.append(label)

    update_meta(project_id, {"confirmed_chars": confirmed_chars})

    return {"status": "ok", "label": label, "image_url": f"/api/projects/{project_id}/chars/{unicode_hex}.png"}


@router.get("/characters", response_model=list[CharacterOut])
async def list_characters(project_id: str) -> list[CharacterOut]:
    """获取已确认字符列表"""
    project = get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 {project_id} 不存在",
        )

    chars_dir = PROJECTS_DIR / project_id / "chars"
    if not chars_dir.exists():
        return []

    characters = []
    for char_file in chars_dir.glob("*.png"):
        unicode_hex = char_file.stem
        try:
            char = chr(int(unicode_hex, 16))
            characters.append(
                {
                    "char": char,
                    "label": char,
                    "image_url": f"/api/projects/{project_id}/chars/{unicode_hex}.png",
                    "confirmed_at": datetime.fromtimestamp(char_file.stat().st_mtime).isoformat(),
                }
            )
        except ValueError:
            continue

    # 按字符排序
    characters.sort(key=lambda x: x["char"])

    return [CharacterOut(**c) for c in characters]


@router.delete("/characters/{char}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_character(project_id: str, char: str) -> None:
    """删除已确认字符"""
    project = get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 {project_id} 不存在",
        )

    # 验证字符
    if len(char) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="字符参数无效",
        )

    # 删除文件
    unicode_hex = f"{ord(char):04X}"
    chars_dir = PROJECTS_DIR / project_id / "chars"
    char_file = chars_dir / f"{unicode_hex}.png"

    if char_file.exists():
        char_file.unlink()

    # 更新元数据
    confirmed_chars = project.get("confirmed_chars", [])
    if char in confirmed_chars:
        confirmed_chars.remove(char)

    update_meta(project_id, {"confirmed_chars": confirmed_chars})


@router.get("/chars/{filename}")
async def get_character_image(project_id: str, filename: str):
    """获取字符图片"""
    from fastapi.responses import FileResponse

    # 验证文件名格式
    if not filename.endswith(".png"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的文件名",
        )

    char_file = PROJECTS_DIR / project_id / "chars" / filename
    if not char_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"字符图片 {filename} 不存在",
        )

    return FileResponse(char_file, media_type="image/png")
