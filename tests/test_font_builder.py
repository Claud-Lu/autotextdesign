import io

from fontTools.ttLib import TTFont

from app.services.font_builder import build_font_from_data
from app.services.font_importer import import_ttf


def test_build_font_contains_requested_glyph(image_base64: str) -> None:
    font_bytes = build_font_from_data(
        [{"char": "永", "image_base64": image_base64}],
        "测试字体",
    )

    font = TTFont(io.BytesIO(font_bytes))
    try:
        assert font.getBestCmap()[ord("永")] == "uni6C38"
        family_names = {
            record.toUnicode()
            for record in font["name"].names
            if record.nameID == 1
        }
        assert "测试字体" in family_names
    finally:
        font.close()


def test_build_font_rejects_empty_glyph() -> None:
    try:
        build_font_from_data([], "测试字体")
    except ValueError as exc:
        assert "没有有效的字符数据" in str(exc)
    else:
        raise AssertionError("empty glyph list should be rejected")


def test_generated_font_can_be_reimported(image_base64: str) -> None:
    font_bytes = build_font_from_data(
        [{"char": "永", "image_base64": image_base64}],
        "测试字体",
    )

    imported = import_ttf(font_bytes)

    assert imported["font_name"] == "测试字体"
    assert [glyph["char"] for glyph in imported["glyphs"]] == ["永"]
    assert imported["glyphs"][0]["image_base64"]
