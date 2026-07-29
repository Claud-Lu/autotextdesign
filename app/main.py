"""FastAPI 主应用入口"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

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

# 挂载静态文件
BASE_DIR = Path(__file__).parent.parent
static_dir = BASE_DIR / "app" / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
