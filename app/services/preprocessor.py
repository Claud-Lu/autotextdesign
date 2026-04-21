"""单字预处理服务"""
from io import BytesIO

import numpy as np
from PIL import Image, ImageOps
from scipy import ndimage as ndi
from skimage import filters, morphology
from pathlib import Path

from app.config import GLYPH_SIZE


def preprocess_single_char(image_bytes: bytes) -> Image.Image:
    """
    预处理单字图片

    Args:
        image_bytes: 图片字节数据

    Returns:
        PIL.Image: 处理后的正方形图片 (1024x1024)
    """
    # 加载图片
    image = Image.open(BytesIO(image_bytes))

    # 转换为灰度图
    if image.mode != "L":
        image = image.convert("L")

    # 反转颜色（假设墨迹是黑色的，背景是白色的）
    # 先自动判断是否需要反转
    arr = np.array(image)
    if arr.mean() > 128:  # 背景亮，需要反转
        image = ImageOps.invert(image)
        arr = np.array(image)

    # Autocontrast 增强对比度
    image = ImageOps.autocontrast(image, cutoff=1)

    # Otsu 二值化
    arr = np.array(image)
    threshold = filters.threshold_otsu(arr)
    binary = arr > threshold

    # 找墨迹 bbox
    rows = np.any(binary, axis=1)
    cols = np.any(binary, axis=0)

    if not np.any(rows) or not np.any(cols):
        # 空白图片，返回空白正方形
        return Image.new("L", (GLYPH_SIZE, GLYPH_SIZE), 255)

    y0, y1 = np.where(rows)[0][[0, -1]]
    x0, x1 = np.where(cols)[0][[0, -1]]

    # 裁剪 + 10% 边距
    height = y1 - y0
    width = x1 - x0
    margin_y = int(height * 0.1)
    margin_x = int(width * 0.1)

    # 确保边界有效
    img_h, img_w = arr.shape
    y0 = max(0, y0 - margin_y)
    y1 = min(img_h, y1 + margin_y)
    x0 = max(0, x0 - margin_x)
    x1 = min(img_w, x1 + margin_x)

    # 裁剪墨迹区域
    cropped = binary[y0:y1, x0:x1]

    # 居中填充为正方形
    size = max(cropped.shape)
    padded = np.zeros((size, size), dtype=bool)
    y_offset = (size - cropped.shape[0]) // 2
    x_offset = (size - cropped.shape[1]) // 2
    padded[y_offset : y_offset + cropped.shape[0], x_offset : x_offset + cropped.shape[1]] = (
        cropped
    )

    # 缩放到 1024x1024
    # 先转换为 uint8
    padded_uint8 = (padded * 255).astype(np.uint8)
    image = Image.fromarray(padded_uint8, mode="L")
    image = image.resize((GLYPH_SIZE, GLYPH_SIZE), Image.Resampling.LANCZOS)

    # 反转回来（背景白，墨迹黑）
    image = ImageOps.invert(image)

    return image
