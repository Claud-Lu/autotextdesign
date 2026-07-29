# 参与贡献

感谢你帮助改进书法字体制作器。

## 开发环境

项目要求 Python 3.11 或更高版本：

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

## 提交修改前

```bash
ruff check .
pytest
```

涉及图片处理或字体轮廓的改动，请同时增加最小回归测试，并说明使用的素材类型。请勿把含有隐私或版权风险的真实手写素材提交到仓库。

## Issue 与 Pull Request

- Bug 请提供浏览器、系统、素材类型、处理方式和可复现步骤。
- 新功能优先保持无账号、无数据库、用户可控的轻量路线。
- Pull Request 请聚焦单一问题，并清楚说明行为变化和验证结果。
