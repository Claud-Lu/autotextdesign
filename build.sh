#!/usr/bin/env bash
set -euo pipefail

echo "=== 书法字体制作器 - 本地打包 ==="

if [[ ! -d ".venv" ]]; then
    python3.11 -m venv .venv
fi

source .venv/bin/activate
python -m pip install -r requirements.txt pywebview pyinstaller
pyinstaller calligraphy.spec --noconfirm --clean

echo "=== 打包完成：dist/书法字体制作器.app ==="
