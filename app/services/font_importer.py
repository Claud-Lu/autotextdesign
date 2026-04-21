"""TTF 字体导入服务 — 解析 TTF 并渲染字形为图片"""
import base64
import io
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw

from app.config import GLYPH_SIZE


def import_ttf(ttf_bytes: bytes) -> dict:
    """
    解析 TTF 文件，提取字形并渲染为图片

    Args:
        ttf_bytes: TTF 文件字节

    Returns:
        {"glyphs": [{"char": "字", "image_base64": "..."}], "font_name": "..."}
    """
    from fontTools.ttLib import TTFont

    font = TTFont(io.BytesIO(ttf_bytes))

    font_name = _extract_font_name(font)

    cmap = font.getBestCmap()
    if not cmap:
        font.close()
        return {"glyphs": [], "font_name": font_name}

    # 筛选 CJK 字符
    cjk_chars = {
        c: g for c, g in cmap.items() if 0x4E00 <= c <= 0x9FFF
    }
    if not cjk_chars:
        font.close()
        return {"glyphs": [], "font_name": font_name}

    glyph_set = font.getGlyphSet()

    glyphs = []
    for codepoint, glyph_name in sorted(cjk_chars.items()):
        char = chr(codepoint)
        try:
            img = _render_glyph(glyph_set, glyph_name)
            if img is None:
                continue

            buf = io.BytesIO()
            img.save(buf, format="PNG")
            img_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

            glyphs.append({"char": char, "image_base64": img_b64})
        except Exception as e:
            print(f"  WARNING: 渲染 glyph {glyph_name} ({char}) 失败: {e}")
            continue

    font.close()

    return {"glyphs": glyphs, "font_name": font_name}


def _extract_font_name(font) -> str:
    """从 TTFont 的 name 表中提取字体名称"""
    name_table = font["name"]
    for plat_id, enc_id in [(3, 1), (1, 0), (3, 0)]:
        for record in name_table.names:
            if (record.nameID == 1
                    and record.platformID == plat_id
                    and record.platEncID == enc_id):
                try:
                    return record.toUnicode()
                except Exception:
                    continue
    return "未命名字体"


def _render_glyph(glyph_set, glyph_name: str) -> Optional[Image.Image]:
    """
    渲染单个字形为 GLYPH_SIZE x GLYPH_SIZE 图片（白底黑字）

    使用 numpy 扫描线 + 非零绕组规则正确处理内外轮廓，
    再用 PIL 超采样缩放到目标尺寸。
    """
    from fontTools.pens.recordingPen import RecordingPen

    # 先检查是否为空字形
    pen = RecordingPen()
    try:
        glyph_set[glyph_name].draw(pen)
    except Exception:
        return None
    if not pen.value:
        return None

    # 收集原始轮廓（带曲线信息）
    raw_contours = _collect_contours(glyph_set, glyph_name)
    if not raw_contours:
        return None

    # 插值曲线，生成多边形点
    polygon_contours = [
        _interpolate_contour(contour) for contour in raw_contours
    ]
    # 过滤太小的轮廓
    polygon_contours = [c for c in polygon_contours if len(c) >= 3]
    if not polygon_contours:
        return None

    # 计算字形边界
    all_x = [p[0] for c in polygon_contours for p in c]
    all_y = [p[1] for c in polygon_contours for p in c]
    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)

    glyph_w = x_max - x_min
    glyph_h = y_max - y_min
    if glyph_w <= 0 or glyph_h <= 0:
        return None

    # 在目标分辨率上直接光栅化，不用超采样
    margin = 0.1
    available = GLYPH_SIZE * (1 - 2 * margin)
    scale = min(available / glyph_w, available / glyph_h)

    offset_x = (GLYPH_SIZE - glyph_w * scale) / 2
    offset_y = (GLYPH_SIZE - glyph_h * scale) / 2

    # 将轮廓坐标变换到画布空间（y 翻转）
    transformed = []
    for contour in polygon_contours:
        pts = np.array(contour)
        xs = (pts[:, 0] - x_min) * scale + offset_x
        ys = offset_y + (y_max - pts[:, 1]) * scale
        transformed.append(np.column_stack([xs, ys]))

    # 用 numpy 扫描线 + non-zero winding number 填充
    img_arr = _rasterize_winding(transformed, GLYPH_SIZE)

    # 转为 PIL Image
    img = Image.fromarray(img_arr.astype(np.uint8), mode="L")

    return img


def _rasterize_winding(
    contours: list[np.ndarray],
    size: int,
) -> np.ndarray:
    """
    使用扫描线 + 非零绕组规则光栅化多边形轮廓。

    白底(255)黑字(0)，正确处理孔洞。
    """
    img = np.full((size, size), 255, dtype=np.uint8)

    # 预处理所有边: 构建 (y_start, y_end, x_at_y_start, x_at_y_end, direction)
    edges = []
    for contour in contours:
        n = len(contour)
        for i in range(n):
            x0, y0 = contour[i]
            x1, y1 = contour[(i + 1) % n]
            dy = y1 - y0
            if abs(dy) < 1e-6:
                continue
            # 方向: y 增大为向上(+1)，y 减小为向下(-1)
            direction = 1 if dy > 0 else -1
            edges.append((min(y0, y1), max(y0, y1), x0, y0, x1, y1, direction))

    if not edges:
        return img

    # 按扫描线处理
    for row in range(size):
        y = row + 0.5

        # 收集此扫描线的所有交点
        intersections = []
        for y_start, y_end, x0, y0, x1, y1, direction in edges:
            if y < y_start or y > y_end:
                continue
            t = (y - y0) / (y1 - y0)
            if t <= 0 or t >= 1:
                continue
            x_intersect = x0 + t * (x1 - x0)
            intersections.append((x_intersect, direction))

        if len(intersections) < 2:
            continue

        # 按 x 排序
        intersections.sort()

        # 从左到右扫描，累加 winding
        winding = 0
        fill_start = -1
        for x_val, direction in intersections:
            if winding == 0:
                # 开始填充
                fill_start = x_val
            winding += direction
            if winding == 0:
                # 结束填充
                col_start = max(0, int(fill_start))
                col_end = min(size, int(x_val))
                if col_end > col_start:
                    img[row, col_start:col_end] = 0

    return img


def _collect_contours(glyph_set, glyph_name: str) -> list:
    """
    使用 PointPen 协议收集字形轮廓。

    返回格式: [[(x, y, segmentType), ...], ...]
    segmentType: 'line', 'qcurve', 'curve', None(=on-curve point)
    """
    class PointCollector:
        def __init__(self):
            self.contours: list = []
            self._current: list = []

        def beginPath(self, identifier=None, **kwargs):
            self._current = []

        def endPath(self):
            if self._current:
                self.contours.append(self._current[:])
            self._current = []

        def addPoint(self, pt, segmentType=None, smooth=False,
                     name=None, identifier=None, **kwargs):
            self._current.append((float(pt[0]), float(pt[1]), segmentType))

    collector = PointCollector()
    try:
        glyph_set[glyph_name].drawPoints(collector)
    except Exception:
        return []

    return collector.contours


def _interpolate_contour(
    raw_contour: list, curve_steps: int = 8
) -> list[tuple[float, float]]:
    """
    将带曲线信息的轮廓插值为纯线段多边形点。
    """
    n = len(raw_contour)
    if n == 0:
        return []

    result = []

    for i in range(n):
        x, y, seg_type = raw_contour[i]

        if seg_type == 'line' or seg_type is None:
            result.append((x, y))

        elif seg_type == 'qcurve':
            controls = [(x, y)]
            j = (i + 1) % n
            while j != i and raw_contour[j][2] is None:
                controls.append((raw_contour[j][0], raw_contour[j][1]))
                j = (j + 1) % n
            end_pt = (raw_contour[j][0], raw_contour[j][1])
            start = result[-1] if result else (0, 0)

            if len(controls) > 1:
                pts = _interpolate_implied_qcurves(start, controls, end_pt, curve_steps)
                result.extend(pts)
            else:
                pts = _quadratic_bezier(start, controls[0], end_pt, curve_steps)
                result.extend(pts[1:])

        elif seg_type == 'curve':
            c1 = (x, y)
            j = (i + 1) % n
            c2 = (raw_contour[j][0], raw_contour[j][1])
            j = (j + 1) % n
            end_pt = (raw_contour[j][0], raw_contour[j][1])
            start = result[-1] if result else (0, 0)
            pts = _cubic_bezier(start, c1, c2, end_pt, curve_steps)
            result.extend(pts[1:])

    return result


def _quadratic_bezier(
    start: tuple, control: tuple, end: tuple, steps: int
) -> list[tuple[float, float]]:
    """二次贝塞尔曲线插值"""
    pts = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        x = u * u * start[0] + 2 * u * t * control[0] + t * t * end[0]
        y = u * u * start[1] + 2 * u * t * control[1] + t * t * end[1]
        pts.append((x, y))
    return pts


def _cubic_bezier(
    start: tuple, c1: tuple, c2: tuple, end: tuple, steps: int
) -> list[tuple[float, float]]:
    """三次贝塞尔曲线插值"""
    pts = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        x = (u**3 * start[0] + 3 * u**2 * t * c1[0]
             + 3 * u * t**2 * c2[0] + t**3 * end[0])
        y = (u**3 * start[1] + 3 * u**2 * t * c1[1]
             + 3 * u * t**2 * c2[1] + t**3 * end[1])
        pts.append((x, y))
    return pts


def _interpolate_implied_qcurves(
    start: tuple,
    controls: list[tuple],
    end: tuple,
    steps: int,
) -> list[tuple[float, float]]:
    """TrueType 隐含 on-curve 点的多段二次贝塞尔插值。"""
    segments = []
    prev_on = start

    for i in range(len(controls) - 1):
        mid = ((controls[i][0] + controls[i + 1][0]) / 2,
               (controls[i][1] + controls[i + 1][1]) / 2)
        segments.append((prev_on, controls[i], mid))
        prev_on = mid

    segments.append((prev_on, controls[-1], end))

    pts = []
    for seg_start, ctrl, seg_end in segments:
        curve_pts = _quadratic_bezier(seg_start, ctrl, seg_end, steps)
        if not pts:
            pts.extend(curve_pts)
        else:
            pts.extend(curve_pts[1:])

    return pts
