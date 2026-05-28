import io
import os
from fontTools.ttLib import TTFont

ROOT = r"d:/autotextdesign"
ttf_path = os.path.join(ROOT, 'out_test.ttf')
if not os.path.exists(ttf_path):
    print('ERROR: out_test.ttf not found')
    raise SystemExit(2)

tt = TTFont(ttf_path)
chars = ['上','内','玉','经','黄']
lines = []
for ch in chars:
    name = f"uni{ord(ch):04X}"
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
    lines.append(f"{name}\t{xMin}\t{xMax}\t{advance}\t{left}\t{right}")

out_file = os.path.join('tools','font_metrics.txt')
with open(out_file,'w',encoding='utf-8') as f:
    f.write('\n'.join(lines))
print('WROTE', out_file)
