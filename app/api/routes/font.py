"""字体生成 API 路由"""
import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, status

from app.api.models import FontGenerateRequest
from app.config import PROJECTS_DIR
from app.services.font_builder import build_font, build_preview_font
from app.services.project_service import get_project, update_meta

router = APIRouter(prefix="/api/projects/{project_id}", tags=["font"])


@router.post("/generate")
async def generate_font(project_id: str, data: FontGenerateRequest) -> dict:
    """生成字体文件"""
    # 验证项目存在
    project = get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 {project_id} 不存在",
        )

    # 检查是否有字符
    confirmed_chars = project.get("confirmed_chars", [])
    if not confirmed_chars:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="项目没有任何已确认的字符",
        )

    # 生成字体
    font_name = data.font_name or project["name"]
    try:
        font_path = build_font(project_id, font_name)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"字体生成失败: {str(e)}",
        )

    # 更新项目元数据
    meta = get_project(project_id)
    meta.setdefault("generated_fonts", [])
    meta["generated_fonts"].append(
        {
            "font_name": font_name,
            "font_path": font_path,
            "glyph_count": len(confirmed_chars),
            "generated_at": datetime.datetime.now().isoformat(),
        }
    )

    update_meta(project_id, {"generated_fonts": meta["generated_fonts"]})

    return {
        "status": "ok",
        "font_path": font_path,
        "font_name": font_name,
        "glyph_count": len(confirmed_chars),
    }


@router.get("/download")
async def download_font(project_id: str):
    """下载字体文件"""
    from fastapi.responses import FileResponse

    project = get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 {project_id} 不存在",
        )

    # 获取最新生成的字体
    generated_fonts = project.get("generated_fonts", [])
    if not generated_fonts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目还没有生成任何字体",
        )

    font_path = generated_fonts[-1]["font_path"]

    if not Path(font_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="字体文件不存在",
        )

    return FileResponse(
        font_path,
        media_type="font/ttf",
        filename=f"{Path(font_path).name}",
    )


@router.get("/preview-font")
async def get_preview_font(project_id: str):
    """获取预览字体"""
    from fastapi.responses import Response

    project = get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 {project_id} 不存在",
        )

    # 检查是否有字符
    confirmed_chars = project.get("confirmed_chars", [])
    if not confirmed_chars:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="项目没有任何已确认的字符",
        )

    # 生成预览字体
    try:
        font_bytes = build_preview_font(project_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"预览字体生成失败: {str(e)}",
        )

    return Response(content=font_bytes, media_type="font/ttf", headers={"Cache-Control": "max-age=3600"})
