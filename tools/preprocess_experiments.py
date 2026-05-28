"""对比实验：更强去噪 与 背景去除（高斯背景减法）

用法: python tools/preprocess_experiments.py
会在仓库根为每张样本生成若干对比图。
"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps
from scipy import ndimage as ndi
from skimage import filters, morphology


SAMPLES = ["啊.jpg", "埃.jpg"]


def variant_strong_denoise(arr: np.ndarray):
    # 更强的开运算和更大的 min_size
    binary = arr > filters.threshold_otsu(arr)
    opened = morphology.opening(binary, morphology.disk(4))
    min_size = max(128, int(0.001 * arr.size))
    cleaned = morphology.remove_small_objects(opened, min_size=min_size)
    cleaned = morphology.remove_small_holes(cleaned, area_threshold=min_size)
    return cleaned


def variant_background_subtract(arr: np.ndarray):
    # 用大的高斯核估计背景并减去，再做 Otsu
    background = ndi.gaussian_filter(arr.astype(float), sigma=12)
    corrected = arr.astype(float) - background
    # 归一化到 0-255
    cmin, cmax = corrected.min(), corrected.max()
    if cmax - cmin > 0:
        corrected = 255 * (corrected - cmin) / (cmax - cmin)
    corrected = corrected.astype(np.uint8)
    thresh = filters.threshold_otsu(corrected)
    binary = corrected > thresh
    opened = morphology.opening(binary, morphology.disk(2))
    min_size = max(64, int(0.0005 * arr.size))
    cleaned = morphology.remove_small_objects(opened, min_size=min_size)
    cleaned = morphology.remove_small_holes(cleaned, area_threshold=min_size)
    return cleaned


def run():
    for s in SAMPLES:
        p = Path(s)
        if not p.exists():
            print("skip", s)
            continue
        img = Image.open(p).convert("L")
        arr = np.array(img)
        # auto-invert if needed (same heuristic)
        if arr.mean() > 128:
            img = ImageOps.invert(img)
            arr = np.array(img)

        # base otsu
        thresh = filters.threshold_otsu(arr)
        base = arr > thresh
        Image.fromarray((base * 255).astype('uint8')).save(f"{p.stem}_base_otsu.png")

        v1 = variant_strong_denoise(arr)
        Image.fromarray((v1 * 255).astype('uint8')).save(f"{p.stem}_strong_denoise.png")

        v2 = variant_background_subtract(arr)
        Image.fromarray((v2 * 255).astype('uint8')).save(f"{p.stem}_bgsub.png")

        print("saved for", p.stem)


if __name__ == '__main__':
    run()
