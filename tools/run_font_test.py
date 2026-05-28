import base64
import io
import os
import sys

from app.services.font_builder import build_font_from_data
from fontTools.ttLib import TTFont

ROOT = r"d:/autotextdesign"
chars = ['上','内','玉','经','黄']

glyphs = []
for ch in chars:
    p = os.path.join(ROOT, f"{ch}.png")
    if not os.path.exists(p):
        print(f"ERROR: file not found: {p}")
        sys.exit(2)
    with open(p, 'rb') as f:
        b = f.read()
    glyphs.append({"char": ch, "image_base64": base64.b64encode(b).decode('ascii')})

try:
    font_bytes = build_font_from_data(glyphs, "ATDTest")
except Exception as e:
    print("ERROR: build_font_from_data failed:", e)
    raise

# inspect
tt = TTFont(io.BytesIO(font_bytes))
out_lines = []
for ch in chars:
    name = f"uni{ord(ch):04X}"
    # advanceWidth
    try:
        advance = tt['hmtx'][name][0]
    except KeyError:
        advance = None
    glyf = tt['glyf'][name]
    glyfset = tt.getGlyphSet()
    try:
        coords, _ = glyf.getCoordinates(glyfset)
        xs = [pt[0] for pt in coords]
        if xs:
            xMin = min(xs)
            xMax = max(xs)
        else:
            xMin = 0
            xMax = 0
    except Exception:
        xMin = getattr(glyf, 'xMin', 0) or 0
        xMax = getattr(glyf, 'xMax', 0) or 0

    left = xMin
    right = (advance - xMax) if (advance is not None) else None
    tol = 3
    left_ok = abs(left - 30) <= tol if left is not None else False
    right_ok = abs(right - 30) <= tol if right is not None else False
    out_lines.append((name, xMin, xMax, advance, left, right, left_ok, right_ok))

for t in out_lines:
    name, xMin, xMax, advance, left, right, left_ok, right_ok = t
    print(f"{name}\t{xMin}\t{xMax}\t{advance}\t{left}\t{right}\tleft≈30:{left_ok}\tright≈30:{right_ok}")

# also write ttf to disk for inspection
with open(os.path.join(ROOT, 'out_test.ttf'), 'wb') as f:
    f.write(font_bytes)

print('DONE')
