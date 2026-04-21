"""图片预处理 API 路由"""
import base64
import io

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from PIL import Image

from app.services.preprocessor import preprocess_single_char

router = APIRouter(prefix="/api", tags=["preprocess"])


@router.post("/preprocess")
async def preprocess_image(file: UploadFile = File(...)) -> dict:
    """预处理单字图片，返回 base64 编码的处理后图片"""
    image_bytes = await file.read()

    try:
        processed = preprocess_single_char(image_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"图片处理失败: {str(e)}",
        )

    buf = io.BytesIO()
    processed.save(buf, format="PNG")
    img_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    return {"image_base64": img_b64}
