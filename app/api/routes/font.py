"""字体导入与生成 API 路由"""
from urllib.parse import quote

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import Response

from app.api.models import GenerateRequest, GlyphInput
from app.services.font_builder import build_font_from_data
from app.services.font_importer import import_ttf

router = APIRouter(prefix="/api", tags=["font"])


@router.post("/import-ttf")
async def import_ttf_file(file: UploadFile = File(...)) -> dict:
    """导入已有 TTF 字体，提取字形返回"""
    if not file.filename or not file.filename.lower().endswith(".ttf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请上传 TTF 字体文件",
        )

    ttf_bytes = await file.read()

    try:
        result = import_ttf(ttf_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TTF 解析失败: {str(e)}",
        )

    return result


@router.post("/generate")
async def generate_font(data: GenerateRequest) -> Response:
    """从图片数据生成 TTF 字体"""
    if not data.glyphs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有可用的字形数据",
        )

    try:
        font_bytes = build_font_from_data(
            [g.model_dump() for g in data.glyphs],
            data.font_name,
        )
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

    return Response(
        content=font_bytes,
        media_type="font/ttf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(data.font_name)}.ttf"},
    )


@router.post("/preview")
async def preview_font(data: GenerateRequest) -> Response:
    """生成预览字体（浏览器端加载用）"""
    if not data.glyphs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有可用的字形数据",
        )

    try:
        font_bytes = build_font_from_data(
            [g.model_dump() for g in data.glyphs],
            data.font_name,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"预览生成失败: {str(e)}",
        )

    return Response(
        content=font_bytes,
        media_type="font/ttf",
        headers={"Cache-Control": "no-cache"},
    )
