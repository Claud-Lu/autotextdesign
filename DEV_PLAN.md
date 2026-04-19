# 开发计划 — 书法字体制作器

> 每完成一步打勾 [x]，中断后从此处恢复。

## Phase 1: 后端骨架 + 项目管理

### 1.1 初始化项目结构
- [x] 创建 `app/` 目录结构
  ```
  app/
  ├── __init__.py
  ├── main.py
  ├── config.py
  ├── api/
  │   ├── __init__.py
  │   ├── models.py
  │   └── routes/
  │       ├── __init__.py
  │       ├── projects.py
  │       ├── segmentation.py
  │       ├── characters.py
  │       └── font.py
  ├── services/
  │   ├── __init__.py
  │   ├── segmenter.py
  │   ├── grid_cutter.py
  │   ├── preprocessor.py
  │   ├── font_builder.py
  │   ├── contour_fitter.py
  │   └── ocr.py
  └── static/
      └── index.html
  data/             (运行时数据，gitignore)
  ```
- [x] 创建 `requirements.txt`
  ```
  fastapi>=0.115.0
  uvicorn[standard]>=0.30.0
  python-multipart>=0.0.9
  Pillow>=10.0.0
  numpy>=1.26.0
  scipy>=1.13.0
  scikit-image>=0.24.0
  opencv-python-headless>=4.10.0
  fonttools>=4.53.0
  PyMuPDF>=1.24.0
  pytesseract>=0.3.10
  ```
- [x] 创建 `run.py`
  ```python
  import uvicorn
  uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
  ```
- [x] 创建 `.gitignore`（忽略 data/、__pycache__/、.ttf 等）
- **验证**: `python -c "from app.main import app"` 不报错

### 1.2 config.py — 全局配置
- [x] 创建 `app/config.py`
  - `BASE_DIR`: 项目根目录
  - `DATA_DIR`: `BASE_DIR/data`
  - `PROJECTS_DIR`: `DATA_DIR/projects`
  - `UNITS_PER_EM = 1000`
  - `ASCENT = 880`, `DESCENT = -120`
  - `GLYPH_SIZE = 1024`
  - `CONTOUR_TOLERANCE = 2.0`
  - `BLUR_SIGMA = 1.0`（轮廓平滑用）
  - `MIN_COMPONENT_SIZE = 30`（过滤小噪点）
  - `ensure_dirs()`: 启动时确保 data/projects 目录存在
- **验证**: `python -c "from app.config import *; print(UNITS_PER_EM)"` 输出 1000

### 1.3 Pydantic 模型 — API 数据结构
- [x] 创建 `app/api/models.py`
  - `ProjectCreate(name: str)`
  - `ProjectOut(id, name, created_at, updated_at, stats: dict)` — stats 含 total_segments / confirmed_chars
  - `SegmentOut(id, bbox, status, label, ocr_candidates, image_url, created_at)`
  - `SegmentAdjustAction(type: Literal["merge","split","move","resize"], ids: list[str], bbox: list[int] | None)`
  - `SegmentAdjustRequest(actions: list[SegmentAdjustAction])`
  - `CharacterOut(char, label, image_url, confirmed_at)`
  - `ConfirmRequest(label: str)`
  - `UploadResponse(segments_count, scan_id, mode)`
  - `FontGenerateRequest(font_name: str | None)`
  - `OcrHintResponse(candidates: list[str], similar: list[str])`
- **验证**: `python -c "from app.api.models import *"` 不报错

### 1.4 项目管理服务 + API
- [x] 创建 `app/services/__init__.py`
- [ ] 在 `app/services/` 中创建项目文件操作辅助函数（或直接在 routes 中处理）
  - `create_project(name)` → 生成 `proj_XXXXXXXX` 目录 + meta.json
  - `get_project(id)` → 读 meta.json
  - `list_projects()` → 扫描 projects/ 目录
  - `delete_project(id)` → 删除整个目录
  - `update_meta(id, updates)` → 原子更新 meta.json
- [x] 实现 `app/api/routes/projects.py`
  - `POST /api/projects` → 创建项目目录 + 初始化 meta.json
  - `GET /api/projects` → 列出所有项目（从目录扫描）
  - `GET /api/projects/{id}` → 返回项目详情 + 统计
  - `DELETE /api/projects/{id}` → 删除项目目录
- **验证**:
  ```bash
  # 启动服务
  python run.py
  # 用 curl 测试
  curl -X POST http://localhost:8000/api/projects -H "Content-Type: application/json" -d '{"name":"测试字体"}'
  curl http://localhost:8000/api/projects
  curl http://localhost:8000/api/projects/proj_XXXXXXXX
  curl -X DELETE http://localhost:8000/api/projects/proj_XXXXXXXX
  ```

### 1.5 FastAPI 主应用入口
- [x] 创建 `app/main.py`
  - 创建 FastAPI 实例
  - 挂载静态文件 `app/static/` → `/`
  - 注册路由: projects, segmentation, characters, font
  - startup 事件调用 `ensure_dirs()`
  - CORS 中间件（允许 localhost）
- **验证**: `python run.py` 启动后访问 `http://localhost:8000/docs` 看到 Swagger UI

### 1.6 空白前端占位
- [x] 创建 `app/static/index.html` — 最小 HTML，显示"书法字体制作器"标题
- **验证**: 浏览器访问 `http://localhost:8000` 看到标题

---

## Phase 2: 图像处理 + 切割修正

### 2.1 preprocessor.py — 单字预处理服务
- [ ] 创建 `app/services/preprocessor.py`
  - `preprocess_single_char(image_file) -> Image`:
    - 转灰度 + autocontrast
    - Otsu 二值化
    - 找墨迹 bbox
    - 裁剪 + 10% 边距
    - 居中填充为正方形
    - 缩放到 1024×1024 (LANCZOS)
    - 返回 PIL Image
  - `save_processed_char(image, project_id, unicode_char) -> str`:
    - 保存到 `chars/{unicode_hex}.png`
    - 返回相对路径
- **验证**: 用现有 glyphs/ 目录中的一张图片测试
  ```python
  from app.services.preprocessor import preprocess_single_char
  img = preprocess_single_char(open("某图片.png", "rb"))
  assert img.size == (1024, 1024)
  ```

### 2.2 segmenter.py — 自动切割服务
- [ ] 创建 `app/services/segmenter.py`
  - **复用 `extract_glyphs.py` 的逻辑**，但去掉硬编码的位置判断
  - `preprocess_scan(image: np.ndarray) -> np.ndarray`:
    - 灰度 + autocontrast + 中值阈值二值化
  - `find_components(binary) -> list[dict]`:
    - scipy.ndimage.label
    - 过滤 < 30px
    - 返回 `[{"id", "size", "cy", "cx", "y0", "x0", "y1", "x1", "coords"}]`
  - `cluster_to_characters(components) -> list[list[dict]]`:
    - Y 质心排序 → 行检测（间距 > 1.5×中位高度 = 新行）
    - 行内 X 质心排序 → 字符分组（间距 > 2.0×中位宽度 = 新字）
  - `extract_segment(binary, component_group, size=1024) -> Image`:
    - **复用 `extract_glyphs.py` 的 `save_glyph` 逻辑**
    - 计算 group 的联合 bbox
    - 裁剪 + mask + pad + center + resize
    - 返回 PIL Image
  - `auto_segment(image_file) -> list[dict]`:
    - 组合以上步骤
    - 返回 `[{"image": PIL.Image, "bbox": [x0,y0,x1,y1], "component_ids": [...]}]`
- **验证**: 用项目自带的测试图片验证，应能检测出多个连通域并聚类

### 2.3 grid_cutter.py — 网格切割服务
- [ ] 创建 `app/services/grid_cutter.py`
  - `grid_segment(image_file, cols: int, rows: int) -> list[dict]`:
    - 加载图像，转灰度
    - 计算每格宽高 = 图片宽/cols, 图片高/rows
    - 遍历每个格子：裁剪 → 居中填充正方形 → 缩放 1024×1024
    - 返回 `[{"image": PIL.Image, "bbox": [x0,y0,x1,y1], "grid_pos": (row, col)}]`
  - `grid_preview(image_file, cols, rows) -> PIL.Image`:
    - 在原图上画出网格线（OpenCV 画线）
    - 返回预览图（让用户确认网格对不对）
- **验证**:
  ```python
  from app.services.grid_cutter import grid_segment
  segments = grid_segment(open("某字帖.png","rb"), cols=10, rows=8)
  assert len(segments) == 80
  assert segments[0]["image"].size == (1024, 1024)
  ```

### 2.4 ocr.py — OCR 提示服务
- [ ] 创建 `app/services/ocr.py`
  - `get_ocr_hints(image_file, lang="chi_sim") -> dict`:
    - 用 pytesseract 做识别
    - `image_to_data()` 获取 Top-3 候选（取 confidence 最高的 3 个）
    - **形近字提示**: 基于候选字，用 Unicode CJK 统一汉字范围生成形近字列表
      - 简单实现：遍历同部首的字（从 unicode 数据中获取）
      - 或预定义常见形近字映射表
    - 返回 `{"candidates": ["黃", "黌", "廣"], "similar": ["黈", "黹"]}`
  - `batch_ocr_hints(segment_images: list) -> list[dict]`:
    - 批量处理，减少 Tesseract 启动开销
- **验证**:
  ```python
  from app.services.ocr import get_ocr_hints
  result = get_ocr_hints(open("glyphs/large_黃.png","rb"))
  assert "candidates" in result
  print(result["candidates"])  # 应包含类似"黃"的字
  ```

### 2.5 扫描件上传 + 自动切割 API
- [ ] 实现 `app/api/routes/segmentation.py` — 扫描件上传部分
  - `POST /api/projects/{id}/scans`:
    - 参数: `file` (UploadFile), `mode` ("auto" | "grid", 默认 "auto"), `cols`/`rows` (grid 模式必填)
    - PDF 文件用 PyMuPDF 转 PNG (300 DPI)
    - 调用 segmenter 或 grid_cutter
    - 保存 segment 图片到 `segments/seg_XXXX.png`
    - 对每个 segment 调用 OCR 获取候选
    - 更新 meta.json（追加 segments + scan_history）
    - 返回 `UploadResponse(segments_count, scan_id, mode)`
  - `GET /api/projects/{id}/segments`:
    - 读 meta.json 中的 segments
    - 返回 `list[SegmentOut]`
  - `DELETE /api/projects/{id}/segments/{sid}`:
    - 删除 segment 图片文件
    - 更新 meta.json 移除该 segment
- **验证**: 上传一张字帖图片，确认 segments 被正确保存到目录并返回

### 2.6 切割修正 API
- [ ] 继续完善 `app/api/routes/segmentation.py` — 修正部分
  - `PUT /api/projects/{id}/segments/adjust`:
    - 请求体: `{"actions": [{"type": "merge|split|move|resize", "ids": [...], "bbox": [...]}]}`
    - **merge**: 合并多个 segment → 读原图对应区域，裁剪联合 bbox，重新生成图片，删除旧 segments，创建新 segment
    - **split**: 将一个 segment 横向/纵向二分 → 创建两个新 segment，删除旧的
    - **move**: 调整 segment 的 bbox 位置 → 从原图重新裁剪
    - **resize**: 调整 segment 的 bbox 大小 → 从原图重新裁剪
    - 所有操作完成后更新 meta.json
  - `GET /api/projects/{id}/segments/{sid}/image`:
    - 返回 segment 图片（用于前端展示）
  - `GET /api/projects/{id}/scans/{scan_id}/overlay`:
    - 返回原图叠加所有切割框的可视化图（用于修正 UI 定位）
- **验证**:
  ```bash
  # 测试合并
  curl -X PUT http://localhost:8000/api/projects/{id}/segments/adjust \
    -H "Content-Type: application/json" \
    -d '{"actions": [{"type": "merge", "ids": ["seg_0001","seg_0002"]}]}'
  ```

### 2.7 单字上传 + 字符确认 API
- [ ] 实现 `app/api/routes/characters.py`
  - `POST /api/projects/{id}/characters`:
    - 参数: `file` (UploadFile), `label` (str, Unicode 字符)
    - 验证 label 是合法 CJK 字符
    - 调用 `preprocessor.preprocess_single_char()` 处理
    - 保存到 `chars/{unicode_hex}.png`
    - 更新 meta.json confirmed
    - 如已存在，返回 warning 但覆盖
  - `GET /api/projects/{id}/characters`:
    - 列出已确认字符（扫描 chars/ 目录）
  - `DELETE /api/projects/{id}/characters/{char}`:
    - 删除字符图片
    - 更新 meta.json
  - `POST /api/projects/{id}/segments/{sid}/confirm`:
    - 请求体: `{"label": "黃"}`
    - 将 segment 图片移动到 chars/ 并重命名
    - 更新 meta.json（segment 状态 → confirmed）
    - 如 label 已存在，返回冲突提示
- **验证**: 上传一张单字图片 + 标注"黃"，确认 chars/9EC3.png 存在

### 2.8 OCR 辅助 API
- [ ] 在 `app/api/routes/segmentation.py` 或新建 `app/api/routes/ocr.py` 中添加
  - `POST /api/ocr/hint`:
    - 参数: `file` (UploadFile), `lang` (可选, 默认 "chi_sim")
    - 调用 `ocr.get_ocr_hints()`
    - 返回 `OcrHintResponse(candidates, similar)`
- **验证**: curl 上传一张字图，确认返回 candidates 列表

---

## Phase 3: 字体生成（增强版）

### 3.1 contour_fitter.py — 轮廓平滑 + Bézier 曲线拟合
- [ ] 创建 `app/services/contour_fitter.py`
  - `smooth_contour(binary_arr, sigma=1.0) -> np.ndarray`:
    - 对二值图做 Gaussian blur 平滑
    - 重新二值化（阈值 0.5）
    - 消除锯齿边缘
  - `fit_bezier_contour(contour_points, tolerance=2.0) -> list[tuple]`:
    - 输入: 轮廓点序列 (N, 2)
    - 用 Ramer-Douglas-Peucker 简化点数
    - 对简化后的点序列拟合三次贝塞尔曲线
    - 返回控制点列表
    - **备选方案**: 如果贝塞尔拟合复杂，先实现 Potrace 管线（`pip install potrace`）
  - `extract_contours_with_holes(binary_arr) -> tuple[list, list]`:
    - 外轮廓: `find_contours(arr, 0.5)` → 面积最大的轮廓
    - 内轮廓（孔洞）: 其余轮廓
    - 判断方向：外轮廓顺时针，内轮廓逆时针（字体规范）
    - 返回 `(outer_contours, inner_contours)`
  - `contours_to_glyph(binary_arr, units_per_em=1000) -> TTGlyph`:
    - 组合以上步骤: smooth → find_contours → 分离内外 → 拟合贝塞尔 → 构建 TTGlyphPen
    - 坐标映射: 像素 × units_per_em / img_size，Y 轴翻转
    - 用 `curveTo` 替代原来的 `lineTo`
    - 返回 pen.glyph()
- **验证**:
  ```python
  from app.services.contour_fitter import contours_to_glyph
  from PIL import Image
  import numpy as np
  img = Image.open("glyphs/large_黃.png").convert("L")
  arr = np.array(img) / 255.0
  glyph = contours_to_glyph(arr)
  assert glyph is not None
  # 对比旧的直线 polygon 方法，验证曲线更平滑
  ```

### 3.2 font_builder.py — 增强版字体生成服务
- [ ] 创建 `app/services/font_builder.py`
  - **复用 `build_font.py` 的核心逻辑**，增强以下方面:
  - `build_font(project_id, font_name=None) -> str`:
    - 扫描 `chars/` 目录所有 PNG
    - 对每个字符调用 `contour_fitter.contours_to_glyph()`
    - FontBuilder 构建:
      - **等宽模式**: `advance_width = UNITS_PER_EM` (固定 1000)
      - **baseline 对齐**: 所有字形垂直居中于 baseline 之上
      - `.notdef` 空白 glyph
      - CJK 度量参数 (ascent=880, descent=-120)
      - OS/2 表完整配置
      - name 表: 字体名/族名/样式名
    - 保存到 `generated/{font_name}.ttf`
    - 返回文件路径
  - `build_preview_font(project_id) -> bytes`:
    - 快速生成预览用字体（不保存文件，返回 bytes）
    - 用于前端 @font-face 实时加载
- **验证**:
  ```python
  from app.services.font_builder import build_font
  path = build_font("proj_XXXXXXXX", "测试字体")
  # 用 fontTools 打开验证
  from fontTools.ttLib import TTFont
  font = TTFont(path)
  print(font["glyf"]["uni9EC3"])  # 应有曲线数据
  ```

### 3.3 字体生成 + 下载 API
- [ ] 实现 `app/api/routes/font.py`
  - `POST /api/projects/{id}/generate`:
    - 请求体: `FontGenerateRequest(font_name)` (可选，默认用项目名)
    - 调用 `font_builder.build_font()`
    - 更新 meta.json 记录生成时间和字体文件路径
    - 返回 `{"status": "ok", "font_path": "...", "glyph_count": N}`
  - `GET /api/projects/{id}/download`:
    - 返回 FileResponse（TTF 文件下载）
    - Content-Type: font/ttf
  - `GET /api/projects/{id}/preview-font`:
    - 调用 `font_builder.build_preview_font()`
    - 返回 StreamingResponse（font/woff2 或 font/ttf，用于前端 @font-face）
    - 加 Cache-Control 头，避免频繁重建
- **验证**:
  ```bash
  # 生成字体
  curl -X POST http://localhost:8000/api/projects/{id}/generate
  # 下载字体
  curl -O http://localhost:8000/api/projects/{id}/download
  # 在 macOS 安装并测试
  ```

---

## Phase 4: 前端界面

### 4.1 HTML 结构 + CSS 基础样式
- [x] 创建 `app/static/index.html` — 完整单页应用框架
  - HTML 骨架: header / main / footer
  - CSS 变量定义:
    ```css
    :root {
      --color-primary: #C84032;    /* 朱红 */
      --color-bg: #F8F7F5;
      --color-surface: #FFFFFF;
      --color-text: #1A1A1A;
      --color-muted: #6B7280;
      --color-border: #E5E5E5;
      --radius: 8px;
      --shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    ```
  - 响应式布局 (CSS Grid / Flexbox)
  - 深色顶栏 + 白色内容区
  - 字体: PingFang SC / system-ui
  - 基础组件样式: 按钮、输入框、卡片、Tab
- **验证**: 浏览器打开看到结构化布局（空内容）

### 4.2 项目选择器 + 新建项目
- [x] 实现 JS: 项目管理
  - 页面加载时 `GET /api/projects` 获取项目列表
  - 顶部下拉选择器切换项目
  - "新建项目"按钮 → 弹出输入框 → `POST /api/projects`
  - 项目详情显示: 名称、已收录字数、创建时间
  - "删除项目"按钮 → 确认后 `DELETE /api/projects/{id}`
  - 切换项目时重新加载所有数据
- **验证**: 新建项目 → 下拉选择器更新 → 详情显示正确

### 4.3 扫描件上传区域
- [x] 实现拖拽上传 UI
  - 两个上传区域并排: "批量上传扫描件" + "上传单字"
  - 拖拽时高亮边框 (dragover/dragleave 事件)
  - 支持点击选择文件
  - 扫描件上传区: 文件类型限制 PNG/JPG/PDF
  - 切割模式选择: 单选按钮 ○自动 ○网格
  - 网格模式下显示列数/行数输入框（带默认值）
  - 上传进度条（大文件时显示）
- [x] 上传后调用 `POST /api/projects/{id}/scans`
  - 解析 UploadResponse
  - 自动切换到"待标注" Tab
  - Toast 提示 "切割完成，共 N 个字"
- **验证**: 拖拽上传一张图片 → 显示切割结果

### 4.4 单字上传区域
- [x] 实现单字上传
  - 文件选择 + 标准汉字输入框
  - 输入验证: 只接受单个 CJK 字符
  - 上传后调用 `POST /api/projects/{id}/characters`
  - 上传成功后自动刷新"已确认"列表
  - 重复字警告（已存在时确认覆盖）
- **验证**: 上传单字 + 输入"黃" → 已确认列表更新

### 4.5 字符网格 — 待标注 Tab
- [x] 实现待标注网格
  - `GET /api/projects/{id}/segments` 获取数据
  - CSS Grid 布局: `auto-fill, minmax(140px, 1fr)`
  - 每张卡片:
    - segment 图片 (1024px 显示为 ~120px)
    - OCR Top-3 候选按钮（点击即填入输入框）
    - 形近字提示（小字显示）
    - 文本输入框（可直接输入标准字）
    - "确认"按钮
    - "删除"按钮（误检时删除）
  - 卡片 hover 放大效果
  - 空状态: "暂无待标注字，请先上传扫描件"
- **验证**: 上传扫描件后，待标注网格显示所有 segment

### 4.6 字符网格 — 已确认 Tab
- [x] 实现已确认网格
  - `GET /api/projects/{id}/characters` 获取数据
  - 卡片显示: 字符图片 + 标注字
  - 每张卡片有"删除"按钮（取消确认）
  - Tab 切换时显示数量: "待标注 (5)" / "已确认 (14)"
- **验证**: 确认几个字后，已确认 Tab 显示正确

### 4.7 切割修正 UI（核心交互）
- [ ] 实现切割修正模式
  - 待标注 Tab 顶部添加"修正切割"按钮
  - 进入修正模式后:
    - 显示原图叠加切割框的可视化（`GET /scans/{scan_id}/overlay`）
    - 切割框可拖拽调整大小/位置
    - 支持框选多个 segment → 工具栏出现"合并"按钮
    - 单个 segment 可点击"分裂"（横向/纵向二分）
    - "删除选中"按钮
  - 修正操作调用 `PUT /segments/adjust`
  - 操作完成后刷新 segments 列表
  - 退出修正模式回到正常标注视图
- **验证**: 合并两个 segment → 刷新后显示合并结果

### 4.8 标注交互优化
- [ ] 实现快捷标注
  - 输入框按 Enter 确认
  - 确认后自动聚焦下一张卡片的输入框
  - OCR 候选按钮点击即确认（不需要额外点击"确认"）
  - 批量确认: 如果连续多个字的 OCR 候选都准确，支持一键全部确认
  - 键盘快捷键: ←→ 切换卡片, Enter 确认, Delete 删除
- **验证**: 连续标注 10 个字，体验流畅

### 4.9 前端 @font-face 实时预览
- [ ] 实现字体预览面板
  - 预览输入框: 用户输入任意文字
  - 字号选择器: 24/36/48/72/96px
  - 点击"生成预览"按钮 → `POST /generate` → 获取字体文件 URL
  - 动态创建 `@font-face`:
    ```javascript
    const fontUrl = `/api/projects/${id}/preview-font`;
    const style = document.createElement('style');
    style.textContent = `
      @font-face {
        font-family: 'PreviewFont';
        src: url('${fontUrl}');
      }
      .preview-text {
        font-family: 'PreviewFont', serif;
      }
    `;
    document.head.appendChild(style);
    ```
  - 预览区域实时渲染
  - 未收录字: 灰色显示 + tooltip "该字未收录"
- **验证**: 生成字体后，预览区显示手写字体效果

### 4.10 生成 + 下载按钮
- [ ] 实现生成和下载
  - "生成字体"按钮 → `POST /generate` → loading 状态 → 完成提示
  - 生成成功后"下载 TTF"按钮变为可用
  - 点击下载 → 浏览器下载 TTF 文件
  - 安装提示: "双击下载的 .ttf 文件即可安装"
- **验证**: 生成 → 下载 → macOS 安装 → 编辑器测试

---

## Phase 5: 联调测试

### 5.1 完整流程测试
- [ ] 创建项目
- [ ] 上传扫描件（自动切割模式）
- [ ] 修正切割错误（合并/分裂/删除）
- [ ] 逐字标注（使用 OCR 候选加速）
- [ ] 上传补充单字
- [ ] 生成字体
- [ ] 前端预览确认
- [ ] 下载安装验证

### 5.2 网格切割模式测试
- [ ] 上传标准字帖
- [ ] 选择网格模式（如 10×8）
- [ ] 验证切割对齐
- [ ] 标注并生成字体

### 5.3 字体质量验证
- [ ] 检查字形无锯齿（Bézier 曲线生效）
- [ ] 检查多轮廓字（如"口"、"日"）渲染正确
- [ ] 检查等宽排列（字宽一致）
- [ ] 检查 baseline 对齐（无上下飘）
- [ ] 检查未收录字 fallback（显示系统字体）

### 5.4 边界情况处理
- [ ] 大文件上传（>10MB PDF）
- [ ] 非 CJK 字符输入（验证拒绝或警告）
- [ ] 重复字覆盖确认
- [ ] 空项目生成字体（提示至少需要 1 个字）

### 5.5 项目恢复测试
- [ ] 标注到一半关闭浏览器
- [ ] 重新打开 → 加载项目 → 验证 meta.json 状态完整
- [ ] 验证 segments 和 chars 数据一致

### 5.6 启动脚本 + 文档
- [ ] 确认 `run.py` 正常启动
- [ ] 确认 `requirements.txt` 完整
- [ ] 项目目录清理（删除临时测试数据）
