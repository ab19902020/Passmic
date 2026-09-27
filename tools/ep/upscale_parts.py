"""Second 4x AI pass (16x the original sheets) for the drawings seen large:
expressions, heads, busts and standing/walking bodies of Mark and Gary, and
Roy's head.

    python3 tools/ep/upscale_parts.py      -> series/ep01/characters_x16/<char>/<panel>/<name>.png

The RGB is re-upscaled from the x4 sheet (with its own background around the
drawing, so edges don't pick up a dark fringe); the alpha is upscaled with a
smooth filter and re-sharpened. Resumable: existing outputs are skipped.
"""
import json, os, sys
import cv2, numpy as np
from realesrgan_ncnn_py import Realesrgan

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EP = os.path.join(ROOT, 'series', 'ep01')


def up_alpha(a, k=4):
    big = cv2.resize(a.astype(np.float32) / 255, None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC)
    big = cv2.GaussianBlur(big, (0, 0), 1.0)
    big = np.clip((big - 0.5) * 2.5 + 0.5, 0, 1)
    return (big * 255).astype(np.uint8)


def main():
    r = Realesrgan(gpuid=-1, model=3, tilesize=256)
    jobs = []
    for panels in (('head', 'expressions'), ('upper', 'body')):
        for ch in ('gary', 'mark'):
            idx = json.load(open(os.path.join(EP, 'characters', ch, 'index.json')))
            sheet = cv2.imread(os.path.join(EP, 'x4', ch + '.png'))
            for panel in panels:
                for name, s in idx[panel].items():
                    if ch == 'mark' and panel == 'body' and not name.startswith('stand'):
                        continue            # Mark never walks
                    jobs.append((ch, panel, name, s, sheet))
    for ch, panel, name, s, sheet in jobs:
        out = os.path.join(EP, 'characters_x16', ch, panel, name + '.png')
        if os.path.exists(out):
            continue
        x, y, w, h = s['sheet_rect_x4']
        rgba = cv2.imread(os.path.join(EP, s['file']), cv2.IMREAD_UNCHANGED)
        rgb = sheet[y:y + h, x:x + w]
        big = r.process_cv2(np.ascontiguousarray(rgb))
        a = up_alpha(rgba[..., 3], big.shape[0] // h)
        a = cv2.resize(a, (big.shape[1], big.shape[0]))
        res = np.dstack([big, a])
        res[a == 0, :3] = 0
        os.makedirs(os.path.dirname(out), exist_ok=True)
        cv2.imwrite(out, res, [cv2.IMWRITE_PNG_COMPRESSION, 4])
        print(out, res.shape, flush=True)
    # Roy's head from the production sheet
    out = os.path.join(EP, 'characters_x16', 'roy', 'head', 'three_quarter.png')
    if not os.path.exists(out):
        im = cv2.imread(os.path.join(EP, 'characters', 'roy', 'src', 'sheet_c_x4.png'))
        m = (cv2.imread(os.path.join(EP, 'characters', 'roy', 'src', 'head_mask.png'), 0) > 127).astype(np.uint8) * 255
        ys, xs = np.nonzero(m)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        big = r.process_cv2(np.ascontiguousarray(im[y0:y1, x0:x1]))
        a = cv2.resize(up_alpha(cv2.GaussianBlur(m[y0:y1, x0:x1], (0, 0), 1.2), 4), (big.shape[1], big.shape[0]))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        cv2.imwrite(out, np.dstack([big, a]))
        print(out, flush=True)


if __name__ == '__main__':
    main()
