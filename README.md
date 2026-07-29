# 书法字体制作器

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Online Demo](https://img.shields.io/badge/在线体验-font.chathappy.cn-B8433A)](https://font.chathappy.cn)

把手写或书法单字图片自动去噪、裁剪和矢量化，一键生成可安装的 TTF 字体。无需注册，服务器不保存项目数据。

**在线体验：<https://font.chathappy.cn>**

## 为什么做这个工具

手写体 OCR 很难稳定识别，复杂的自动切割也不一定符合真实素材。这个项目采用更可靠的流程：

> 用户负责确认汉字，程序负责图像处理和字体生成。

保持人工可控，也不引入账号、数据库或云端项目存储。

## 功能

- **批量上传**：支持拖拽、多选和粘贴 PNG、JPG、WebP、BMP 图片。
- **文件名识别**：`永.png` 会自动预填为“永”，可一键批量收录。
- **四种预处理方式**：自动判断、扫描稿、手机拍照、纹理纸张。
- **实时预览**：自定义字体与系统楷体并排对照。
- **本地自动保存**：使用 IndexedDB 保存进度，刷新后自动恢复。
- **无损项目备份**：导出、导入 `.atd.json` 项目文件。
- **继续编辑 TTF**：可导入已有 TTF 字体，提取其中的中文字符继续制作。
- **一键导出**：生成标准 TTF 文件，可直接安装到系统。

## 使用流程

1. 将单字图片命名为对应汉字，例如 `永.png`、`和.jpg`。
2. 批量拖入页面，等待处理进度完成。
3. 点击“按文件名全部收录”，重复字或未识别项单独确认。
4. 在预览区检查字体效果。
5. 下载 TTF，并导出 `.atd.json` 项目文件作为无损备份。

> 项目进度只保存在当前浏览器。清理浏览器数据或更换设备前，请先导出项目文件。

## 图片处理方式

| 方式 | 适用素材 |
|---|---|
| 自动判断 | 不确定素材类型时优先尝试 |
| 扫描稿 | 白底、背景干净的扫描图片 |
| 手机拍照 | 光照不均或带轻微纸张背景 |
| 纹理纸张 | 噪点、纸纹较明显的图片 |

## 本地运行

需要 Python 3.11 或更高版本。

```bash
git clone https://github.com/Claud-Lu/autotextdesign.git
cd autotextdesign

python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```

打开 <http://127.0.0.1:8000>。

## 开发与测试

```bash
python -m pip install -r requirements-dev.txt
ruff check .
pytest
```

## 桌面版

推送 `v*` 标签后，GitHub Actions 会生成以下安装包并发布到
[Releases](https://github.com/Claud-Lu/autotextdesign/releases)：

- macOS Apple Silicon
- macOS Intel
- Windows x86_64

本地 macOS 打包：

```bash
./build.sh
```

## 技术架构

- 后端：FastAPI、Pillow、NumPy、SciPy、scikit-image
- 字体：fontTools
- 前端：原生 HTML、CSS、JavaScript
- 本地存储：IndexedDB
- 桌面封装：pywebview、PyInstaller

后端保持无状态，只负责图片预处理、字体预览、TTF 导入和生成。公开 API 对上传体积、图片像素、字形总量、请求频率和 CPU 并发设置了边界。

## 隐私

- 不需要注册或登录。
- 服务端不保存上传图片、项目文件或生成字体。
- 项目自动保存仅发生在用户自己的浏览器中。

## 参与贡献

欢迎提交 Issue 和 Pull Request。开发约定见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

[MIT](LICENSE) © Claud-Lu
