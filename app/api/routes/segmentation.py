"""切割和分段 API 路由"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.api.models import (
    ConfirmRequest,
    SegmentAdjustAction,
    SegmentAdjustRequest,
    SegmentOut,
    UploadResponse,
)
from app.config import PROJECTS_DIR
from app.services.grid_cutter import grid_segment
from app.services.ocr import batch_ocr_hints, get_ocr_hints
from app.services.project_service import get_project, update_meta
from app.services.segmenter import auto_segment

router = APIRouter(prefix="/api/projects/{project_id}", tags=["segmentation"])


def _save_segment_image(image, project_id: str, segment_id: str) -> str:
    """保存切割图片"""
    segments_dir = PROJECTS_DIR / project_id / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{segment_id}.png"
    filepath = segments_dir / filename
    image.save(filepath, "PNG")

    return f"/api/projects/{project_id}/segments/{segment_id}/image"


@router.post("/scans", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_scan(
    project_id: str,
    file: UploadFile = File(...),
    mode: str = Form("auto"),
    cols: Optional[int] = Form(None),
    rows: Optional[int] = Form(None),
) -> UploadResponse:
    """上传扫描件并切割"""
    # 验证项目存在
    project = get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 {project_id} 不存在",
        )

    # 读取文件
    image_bytes = await file.read()

    # 处理 PDF
    if file.filename and file.filename.lower().endswith(".pdf"):
        try:
            import fitz

            doc = fitz.open(stream=image_bytes, filetype="pdf")
            page = doc[0]  # 只取第一页
            pix = page.get_pixmap(dpi=300)
            img_data = pix.tobytes("png")
            image_bytes = img_data
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"PDF 处理失败: {str(e)}",
            )

    # 生成扫描 ID
    scan_id = f"scan_{uuid.uuid4().hex[:8].upper()}"

    # 切割
    if mode == "grid":
        if cols is None or rows is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="网格模式需要指定 cols 和 rows",
            )

        segments_data = grid_segment(image_bytes, cols, rows)
    else:  # auto
        segments_data = auto_segment(image_bytes)

    # 保存切割片段
    segments_meta = []
    segment_index = 0

    for seg_data in segments_data:
        seg_id = f"seg_{segment_index:04d}"
        image_url = _save_segment_image(seg_data["image"], project_id, seg_id)

        # OCR 识别
        import io

        img_bytes = io.BytesIO()
        seg_data["image"].save(img_bytes, format="PNG")
        ocr_result = get_ocr_hints(img_bytes.getvalue())

        segment_meta = {
            "id": seg_id,
            "bbox": seg_data["bbox"],
            "status": "pending",
            "label": None,
            "ocr_candidates": ocr_result["candidates"],
            "image_url": image_url,
            "created_at": datetime.now().isoformat(),
            "scan_id": scan_id,
        }

        segments_meta.append(segment_meta)
        segment_index += 1

    # 更新项目元数据
    meta = get_project(project_id)
    meta["segments"].extend(segments_meta)
    meta["scan_history"].append(
        {
            "scan_id": scan_id,
            "mode": mode,
            "segments_count": len(segments_meta),
            "created_at": datetime.now().isoformat(),
        }
    )

    update_meta(project_id, meta)

    return UploadResponse(
        segments_count=len(segments_meta), scan_id=scan_id, mode=mode  # type: ignore
    )


@router.get("/segments", response_model=list[SegmentOut])
async def list_segments(project_id: str) -> list[SegmentOut]:
    """获取所有切割片段"""
    project = get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 {project_id} 不存在",
        )

    segments = project.get("segments", [])
    return [
        SegmentOut(
            id=s["id"],
            bbox=s["bbox"],
            status=s["status"],
            label=s.get("label"),
            ocr_candidates=s.get("ocr_candidates", []),
            image_url=s["image_url"],
            created_at=datetime.fromisoformat(s["created_at"]),
        )
        for s in segments
        if s["status"] != "deleted"
    ]


@router.delete("/segments/{segment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_segment(project_id: str, segment_id: str) -> None:
    """删除切割片段"""
    project = get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 {project_id} 不存在",
        )

    # 删除图片文件
    segments_dir = PROJECTS_DIR / project_id / "segments"
    segment_file = segments_dir / f"{segment_id}.png"
    if segment_file.exists():
        segment_file.unlink()

    # 更新元数据
    segments = project.get("segments", [])
    for seg in segments:
        if seg["id"] == segment_id:
            seg["status"] = "deleted"
            break

    update_meta(project_id, {"segments": segments})


@router.get("/segments/{segment_id}/image")
async def get_segment_image(project_id: str, segment_id: str):
    """获取切割片段图片"""
    from fastapi.responses import FileResponse

    segment_file = PROJECTS_DIR / project_id / "segments" / f"{segment_id}.png"
    if not segment_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"片段 {segment_id} 不存在",
        )

    return FileResponse(segment_file, media_type="image/png")


@router.put("/segments/adjust")
async def adjust_segments(project_id: str, request: SegmentAdjustRequest) -> dict:
    """调整切割片段"""
    project = get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 {project_id} 不存在",
        )

    # TODO: 实现合并、分裂、移动、调整大小
    # 这里暂时返回成功，实际实现需要读取原图并重新切割

    return {"status": "ok", "message": "调整功能待实现"}


@router.post("/segments/{segment_id}/confirm", status_code=status.HTTP_200_OK)
async def confirm_segment(project_id: str, segment_id: str, data: ConfirmRequest) -> dict:
    """确认切割片段为字符"""
    project = get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 {project_id} 不存在",
        )

    # 验证标签是单个 CJK 字符
    label = data.label
    if len(label) != 1 or not (0x4E00 <= ord(label) <= 0x9FFF):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="标签必须是单个 CJK 字符",
        )

    # 检查是否已存在
    unicode_hex = f"{ord(label):04X}"
    chars_dir = PROJECTS_DIR / project_id / "chars"
    char_file = chars_dir / f"{unicode_hex}.png"

    if char_file.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"字符 {label} 已存在",
        )

    # 移动图片
    segments_dir = PROJECTS_DIR / project_id / "segments"
    segment_file = segments_dir / f"{segment_id}.png"

    if not segment_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"片段 {segment_id} 不存在",
        )

    chars_dir.mkdir(parents=True, exist_ok=True)
    segment_file.rename(char_file)

    # 更新元数据
    segments = project.get("segments", [])
    for seg in segments:
        if seg["id"] == segment_id:
            seg["status"] = "confirmed"
            seg["label"] = label
            seg["confirmed_at"] = datetime.now().isoformat()
            break

    confirmed_chars = project.get("confirmed_chars", [])
    confirmed_chars.append(label)

    update_meta(project_id, {"segments": segments, "confirmed_chars": confirmed_chars})

    return {"status": "ok", "label": label}


@router.post("/scans/{scan_id}/overlay")
async def get_scan_overlay(project_id: str, scan_id: str):
    """获取扫描件叠加切割框的可视化图"""
    # TODO: 实现叠加可视化
    return {"status": "ok", "message": "叠加可视化功能待实现"}
