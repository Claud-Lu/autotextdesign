"""预处理可视化脚本

用法: python tools/preprocess_preview.py <input_image> [output_prefix]

会输出以下文件（在当前工作目录）:
- <prefix>_orig.png       原始灰度图
- <prefix>_otsu.png       Otsu 二值化结果
- <prefix>_cleaned.png    形态学去噪后结果
- <prefix>_final.png      预处理后（1024x1024，反转回背景白）
"""
import sys
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from skimage import filters, morphology

from app.services.preprocessor import preprocess_single_char
from app.config import GLYPH_SIZE


def visualize_preprocess(path: Path, out_prefix: str, strategy: str = None):
    img = Image.open(path).convert("L")
    arr = np.array(img)

    # 判断是否需要反转
    img_work = img.copy()
    if arr.mean() > 128:
        img_work = ImageOps.invert(img_work)
        arr = np.array(img_work)

    img_work = ImageOps.autocontrast(img_work, cutoff=1)
    arr = np.array(img_work)

    # Otsu
    thresh = filters.threshold_otsu(arr)
    binary = arr > thresh

    # denoise
    min_size = max(64, int(0.0005 * arr.size))
    opened = morphology.opening(binary, morphology.disk(2))
    cleaned = morphology.remove_small_objects(opened, min_size=min_size)
    cleaned = morphology.remove_small_holes(cleaned, area_threshold=min_size)

    # final processed image from existing function (uses same pipeline)
    with open(path, "rb") as f:
        if strategy:
            final = preprocess_single_char(f.read(), strategy=strategy)
        else:
            final = preprocess_single_char(f.read())

    # 保存可视化结果
    Image.fromarray(arr).save(f"{out_prefix}_orig.png")
    Image.fromarray((binary * 255).astype('uint8')).save(f"{out_prefix}_otsu.png")
    Image.fromarray((cleaned * 255).astype('uint8')).save(f"{out_prefix}_cleaned.png")
    final.save(f"{out_prefix}_final.png")


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/preprocess_preview.py <input_image> [output_prefix] [strategy]")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print("Input not found:", path)
        sys.exit(1)

    prefix = sys.argv[2] if len(sys.argv) > 2 else path.stem
    strategy = sys.argv[3] if len(sys.argv) > 3 else None
    visualize_preprocess(path, prefix, strategy=strategy)
    print("Saved:", f"{prefix}_orig.png", f"{prefix}_otsu.png", f"{prefix}_cleaned.png", f"{prefix}_final.png")


if __name__ == '__main__':
    main()
