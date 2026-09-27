"""Cut every drawing out of a (4x-upscaled) character sheet.

    python3 tools/ep/cut_sheet.py mark [gary ...]
    -> series/ep01/characters/<name>/<panel>/<label>.png  (RGBA, 4x resolution) + index.json

The sheets are outlined cartoon art on a light panel. For each band in
series/ep01/sheets/layout.json:
  1. background = light pixels connected to the band's border (flood fill),
     so white eyes, teeth and highlights inside the outlines stay drawing;
  2. the band is split into its drawings at the emptiest columns near evenly
     spaced guesses (drawings that touch - busts, heads - are split there);
  3. each drawing keeps its main blob plus nearby pieces, holes filled, and
     gets a 1-px feathered edge (the ink outline hides any fringe).
"""
import json, os, sys
import cv2, numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EP = os.path.join(ROOT, 'series', 'ep01')
K = 4          # upscale factor of the x4 sheets


def lab(bgr):
    return cv2.cvtColor(bgr.astype(np.float32) / 255, cv2.COLOR_BGR2LAB)


def background_mask(crop, tol=9.0):
    """Light, low-contrast pixels connected to the crop border."""
    L = lab(crop)
    border = np.concatenate([L[0], L[-1], L[:, 0], L[:, -1]])
    bgc = np.median(border, axis=0)
    near = np.linalg.norm(L - bgc, axis=2) < tol
    # the panel shading drifts a little: also accept very light low-chroma pixels
    near |= (L[..., 0] > 90) & (np.hypot(L[..., 1], L[..., 2]) < 6)
    n, cc = cv2.connectedComponents(near.astype(np.uint8), connectivity=4)
    edge = np.unique(np.concatenate([cc[0], cc[-1], cc[:, 0], cc[:, -1]]))
    bg = np.isin(cc, edge[edge > 0])
    return bg


def split_columns(fg, n):
    """n-1 split columns at the emptiest spots near evenly spaced guesses."""
    W = fg.shape[1]
    prof = cv2.GaussianBlur(fg.sum(0).astype(np.float32).reshape(1, -1), (0, 0), 3).ravel()
    cuts = []
    for i in range(1, n):
        g = W * i / n
        lo, hi = int(g - W / n * 0.35), int(g + W / n * 0.35)
        j = lo + int(np.argmin(prof[lo:hi]))
        cuts.append(j)
    return [0] + cuts + [W]


def fill_holes(m):
    h, w = m.shape
    ff = np.pad(m.astype(np.uint8), 1)
    mask = np.zeros((h + 4, w + 4), np.uint8)
    cv2.floodFill(ff, mask, (0, 0), 2)
    return ff[1:-1, 1:-1] != 2


def cut_band(img, box, labels):
    x0, y0, x1, y1 = [v * K for v in box]
    crop = img[y0:y1, x0:x1]
    bg = background_mask(crop)
    fg = ~bg
    fg = cv2.morphologyEx(fg.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
    cols = split_columns(fg, len(labels))
    out = []
    for i, name in enumerate(labels):
        a, b = cols[i], cols[i + 1]
        part = np.zeros_like(fg)
        part[:, a:b] = fg[:, a:b]
        n, cc, st, _ = cv2.connectedComponentsWithStats(part.astype(np.uint8), connectivity=8)
        if n < 2:
            continue
        big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        keep = cc == big
        # nearby detached pieces (a hand, a mic) belong to this drawing too
        near = cv2.dilate(keep.astype(np.uint8), np.ones((K * 10, K * 10), np.uint8)) > 0
        for j in range(1, n):
            if j != big and st[j, cv2.CC_STAT_AREA] > 40 * K * K and (near & (cc == j)).any():
                keep |= cc == j
        keep = fill_holes(keep) & ~(bg & ~fill_holes(keep))
        alpha = cv2.GaussianBlur(keep.astype(np.float32), (0, 0), 0.7)
        alpha[keep] = np.maximum(alpha[keep], 0.5)
        ys, xs = np.nonzero(alpha > 0.02)
        ya, yb, xa, xb = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        rgba = np.dstack([crop[ya:yb, xa:xb], (alpha[ya:yb, xa:xb] * 255).astype(np.uint8)])
        rgba[rgba[..., 3] == 0, :3] = 0
        # which edges were cut by the band / split (a bust cropped at the bottom etc.)
        cut = dict(bottom=bool(yb >= crop.shape[0] - 2), left=bool(xa <= a + 1 and a > 0),
                   right=bool(xb >= b - 1 and b < crop.shape[1]))
        out.append((name, rgba, [int(x0 + xa), int(y0 + ya), int(xb - xa), int(yb - ya)], cut))
    return out


def run(char):
    lay = json.load(open(os.path.join(EP, 'sheets', 'layout.json')))[char]
    img = cv2.imread(os.path.join(EP, 'x4', lay['sheet']))
    index = {}
    for band in lay['bands']:
        for name, rgba, rect, cut in cut_band(img, band['box'], band['labels']):
            rel = os.path.join('characters', char, band['panel'], name + '.png')
            os.makedirs(os.path.dirname(os.path.join(EP, rel)), exist_ok=True)
            cv2.imwrite(os.path.join(EP, rel), rgba, [cv2.IMWRITE_PNG_COMPRESSION, 6])
            index.setdefault(band['panel'], {})[name] = dict(file=rel, sheet_rect_x4=rect, size=[rgba.shape[1], rgba.shape[0]],
                                                             cut=cut)
    with open(os.path.join(EP, 'characters', char, 'index.json'), 'w') as f:
        json.dump(index, f, indent=1)
    print(char, sum(len(v) for v in index.values()), 'drawings')


if __name__ == '__main__':
    for c in sys.argv[1:]:
        run(c)
