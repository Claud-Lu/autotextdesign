import base64
import io

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.config import (
    APP_VERSION,
    MAX_REQUEST_BODY_BYTES,
    RATE_LIMIT_REQUESTS_PER_WINDOW,
)
from app.main import app
from app.middleware.request_guard import RequestGuardMiddleware

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as async_client:
        yield async_client


async def test_health_and_security_headers(client: AsyncClient) -> None:
    response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "content-security-policy" in response.headers
    assert "access-control-allow-origin" not in response.headers
    assert app.version == APP_VERSION


async def test_preprocess_endpoint(client: AsyncClient, image_bytes: bytes) -> None:
    response = await client.post(
        "/api/preprocess",
        files={"file": ("永.png", image_bytes, "image/png")},
        data={"strategy": "original"},
    )

    assert response.status_code == 200
    processed_bytes = base64.b64decode(response.json()["image_base64"])
    processed = Image.open(io.BytesIO(processed_bytes))
    assert processed.size == (1024, 1024)


async def test_preprocess_rejects_unsupported_strategy(
    client: AsyncClient,
    image_bytes: bytes,
) -> None:
    response = await client.post(
        "/api/preprocess",
        files={"file": ("永.png", image_bytes, "image/png")},
        data={"strategy": "unknown"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "不支持的图片处理策略"


async def test_preprocess_rejects_unsupported_media_type(client: AsyncClient) -> None:
    response = await client.post(
        "/api/preprocess",
        files={"file": ("永.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 415


async def test_generate_endpoint(client: AsyncClient, image_base64: str) -> None:
    response = await client.post(
        "/api/generate",
        json={
            "font_name": "测试字体",
            "glyphs": [{"char": "永", "image_base64": image_base64}],
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("font/ttf")
    assert response.content[:4] == b"\x00\x01\x00\x00"


async def test_generate_rejects_duplicate_characters(
    client: AsyncClient,
    image_base64: str,
) -> None:
    response = await client.post(
        "/api/generate",
        json={
            "font_name": "测试字体",
            "glyphs": [
                {"char": "永", "image_base64": image_base64},
                {"char": "永", "image_base64": image_base64},
            ],
        },
    )

    assert response.status_code == 422


async def test_request_body_content_length_limit() -> None:
    guarded_app = FastAPI()
    guarded_app.add_middleware(RequestGuardMiddleware)

    @guarded_app.post("/api/test")
    async def endpoint() -> dict:
        return {"ok": True}

    async with AsyncClient(
        transport=ASGITransport(app=guarded_app),
        base_url="http://test",
    ) as guarded_client:
        response = await guarded_client.post(
            "/api/test",
            content=b"x",
            headers={"content-length": str(MAX_REQUEST_BODY_BYTES + 1)},
        )

    assert response.status_code == 413
    assert response.headers["x-content-type-options"] == "nosniff"


async def test_rate_limit() -> None:
    guarded_app = FastAPI()
    guarded_app.add_middleware(RequestGuardMiddleware)

    @guarded_app.post("/api/test")
    async def endpoint() -> dict:
        return {"ok": True}

    async with AsyncClient(
        transport=ASGITransport(app=guarded_app),
        base_url="http://test",
    ) as guarded_client:
        for _ in range(RATE_LIMIT_REQUESTS_PER_WINDOW):
            response = await guarded_client.post("/api/test")
            assert response.status_code == 200
        response = await guarded_client.post("/api/test")

    assert response.status_code == 429
    assert response.headers["retry-after"]
    assert response.headers["x-content-type-options"] == "nosniff"
