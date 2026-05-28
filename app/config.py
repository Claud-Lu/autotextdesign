"""全局配置"""
from typing import Final

# 字体度量参数
UNITS_PER_EM: Final = 1000
ASCENT: Final = 880
DESCENT: Final = -120
GLYPH_SIZE: Final = 1024

# 图像处理参数
CONTOUR_TOLERANCE: Final = 2.0
BLUR_SIGMA: Final = 1.0
# 预处理策略和参数
# 默认预处理策略: 'auto' | 'strong' | 'bgsub' | 'original'
DEFAULT_PREPROCESS_STRATEGY: Final = "original"

# 纹理检测（用于 auto 策略）
TEXTURE_BG_SIGMA: Final = 10.0
TEXTURE_THRESHOLD: Final = 6.0

# 强去噪策略参数
STRONG_OPENING_RADIUS: Final = 4  # morphology.disk radius for strong opening
STRONG_MIN_SIZE_RATIO: Final = 0.001  # min object area ratio for strong denoise

# 常规预处理参数（原路径）
OPENING_RADIUS: Final = 2
MIN_SIZE_RATIO: Final = 0.0005

# 背景减法参数
BG_SIGMA: Final = 12.0
BG_CLOSING_RADIUS: Final = 1
# 预处理前的小幅高斯模糊，减轻锯齿和小噪点
PRE_BLUR_SIGMA: Final = 0.6
# 轮廓平滑迭代次数（Chaikin）
CONTOUR_SMOOTH_ITERS: Final = 2
