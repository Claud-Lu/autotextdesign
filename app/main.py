"""FastAPI 主应用入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import font, preprocess

# 创建 FastAPI 应用
app = FastAPI(
    title="书法字体制作器",
    description="将手写字体转换为可使用的 TTF 字体文件",
    version="2.0.0",
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 健康检查
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "服务运行正常"}


# 注册路由（无状态 API）
app.include_router(preprocess.router)
app.include_router(font.router)

# 挂载静态文件
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
static_dir = BASE_DIR / "app" / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
