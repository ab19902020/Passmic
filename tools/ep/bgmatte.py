"""Foreground mattes for the studio backgrounds (the desk and what's on it).

    python3 tools/ep/bgmatte.py front_a   -> out/ep01/bg/<name>_fg.png (RGBA, 4x size)

Shapes (polygon / capsule / ellipse in 1x coords) are rasterised at 4x, then
the edges are snapped to the picture with a narrow GrabCut band, and softened.
"""
import json, os, sys
import cv2, numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EP = os.path.join(ROOT, 'series', 'ep01')
K = 4


def shape_mask(shape, H, W):
    m = np.zeros((H, W), np.uint8)
    if 'poly' in shape:
        cv2.fillPoly(m, [np.round(np.array(shape['poly']) * K).astype(np.int32)], 1)
    elif 'capsule' in shape:
        (a, b, r) = shape['capsule']
        cv2.line(m, (int(a[0] * K), int(a[1] * K)), (int(b[0] * K), int(b[1] * K)), 1, int(r * 2 * K))
        for p in (a, b):
            cv2.circle(m, (int(p[0] * K), int(p[1] * K)), int(r * K), 1, -1)
    elif 'ellipse' in shape:
        (c, ax) = shape['ellipse']
        cv2.ellipse(m, (int(c[0] * K), int(c[1] * K)), (int(ax[0] * K), int(ax[1] * K)), 0, 0, 360, 1, -1)
    return m


def build(name):
    cfg = json.load(open(os.path.join(EP, 'backgrounds', name + '.json')))
    img = cv2.imread(os.path.join(EP, 'x4', cfg['image']))
    H, W = img.shape[:2]
    fg = np.zeros((H, W), np.uint8)
    for sh in cfg['fg']:
        m = shape_mask(sh, H, W)
        if sh.get('snap', True) and sh['name'] != 'desk':
            ys, xs = np.nonzero(m)
            pad = 12
            y0, y1, x0, x1 = max(0, ys.min() - pad), min(H, ys.max() + pad), max(0, xs.min() - pad), min(W, xs.max() + pad)
            sub = m[y0:y1, x0:x1]
            k = np.ones((7, 7), np.uint8)
            tri = np.full(sub.shape, cv2.GC_BGD, np.uint8)
            tri[cv2.dilate(sub, k) > 0] = cv2.GC_PR_BGD
            tri[sub > 0] = cv2.GC_PR_FGD
            tri[cv2.erode(sub, k) > 0] = cv2.GC_FGD
            try:
                bgd, fgd = np.zeros((1, 65)), np.zeros((1, 65))
                cv2.grabCut(img[y0:y1, x0:x1], tri, None, bgd, fgd, 4, cv2.GC_INIT_WITH_MASK)
                sub = ((tri == cv2.GC_FGD) | (tri == cv2.GC_PR_FGD)).astype(np.uint8)
            except cv2.error:
                pass
            m = np.zeros_like(m)
            m[y0:y1, x0:x1] = sub
        fg |= m
    a = cv2.GaussianBlur(fg.astype(np.float32), (0, 0), 1.2)
    out = np.dstack([img, (a * 255).astype(np.uint8)])
    os.makedirs(os.path.join(ROOT, 'out', 'ep01', 'bg'), exist_ok=True)
    cv2.imwrite(os.path.join(ROOT, 'out', 'ep01', 'bg', name + '_fg.png'), out)
    print(name, 'fg matte', out.shape)


if __name__ == '__main__':
    for n in sys.argv[1:]:
        build(n)
