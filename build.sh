#!/bin/bash
set -e

echo "=== 书法字体制作器 — macOS 打包 ==="

# 清理旧构建
rm -rf build dist

# PyInstaller 打包
pyinstaller \
    --name "书法字体制作器" \
    --windowed \
    --onedir \
    --noconfirm \
    --clean \
    --add-data "app:app" \
    --hidden-import uvicorn.logging \
    --hidden-import uvicorn.loops \
    --hidden-import uvicorn.loops.auto \
    --hidden-import uvicorn.protocols \
    --hidden-import uvicorn.protocols.http \
    --hidden-import uvicorn.protocols.http.auto \
    --hidden-import uvicorn.protocols.websockets \
    --hidden-import uvicorn.protocols.websockets.auto \
    --hidden-import uvicorn.lifespan \
    --hidden-import uvicorn.lifespan.on \
    --hidden-import multipart \
    --hidden-import pytesseract \
    --hidden-import app.main \
    --hidden-import app.api.routes.projects \
    --hidden-import app.api.routes.segmentation \
    --hidden-import app.api.routes.characters \
    --hidden-import app.api.routes.font \
    --hidden-import app.services.project_service \
    --hidden-import app.services.preprocessor \
    --hidden-import app.services.segmenter \
    --hidden-import app.services.grid_cutter \
    --hidden-import app.services.ocr \
    --hidden-import app.services.contour_fitter \
    --hidden-import app.services.font_builder \
    --collect-all fonttools \
    --collect-all pytesseract \
    desktop.py

echo ""
echo "=== 打包完成 ==="
echo "应用位置: dist/书法字体制作器.app"
