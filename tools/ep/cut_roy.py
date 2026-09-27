"""Cut Roy Keane's drawings out of his character sheet (sheets/roy.png).

    python3 tools/ep/cut_roy.py   -> series/ep01/characters/roy/<panel>/<name>.png + index.json

His sheet has dark and grey panels behind black clothes, so the flood-fill
cutter used for Mark and Gary can't separate him: each drawing is matted with
an AI segmentation model (rembg u2net) on the 4x-upscaled sheet, and the matte's
edge is refined against the artwork with a guided filter. The mouth-shape
cells are kept whole (they are patches of mouth, moustache and beard, pasted
over his mouth for lip sync).

The walk cycle isn't on his sheet: make_roy.py builds it (Gary's walking
drawings, black-clad like Roy, with Roy's head from this sheet).
"""
import json, os, sys
import cv2, numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EP = os.path.join(ROOT, 'series', 'ep01')
K = 4

# boxes on the 1x sheet (1536 x 1024): x0, y0, x1, y1
EXPR_X = [0, 155, 301, 453, 604, 749, 898, 1059, 1223, 1380, 1534]
EXPR_NAMES = ['neutral', 'angry', 'speaking', 'disgust', 'sarcastic', 'confused', 'annoyed', 'shouting', 'dry_humour',
              'thinking']
CELLS = {}
for i, n in enumerate(EXPR_NAMES):
    CELLS['expressions/' + n] = (EXPR_X[i] + 2, 490, EXPR_X[i + 1] - 2, 668)
CELLS['head/detail'] = (1156, 170, 1338, 434)
for n, (x0, x1) in dict(arms_crossed=(612, 747), pointing=(750, 882), open_hand=(880, 1030),
                        palm_down=(1030, 1190)).items():
    CELLS['body/' + n] = (x0, 738, x1, 968)
for n, (x0, x1) in dict(front=(0, 250), three_quarter_left=(248, 450), side_left=(450, 530), back=(528, 775),
                        side_right=(775, 872), three_quarter_right=(872, 1150)).items():
    CELLS['turnaround/' + n] = (x0, 165, x1, 434)
MOUTHS = {
    'a': (8, 739, 115, 822), 'e': (125, 739, 234, 822), 'i': (244, 739, 352, 822), 'o': (362, 739, 472, 822),
    'u': (484, 739, 593, 822),
    'cdg': (8, 870, 97, 952), 'fv': (106, 870, 197, 952), 'l': (206, 870, 297, 952), 'mbp': (308, 870, 399, 952),
    'r': (412, 870, 502, 952), 'th': (511, 870, 600, 952),
}

_SESSION = None


def guided(I, p, r, eps):
    """Guided filter (He et al.) with a grey guide: edge-aware smoothing of p along I's edges."""
    I = cv2.cvtColor(I, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
    box = lambda x: cv2.boxFilter(x, -1, (2 * r + 1, 2 * r + 1))
    mI, mp = box(I), box(p)
    cov = box(I * p) - mI * mp
    var = box(I * I) - mI * mI
    a = cov / (var + eps)
    b = mp - a * mI
    return box(a) * I + box(b)


def matte(rgb, full_body=False):
    """Soft alpha (0..1) of the figure in an RGB crop. Heads are matted at full
    resolution; for full figures (black clothes on a dark panel) the models do
    better at the sheet's own size, and u2net and isnet each lose a different
    part (a hand, the legs), so their mattes are combined."""
    global _SESSION
    from rembg import remove, new_session
    if _SESSION is None:
        _SESSION = {m: new_session(m) for m in ('u2net', 'isnet-general-use')}
    if full_body:
        small = cv2.resize(rgb, None, fx=1 / K, fy=1 / K, interpolation=cv2.INTER_AREA)
        a = np.zeros(rgb.shape[:2], np.float32)
        for m in ('u2net', 'isnet-general-use'):
            am = remove(cv2.cvtColor(small, cv2.COLOR_BGR2RGB), session=_SESSION[m], only_mask=True)
            a = np.maximum(a, cv2.resize(am, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_CUBIC) / 255.0)
        a = np.clip(a, 0, 1).astype(np.float32)
    else:
        a = remove(cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB), session=_SESSION['u2net'], only_mask=True)
        a = a.astype(np.float32) / 255
    # snap the edge to the artwork
    g = guided(rgb, a, max(2, rgb.shape[0] // 150), 1e-3)
    a = np.clip((np.clip(g, 0, 1) - 0.15) / 0.7, 0, 1)
    # the figure only: the biggest piece plus pieces close to it
    hard = (a > 0.5).astype(np.uint8)
    n, cc, st, _ = cv2.connectedComponentsWithStats(hard, connectivity=8)
    if n > 2:
        big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        keep = np.zeros_like(hard)
        near = cv2.dilate((cc == big).astype(np.uint8), np.ones((25, 25), np.uint8))
        for i in range(1, n):
            if i == big or ((near > 0) & (cc == i)).any() and st[i, cv2.CC_STAT_AREA] > 0.002 * st[big, cv2.CC_STAT_AREA]:
                keep[cc == i] = 1
        a *= cv2.dilate(keep, np.ones((5, 5), np.uint8)).astype(np.float32)
    return a


def rgba_of(rgb, a):
    out = np.dstack([rgb, (a * 255).astype(np.uint8)])
    ys, xs = np.nonzero(a > 0.02)
    return out[ys.min():ys.max() + 1, xs.min():xs.max() + 1], (int(xs.min()), int(ys.min()))


def main():
    sheet = cv2.imread(os.path.join(EP, 'x4', 'roy.png'))
    cdir = os.path.join(EP, 'characters', 'roy')
    index = {}

    def save(key, rgba, rect):
        panel, name = key.split('/')
        rel = os.path.join('characters', 'roy', panel, name + '.png')
        os.makedirs(os.path.join(EP, 'characters', 'roy', panel), exist_ok=True)
        cv2.imwrite(os.path.join(EP, rel), rgba, [cv2.IMWRITE_PNG_COMPRESSION, 6])
        index.setdefault(panel, {})[name] = dict(file=rel, sheet_rect_x4=[int(v) for v in rect],
                                                 size=[rgba.shape[1], rgba.shape[0]], cut={})
        print(key, rgba.shape, flush=True)

    for key, (x0, y0, x1, y1) in CELLS.items():
        rgb = sheet[y0 * K:y1 * K, x0 * K:x1 * K]
        rgba, (ox, oy) = rgba_of(rgb, matte(rgb, full_body=key.split('/')[0] in ('body', 'turnaround')))
        save(key, rgba, (x0 * K + ox, y0 * K + oy, rgba.shape[1], rgba.shape[0]))
    for n, (x0, y0, x1, y1) in MOUTHS.items():
        rgb = sheet[(y0 + 2) * K:(y1 - 2) * K, (x0 + 2) * K:(x1 - 2) * K]
        save('mouths/' + n, np.dstack([rgb, np.full(rgb.shape[:2], 255, np.uint8)]),
             ((x0 + 2) * K, (y0 + 2) * K, rgb.shape[1], rgb.shape[0]))
    with open(os.path.join(cdir, 'index.json'), 'w') as f:
        json.dump(index, f, indent=1)


if __name__ == '__main__':
    main()
