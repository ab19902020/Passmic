"""Roy Keane stand-in: his head (from production sheet C, the only drawing of
him in the series' style) on Gary's black-clad body drawings.

    python3 tools/ep/make_roy.py   -> series/ep01/characters/roy/... + index.json

Gary's head is removed above his chin, and Roy's head is scaled to Gary's head
size (a touch broader) with the beard overlapping the collar. Roy's head
faces left in the source; it is mirrored to match each body's facing.
"""
import json, os, sys
import cv2, numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EP = os.path.join(ROOT, 'series', 'ep01')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import face_rig as F

# body drawing -> (facing of the body: 'left'/'right'/'front', head_frac for face search)
BODIES = {
    'upper/crossed_arms': ('front', 0.6),
    'upper/arms_down': ('front', 0.6),
    'body/stand_neutral': ('front', 0.35),
    'body/walk_1': ('right', 0.35), 'body/walk_2': ('right', 0.35), 'body/walk_3': ('right', 0.35),
    'body/walk_3b': ('right', 0.35), 'body/walk_4': ('right', 0.35),
    'turnaround/front': ('front', 0.35), 'turnaround/three_quarter_right': ('right', 0.35),
}


def gary_img(gidx, panel, name):
    hi = os.path.join(EP, 'characters_x16', 'gary', panel, name + '.png')
    return cv2.imread(hi if os.path.exists(hi) else os.path.join(EP, gidx[panel][name]['file']), cv2.IMREAD_UNCHANGED)


def clean_bits(rgba, frac=0.01):
    """Drop stray specks (bits of the sheet caught in a mask) not joined to the drawing."""
    n, cc, st, _ = cv2.connectedComponentsWithStats((rgba[..., 3] > 20).astype(np.uint8), connectivity=8)
    if n > 2:
        big = st[1:, cv2.CC_STAT_AREA].max()
        for i in range(1, n):
            if st[i, cv2.CC_STAT_AREA] < frac * big:
                rgba[cc == i, 3] = 0
    ys, xs = np.nonzero(rgba[..., 3])
    return rgba[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def roy_head_hi():
    hi = os.path.join(EP, 'characters_x16', 'roy', 'head', 'three_quarter.png')
    return clean_bits(cv2.imread(hi, cv2.IMREAD_UNCHANGED)) if os.path.exists(hi) else roy_head()


def roy_head():
    im = cv2.imread(os.path.join(EP, 'characters', 'roy', 'src', 'sheet_c_x4.png'))
    m = (cv2.imread(os.path.join(EP, 'characters', 'roy', 'src', 'head_mask.png'), 0) > 127).astype(np.float32)
    a = cv2.GaussianBlur(m, (0, 0), 1.2)
    a[m > 0] = np.maximum(a[m > 0], 0.6)
    ys, xs = np.nonzero(m)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    rgba = np.dstack([im[y0:y1, x0:x1], (a[y0:y1, x0:x1] * 255).astype(np.uint8)])
    return clean_bits(rgba)


def gary_head_region(rgba, info):
    """Gary's head (hair + face + ears): everything above his chin inside a
    widened face column, plus hair connected above it."""
    H, W = rgba.shape[:2]
    fx0, fy0, fx1, fy1 = info['box']
    fw = fx1 - fx0
    chin = fy1
    col0, col1 = max(0, int(fx0 - fw * 0.35)), min(W, int(fx1 + fw * 0.35))
    m = np.zeros((H, W), bool)
    m[:int(chin - fw * 0.3), col0:col1] = True             # hair and ears
    m[:int(chin + fw * 0.02), max(0, int(fx0)):int(fx1)] = True  # jaw and neck; the shoulders beside it stay
    m &= rgba[..., 3] > 0
    # but not the jacket: black cloth below the ears stays (thin outlines don't)
    L = F.lab(rgba[..., :3])
    cloth = (L[..., 0] < 22) & (np.hypot(L[..., 1], L[..., 2]) < 9)
    cloth[:int(chin - fw * 0.35)] = False
    k = max(3, int(fw * 0.07))
    cloth = cv2.morphologyEx(cloth.astype(np.uint8), cv2.MORPH_OPEN, np.ones((k, k), np.uint8)) > 0
    cloth = cv2.erode(cloth.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    return m & ~cloth, (fx0, fy0, fx1, fy1)


def build():
    gidx = json.load(open(os.path.join(EP, 'characters', 'gary', 'index.json')))
    head = roy_head()
    hH, hW = head.shape[:2]
    hhi = roy_head_hi()
    info_hi = F.find_face(hhi)
    out_idx = {}
    for key, (facing, hf) in BODIES.items():
        panel, name = key.split('/')
        g = gary_img(gidx, panel, name)
        canvas = swap_head(g, hhi, info_hi, facing, hf, 0.98 if panel == 'upper' else 1.12)
        rel = os.path.join('characters', 'roy', panel, name + '.png')
        os.makedirs(os.path.dirname(os.path.join(EP, rel)), exist_ok=True)
        cv2.imwrite(os.path.join(EP, rel), canvas, [cv2.IMWRITE_PNG_COMPRESSION, 6])
        out_idx.setdefault(panel, {})[name] = dict(file=rel, size=[canvas.shape[1], canvas.shape[0]], body='gary/' + key,
                                                   cut=gidx[panel][name].get('cut', {}))
    rel = os.path.join('characters', 'roy', 'head', 'three_quarter.png')
    os.makedirs(os.path.dirname(os.path.join(EP, rel)), exist_ok=True)
    cv2.imwrite(os.path.join(EP, rel), head)
    out_idx.setdefault('head', {})['three_quarter'] = dict(file=rel, size=[hW, hH], cut={})
    with open(os.path.join(EP, 'characters', 'roy', 'index.json'), 'w') as f:
        json.dump(out_idx, f, indent=1)
    print('roy', sum(len(v) for v in out_idx.values()), 'drawings')


def swap_head(g, head, info_h, facing, hf, factor):
    """Gary's drawing `g` with his head replaced by Roy's."""
    hH, hW = head.shape[:2]
    rfx0, rfy0, rfx1, rfy1 = info_h['box']
    info = F.find_face(g, head_frac=hf)
    region, (fx0, fy0, fx1, fy1) = gary_head_region(g, info)
    body = g.copy()
    body[region, 3] = 0
    n, cc, st, _ = cv2.connectedComponentsWithStats((body[..., 3] > 20).astype(np.uint8), connectivity=8)
    if n > 2:
        keep = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        for i in range(1, n):
            if i != keep and st[i, cv2.CC_STAT_AREA] < 0.02 * st[keep, cv2.CC_STAT_AREA]:
                body[cc == i, 3] = 0
    # scale Roy's face width to Gary's face width (x1.12: Roy is broader)
    s = (fx1 - fx0) * factor / max(rfx1 - rfx0, 1)
    hd = cv2.resize(head, None, fx=s, fy=s, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
    if facing == 'right':
        hd = hd[:, ::-1].copy()
        rcx = (hW - (rfx0 + rfx1) / 2) * s
    else:
        rcx = (rfx0 + rfx1) / 2 * s
    # beard bottom a little below Gary's chin
    top = int(fy1 + (fx1 - fx0) * 0.30 - hd.shape[0])
    left = int((fx0 + fx1) / 2 - rcx)
    # canvas big enough for the head
    padT = max(0, -top)
    padL, padR = max(0, -left), max(0, left + hd.shape[1] - body.shape[1])
    canvas = cv2.copyMakeBorder(body, padT, 0, padL, padR, cv2.BORDER_CONSTANT, value=0)
    F.paste_over(canvas, hd, left + padL, top + padT)
    return clean_bits(canvas)


def row_span(rgba, y):
    xs = np.nonzero(rgba[int(y), :, 3] > 128)[0]
    return (int(xs.min()), int(xs.max())) if len(xs) else (0, 0)


def crossed_standing(stand, bust):
    """Gary standing with his arms folded: the crossed-arms bust scaled to the
    standing body's shoulders and set at its chin, the hanging sleeves and
    fists below the bust erased, and the bust's cut-off elbows rounded."""
    fs = F.find_face(stand, head_frac=0.35)
    fb = F.find_face(bust, head_frac=0.6)
    sw = fs['box'][2] - fs['box'][0]
    bw = fb['box'][2] - fb['box'][0]
    s0, s1 = row_span(stand, fs['box'][3] + 0.3 * sw)
    b0, b1 = row_span(bust, fb['box'][3] + 0.3 * bw)
    k = (s1 - s0) / (b1 - b0)
    b = bust.copy()
    region, _ = gary_head_region(b, fb)
    b[region, 3] = 0
    b = cv2.resize(b, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    bh, bwid = b.shape[:2]
    ox = int((s0 + s1) / 2 - (b0 + b1) / 2 * k)
    oy = int(fs['box'][3] - fb['box'][3] * k)
    bottom = oy + bh
    # the torso column: the trousers' width just below the jacket
    H, W = stand.shape[:2]
    widths = [(y, *row_span(stand, y)) for y in range(bottom, H)]
    top_leg = next((y, x0, x1) for y, x0, x1 in widths if x1 - x0 < 0.62 * (s1 - s0) * 1.25)
    _, t0, t1 = top_leg
    pad = int((t1 - t0) * 0.03)
    # round the bust's cut-off bottom into the torso, and fade its last rows into the jacket below
    yy, xx = np.mgrid[0:bh, 0:bwid]
    cx = (t0 + t1) / 2 - ox
    rx = max(bwid - cx, cx)
    ry = bh * 0.4
    ell = ((xx - cx) / rx) ** 2 + ((yy - (bh - ry)) / ry) ** 2 <= 1.0
    inside = (xx >= t0 - pad - ox) & (xx <= t1 + pad - ox)
    keep = ((yy < bh - ry) | ell | inside).astype(np.float32)
    keep = cv2.GaussianBlur(keep, (0, 0), max(1.2, bh * 0.004))
    ramp = np.clip((bh - yy) / (bh * 0.1), 0, 1)
    keep = np.where(inside, keep * ramp, keep)
    b[..., 3] = (b[..., 3] * keep).astype(np.uint8)
    padT, padL = max(0, -oy), max(0, -ox)
    padR = max(0, ox + bwid - W)
    canvas = cv2.copyMakeBorder(stand, padT, 0, padL, padR, cv2.BORDER_CONSTANT, value=0)
    # the hanging arms go: below the shoulders, the standing drawing is kept only
    # inside the torso column or under the folded arms
    CH, CW = canvas.shape[:2]
    under = np.zeros((CH, CW), np.uint8)
    under[oy + padT:oy + padT + bh, ox + padL:ox + padL + bwid] = b[..., 3] > 60
    under = cv2.erode(under, np.ones((5, 5), np.uint8))
    col = np.zeros((CH, CW), bool)
    col[:, max(0, t0 - pad + padL):t1 + pad + padL] = True
    y0 = int(fs['box'][3] + 0.3 * sw) + padT
    y_end = top_leg[0] + int((H - top_leg[0]) * 0.35) + padT
    band = np.zeros((CH, CW), bool)
    band[y0:y_end] = True
    canvas[band & ~col & (under == 0), 3] = 0
    # and any knuckles of the hanging fists left inside the column
    L = F.lab(canvas[..., :3])
    skin = band & (L[..., 0] > 45) & (L[..., 1] > 8) & (L[..., 2] > 12)
    skin = cv2.dilate(skin.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    canvas[skin & band, 3] = 0
    F.paste_over(canvas, b, ox + padL, oy + padT)
    return canvas


def build_extra():
    """Roy standing with arms folded (crossed-arms bust over the standing
    legs) and a close-up bust with the high-res head."""
    ridx = json.load(open(os.path.join(EP, 'characters', 'roy', 'index.json')))
    gidx = json.load(open(os.path.join(EP, 'characters', 'gary', 'index.json')))
    canvas = crossed_standing(gary_img(gidx, 'body', 'stand_neutral'), gary_img(gidx, 'upper', 'crossed_arms'))
    head = roy_head_hi()
    canvas = swap_head(canvas, head, F.find_face(head), 'front', 0.35, 1.12)
    rel = os.path.join('characters', 'roy', 'body', 'stand_crossed.png')
    cv2.imwrite(os.path.join(EP, rel), canvas, [cv2.IMWRITE_PNG_COMPRESSION, 6])
    ridx['body']['stand_crossed'] = dict(file=rel, size=[canvas.shape[1], canvas.shape[0]], cut={})
    # close-up: the high-res head on a scaled Gary crossed-arms bust
    fh = F.find_face(head)
    hw = fh['box'][2] - fh['box'][0]
    g = gary_img(gidx, 'upper', 'crossed_arms')
    fg_ = F.find_face(g, head_frac=0.6)
    gw = fg_['box'][2] - fg_['box'][0]
    k = hw / 0.98 / gw
    g2 = cv2.resize(g, None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC)
    region, box = gary_head_region(g2, F.find_face(g2, head_frac=0.6))
    g2[region, 3] = 0
    fx0, fy0, fx1, fy1 = box
    rcx = (fh['box'][0] + fh['box'][2]) / 2
    top = int(fy1 + (fx1 - fx0) * 0.30 - head.shape[0])
    left = int((fx0 + fx1) / 2 - rcx)
    padT, padL = max(0, -top), max(0, -left)
    padR = max(0, left + head.shape[1] - g2.shape[1])
    cu = cv2.copyMakeBorder(g2, padT, 0, padL, padR, cv2.BORDER_CONSTANT, value=0)
    F.paste_over(cu, head, left + padL, top + padT)
    cu = clean_bits(cu)
    rel = os.path.join('characters', 'roy', 'closeup', 'crossed_arms.png')
    os.makedirs(os.path.dirname(os.path.join(EP, rel)), exist_ok=True)
    cv2.imwrite(os.path.join(EP, rel), cu, [cv2.IMWRITE_PNG_COMPRESSION, 6])
    ridx.setdefault('closeup', {})['crossed_arms'] = dict(file=rel, size=[cu.shape[1], cu.shape[0]], cut={})
    with open(os.path.join(EP, 'characters', 'roy', 'index.json'), 'w') as f:
        json.dump(ridx, f, indent=1)
    print('roy extras: stand_crossed', canvas.shape, 'closeup', cu.shape)


if __name__ == '__main__':
    build()
    build_extra()
