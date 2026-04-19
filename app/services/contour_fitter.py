"""轮廓拟合服务"""
from typing import Optional

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import measure, filters

from app.config import BLUR_SIGMA, CONTOUR_TOLERANCE, UNITS_PER_EM


def smooth_contour(binary_arr: np.ndarray, sigma: float = BLUR_SIGMA) -> np.ndarray:
    """
    平滑轮廓

    Args:
        binary_arr: 二值图像
        sigma: 高斯模糊标准差

    Returns:
        平滑后的二值图像
    """
    # 高斯模糊
    blurred = ndi.gaussian_filter(binary_arr.astype(float), sigma=sigma)

    # 重新二值化
    threshold = 0.5
    smoothed = blurred > threshold

    return smoothed


def extract_contours_with_holes(
    binary_arr: np.ndarray,
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """
    提取内外轮廓

    Args:
        binary_arr: 二值图像

    Returns:
        (外轮廓列表, 内轮廓列表)
    """
    # 查找所有轮廓
    contours = measure.find_contours(binary_arr, 0.5)

    if not contours:
        return [], []

    # 计算面积并排序
    areas = [measure.approximate_polygon(c, 1).shape[0] for c in contours]
    sorted_indices = np.argsort(areas)[::-1]

    # 最大的是外轮廓，其余是内轮廓（孔洞）
    outer_contours = [contours[sorted_indices[0]]]
    inner_contours = [contours[i] for i in sorted_indices[1:]]

    return outer_contours, inner_contours


def simplify_polygon(points: np.ndarray, tolerance: float = CONTOUR_TOLERANCE) -> np.ndarray:
    """
    简化多边形（Ramer-Douglas-Peucker 算法）

    Args:
        points: 轮廓点 (N, 2)
        tolerance: 简化容差

    Returns:
        简化后的点
    """
    from skimage.measure import approximate_polygon

    return approximate_polygon(points, tolerance)


def contours_to_glyph(
    binary_arr: np.ndarray, units_per_em: int = UNITS_PER_EM
) -> Optional[dict]:
    """
    将轮廓转换为字形数据

    Args:
        binary_arr: 二值图像
        units_per_em: 字体单位

    Returns:
        字形数据字典
    """
    try:
        # 平滑
        smoothed = smooth_contour(binary_arr)

        # 提取轮廓
        outer_contours, inner_contours = extract_contours_with_holes(smoothed)

        if not outer_contours:
            return None

        # 简化轮廓
        outer_simplified = [simplify_polygon(c) for c in outer_contours]
        inner_simplified = [simplify_polygon(c) for c in inner_contours]

        # 转换坐标到字体单位
        img_h, img_w = binary_arr.shape
        scale = units_per_em / img_w

        def scale_points(points: np.ndarray) -> list[tuple[float, float]]:
            # Y 轴翻转
            scaled = []
            for y, x in points:
                font_x = x * scale
                font_y = units_per_em - (y * scale)  # 翻转 Y
                scaled.append((font_x, font_y))
            return scaled

        outer_coords = [scale_points(c) for c in outer_simplified]
        inner_coords = [scale_points(c) for c in inner_simplified]

        return {
            "outer": outer_coords,
            "inner": inner_coords,
        }

    except Exception as e:
        print(f"Error converting contours: {e}")
        return None
