"""项目管理 API 路由"""
from fastapi import APIRouter, HTTPException, status

from app.api.models import ProjectCreate, ProjectOut
from app.services.project_service import (
    create_project,
    delete_project,
    get_project,
    list_projects,
    update_meta,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_new_project(data: ProjectCreate) -> ProjectOut:
    """创建新项目"""
    try:
        meta = create_project(data.name)
        return ProjectOut(**meta)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建项目失败: {str(e)}",
        )


@router.get("", response_model=list[ProjectOut])
async def get_all_projects() -> list[ProjectOut]:
    """获取所有项目列表"""
    try:
        projects = list_projects()
        return [ProjectOut(**p) for p in projects]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取项目列表失败: {str(e)}",
        )


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project_detail(project_id: str) -> ProjectOut:
    """获取项目详情"""
    meta = get_project(project_id)
    if not meta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 {project_id} 不存在",
        )

    # 计算统计信息
    from pathlib import Path

    from app.config import PROJECTS_DIR

    segments_dir = PROJECTS_DIR / project_id / "segments"
    chars_dir = PROJECTS_DIR / project_id / "chars"

    total_segments = (
        len([f for f in segments_dir.glob("seg_*.png") if f.is_file()])
        if segments_dir.exists()
        else 0
    )
    confirmed_chars = (
        len([f for f in chars_dir.glob("*.png") if f.is_file()]) if chars_dir.exists() else 0
    )

    meta["stats"] = {
        "total_segments": total_segments,
        "confirmed_chars": confirmed_chars,
    }

    return ProjectOut(**meta)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_endpoint(project_id: str) -> None:
    """删除项目"""
    success = delete_project(project_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 {project_id} 不存在",
        )
