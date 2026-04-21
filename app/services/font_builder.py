"""字体构建服务（无状态）"""
import base64
import io
import re

import numpy as np
from PIL import Image
from fontTools.pens.ttGlyphPen import TTGlyphPen

from app.config import ASCENT, DESCENT, GLYPH_SIZE, UNITS_PER_EM
from app.services.contour_fitter import contours_to_glyph


def _safe_postscript_name(font_name: str) -> str:
    """生成兼容性更好的 PostScript 名称（ASCII、无空格、以字母开头）。"""
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "", font_name)
    if not cleaned:
        cleaned = "Font"
    if not cleaned[0].isalpha():
        cleaned = f"ATD{cleaned}"
    return f"{cleaned}-Regular"


def build_font_from_data(
    glyphs: list[dict], font_name: str
) -> bytes:
    """
    从图片数据构建 TTF 字体

    Args:
        glyphs: [{"char": "字", "image_base64": "..."}]
        font_name: 字体名称

    Returns:
        TTF 字体文件字节
    """
    glyphs_data = {}
    for g in glyphs:
        char = g["char"]
        img_bytes = base64.b64decode(g["image_base64"])
        img = Image.open(io.BytesIO(img_bytes)).convert("L")
        gray = np.array(img)
        # 统一为"墨迹=True，背景=False"的二值掩码
        arr = gray < 128

        contour_data = contours_to_glyph(arr)
        if contour_data is None:
            print(f"  WARNING: 轮廓提取失败 for {char}")
            continue

        glyphs_data[char] = contour_data

    if not glyphs_data:
        raise ValueError("没有有效的字符数据")

    from fontTools.fontBuilder import FontBuilder

    fb = FontBuilder(UNITS_PER_EM, isTTF=True)

    glyph_order = [".notdef"] + [f"uni{ord(c):04X}" for c in glyphs_data]
    char_to_glyph = {c: f"uni{ord(c):04X}" for c in glyphs_data}

    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap({ord(c): char_to_glyph[c] for c in glyphs_data})
    fb.setupHead(unitsPerEm=UNITS_PER_EM)
    fb.setupHorizontalHeader(ascent=ASCENT, descent=DESCENT)

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

    metrics = {name: (advance_width, 0) for name in glyph_order}
    fb.setupHorizontalMetrics(metrics)
    fb.setupMaxp()
    fb.setupOS2(
        sTypoAscender=ASCENT,
        sTypoDescender=DESCENT,
        usWinAscent=ASCENT,
        usWinDescent=abs(DESCENT),
    )

    # Improve Office/Word compatibility for CJK usage.
    os2 = fb.font["OS/2"]
    os2.ulCodePageRange1 = (1 << 17) | (1 << 19)  # CP936 (GBK), CP950 (Big5)
    os2.ulCodePageRange2 = 0
    os2.fsSelection = 0x40  # REGULAR

    postscript_name = _safe_postscript_name(font_name)
    fb.setupNameTable(
        {
            "familyName": font_name,
            "styleName": "Regular",
            "fullName": f"{font_name} Regular",
            "psName": postscript_name,
            "uniqueFontIdentifier": f"{postscript_name};Version 1.0",
            "version": "Version 1.0",
        }
    )
    fb.setupPost()

    buf = io.BytesIO()
    fb.save(buf)
    return buf.getvalue()
