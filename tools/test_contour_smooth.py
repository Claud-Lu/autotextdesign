from PIL import Image
import numpy as np
from skimage import filters
from app.services.contour_fitter import contours_to_glyph

print('Loading image 啊.jpg')
img = Image.open('啊.jpg').convert('L')
arr = np.array(img)
thr = filters.threshold_otsu(arr)
# ink darker => True
binarr = arr < thr
print('Binary shape', binarr.shape)
res = contours_to_glyph(binarr)
print('result is None?', res is None)
if res:
    print('outer counts:', [len(r) for r in res['outer']])
    print('inner counts:', [len(r) for r in res['inner']])
else:
    print('No contours found')
