"""API 上传读取与 CPU 密集型任务的公共边界。"""

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.config import (
    MAX_CONCURRENT_PROCESSING_JOBS,
    PROCESSING_QUEUE_TIMEOUT_SECONDS,
)

_processing_semaphore = asyncio.Semaphore(MAX_CONCURRENT_PROCESSING_JOBS)


async def read_upload_limited(file: UploadFile, max_bytes: int) -> bytes:
    """分块读取上传内容，在超过上限时立即停止。"""
    chunks: list[bytes] = []
    total = 0

    while chunk := await file.read(1024 * 1024):
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"上传文件不能超过 {max_bytes // (1024 * 1024)}MB",
            )
        chunks.append(chunk)

    if total == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="上传文件为空",
        )
    return b"".join(chunks)


@asynccontextmanager
async def processing_slot() -> AsyncIterator[None]:
    """限制 CPU 密集型字体任务并发，并避免请求无限排队。"""
    try:
        await asyncio.wait_for(
            _processing_semaphore.acquire(),
            timeout=PROCESSING_QUEUE_TIMEOUT_SECONDS,
        )
    except TimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="当前处理任务较多，请稍后重试",
            headers={"Retry-After": "5"},
        ) from exc

    try:
        yield
    finally:
        _processing_semaphore.release()


async def run_processing(function: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """在线程池中运行同步图像/字体处理，避免阻塞事件循环。"""
    async with processing_slot():
        return await run_in_threadpool(function, *args, **kwargs)
