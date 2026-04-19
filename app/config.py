"""全局配置"""
from pathlib import Path
from typing import Final

# 项目路径
BASE_DIR: Final = Path(__file__).parent.parent
DATA_DIR: Final = BASE_DIR / "data"
PROJECTS_DIR: Final = DATA_DIR / "projects"

# 字体度量参数
UNITS_PER_EM: Final = 1000
ASCENT: Final = 880
DESCENT: Final = -120
GLYPH_SIZE: Final = 1024

# 图像处理参数
CONTOUR_TOLERANCE: Final = 2.0
BLUR_SIGMA: Final = 1.0
MIN_COMPONENT_SIZE: Final = 30


def ensure_dirs() -> None:
    """确保必要的目录存在"""
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    # 验证配置
    ensure_dirs()
    print(f"BASE_DIR: {BASE_DIR}")
    print(f"DATA_DIR: {DATA_DIR}")
    print(f"PROJECTS_DIR: {PROJECTS_DIR}")
    print(f"UNITS_PER_EM: {UNITS_PER_EM}")
