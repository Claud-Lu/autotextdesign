"""请求体、频率和基础安全响应头保护。"""

import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from starlette.responses import JSONResponse
from starlette.types import Message, Receive, Scope, Send

from app.config import (
    MAX_REQUEST_BODY_BYTES,
    RATE_LIMIT_GENERATE_REQUESTS_PER_WINDOW,
    RATE_LIMIT_IMPORT_REQUESTS_PER_WINDOW,
    RATE_LIMIT_PREPROCESS_REQUESTS_PER_WINDOW,
    RATE_LIMIT_REQUESTS_PER_WINDOW,
    RATE_LIMIT_WINDOW_SECONDS,
)


class RequestBodyTooLarge(Exception):
    """请求流超过允许上限。"""


class RequestGuardMiddleware:
    """为公开 API 提供轻量、单进程可用的请求保护。"""

    _SECURITY_HEADERS = (
        (b"x-content-type-options", b"nosniff"),
        (b"x-frame-options", b"DENY"),
        (b"referrer-policy", b"strict-origin-when-cross-origin"),
        (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
        (b"cross-origin-opener-policy", b"same-origin"),
        (
            b"content-security-policy",
            (
                b"default-src 'self'; base-uri 'self'; object-src 'none'; "
                b"frame-ancestors 'none'; "
                b"script-src 'self' 'unsafe-inline' https://ops.chathappy.cn; "
                b"style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                b"font-src 'self' data: blob: https://fonts.gstatic.com; "
                b"img-src 'self' data: blob:; connect-src 'self' https://ops.chathappy.cn"
            ),
        ),
    )

    def __init__(self, app: Callable[..., Awaitable[None]]) -> None:
        self.app = app
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._last_cleanup = time.monotonic()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        path = scope.get("path", "")
        method = scope.get("method", "GET").upper()

        if method == "POST" and path.startswith("/api/"):
            content_length = self._parse_content_length(headers.get(b"content-length"))
            if content_length is not None and content_length > MAX_REQUEST_BODY_BYTES:
                await self._json_error(
                    scope,
                    receive,
                    send,
                    413,
                    "请求内容过大",
                )
                return
            if self._is_rate_limited(scope, headers, path):
                await self._json_error(
                    scope,
                    receive,
                    send,
                    429,
                    "请求过于频繁，请稍后重试",
                    extra_headers={"Retry-After": str(RATE_LIMIT_WINDOW_SECONDS)},
                )
                return

        received_bytes = 0

        async def limited_receive() -> Message:
            nonlocal received_bytes
            message = await receive()
            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > MAX_REQUEST_BODY_BYTES:
                    raise RequestBodyTooLarge
            return message

        async def secure_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = list(message.get("headers", []))
                existing = {key.lower() for key, _ in response_headers}
                response_headers.extend(
                    (key, value)
                    for key, value in self._SECURITY_HEADERS
                    if key not in existing
                )
                message["headers"] = response_headers
            await send(message)

        try:
            await self.app(scope, limited_receive, secure_send)
        except RequestBodyTooLarge:
            await self._json_error(scope, receive, secure_send, 413, "请求内容过大")

    def _is_rate_limited(
        self,
        scope: Scope,
        headers: dict[bytes, bytes],
        path: str,
    ) -> bool:
        now = time.monotonic()
        cutoff = now - RATE_LIMIT_WINDOW_SECONDS
        client_key = f"{self._client_key(scope, headers)}:{path}"
        timestamps = self._requests[client_key]
        request_limit = self._request_limit(path)

        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()
        if len(timestamps) >= request_limit:
            return True

        timestamps.append(now)
        if now - self._last_cleanup > RATE_LIMIT_WINDOW_SECONDS:
            self._cleanup(cutoff)
            self._last_cleanup = now
        return False

    @staticmethod
    def _request_limit(path: str) -> int:
        if path == "/api/preprocess":
            return RATE_LIMIT_PREPROCESS_REQUESTS_PER_WINDOW
        if path == "/api/generate":
            return RATE_LIMIT_GENERATE_REQUESTS_PER_WINDOW
        if path == "/api/import-ttf":
            return RATE_LIMIT_IMPORT_REQUESTS_PER_WINDOW
        return RATE_LIMIT_REQUESTS_PER_WINDOW

    def _cleanup(self, cutoff: float) -> None:
        stale_keys = []
        for key, timestamps in self._requests.items():
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if not timestamps:
                stale_keys.append(key)
        for key in stale_keys:
            self._requests.pop(key, None)

    @staticmethod
    def _client_key(scope: Scope, headers: dict[bytes, bytes]) -> str:
        # 线上仅信任 Cloudflare 注入的专用头；本地开发回退到 socket 地址。
        cloudflare_ip = headers.get(b"cf-connecting-ip")
        if cloudflare_ip:
            return cloudflare_ip.decode("ascii", errors="ignore")[:64]
        client = scope.get("client")
        return str(client[0])[:64] if client else "unknown"

    @staticmethod
    def _parse_content_length(raw_value: bytes | None) -> int | None:
        if raw_value is None:
            return None
        try:
            return max(0, int(raw_value))
        except (TypeError, ValueError):
            return None

    @classmethod
    async def _json_error(
        cls,
        scope: Scope,
        receive: Receive,
        send: Send,
        status_code: int,
        detail: str,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        response_headers = {
            key.decode("ascii"): value.decode("ascii")
            for key, value in cls._SECURITY_HEADERS
        }
        response_headers.update(extra_headers or {})
        response = JSONResponse(
            {"detail": detail},
            status_code=status_code,
            headers=response_headers,
        )
        await response(scope, receive, send)
