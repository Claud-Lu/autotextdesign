"""轮廓拟合服务"""

import numpy as np
from scipy import ndimage as ndi
from skimage import measure

from app.config import (
    ASCENT,
    BLUR_SIGMA,
    CONTOUR_SMOOTH_ITERS,
    CONTOUR_TOLERANCE,
    DESCENT,
    UNITS_PER_EM,
)


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

    poly = approximate_polygon(points, tolerance)
    # ensure closed polygon (first != last in skimage result sometimes)
    if poly.shape[0] > 0 and not np.allclose(poly[0], poly[-1]):
        poly = np.vstack([poly, poly[0]])
    return poly


def chaikin_smooth(points: np.ndarray, iterations: int = CONTOUR_SMOOTH_ITERS) -> np.ndarray:
    """
    Chaikin 曲线细分平滑（针对闭合多边形）

    Args:
        points: (N,2) 点序列，期望首尾相连
        iterations: 迭代次数

    Returns:
        平滑后的点序列 (M,2)
    """
    if points.shape[0] < 3:
        return points

    # work on float copy
    pts = points.astype(float)

    # ensure closed
    if not np.allclose(pts[0], pts[-1]):
        pts = np.vstack([pts, pts[0]])

    for _ in range(max(0, int(iterations))):
        new_pts = []
        n = pts.shape[0]
        for i in range(n - 1):
            p0 = pts[i]
            p1 = pts[i + 1]
            q = 0.75 * p0 + 0.25 * p1
            r = 0.25 * p0 + 0.75 * p1
            new_pts.append(q)
            new_pts.append(r)
        # close
        new_pts.append(new_pts[0])
        pts = np.vstack(new_pts)

    return pts


def contours_to_glyph(
    binary_arr: np.ndarray, units_per_em: int = UNITS_PER_EM
) -> dict | None:
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

        # 简化并平滑轮廓（先 Douglas–Peucker 降噪，再 Chaikin 平滑）
        outer_simplified = []
        for c in outer_contours:
            s = simplify_polygon(c)
            p = chaikin_smooth(s, iterations=CONTOUR_SMOOTH_ITERS)
            outer_simplified.append(p)

        inner_simplified = []
        for c in inner_contours:
            s = simplify_polygon(c)
            p = chaikin_smooth(s, iterations=CONTOUR_SMOOTH_ITERS)
            inner_simplified.append(p)

        # 以墨迹外接框确定缩放比例，再把右边界贴到可用区域右侧，清掉右侧留白
        if inner_simplified:
            all_points = np.vstack(outer_simplified + inner_simplified)
        else:
            all_points = np.vstack(outer_simplified)

        y_min = float(np.min(all_points[:, 0]))
        y_max = float(np.max(all_points[:, 0]))
        x_min = float(np.min(all_points[:, 1]))
        x_max = float(np.max(all_points[:, 1]))

        glyph_w = x_max - x_min
        glyph_h = y_max - y_min
        if glyph_w <= 0 or glyph_h <= 0:
            return None

        ink_points = np.argwhere(smoothed)
        if ink_points.size == 0:
            return None
        centroid_y = float(np.mean(ink_points[:, 0]))
        centroid_x = float(np.mean(ink_points[:, 1]))

        # 统一固定可用区域（所有字使用相同 available box），并按墨迹重心在该区域等比居中
        margin_ratio = 0.03
        left = units_per_em * margin_ratio
        right = units_per_em * (1 - margin_ratio)
        bottom = DESCENT + (ASCENT - DESCENT) * margin_ratio
        top = ASCENT - (ASCENT - DESCENT) * margin_ratio

        available_w = right - left
        available_h = top - bottom

        # 计算统一缩放（在 available box 内等比缩放）
        scale = min(available_w / glyph_w, available_h / glyph_h)

        # 以墨迹质心为对齐中心（在 available box 内居中）
        target_center_x = left + available_w / 2
        target_center_y = bottom + available_h / 2

        def scale_points(points: np.ndarray) -> list[tuple[float, float]]:
            scaled = []
            for y, x in points:
                font_x = target_center_x + (x - centroid_x) * scale
                font_y = target_center_y + (centroid_y - y) * scale
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
