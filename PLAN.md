# 书法字体制作器 — 实现计划书

## 背景

用户有手写楷书扫描件（PDF/图片），希望做成可安装的电脑字体（TTF）。核心难点是手写体 OCR 准确率低，因此做一个 Web 工具：**用户负责认字标注，机器负责图像处理和字体生成**。

> 本质定位：**半自动字体制作工具（human-in-the-loop）**，关键不是算法多强，而是让用户改起来轻松。

## 技术方案

| 层 | 选型 | 理由 |
|---|---|---|
| 前端 | 单页 HTML + 内联 CSS/JS | 无需构建工具，FastAPI 直接托管 |
| 后端 | FastAPI v0.121.2 | 已安装，异步支持，自动 API 文档 |
| 字体生成 | fontTools 4.60.2 + scikit-image 0.24.0 | 已安装，已有现成脚本 `build_font.py` 验证可行 |
| 轮廓拟合 | Potrace (potrace) 或 spline 贝塞尔拟合 | 解决直线 polygon 导致的锯齿问题 |
| 图像切割 | OpenCV 4.12.0 + scipy 1.13.1 | 已安装，已有 `extract_glyphs.py` 验证可行 |
| PDF 处理 | PyMuPDF 1.26.5 | 已安装 |
| OCR 辅助 | Tesseract 5.5.2（chi_sim/chi_tra） | 已安装，提供 Top-3 候选 + 形近字提示 |
| 数据存储 | 本地文件系统（JSON + 目录） | 单用户桌面工具，无需数据库 |

## 核心工作流

```
用户创建项目（输入字体名称）
        ↓
上传扫描件（PNG/JPG/PDF）
        ↓ 后端自动切割成单字
        ↓ 展示网格供用户标注
        ↓ 用户可手动修正切割错误（拖动/分裂/合并/删除）
        ↓
用户输入标准汉字（参考 OCR Top-3 候选 + 形近字提示）→ 确认
        ↓
点击"生成字体" → 后端：轮廓平滑 → Bézier 拟合 → 多轮廓处理 → 打包 TTF
        ↓
前端 @font-face 实时预览 → 下载安装
```

## 项目结构

```
字体/
├── app/
│   ├── main.py                  # FastAPI 应用入口
│   ├── config.py                # 配置常量（路径、阈值、字体参数）
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── projects.py      # 项目 CRUD
│   │   │   ├── characters.py    # 单字上传/确认/删除
│   │   │   ├── segmentation.py  # 扫描件上传 + 自动切割 + 手动修正
│   │   │   └── font.py          # 字体生成 + 下载
│   │   └── models.py            # Pydantic 请求/响应 schema
│   ├── services/
│   │   ├── __init__.py
│   │   ├── segmenter.py         # 图像切割（复用 extract_glyphs.py 逻辑）
│   │   ├── grid_cutter.py       # 网格切割模式（固定行列切格子）
│   │   ├── preprocessor.py      # 单字预处理（裁剪/居中/归一化为1024×1024）
│   │   ├── font_builder.py      # TTF 生成（复用 build_font.py 逻辑）
│   │   ├── contour_fitter.py    # 轮廓平滑 + Bézier 曲线拟合 + 多轮廓合并
│   │   └── ocr.py               # Tesseract OCR 提示服务（Top-3 + 形近字）
│   └── static/
│       └── index.html           # 单页应用（HTML + CSS + JS 全内联）
│
├── data/                        # 运行时数据（gitignore）
│   └── projects/
│       └── {project_id}/
│           ├── meta.json             # 项目元信息（单一真相源，含状态快照）
│           ├── scans/                # 原始上传的扫描件
│           │   └── {uuid}.png
│           ├── segments/             # 自动切割、待用户标注
│           │   └── {uuid}.png
│           ├── chars/                # 已确认字符（以 Unicode 编码命名）
│           │   └── {unicode_hex}.png # 例: 9EC3.png = 黃 (U+9EC3)
│           └── generated/            # 生成的 TTF 文件
│               └── {font_name}.ttf
│
├── extract_glyphs.py            # [已有] 图像切割脚本（参考复用）
├── build_font.py                # [已有] 字体生成脚本（参考复用）
├── requirements.txt
├── run.py                       # uvicorn 启动脚本
└── PLAN.md                      # 本文件
```

## API 端点设计

### 项目管理
| 方法 | 路径 | 功能 | 请求体 |
|------|------|------|--------|
| POST | /api/projects | 创建项目 | `{ "name": "我的楷书" }` |
| GET | /api/projects | 列出所有项目 | — |
| GET | /api/projects/{id} | 获取项目详情 | — |
| DELETE | /api/projects/{id} | 删除项目 | — |

### 扫描件切割
| 方法 | 路径 | 功能 | 请求体 |
|------|------|------|--------|
| POST | /api/projects/{id}/scans | 上传扫描件→自动切割 | multipart: file + mode(auto\|grid) + cols + rows |
| GET | /api/projects/{id}/segments | 列出待标注字（含 bbox 坐标） | — |
| DELETE | /api/projects/{id}/segments/{sid} | 删除错误切割 | — |
| PUT | /api/projects/{id}/segments/adjust | 手动修正切割（合并/分裂/调整框） | `{ "actions": [{"type": "merge\|split\|move\|resize", "ids": [...], "bbox": [...]}] }` |
| POST | /api/projects/{id}/segments/{sid}/confirm | 确认字符 | `{ "label": "黃" }` |

### 单字管理
| 方法 | 路径 | 功能 | 请求体 |
|------|------|------|--------|
| POST | /api/projects/{id}/characters | 直接上传单字 | multipart: file + label |
| GET | /api/projects/{id}/characters | 列出已确认字符 | — |
| DELETE | /api/projects/{id}/characters/{char} | 删除已确认字符 | — |

### 字体生成
| 方法 | 路径 | 功能 | 请求体 |
|------|------|------|--------|
| POST | /api/projects/{id}/generate | 生成 TTF | `{ "font_name": "我的楷书" }`(可选) |
| GET | /api/projects/{id}/download | 下载字体文件 | — |

### 辅助
| 方法 | 路径 | 功能 | 请求体 |
|------|------|------|--------|
| POST | /api/ocr/hint | OCR Top-3 候选 + 形近字提示 | multipart: file + lang |

## 前端界面设计

### 整体布局
```
┌──────────────────────────────────────────────────────┐
│  书法字体制作器              [项目选择 ▼]  [+ 新建]    │
├──────────────────────────────────────────────────────┤
│  项目名: 我的楷书字体              已收录: 14 字       │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │ 批量上传扫描件    │  │ 上传单字                  │  │
│  │ 拖拽或点击上传    │  │ 拖拽或点击上传图片         │  │
│  │ 支持 PNG/JPG/PDF │  │ 标准汉字: [________]     │  │
│  │ 切割模式: ○自动 ○网格 │                          │  │
│  │ [列数: 10] [行数: 8]│                          │  │
│  └──────────────────┘  └──────────────────────────┘  │
│                                                      │
│  [待标注 (5)]  [已确认 (14)]                           │
│                                                      │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐            │
│  │ img │ │ img │ │ img │ │ img │ │ img │            │
│  │1.黃 │ │2.庭 │ │     │ │  ✓  │ │  ✓  │            │
│  │3.堂 │ │ 形近:│ │[确认]│ │ 黃  │ │ 庭  │            │
│  │[确认]│ │堂塟│ │[删除]│ │[编辑]│ │[编辑]│            │
│  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘            │
│                                                      │
│  [合并选中] [分裂] [删除选中]                          │
│                                                      │
├──────────────────────────────────────────────────────┤
│  预览文字: [请在此输入预览文字__________]  字号: [48]px │
│  ┌──────────────────────────────────────────────┐    │
│  │  黄 庭 内 景 玉 经                            │    │
│  │  (前端 @font-face 实时渲染)                    │    │
│  └──────────────────────────────────────────────┘    │
├──────────────────────────────────────────────────────┤
│  [生成字体]                          [下载 TTF]       │
└──────────────────────────────────────────────────────┘
```

### 交互细节
- **拖拽上传**：扫描件和单字均支持拖拽，拖入时高亮边框
- **切割模式选择**：
  - **自动模式**：连通域分析（适合不规则排列）
  - **网格模式**：用户指定行列数，均匀切格子（适合标准字帖，比连通域稳定）
- **手动修正切割**（核心交互，必须做到极致）：
  - 框选多个 segment → 点击"合并"
  - 单个 segment → 点击"分裂"（横向/纵向二分）
  - 拖动边框调整裁剪范围
  - 选中后点击"删除"
  - 原图叠加切割框可视化，方便定位
- **OCR 提示增强**：
  - 待标注卡片显示 Top-3 OCR 候选，点击即填入
  - 显示形近字提示（降低输入成本）
  - 用户可直接输入或从候选中选取
- **确认流程**：点击候选字或输入后按 Enter，卡片移到"已确认"
- **重复字处理**：如果标注的字已存在，弹出确认是否替换
- **前端实时预览**：生成字体后，通过 `@font-face` 加载，前端直接用 CSS 渲染预览文字，无需后端参与
- **字符覆盖提示**：预览区显示已收录字数，未收录字用 fallback 系统字体渲染并灰色标注

### 样式方向
- 深色顶栏 + 白色内容区
- 主色调：朱红 (#C84032) 或靛蓝 (#4361EE)
- 字体：PingFang SC / Microsoft YaHei
- 卡片：圆角 8px，微阴影，hover 放大
- 响应式网格：CSS Grid `auto-fill, minmax(140px, 1fr)`
- 切割修正时：显示原图半透明叠加层 + 可拖拽切割框

## 字体生成管线（增强版）

```
已确认字符图片 (1024×1024 灰度 PNG)
        ↓
二值化处理 (Otsu 阈值)
        ↓
轮廓平滑 (Gaussian blur, σ=1.0)          ← 新增：消除锯齿
        ↓
轮廓追踪 (scikit-image measure.find_contours)
        ↓
多轮廓处理                                ← 新增：内外轮廓分离
  ├── 外轮廓：字形主体
  ├── 内轮廓（孔洞）：如"口"字的内部空间
  └── 多轮廓合并：确保同一字形的所有轮廓正确组合
        ↓
Bézier 曲线拟合                            ← 替换：直线 polygon → 曲线
  ├── Potrace 管线 或
  ├── fontTools.pens + spline 拟合 或
  └── 自实现贝塞尔控制点计算
        ↓
坐标映射: 像素 → 字体单位 (×1000/1024, Y轴翻转)
        ↓
fontTools FontBuilder 构建:
  ├── glyphOrder:  [.notdef, uniXXXX, ...]
  ├── characterMap: {ord(char): glyph_name}
  ├── glyf:         {glyph_name: Glyph} (含多轮廓 + Bézier 曲线)
  ├── hmtx:         {glyph_name: (advance_width, lsb)}
  ├── hhea:         ascent=880, descent=-120
  ├── OS/2:         CJK 度量参数
  ├── name:         字体名/族名/样式名
  ├── head:         unitsPerEm=1000
  └── post:         格式 3.0
        ↓
输出 .ttf 文件
```

### CJK 字体度量参数
```python
UNITS_PER_EM = 1000
ASCENT = 880
DESCENT = -120
TYPICAL_ASCENDER = 880
TYPICAL_DESCENDER = -120
WIN_ASCENT = 1000
WIN_DESCENT = 200
CONTOUR_TOLERANCE = 2.0
GLYPH_SIZE = 1024  # 预处理后字符图尺寸
```

### advance_width 计算（等宽模式）
```python
# 书法字体推荐统一等宽，避免字宽抖动
advance_width = UNITS_PER_EM  # 固定 1000
# 左侧边距 = (UNITS_PER_EM - 字形实际宽度) / 2，实现视觉居中
```

### baseline 对齐（新增）
```python
# 所有字形必须对齐 baseline
# 将字形垂直定位在 baseline 之上
# 确保字体渲染时不出现上下飘动
# 底部留 descent 空间（如某些笔画下伸时使用）
```

### 未收录字符 fallback 策略
```python
# 已收录字符 → 使用本字体渲染
# 未收录字符 → 回退到系统默认字体（.notdef glyph 显示空白）
# 前端预览时：未收录字灰色标注，提示用户"该字未收录"
```

## 图像切割管线（增强版）

```
上传扫描件 (PNG/JPG/PDF)
        ↓
PDF → PNG (PyMuPDF, 300 DPI)
        ↓
灰度转换 + Otsu 二值化
        ↓
形态学去噪 (开运算)
        ↓
┌────────────────────────────────────────┐
│ 切割模式选择（用户在上传时选择）          │
├──────────────────┬─────────────────────┤
│ 自动模式          │ 网格模式             │
├──────────────────┼─────────────────────┤
│ 连通域分析         │ 用户指定 cols × rows │
│ (scipy.ndimage)   │ 均匀切格子           │
│ ↓                 │ ↓                   │
│ 过滤小区域         │ 无需聚类             │
│ (< 30 像素)       │                     │
│ ↓                 │                     │
│ 连通域聚类:        │                     │
│ Y质心→行           │                     │
│ X质心→字          │                     │
└──────────────────┴─────────────────────┘
        ↓
提取每个字符区域:
  裁剪 → 居中填充为正方形 → 缩放到 1024×1024
        ↓
保存为待标注 segments（记录 bbox 到 meta.json）
        ↓
用户在切割修正 UI 中手动调整（合并/分裂/移动/删除）
        ↓
确认后的 segments 进入标注流程
```

## 单字预处理管线

```
上传单字图片
    ↓
转灰度 + 自动对比度增强
    ↓
Otsu 二值化
    ↓
找到墨迹边界框
    ↓
裁剪 + 10% 边距
    ↓
居中填充为正方形
    ↓
缩放到 1024×1024 (LANCZOS)
    ↓
保存为 chars/{unicode_hex}.png
```

## 项目状态管理（新增）

`meta.json` 作为单一真相源，支持项目恢复和状态一致性：

```json
{
  "name": "我的楷书",
  "created_at": "2026-04-18T10:00:00Z",
  "updated_at": "2026-04-18T12:30:00Z",
  "font_name": "我的楷书字体",
  "stats": {
    "total_segments": 25,
    "confirmed_chars": 14,
    "total_scans": 2
  },
  "segments": [
    {
      "id": "seg_0001",
      "source_scan": "scan_xxx.png",
      "bbox": [100, 200, 300, 400],
      "status": "pending",
      "label": null,
      "ocr_candidates": ["黃", "黌", "廣"],
      "created_at": "2026-04-18T10:05:00Z"
    }
  ],
  "confirmed": {
    "9EC3": {
      "segment_id": "seg_0001",
      "label": "黃",
      "confirmed_at": "2026-04-18T10:10:00Z",
      "image_path": "chars/9EC3.png"
    }
  },
  "scan_history": [
    {
      "path": "scans/scan_xxx.png",
      "mode": "auto",
      "segment_count": 15,
      "uploaded_at": "2026-04-18T10:00:00Z"
    }
  ]
}
```

**好处**：
- 崩溃后可从 meta.json 完整恢复状态
- segments 和 chars 始终同步
- 支持增量更新（新增扫描件不会丢失已有标注）

## 关键复用

| 现有文件 | 复用内容 |
|---------|---------|
| `build_font.py` | `create_glyph_from_png()` — 轮廓追踪 + 字形构建核心逻辑（需增强为 Bézier） |
| `extract_glyphs.py` | 连通域分析 + 聚类算法 → 泛化为通用 segmenter |

## 文件命名约定

- 项目 ID: `proj_` + 8 位随机 hex
- 扫描件: `{timestamp}_{random}.png`
- 待标注段: `seg_{4位序号}.png`
- 已确认字符: `{Unicode码点大写hex}.png`（例: `9EC3.png` = 黃）
- 字体文件: `{字体名}.ttf`

## 实施步骤

### Phase 1: 后端骨架 + 项目管理
- [ ] FastAPI 应用结构 + 静态文件托管
- [ ] 项目 CRUD API（创建/列表/详情/删除）
- [ ] `config.py` 配置文件
- [ ] `requirements.txt`
- [ ] meta.json 状态管理（单一真相源）

### Phase 2: 图像处理 + 切割修正 UI
- [ ] `segmenter.py` 扫描件自动切割服务（复用 extract_glyphs.py）
- [ ] `grid_cutter.py` 网格切割模式（固定行列切格子）
- [ ] `preprocessor.py` 单字预处理服务
- [ ] `ocr.py` Tesseract OCR Top-3 候选 + 形近字提示
- [ ] 扫描件上传 + 切割 API（支持 auto/grid 模式选择）
- [ ] 切割修正 API（合并/分裂/调整框/删除）
- [ ] 单字上传 API

### Phase 3: 字体生成（增强版）
- [ ] `contour_fitter.py` 轮廓平滑（Gaussian blur）+ Bézier 曲线拟合 + 多轮廓合并
- [ ] `font_builder.py` 字体生成服务（等宽 + baseline 对齐 + 未收录 fallback）
- [ ] 字符确认 API（segment → char）
- [ ] 字体生成 + 下载 API

### Phase 4: 前端界面（标注体验优先）
- [ ] HTML 结构 + CSS 样式
- [ ] 项目选择器 + 新建项目
- [ ] 拖拽上传区域（扫描件 + 单字）+ 切割模式选择
- [ ] 字符网格（待标注 / 已确认 Tab 切换）
- [ ] **切割修正 UI**（拖动/合并/分裂/删除 — 核心交互，优先打磨）
- [ ] 标注交互（OCR Top-3 候选 + 形近字 + 确认）
- [ ] **前端 @font-face 实时预览**（未收录字灰色标注）
- [ ] 生成 + 下载按钮

### Phase 5: 联调测试
- [ ] 用现有 PDF 扫描件测试完整流程
- [ ] 验证生成 TTF 可在 macOS 安装使用
- [ ] 验证 Bézier 曲线字体质量（无明显锯齿/轮廓破碎）
- [ ] 验证等宽 + baseline 对齐（排版整齐不抖动）
- [ ] 处理边界情况（大文件、非CJK字符、重复字、多轮廓字）
- [ ] 测试手动修正切割流程（合并分裂场景）
- [ ] 测试项目恢复（模拟中断后从 meta.json 恢复）

### Phase 6: 进阶优化（可选）
- [ ] 自动去背景（纸张泛黄处理、光照不均）
- [ ] 笔画粗细归一化
- [ ] 字形风格统一
- [ ] 导出 OTF 格式
- [ ] 竖排书法支持

## 启动方式

```bash
cd autotextdesign
pip install -r requirements.txt
python run.py
# 浏览器打开 http://localhost:8000
```

## 验证清单

1. 创建项目 → 输入字体名 → 确认项目列表更新
2. 上传扫描件 → 选择切割模式 → 切割结果展示 → OCR Top-3 候选显示
3. 手动修正切割 → 合并/分裂/删除 → 验证修正结果
4. 逐字标注确认（点击候选或输入）→ 已确认 Tab 更新
5. 直接上传单字 + 输入标准字 → 确认
6. 点击生成 → 无报错 → 下载按钮可用
7. 下载 TTF → macOS 双击安装 → 编辑器中输入标注过的字 → 显示正确
8. 前端 @font-face 预览 → 实时渲染 → 未收录字灰色标注
9. 验证字体质量：无明显锯齿、笔画平滑、多轮廓字（如"口"）正确渲染
10. 验证等宽排列 + baseline 对齐：排版整齐无抖动
11. 模拟中断 → 重新打开 → 从 meta.json 恢复状态 → 无数据丢失
