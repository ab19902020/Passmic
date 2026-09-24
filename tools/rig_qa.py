# Rig QA: python3 tools/rig_qa.py <out.jpg> <sprite> [<sprite> ...]
# Each drawing with both arms at -0.35 / 0 / +0.35 (the renderer's compose_body), head on, grey background.
import os, sys, cv2, numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'render')); ARGS = sys.argv[1:]
import render as R
rows = []
for n in ARGS[1:]:
    spr = R.SPR[n]; row = []
    for up in (-0.35, 0.0, 0.35):
        img, ol, rim = R.compose_body(spr, {'aL': up, 'aR': up})
        H, W = img.shape[:2]; fr = np.full((H + 40, W + 40, 3), (150, 150, 158), np.float32)
        M = R.aff(1, 1, 0, 0, 0, 20, 20)
        R.draw_sprite(fr, ol, M, 1.0, W + 40, H + 40); R.draw_sprite(fr, img, M, 1.0, W + 40, H + 40)
        R.draw_sprite(fr, spr['head_ol'], M, 1.0, W + 40, H + 40); R.draw_sprite(fr, spr['head'], M, 1.0, W + 40, H + 40)
        s = 620 / fr.shape[0]; row.append(cv2.resize(fr.astype(np.uint8), None, fx=s, fy=s, interpolation=cv2.INTER_AREA))
    rows.append(np.hstack(row))
w = max(r.shape[1] for r in rows)
cv2.imwrite(ARGS[0], np.vstack([cv2.copyMakeBorder(r, 0, 4, 0, w - r.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for r in rows]))
