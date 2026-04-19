"""API 数据结构定义"""
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


# ========== 项目相关 ==========
class ProjectCreate(BaseModel):
    """创建项目请求"""
    name: str = Field(..., min_length=1, max_length=100, description="项目名称")


class ProjectStats(BaseModel):
    """项目统计信息"""
    total_segments: int = 0
    confirmed_chars: int = 0


class ProjectOut(BaseModel):
    """项目输出"""
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    stats: ProjectStats


# ========== 切割相关 ==========
class SegmentOut(BaseModel):
    """切割片段输出"""
    id: str
    bbox: list[int]  # [x0, y0, x1, y1]
    status: Literal["pending", "confirmed", "deleted"]
    label: Optional[str] = None
    ocr_candidates: list[str] = []
    image_url: str
    created_at: datetime


class SegmentAdjustAction(BaseModel):
    """切割修正动作"""
    type: Literal["merge", "split", "move", "resize"]
    ids: list[str] = Field(..., min_length=1)
    bbox: Optional[list[int]] = None  # 用于 move/resize


class SegmentAdjustRequest(BaseModel):
    """切割修正请求"""
    actions: list[SegmentAdjustAction]


class UploadResponse(BaseModel):
    """上传响应"""
    segments_count: int
    scan_id: str
    mode: Literal["auto", "grid"]


# ========== 字符相关 ==========
class CharacterOut(BaseModel):
    """字符输出"""
    char: str
    label: str
    image_url: str
    confirmed_at: datetime


class ConfirmRequest(BaseModel):
    """确认请求"""
    label: str = Field(..., min_length=1, max_length=1, description="标准汉字")


# ========== 字体生成相关 ==========
class FontGenerateRequest(BaseModel):
    """字体生成请求"""
    font_name: Optional[str] = None  # 默认使用项目名


# ========== OCR 相关 ==========
class OcrHintResponse(BaseModel):
    """OCR 提示响应"""
    candidates: list[str] = Field(default_factory=list)
    similar: list[str] = Field(default_factory=list)
