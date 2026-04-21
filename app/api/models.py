"""API 数据结构定义"""
from typing import Optional

from pydantic import BaseModel, Field


class PreprocessRequest(BaseModel):
    """预处理请求"""
    pass  # 图片通过 multipart form 上传


class PreprocessResponse(BaseModel):
    """预处理响应"""
    image_base64: str


class GlyphInput(BaseModel):
    """单个字形输入"""
    char: str = Field(..., min_length=1, max_length=1, description="标准汉字")
    image_base64: str = Field(..., description="处理后图片的 base64 编码（不含前缀）")


class GenerateRequest(BaseModel):
    """字体生成请求"""
    glyphs: list[GlyphInput]
    font_name: str = "未命名字体"


class ImportResponse(BaseModel):
    """TTF 导入响应"""
    glyphs: list[GlyphInput]
    font_name: str
