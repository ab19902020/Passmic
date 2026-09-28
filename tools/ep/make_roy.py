"""Roy Keane's walk cycle: his sheet (cut by cut_roy.py) has no walk, so his
head from the turnaround goes on Gary's black-clad walking drawings.

    python3 tools/ep/make_roy.py   -> series/ep01/characters/roy/body/walk_*.png (+ index.json entries)

Gary's head is removed above his collar and Roy's head (the three-quarter view,
mirrored to face the way the body walks) is set on in its place, scaled to
Gary's head width with the beard over the collar.
"""
import json, os, sys
import cv2, numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EP = os.path.join(ROOT, 'series', 'ep01')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import face_rig as F

WALKS = ['walk_1', 'walk_2', 'walk_3', 'walk_3b', 'walk_4']     # Gary's, facing right


def gary_img(gidx, panel, name):
    hi = os.path.join(EP, 'characters_x16', 'gary', panel, name + '.png')
    return cv2.imread(hi if os.path.exists(hi) else os.path.join(EP, gidx[panel][name]['file']), cv2.IMREAD_UNCHANGED)


def clean_bits(rgba, frac=0.01, crop=True):
    """Drop stray specks not joined to the drawing (and crop to it)."""
    n, cc, st, _ = cv2.connectedComponentsWithStats((rgba[..., 3] > 20).astype(np.uint8), connectivity=8)
    if n > 2:
        big = st[1:, cv2.CC_STAT_AREA].max()
        for i in range(1, n):
            if st[i, cv2.CC_STAT_AREA] < frac * big:
                rgba[cc == i, 3] = 0
    if not crop:
        return rgba
    ys, xs = np.nonzero(rgba[..., 3])
    return rgba[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def roy_head(ridx):
    """Roy's head and beard from the three-quarter turnaround, facing right."""
    a = cv2.imread(os.path.join(EP, ridx['turnaround']['three_quarter_left']['file']), cv2.IMREAD_UNCHANGED)
    info = F.find_face(a, head_frac=0.35)
    fx0, fy0, fx1, fy1 = info['box']
    fw = fx1 - fx0
    w = (a[..., 3] > 128).sum(1)
    shoulders = int(np.argmax(w > 2.5 * np.median(w[20:int(fy0 + fw * 0.5)])))
    # head, beard, neck and his black collar down onto the shoulders: the collar lands on
    # Gary's black jacket, so the join is black on black; it fades out downwards and sideways
    H, W = a.shape[:2]
    y1 = min(H, int(shoulders + 0.3 * fw))
    x0, x1 = max(0, int(fx0 - 0.6 * fw)), min(W, int(fx1 + 0.6 * fw))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    keep = np.clip((y1 - yy) / (0.22 * fw), 0, 1)
    cx = (fx0 + fx1) / 2
    side = np.clip((0.75 * fw - np.abs(xx - cx)) / (0.3 * fw), 0, 1)
    low = np.clip((yy - (shoulders - 0.05 * fw)) / (0.15 * fw), 0, 1)     # the neck stays whole
    keep *= 1 - low * (1 - side)
    keep[:, :x0] = 0
    keep[:, x1:] = 0
    head = a.copy()
    head[..., 3] = (a[..., 3] * keep).astype(np.uint8)
    head = clean_bits(head)[:, ::-1].copy()                  # face right, like the walks
    return head, F.find_face(head)


def head_width(rgba, info):
    """Width of the head (ears included) at eye level."""
    ey = int(np.mean([e[1] for e in info['eyes']])) if info['eyes'] else int((info['box'][1] + info['box'][3]) / 2)
    cx = int((info['box'][0] + info['box'][2]) / 2)
    row = rgba[ey, :, 3] > 100
    x0 = cx
    while x0 > 0 and row[x0 - 1]:
        x0 -= 1
    x1 = cx
    while x1 < len(row) - 1 and row[x1 + 1]:
        x1 += 1
    return x1 - x0, ey


def gary_head_region(rgba, info):
    """Gary's head (hair, face, ears) above his collar, not the jacket beside it."""
    H, W = rgba.shape[:2]
    fx0, fy0, fx1, fy1 = info['box']
    fw = fx1 - fx0
    m = np.zeros((H, W), bool)
    m[:int(fy1 - fw * 0.3), max(0, int(fx0 - fw * 0.35)):min(W, int(fx1 + fw * 0.35))] = True
    m[:int(fy1 + fw * 0.02), max(0, int(fx0)):int(fx1)] = True
    m &= rgba[..., 3] > 0
    L = F.lab(rgba[..., :3])
    cloth = (L[..., 0] < 22) & (np.hypot(L[..., 1], L[..., 2]) < 9)
    cloth[:int(fy1 - fw * 0.35)] = False
    k = max(3, int(fw * 0.07))
    cloth = cv2.morphologyEx(cloth.astype(np.uint8), cv2.MORPH_OPEN, np.ones((k, k), np.uint8)) > 0
    return m & ~cloth


def build():
    gidx = json.load(open(os.path.join(EP, 'characters', 'gary', 'index.json')))
    ridx = json.load(open(os.path.join(EP, 'characters', 'roy', 'index.json')))
    head, hinfo = roy_head(ridx)
    hfx0, _, hfx1, hfy1 = hinfo['box']
    hhw, hey = head_width(head, hinfo)
    # scale from a walk drawing whose head is clear of the arms, carried to the others by Gary's face width
    g2 = gary_img(gidx, 'body', 'walk_2')
    i2 = F.find_face(g2, head_frac=0.35)
    s = head_width(g2, i2)[0] * 1.05 / max(hhw, 1)           # all the walks are drawn at one size
    hys = np.nonzero(head[..., 3] > 128)[0]
    h_top = hys.min()
    for name in WALKS:
        g = gary_img(gidx, 'body', name)
        info = F.find_face(g, head_frac=0.35)
        fx0, fy0, fx1, fy1 = info['box']
        body = g.copy()
        body[gary_head_region(g, info), 3] = 0
        body = clean_bits(body, 0.02, crop=False)
        dx = dy = 0
        hd = cv2.resize(head, None, fx=s, fy=s, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
        # the top of Roy's hair at the top of Gary's, face centres lined up
        g_top = np.nonzero((g[:, int(fx0):int(fx1), 3] > 128).any(1))[0].min()
        top = int(g_top - h_top * s) - dy
        left = int((fx0 + fx1) / 2 - (hfx0 + hfx1) / 2 * s) - dx
        body_full = body
        padT, padL = max(0, -(top + dy)), max(0, -(left + dx))
        padR = max(0, left + dx + hd.shape[1] - g.shape[1])
        canvas = cv2.copyMakeBorder(body_full, padT, 0, padL, padR, cv2.BORDER_CONSTANT, value=0)
        # Roy's black collar only where Gary's jacket is (no dark haze round the beard)
        hx, hy = left + dx + padL, top + dy + padT
        hd = hd.copy()
        L = F.lab(hd[..., :3])
        hh, hw = hd.shape[:2]
        under = np.zeros((hh, hw), np.float32)
        ya, xa = max(0, hy), max(0, hx)
        yb, xb = min(canvas.shape[0], hy + hh), min(canvas.shape[1], hx + hw)
        under[ya - hy:yb - hy, xa - hx:xb - hx] = canvas[ya:yb, xa:xb, 3] / 255.0
        chin = int(F.find_face(hd)['box'][3])
        # his shirt: large dark areas (the beard's ink lines are thin and don't survive the opening)
        kk = max(5, int(0.05 * (hinfo['box'][2] - hinfo['box'][0]) * s)) | 1
        cloth = cv2.morphologyEx((L[..., 0] < 30).astype(np.uint8), cv2.MORPH_OPEN,
                                 cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kk, kk)))
        cloth |= ((hd[..., 3] > 0) & (hd[..., 3] < 250) & (L[..., 0] < 45)).astype(np.uint8)   # its faded edge
        cloth = cv2.dilate(cloth, np.ones((5, 5), np.uint8))
        dark = cloth.astype(np.float32)
        dark[:chin] = 0
        hd[..., 3] = (hd[..., 3] * (1 - dark * (1 - under))).astype(np.uint8)
        # and off the jacket, only the solid head and beard: no faint leftover sheet lines
        n, cc = cv2.connectedComponents((hd[..., 3] > 200).astype(np.uint8), connectivity=8)
        fb = hinfo['box']
        fc = cc[int((fb[1] + fb[3]) / 2 * s), int((fb[0] + fb[2]) / 2 * s)] if n > 1 else 0
        solid = cv2.dilate((cc == fc).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32) if fc else 1.0
        stray = np.zeros((hh, hw), np.float32)
        stray[chin:] = 1
        hd[..., 3] = (hd[..., 3] * (1 - stray * (1 - np.maximum(solid, under)))).astype(np.uint8)
        F.paste_over(canvas, hd, hx, hy)
        canvas = clean_bits(canvas)
        rel = os.path.join('characters', 'roy', 'body', name + '.png')
        cv2.imwrite(os.path.join(EP, rel), canvas, [cv2.IMWRITE_PNG_COMPRESSION, 6])
        ridx['body'][name] = dict(file=rel, size=[canvas.shape[1], canvas.shape[0]], body='gary/body/' + name, cut={})
        print(name, canvas.shape)
    with open(os.path.join(EP, 'characters', 'roy', 'index.json'), 'w') as f:
        json.dump(ridx, f, indent=1)


if __name__ == '__main__':
    build()
