import io

import numpy as np
import pytest
from PIL import Image

from app.config import GLYPH_SIZE
from app.services.preprocessor import preprocess_single_char


@pytest.mark.parametrize("strategy", ["auto", "strong", "bgsub", "original"])
def test_preprocess_supported_strategies(image_bytes: bytes, strategy: str) -> None:
    result = preprocess_single_char(image_bytes, strategy)

    assert result.mode == "L"
    assert result.size == (GLYPH_SIZE, GLYPH_SIZE)
    pixels = np.asarray(result)
    assert pixels.min() == 0
    assert pixels.max() == 255


def test_preprocess_rejects_blank_image() -> None:
    image = Image.new("L", (128, 128), 255)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    with pytest.raises(ValueError, match="未检测到有效墨迹"):
        preprocess_single_char(buffer.getvalue())


def test_preprocess_rejects_invalid_bytes() -> None:
    with pytest.raises(ValueError, match="无法识别图片格式"):
        preprocess_single_char(b"not-an-image")
