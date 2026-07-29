"""API 数据结构定义"""
import base64
import binascii

from pydantic import BaseModel, Field, field_validator, model_validator

from app.config import (
    MAX_FONT_NAME_LENGTH,
    MAX_GLYPH_BASE64_CHARS,
    MAX_GLYPHS,
    MAX_TOTAL_GLYPH_BASE64_CHARS,
)


class PreprocessResponse(BaseModel):
    """预处理响应"""
    image_base64: str


class GlyphInput(BaseModel):
    """单个字形输入"""
    char: str = Field(..., min_length=1, max_length=1, description="标准汉字")
    image_base64: str = Field(
        ...,
        min_length=16,
        max_length=MAX_GLYPH_BASE64_CHARS,
        description="处理后图片的 base64 编码（不含前缀）",
    )

    @field_validator("char")
    @classmethod
    def validate_cjk_character(cls, value: str) -> str:
        codepoint = ord(value)
        if not (
            0x3400 <= codepoint <= 0x4DBF
            or 0x4E00 <= codepoint <= 0x9FFF
            or 0xF900 <= codepoint <= 0xFAFF
        ):
            raise ValueError("仅支持单个汉字")
        return value

    @field_validator("image_base64")
    @classmethod
    def validate_image_base64(cls, value: str) -> str:
        try:
            base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("字形图片不是有效的 base64 数据") from exc
        return value


class GenerateRequest(BaseModel):
    """字体生成请求"""
    glyphs: list[GlyphInput] = Field(..., min_length=1, max_length=MAX_GLYPHS)
    font_name: str = Field(
        default="未命名字体",
        min_length=1,
        max_length=MAX_FONT_NAME_LENGTH,
    )

    @field_validator("font_name")
    @classmethod
    def normalize_font_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("字体名称不能为空")
        return normalized

    @model_validator(mode="after")
    def validate_glyph_collection(self) -> "GenerateRequest":
        chars = [glyph.char for glyph in self.glyphs]
        if len(chars) != len(set(chars)):
            raise ValueError("字形列表包含重复汉字")
        if sum(len(glyph.image_base64) for glyph in self.glyphs) > MAX_TOTAL_GLYPH_BASE64_CHARS:
            raise ValueError("字形数据总量过大")
        return self


class ImportResponse(BaseModel):
    """TTF 导入响应"""
    glyphs: list[GlyphInput]
    font_name: str
