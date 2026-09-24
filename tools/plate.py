import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
ASSETS = _os.path.join(ROOT, 'assets'); MASKS = _os.path.join(ROOT, 'masks'); DATA = _os.path.join(ROOT, 'data'); SOURCE = _os.path.join(ROOT, 'source'); OUTDIR = _os.path.join(ROOT, 'out'); TOOLS = _os.path.join(ROOT, 'tools')
# Builds the empty studio backdrop (assets/plate_rows.png) from 18306 by removing the three pundits.
# The hole is filled with LaMa (learned inpainting, runs offline on CPU):
#   pip install simple-lama-inpainting   (then restore: pip install "numpy>=2"; pip uninstall opencv-python;
#                                          pip install --force-reinstall --no-deps opencv-contrib-python)
# LaMa is run at half resolution (it fills large holes with structure there), then refined at full
# resolution so the filled area has the same sharpness as the rest of the painting.
import cv2, numpy as np
from PIL import Image
from simple_lama_inpainting import SimpleLama
img = cv2.imread(SOURCE + '/18306.png')
H, W = img.shape[:2]
hole = np.zeros((H, W), np.uint8)
for n in ['carra1', 'nev1', 'keane1']: hole |= cv2.imread(f'{MASKS}/maskc_{n}.png', 0)
# the source masks miss a hand or two and the pundits' dark shadows on the floor: add skin-coloured and very
# dark pixels that touch the pundits (the beers on the side table are kept)
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
near = cv2.dilate(hole, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (81, 81))) > 0
skin = (hsv[..., 0] >= 5) & (hsv[..., 0] <= 22) & (hsv[..., 1] > 70) & (hsv[..., 2] > 150)
dark = (hsv[..., 2] < 45)
dark[:760] = False                                            # shadows only on the floor
cand = ((skin | dark) & near).astype(np.uint8); cand[640:820, :660] = 0   # beers on the side table
n_, lab, st, _ = cv2.connectedComponentsWithStats(cand, 8)
touch = set(np.unique(lab[(cv2.dilate(hole, np.ones((9, 9), np.uint8)) > 0) & (lab > 0)]))
for i in range(1, n_):
    if i in touch and st[i, 4] > 120: hole[lab == i] = 255
cv2.fillPoly(hole, [np.array([(640, 800), (1700, 800), (1760, 1254), (560, 1254)], np.int32)], 255)  # their floor shadows
hole = cv2.morphologyEx(hole, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25)))
hole = cv2.dilate(hole, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)))   # outlines, glow and shadows too
lama = SimpleLama()
def fill(bgr, m):
    out = lama(Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)), Image.fromarray(m))
    return cv2.cvtColor(np.array(out), cv2.COLOR_RGB2BGR)[:bgr.shape[0], :bgr.shape[1]]
half = fill(cv2.resize(img, (W // 2, H // 2), interpolation=cv2.INTER_AREA), cv2.resize(hole, (W // 2, H // 2), interpolation=cv2.INTER_NEAREST))
coarse = img.copy(); up = cv2.resize(half, (W, H), interpolation=cv2.INTER_CUBIC)
coarse[hole > 0] = up[hole > 0]
fine = fill(coarse, hole)                                                           # full-res refinement pass
hf = cv2.GaussianBlur((hole > 0).astype(np.float32), (0, 0), 3)[..., None]
out = (img * (1 - hf) + fine * hf).astype(np.uint8)
cv2.imwrite(ASSETS + '/plate_rows.png', out)
cv2.imwrite(ASSETS + '/hole.png', hole)
print('wrote assets/plate_rows.png')
