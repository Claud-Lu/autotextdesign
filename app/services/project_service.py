"""项目管理服务"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Final, Optional

from app.config import PROJECTS_DIR


# 项目元数据结构
# {
#   "id": "proj_XXXXXXXX",
#   "name": "项目名称",
#   "created_at": "2024-01-01T00:00:00",
#   "updated_at": "2024-01-01T00:00:00",
#   "segments": [],
#   "confirmed_chars": [],
#   "scan_history": []
# }


def _generate_project_id() -> str:
    """生成项目ID"""
    return f"proj_{uuid.uuid4().hex[:8].upper()}"


def create_project(name: str) -> dict:
    """创建项目"""
    project_id = _generate_project_id()
    project_dir = PROJECTS_DIR / project_id

    # 创建项目目录结构
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "segments").mkdir(exist_ok=True)
    (project_dir / "chars").mkdir(exist_ok=True)

    # 初始化元数据
    meta = {
        "id": project_id,
        "name": name,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "segments": [],
        "confirmed_chars": [],
        "scan_history": [],
        "stats": {
            "total_segments": 0,
            "confirmed_chars": 0,
        },
    }

    # 保存元数据
    with open(project_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return meta


def get_project(project_id: str) -> Optional[dict]:
    """获取项目详情"""
    project_dir = PROJECTS_DIR / project_id
    if not project_dir.exists():
        return None

    with open(project_dir / "meta.json", "r", encoding="utf-8") as f:
        return json.load(f)


def list_projects() -> list[dict]:
    """列出所有项目"""
    projects = []
    for project_dir in PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue

        meta_path = project_dir / "meta.json"
        if not meta_path.exists():
            continue

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        # 计算统计信息
        segments_dir = project_dir / "segments"
        chars_dir = project_dir / "chars"

        total_segments = len([f for f in segments_dir.glob("seg_*.png") if f.is_file()])
        confirmed_chars = len([f for f in chars_dir.glob("*.png") if f.is_file()])

        meta["stats"] = {
            "total_segments": total_segments,
            "confirmed_chars": confirmed_chars,
        }

        projects.append(meta)

    return projects


def delete_project(project_id: str) -> bool:
    """删除项目"""
    project_dir = PROJECTS_DIR / project_id
    if not project_dir.exists():
        return False

    # 递归删除整个目录
    import shutil

    shutil.rmtree(project_dir)
    return True


def update_meta(project_id: str, updates: dict) -> Optional[dict]:
    """更新项目元数据"""
    project_dir = PROJECTS_DIR / project_id
    if not project_dir.exists():
        return None

    # 读取现有元数据
    with open(project_dir / "meta.json", "r", encoding="utf-8") as f:
        meta = json.load(f)

    # 更新字段
    meta.update(updates)
    meta["updated_at"] = datetime.now().isoformat()

    # 保存
    with open(project_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return meta
