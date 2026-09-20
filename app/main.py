"""FastAPI 主应用入口"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.types import Message, Receive, Scope, Send

from app.api.routes import font, preprocess
from app.config import APP_VERSION
from app.middleware.request_guard import RequestGuardMiddleware

# 创建 FastAPI 应用
app = FastAPI(
    title="书法字体制作器",
    description="将手写字体转换为可使用的 TTF 字体文件",
    version=APP_VERSION,
)

# Web 与 API 同源，不开放跨域；中间件负责体积、频率和安全响应头。
app.add_middleware(RequestGuardMiddleware)


# 健康检查
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "服务运行正常"}


# 注册路由（无状态 API）
app.include_router(preprocess.router)
app.include_router(font.router)


class CachedStaticFiles(StaticFiles):
    """按资源类型附加 Cache-Control，让浏览器与 CDN 边缘缓存静态资源。

    - 字体文件内容不变，允许长缓存；
    - 页面 HTML 给短浏览器缓存与 s-maxage，方便后续接入边缘整页缓存；
    - 其余静态文件缓存一天，兼顾更新时效。
    """

    _IMMUTABLE_EXTENSIONS = (".woff2",)
    _DAILY_EXTENSIONS = (".css", ".js", ".png", ".jpg", ".svg", ".ico", ".txt", ".xml")
    _HTML_CACHE_CONTROL = b"public, max-age=300, s-maxage=3600"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method", "GET").upper() != "GET":
            await super().__call__(scope, receive, send)
            return

        cache_control = self._cache_control_for(scope.get("path", ""))

        async def send_with_cache(message: Message) -> None:
            if message["type"] == "http.response.start" and cache_control:
                headers = list(message.get("headers", []))
                if not any(key.lower() == b"cache-control" for key, _ in headers):
                    headers.append((b"cache-control", cache_control))
                message["headers"] = headers
            await send(message)

        await super().__call__(scope, receive, send_with_cache)

    @classmethod
    def _cache_control_for(cls, path: str) -> bytes | None:
        if path.startswith("/fonts/") or path.endswith(cls._IMMUTABLE_EXTENSIONS):
            return b"public, max-age=31536000, immutable"
        if path.endswith(cls._DAILY_EXTENSIONS):
            return b"public, max-age=86400"
        if path == "/" or path.endswith(".html"):
            return cls._HTML_CACHE_CONTROL
        return None


# 挂载静态文件
BASE_DIR = Path(__file__).parent.parent
static_dir = BASE_DIR / "app" / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/", CachedStaticFiles(directory=str(static_dir), html=True), name="static")
