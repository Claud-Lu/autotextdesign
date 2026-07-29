"""全局配置"""
from typing import Final

# 应用版本
APP_VERSION: Final = "1.2.0"

# 字体度量参数
UNITS_PER_EM: Final = 1000
ASCENT: Final = 880
DESCENT: Final = -120
GLYPH_SIZE: Final = 1024

# API 资源边界
MAX_IMAGE_UPLOAD_BYTES: Final = 10 * 1024 * 1024
MAX_TTF_UPLOAD_BYTES: Final = 30 * 1024 * 1024
MAX_REQUEST_BODY_BYTES: Final = 80 * 1024 * 1024
MAX_IMAGE_PIXELS: Final = 25_000_000
MAX_GLYPHS: Final = 5000
MAX_GLYPH_BASE64_CHARS: Final = 2 * 1024 * 1024
MAX_TOTAL_GLYPH_BASE64_CHARS: Final = 60 * 1024 * 1024
MAX_FONT_NAME_LENGTH: Final = 80
MAX_CONCURRENT_PROCESSING_JOBS: Final = 2
PROCESSING_QUEUE_TIMEOUT_SECONDS: Final = 15
RATE_LIMIT_WINDOW_SECONDS: Final = 60
RATE_LIMIT_REQUESTS_PER_WINDOW: Final = 30
RATE_LIMIT_PREPROCESS_REQUESTS_PER_WINDOW: Final = 120
RATE_LIMIT_GENERATE_REQUESTS_PER_WINDOW: Final = 10
RATE_LIMIT_IMPORT_REQUESTS_PER_WINDOW: Final = 10

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
