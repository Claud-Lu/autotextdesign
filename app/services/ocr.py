"""OCR 提示服务"""
from io import BytesIO
from typing import Optional

import numpy as np
from PIL import Image

try:
    import pytesseract
except ImportError:
    pytesseract = None

# 常见形近字映射表（简化版）
SIMILAR_CHARS_MAP = {
    "黃": ["黌", "廣", "黈", "黹"],
    "日": ["曰", "目", "白"],
    "曰": ["日", "目"],
    "人": ["入", "八"],
    "入": ["人", "八"],
    "八": ["人", "入"],
    "大": ["太", "犬"],
    "太": ["大", "犬"],
    "犬": ["大", "太"],
    "土": ["士"],
    "士": ["土"],
    "天": ["夫", "夭"],
    "夫": ["天", "夭"],
    "夭": ["天", "夫"],
}


def get_ocr_hints(image_bytes: bytes, lang: str = "chi_sim") -> dict:
    """
    获取 OCR 提示

    Args:
        image_bytes: 图片字节数据
        lang: 语言 (默认 chi_sim)

    Returns:
        {"candidates": [...], "similar": [...]}
    """
    if pytesseract is None:
        return {"candidates": [], "similar": []}

    try:
        # 加载图片
        image = Image.open(BytesIO(image_bytes))

        # 转灰度并增强对比度
        if image.mode != "L":
            image = image.convert("L")

        from PIL import ImageOps

        image = ImageOps.autocontrast(image, cutoff=1)

        # 获取 OCR 数据
        data = pytesseract.image_to_data(
            image, lang=lang, output_type=pytesseract.Output.DICT
        )

        # 提取候选字（取 confidence 最高的前3个）
        candidates = []
        confidences = []
        texts = []

        for i, text in enumerate(data["text"]):
            conf = int(data["conf"][i])
            if conf > 0 and text.strip():
                texts.append((text, conf))

        # 按置信度排序
        texts.sort(key=lambda x: x[1], reverse=True)

        # 去重并取前3
        seen = set()
        for text, conf in texts:
            if text not in seen and len(text) == 1:
                candidates.append(text)
                seen.add(text)
                if len(candidates) >= 3:
                    break

        # 生成形近字
        similar = []
        for char in candidates[:2]:  # 只对前2个候选字生成形近字
            if char in SIMILAR_CHARS_MAP:
                similar.extend(SIMILAR_CHARS_MAP[char])

        # 去重
        similar = list(set(similar) - set(candidates))

        return {
            "candidates": candidates,
            "similar": similar[:5],  # 最多返回5个形近字
        }

    except Exception as e:
        print(f"OCR error: {e}")
        return {"candidates": [], "similar": []}


def batch_ocr_hints(segment_images: list[bytes], lang: str = "chi_sim") -> list[dict]:
    """
    批量获取 OCR 提示

    Args:
        segment_images: 图片字节数据列表
        lang: 语言

    Returns:
        OCR 提示列表
    """
    results = []
    for image_bytes in segment_images:
        result = get_ocr_hints(image_bytes, lang)
        results.append(result)
    return results
