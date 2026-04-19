"""网格切割服务"""
from io import BytesIO

import numpy as np
from PIL import Image, ImageDraw

from app.config import GLYPH_SIZE


def grid_segment(
    image_bytes: bytes, cols: int, rows: int
) -> list[dict]:
    """
    网格切割

    Args:
        image_bytes: 图片字节数据
        cols: 列数
        rows: 行数

    Returns:
        切割片段列表
    """
    # 加载图片
    image = Image.open(BytesIO(image_bytes))

    # 转灰度
    if image.mode != "L":
        image = image.convert("L")

    img_w, img_h = image.size

    # 计算每个格子的大小
    cell_w = img_w / cols
    cell_h = img_h / rows

    segments = []

    for row in range(rows):
        for col in range(cols):
            # 计算当前格子的边界
            x0 = int(col * cell_w)
            y0 = int(row * cell_h)
            x1 = int((col + 1) * cell_w)
            y1 = int((row + 1) * cell_h)

            # 裁剪
            cropped = image.crop((x0, y0, x1, y1))

            # 反转颜色（墨迹黑，背景白）
            cropped_arr = np.array(cropped)
            if cropped_arr.mean() > 128:  # 背景亮
                cropped = Image.fromarray(255 - cropped_arr, mode="L")

            # 居中填充为正方形
            w, h = cropped.size
            max_size = max(w, h)
            padded = Image.new("L", (max_size, max_size), 255)  # 白色背景
            x_offset = (max_size - w) // 2
            y_offset = (max_size - h) // 2
            padded.paste(cropped, (x_offset, y_offset))

            # 缩放到目标尺寸
            resized = padded.resize((GLYPH_SIZE, GLYPH_SIZE), Image.Resampling.LANCZOS)

            segments.append(
                {
                    "image": resized,
                    "bbox": [x0, y0, x1, y1],
                    "grid_pos": (row, col),
                }
            )

    return segments


def grid_preview(
    image_bytes: bytes, cols: int, rows: int
) -> Image.Image:
    """
    生成网格预览图

    Args:
        image_bytes: 图片字节数据
        cols: 列数
        rows: 行数

    Returns:
        带网格线的预览图
    """
    # 加载图片
    image = Image.open(BytesIO(image_bytes))

    # 转灰度
    if image.mode != "L":
        image = image.convert("L")

    img_w, img_h = image.size

    # 计算每个格子的大小
    cell_w = img_w / cols
    cell_h = img_h / rows

    # 转换为 RGB 以便绘制彩色网格线
    if image.mode != "RGB":
        image = image.convert("RGB")

    # 绘制网格线
    draw = ImageDraw.Draw(image)

    # 绘制垂直线
    for col in range(1, cols):
        x = int(col * cell_w)
        draw.line([(x, 0), (x, img_h)], fill="red", width=2)

    # 绘制水平线
    for row in range(1, rows):
        y = int(row * cell_h)
        draw.line([(0, y), (img_w, y)], fill="red", width=2)

    return image
