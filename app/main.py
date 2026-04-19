"""FastAPI 主应用入口"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import characters, font, projects, segmentation
from app.config import BASE_DIR, ensure_dirs


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时确保目录存在
    ensure_dirs()
    yield
    # 关闭时清理资源（如需要）


# 创建 FastAPI 应用
app = FastAPI(
    title="书法字体制作器",
    description="将手写字体转换为可使用的 TTF 字体文件",
    version="1.0.0",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 健康检查
@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "message": "服务运行正常"}


# 注册路由
app.include_router(projects.router)
app.include_router(segmentation.router)
app.include_router(characters.router)
app.include_router(font.router)

# 挂载静态文件（使用 html 目录作为根路径）
static_dir = BASE_DIR / "app" / "static"
static_dir.mkdir(exist_ok=True)
# 挂载所有其他请求到静态文件
app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
