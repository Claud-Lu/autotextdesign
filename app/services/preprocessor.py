"""单字预处理服务"""
from io import BytesIO

import numpy as np
from PIL import Image, ImageOps
from scipy import ndimage as ndi
from skimage import filters, morphology
from pathlib import Path

from app.config import (
    GLYPH_SIZE,
    DEFAULT_PREPROCESS_STRATEGY,
    TEXTURE_BG_SIGMA,
    TEXTURE_THRESHOLD,
    STRONG_OPENING_RADIUS,
    STRONG_MIN_SIZE_RATIO,
    OPENING_RADIUS,
    MIN_SIZE_RATIO,
    BG_SIGMA,
    BG_CLOSING_RADIUS,
    PRE_BLUR_SIGMA,
)


def preprocess_single_char(image_bytes: bytes, strategy: str = DEFAULT_PREPROCESS_STRATEGY) -> Image.Image:
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

    # 准备数组
    arr = np.array(image)

    # 纹理强度检测：用大尺度高斯估计背景，计算细节层的标准差
    # 这可以检测纸张纹理/噪点强度，作为是否采用背景减法的依据
    def texture_strength(img_arr: np.ndarray, sigma: float = TEXTURE_BG_SIGMA) -> float:
        bg = ndi.gaussian_filter(img_arr.astype(float), sigma=sigma)
        detail = img_arr.astype(float) - bg
        return float(np.std(detail))

    tex_score = texture_strength(arr, sigma=TEXTURE_BG_SIGMA)

    def bg_subtract_and_binarize(img_arr: np.ndarray) -> np.ndarray:
        # 先做小幅高斯模糊以减少高频噪点
        blurred = ndi.gaussian_filter(img_arr.astype(float), sigma=PRE_BLUR_SIGMA)
        bg = ndi.gaussian_filter(blurred, sigma=BG_SIGMA)
        corrected = blurred - bg
        cmin, cmax = corrected.min(), corrected.max()
        if cmax - cmin > 0:
            corrected = 255 * (corrected - cmin) / (cmax - cmin)
        corrected = corrected.astype(np.uint8)
        thresh = filters.threshold_otsu(corrected)
        binary_local = corrected > thresh
        opened_local = morphology.opening(binary_local, morphology.disk(OPENING_RADIUS))
        # 小尺度 closing 用于修复因二值化/背景减法导致的断笔
        closed_local = morphology.closing(opened_local, morphology.disk(BG_CLOSING_RADIUS))
        min_size_local = max(64, int(MIN_SIZE_RATIO * img_arr.size))
        cleaned_local = morphology.remove_small_objects(closed_local, min_size=min_size_local)
        cleaned_local = morphology.remove_small_holes(cleaned_local, area_threshold=min_size_local)
        return cleaned_local

    # 支持多种策略：'auto'（原有自适应），'strong'（强去噪），'bgsub'（背景减法），'original'（原始路径）
    strategy = strategy.lower() if strategy else "auto"

    if strategy == "strong":
        # 强去噪：更大的开运算 + 更高 min_size
        # 先小幅模糊，减少锯齿
        arr_blur = ndi.gaussian_filter(arr.astype(float), sigma=PRE_BLUR_SIGMA).astype(np.uint8)
        threshold = filters.threshold_otsu(arr_blur)
        binary0 = arr_blur > threshold
        opened0 = morphology.opening(binary0, morphology.disk(STRONG_OPENING_RADIUS))
        closed0 = morphology.closing(opened0, morphology.disk(1))
        min_size0 = max(128, int(STRONG_MIN_SIZE_RATIO * arr.size))
        cleaned0 = morphology.remove_small_objects(opened0, min_size=min_size0)
        cleaned0 = morphology.remove_small_holes(cleaned0, area_threshold=min_size0)
        binary = cleaned0

    elif strategy == "bgsub":
        binary = bg_subtract_and_binarize(arr)

    elif strategy == "original":
        # 先小幅模糊以减少锯齿
        arr_blur = ndi.gaussian_filter(arr.astype(float), sigma=PRE_BLUR_SIGMA).astype(np.uint8)
        threshold = filters.threshold_otsu(arr_blur)
        binary = arr_blur > threshold
        min_size = max(64, int(0.0005 * arr.size))
        opened = morphology.opening(binary, morphology.disk(2))
        closed = morphology.closing(opened, morphology.disk(1))
        cleaned = morphology.remove_small_objects(closed, min_size=min_size)
        cleaned = morphology.remove_small_holes(cleaned, area_threshold=min_size)
        binary = cleaned

    else:
        # 'auto'（默认）: 依据纹理强度选择 bg_subtract 路径或原始路径
        if tex_score > TEXTURE_THRESHOLD:
            binary = bg_subtract_and_binarize(arr)
        else:
            arr_blur = ndi.gaussian_filter(arr.astype(float), sigma=PRE_BLUR_SIGMA).astype(np.uint8)
            threshold = filters.threshold_otsu(arr_blur)
            binary = arr_blur > threshold
            min_size = max(64, int(MIN_SIZE_RATIO * arr.size))
            opened = morphology.opening(binary, morphology.disk(OPENING_RADIUS))
            closed = morphology.closing(opened, morphology.disk(1))
            cleaned = morphology.remove_small_objects(closed, min_size=min_size)
            cleaned = morphology.remove_small_holes(cleaned, area_threshold=min_size)
            binary = cleaned

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
