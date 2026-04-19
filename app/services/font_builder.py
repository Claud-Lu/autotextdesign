"""字体构建服务"""
import io
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image
from fontTools.pens.ttGlyphPen import TTGlyphPen

from app.config import (
    ASCENT,
    DESCENT,
    GLYPH_SIZE,
    PROJECTS_DIR,
    UNITS_PER_EM,
)
from app.services.contour_fitter import contours_to_glyph


def build_font(
    project_id: str, font_name: Optional[str] = None
) -> str:
    """
    构建字体文件

    Args:
        project_id: 项目ID
        font_name: 字体名称（默认使用项目名）

    Returns:
        字体文件路径
    """
    from app.services.project_service import get_project

    # 获取项目信息
    project = get_project(project_id)
    if not project:
        raise ValueError(f"项目 {project_id} 不存在")

    if font_name is None:
        font_name = project["name"]

    # 扫描字符目录
    chars_dir = PROJECTS_DIR / project_id / "chars"
    if not chars_dir.exists():
        raise ValueError(f"项目 {project_id} 没有字符数据")

    # 收集字符
    glyphs_data = {}
    for char_file in chars_dir.glob("*.png"):
        unicode_hex = char_file.stem
        try:
            char = chr(int(unicode_hex, 16))

            # 加载并处理图片
            img = Image.open(char_file).convert("L")
            arr = np.array(img) / 255.0

            # 转换为轮廓
            contour_data = contours_to_glyph(arr)
            if contour_data is None:
                print(f"  WARNING: 轮廓提取失败 for {char}")
                continue

            glyphs_data[char] = contour_data

        except ValueError:
            continue

    if not glyphs_data:
        raise ValueError(f"项目 {project_id} 没有有效的字符数据")

    # 构建字体
    from fontTools.fontBuilder import FontBuilder

    fb = FontBuilder(UNITS_PER_EM, isTTF=True)

    # glyph 名称: .notdef + uniXXXX 格式
    glyph_order = [".notdef"] + [f"uni{ord(c):04X}" for c in glyphs_data]
    char_to_glyph = {c: f"uni{ord(c):04X}" for c in glyphs_data}

    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap({ord(c): char_to_glyph[c] for c in glyphs_data})

    # 头部表
    fb.setupHead(
        unitsPerEm=UNITS_PER_EM,
    )

    # 水平头部表
    fb.setupHorizontalHeader(
        ascent=ASCENT,
        descent=DESCENT,
    )

    # 构建字形
    advance_width = UNITS_PER_EM
    glyph_set = {}

    # .notdef 空白字形
    pen = TTGlyphPen(None)
    pen.moveTo((0, 0))
    pen.lineTo((advance_width, 0))
    pen.lineTo((advance_width, UNITS_PER_EM))
    pen.lineTo((0, UNITS_PER_EM))
    pen.closePath()
    glyph_set[".notdef"] = pen.glyph()

    # 构建各字符字形
    for char, contour_data in glyphs_data.items():
        pen = TTGlyphPen(None)

        for outer_contour in contour_data["outer"]:
            if len(outer_contour) < 3:
                continue
            pen.moveTo(outer_contour[0])
            for point in outer_contour[1:]:
                pen.lineTo(point)
            pen.closePath()

        for inner_contour in contour_data["inner"]:
            if len(inner_contour) < 3:
                continue
            pen.moveTo(inner_contour[0])
            for point in inner_contour[1:]:
                pen.lineTo(point)
            pen.closePath()

        glyph_set[char_to_glyph[char]] = pen.glyph()

    fb.setupGlyf(glyph_set)

    # 水平度量（等宽）— 必须在 OS/2 之前
    metrics = {}
    for name in glyph_order:
        metrics[name] = (advance_width, 0)
    fb.setupHorizontalMetrics(metrics)

    fb.setupMaxp()

    # OS/2 表
    fb.setupOS2(
        sTypoAscender=ASCENT,
        sTypoDescender=DESCENT,
        usWinAscent=ASCENT,
        usWinDescent=abs(DESCENT),
    )

    fb.setupNameTable(
        {
            "familyName": font_name,
            "styleName": "Regular",
        }
    )

    fb.setupPost()

    # 保存字体
    generated_dir = PROJECTS_DIR / project_id / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)

    font_filename = f"{font_name}.ttf"
    font_path = generated_dir / font_filename

    fb.save(str(font_path))
    print(f"Font saved: {font_path}, glyphs: {len(glyphs_data)}")

    return str(font_path)


def build_preview_font(project_id: str) -> bytes:
    """
    构建预览字体（返回字节）

    Args:
        project_id: 项目ID

    Returns:
        字体文件字节
    """
    font_path = build_font(project_id)

    with open(font_path, "rb") as f:
        return f.read()
