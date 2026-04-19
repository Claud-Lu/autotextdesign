"""自动切割服务"""
from io import BytesIO
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageOps
from scipy import ndimage as ndi
from skimage import filters, measure, morphology

from app.config import GLYPH_SIZE, MIN_COMPONENT_SIZE, PROJECTS_DIR


def preprocess_scan(image: np.ndarray) -> np.ndarray:
    """
    预处理扫描件

    Args:
        image: 输入图像 (numpy array)

    Returns:
        处理后的二值图像
    """
    # 转灰度
    if len(image.shape) == 3:
        image = np.mean(image, axis=2)

    # Autocontrast
    from PIL import Image

    pil_img = Image.fromarray((image * 255).astype(np.uint8))
    pil_img = ImageOps.autocontrast(pil_img, cutoff=1)
    image = np.array(pil_img) / 255.0

    # 中值阈值二值化
    threshold = np.median(image)
    binary = image < threshold  # 墨迹是黑色的

    return binary


def find_components(binary: np.ndarray) -> list[dict]:
    """
    查找连通域

    Args:
        binary: 二值图像

    Returns:
        连通域列表
    """
    # 标记连通域
    labeled, num_features = ndi.label(binary)

    components = []
    for label_id in range(1, num_features + 1):
        # 获取当前连通域的掩码
        mask = labeled == label_id

        # 计算属性
        size = np.sum(mask)
        if size < MIN_COMPONENT_SIZE:
            continue  # 过滤小噪点

        # 获取边界框
        coords = np.argwhere(mask)
        y0, x0 = coords.min(axis=0)
        y1, x1 = coords.max(axis=0) + 1

        # 计算质心
        cy, cx = ndi.center_of_mass(mask)

        components.append(
            {
                "id": f"comp_{label_id:04d}",
                "size": size,
                "cy": float(cy),
                "cx": float(cx),
                "y0": int(y0),
                "x0": int(x0),
                "y1": int(y1),
                "x1": int(x1),
                "coords": coords,
            }
        )

    return components


def cluster_to_characters(components: list[dict]) -> list[list[dict]]:
    """
    将连通域聚类为字符

    Args:
        components: 连通域列表

    Returns:
        字符列表（每个字符可能包含多个连通域）
    """
    if not components:
        return []

    # 按 Y 质心排序
    components_sorted = sorted(components, key=lambda c: c["cy"])

    # 检测行
    rows = []
    current_row = [components_sorted[0]]

    # 计算中位高度
    heights = [c["y1"] - c["y0"] for c in components]
    median_height = np.median(heights)

    for i in range(1, len(components_sorted)):
        comp = components_sorted[i]
        last_comp = current_row[-1]

        # 如果 Y 间距 > 1.5 * 中位高度，则为新行
        if comp["cy"] - last_comp["cy"] > 1.5 * median_height:
            rows.append(current_row)
            current_row = [comp]
        else:
            current_row.append(comp)

    if current_row:
        rows.append(current_row)

    # 行内按 X 质心排序并分组
    characters = []
    for row in rows:
        # 按 X 质心排序
        row_sorted = sorted(row, key=lambda c: c["cx"])

        # 计算中位宽度
        widths = [c["x1"] - c["x0"] for c in row_sorted]
        median_width = np.median(widths) if widths else 0

        # 分组字符
        current_char = [row_sorted[0]]

        for i in range(1, len(row_sorted)):
            comp = row_sorted[i]
            last_comp = current_char[-1]

            # 如果 X 间距 > 2.0 * 中位宽度，则为新字符
            if comp["cx"] - last_comp["cx"] > 2.0 * median_width:
                characters.append(current_char)
                current_char = [comp]
            else:
                current_char.append(comp)

        if current_char:
            characters.append(current_char)

    return characters


def extract_segment(
    binary: np.ndarray, component_group: list[dict], size: int = GLYPH_SIZE
) -> Image.Image:
    """
    从二值图像中提取切割片段

    Args:
        binary: 二值图像
        component_group: 连通域组
        size: 输出尺寸

    Returns:
        PIL Image
    """
    # 计算联合 bbox
    y0 = min(c["y0"] for c in component_group)
    x0 = min(c["x0"] for c in component_group)
    y1 = max(c["y1"] for c in component_group)
    x1 = max(c["x1"] for c in component_group)

    # 裁剪
    cropped = binary[y0:y1, x0:x1].copy()

    # 创建 mask
    mask = np.zeros_like(cropped, dtype=bool)
    for comp in component_group:
        # 调整坐标到裁剪区域
        local_y0 = comp["y0"] - y0
        local_x0 = comp["x0"] - x0
        local_y1 = comp["y1"] - y0
        local_x1 = comp["x1"] - x0

        # 将连通域坐标也调整
        local_coords = comp["coords"].copy()
        local_coords[:, 0] -= y0
        local_coords[:, 1] -= x0

        for coord in local_coords:
            if 0 <= coord[0] < mask.shape[0] and 0 <= coord[1] < mask.shape[1]:
                mask[coord[0], coord[1]] = True

    # 应用 mask
    result = np.zeros_like(cropped, dtype=np.uint8)
    result[mask] = cropped[mask]

    # 居中填充为正方形
    h, w = result.shape
    max_size = max(h, w)
    padded = np.zeros((max_size, max_size), dtype=np.uint8)
    y_offset = (max_size - h) // 2
    x_offset = (max_size - w) // 2
    padded[y_offset : y_offset + h, x_offset : x_offset + w] = result

    # 缩放到目标尺寸
    from PIL import Image

    image = Image.fromarray((1 - padded) * 255, mode="L")  # 反转：墨迹黑
    image = image.resize((size, size), Image.Resampling.LANCZOS)

    return image


def auto_segment(image_bytes: bytes) -> list[dict]:
    """
    自动切割扫描件

    Args:
        image_bytes: 图片字节数据

    Returns:
        切割片段列表
    """
    # 加载图片
    image = Image.open(BytesIO(image_bytes))
    arr = np.array(image)

    # 预处理
    binary = preprocess_scan(arr)

    # 查找连通域
    components = find_components(binary)

    # 聚类为字符
    char_groups = cluster_to_characters(components)

    # 提取每个字符
    segments = []
    segment_id = 0

    for group in char_groups:
        if not group:
            continue

        # 提取图片
        segment_img = extract_segment(binary, group)

        # 计算 bbox
        y0 = min(c["y0"] for c in group)
        x0 = min(c["x0"] for c in group)
        y1 = max(c["y1"] for c in group)
        x1 = max(c["x1"] for c in group)

        segments.append(
            {
                "image": segment_img,
                "bbox": [int(x0), int(y0), int(x1), int(y1)],
                "component_ids": [c["id"] for c in group],
            }
        )

        segment_id += 1

    return segments
