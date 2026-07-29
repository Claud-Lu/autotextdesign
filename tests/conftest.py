import base64
import io

import pytest
from PIL import Image, ImageDraw


def create_test_image_bytes(size: tuple[int, int] = (256, 256)) -> bytes:
    image = Image.new("L", size, 255)
    draw = ImageDraw.Draw(image)
    draw.rectangle((64, 40, 192, 216), fill=0)
    draw.rectangle((96, 80, 160, 176), fill=255)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def image_bytes() -> bytes:
    return create_test_image_bytes()


@pytest.fixture
def image_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("ascii")
