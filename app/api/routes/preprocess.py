"""图片预处理 API 路由"""
import base64
import io
import logging
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.api.limits import read_upload_limited, run_processing
from app.config import MAX_IMAGE_UPLOAD_BYTES
from app.services.preprocessor import preprocess_single_char

router = APIRouter(prefix="/api", tags=["preprocess"])
logger = logging.getLogger(__name__)

SUPPORTED_STRATEGIES = {"auto", "strong", "bgsub", "original"}
SUPPORTED_IMAGE_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/bmp",
    "application/octet-stream",
}


@router.post("/preprocess")
async def preprocess_image(
    file: Annotated[UploadFile, File()],
    strategy: Annotated[str | None, Form()] = None,
) -> dict:
    """预处理单字图片，返回 base64 编码的处理后图片"""
    if file.content_type and file.content_type.lower() not in SUPPORTED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="仅支持 PNG、JPG、WebP 或 BMP 图片",
        )
    selected_strategy = (strategy or "original").lower()
    if selected_strategy not in SUPPORTED_STRATEGIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的图片处理策略",
        )

    image_bytes = await read_upload_limited(file, MAX_IMAGE_UPLOAD_BYTES)

    try:
        processed = await run_processing(
            preprocess_single_char,
            image_bytes,
            selected_strategy,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Image preprocessing failed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="图片处理失败，请确认文件完整且格式受支持",
        ) from exc

    buf = io.BytesIO()
    processed.save(buf, format="PNG")
    img_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    return {"image_base64": img_b64}
