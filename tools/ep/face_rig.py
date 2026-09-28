"""Face analysis and part swaps for the episode's cartoon (bitmap) characters.

find_face(rgba)            -> dict(skin, face, eyes=[(cx, cy, rx, ry)], mouth=(cx, cy, w, h), mouth_mask)
mouth_part(rgba)           -> (patch RGBA, (cx, cy), width): a phoneme drawing's mouth with a soft skin margin
without_mouth(rgba, info)  -> the drawing with its mouth painted out (inpainted with skin)
with_mouth(base, info, part, scale_w, ...) -> base + a pasted mouth
blink(rgba, info, amount)  -> eyelids closed over the eye whites, with a lash line

Everything is found from colour: the skin is the most common warm mid-tone,
eyes are white blobs in the upper face, the mouth is the biggest dark/red
non-skin blob in the lower middle of the face.
"""
import cv2, numpy as np


def lab(bgr):
    return cv2.cvtColor(bgr.astype(np.float32) / 255, cv2.COLOR_BGR2LAB)


def fill_holes(m):
    h, w = m.shape
    ff = np.pad(m.astype(np.uint8), 1)
    mask = np.zeros((h + 4, w + 4), np.uint8)
    cv2.floodFill(ff, mask, (0, 0), 2)
    return ff[1:-1, 1:-1] != 2


def drop_intrusions(rgba):
    """Remove pieces of the neighbouring drawings on the sheet: parts not joined
    to the figure that come in from the left or right edge (a hand, a sleeve).
    Ground shadows spanning the drawing's width stay."""
    m = (rgba[..., 3] > 60).astype(np.uint8)
    n, cc, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    if n <= 2:
        return rgba, 0
    H, W = m.shape
    big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    out, k = rgba.copy(), 0
    for i in range(1, n):
        x, y, w, h, ar = st[i]
        if i == big or w > 0.6 * W or ar > 0.25 * st[big, cv2.CC_STAT_AREA]:
            continue
        if x <= 4 or x + w >= W - 4:
            piece = cv2.dilate((cc == i).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
            out[piece & (cc != big), 3] = 0
            k += 1
    return out, k


def open_gaps(rgba, low=0.4):
    """Clear the sheet's background left inside a figure (the gap between
    walking legs, under an arm): large, flat, near-white, low-chroma areas in
    the lower part of the drawing. Eye whites, teeth and shoe soles are small
    and stay."""
    a = rgba[..., 3] > 128
    H, W = a.shape
    L = lab(rgba[..., :3])
    pale = a & (L[..., 0] > 86) & (np.hypot(L[..., 1], L[..., 2]) < 7)
    pale[:int(H * low)] = False
    pale = cv2.morphologyEx(pale.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, cc, st, _ = cv2.connectedComponentsWithStats(pale, connectivity=8)
    total = a.sum()
    out, k = rgba.copy(), 0
    for i in range(1, n):
        x, y, w, h, ar = st[i]
        if ar > 0.03 * total and h > 0.12 * H:          # the leg gap; shoe soles are far smaller
            m = cv2.dilate((cc == i).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
            out[m & ~(L[..., 0] < 40), 3] = 0        # keep the ink outline around it
            k += 1
    return out, k


def skin_colour(rgba, region=None):
    L = lab(rgba[..., :3])
    a = rgba[..., 3] > 200
    if region is not None:
        a &= region
    warm = a & (L[..., 0] > 55) & (L[..., 0] < 90) & (L[..., 1] > 8) & (L[..., 1] < 35) & (L[..., 2] > 15) & (L[..., 2] < 50)
    px = L[warm]
    if len(px) == 0:
        return None
    return np.median(px, axis=0)


def find_face(rgba, head_frac=1.0, skin=None):
    """head_frac: only look in the top fraction of the drawing (bodies below)."""
    H, W = rgba.shape[:2]
    L = lab(rgba[..., :3])
    a = rgba[..., 3] > 128
    top = np.zeros((H, W), bool)
    top[:int(H * head_frac)] = True
    skin = skin_colour(rgba, top) if skin is None else skin
    sk = a & top & (np.linalg.norm(L - skin, axis=2) < 16)
    sk = cv2.morphologyEx(sk.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)) > 0
    n, cc, st, _ = cv2.connectedComponentsWithStats(sk.astype(np.uint8), connectivity=8)
    if n < 2:
        return None
    # the face: the biggest skin blob in the top part (hands are smaller / lower)
    order = np.argsort(-st[1:, cv2.CC_STAT_AREA]) + 1
    big = order[0]
    face_skin = cc == big
    hull = np.zeros((H, W), np.uint8)
    cv2.fillConvexPoly(hull, cv2.convexHull(cv2.findNonZero(face_skin.astype(np.uint8))), 1)
    face = (hull > 0) & a
    ys, xs = np.nonzero(face)
    fx0, fx1, fy0, fy1 = xs.min(), xs.max(), ys.min(), ys.max()
    fw, fh = fx1 - fx0, fy1 - fy0
    # eyes: white blobs in the face
    white = face & (L[..., 0] > 86) & (np.hypot(L[..., 1], L[..., 2]) < 10)
    n, ec, est, ecen = cv2.connectedComponentsWithStats(white.astype(np.uint8), connectivity=8)
    eyes = []
    for i in range(1, n):
        x, y, w, h, ar = est[i]
        if ar > 0.002 * fw * fh and y + h / 2 < fy0 + fh * 0.7 and w < fw * 0.45:
            eyes.append((float(ecen[i][0]), float(ecen[i][1]), w / 2.0, h / 2.0, i))
    eyes = sorted(eyes, key=lambda e: -est[e[4], cv2.CC_STAT_AREA])[:2]
    eyes = sorted(eyes, key=lambda e: e[0])
    eye_mask = np.isin(ec, [e[4] for e in eyes]) if eyes else np.zeros((H, W), bool)
    eye_bottom = max((e[1] + e[3] for e in eyes), default=fy0 + fh * 0.45)
    eye_cx = np.mean([e[0] for e in eyes]) if eyes else (fx0 + fx1) / 2
    # mouth: dark or red non-skin blob below the eyes and nose
    nonskin = face & ~face_skin & ~fill_holes(cv2.dilate(eye_mask.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0)
    darkred = nonskin & ((L[..., 0] < 45) | ((L[..., 1] > 28) & (L[..., 0] < 70)) | (L[..., 0] > 88))
    eye_y = np.mean([e[1] for e in eyes]) if eyes else fy0 + fh * 0.45
    lo_y, hi_y, want_y = eye_y + 0.32 * fw, eye_y + 0.78 * fw, eye_y + 0.46 * fw
    darkred_all = darkred.copy()
    darkred[:int(lo_y)] = False
    darkred[int(hi_y):] = False
    n, mc, mst, mcen = cv2.connectedComponentsWithStats(darkred.astype(np.uint8), connectivity=8)
    best, score = None, 0
    if len(eyes) == 2:
        ex0, ex1 = eyes[0][0], eyes[1][0]
        gap = max(ex1 - ex0, fw * 0.15)
        lo_x, hi_x = ex0 - gap * 0.25, ex1 + gap * 0.45
        want_x = ex0 + (ex1 - ex0) * 0.6            # 3/4 faces: the mouth sits nearer the far eye
    else:
        lo_x, hi_x, want_x = fx0 + fw * 0.2, fx1 - fw * 0.1, eye_cx
    for i in range(1, n):
        x, y, w, h, ar = mst[i]
        cxm, cym = mcen[i]
        if w > fw * 0.6 or ar < 0.0006 * fw * fh or not (lo_x <= cxm <= hi_x):
            continue
        dark = float((L[..., 0][mc == i] < 45).mean())
        s = ar * (0.4 + dark) / (1 + abs(cxm - want_x) / (fw * 0.1)) / (1 + abs(cym - want_y) / (fw * 0.12))
        if s > score:
            best, score = i, s
    mouth, mouth_mask = None, np.zeros((H, W), bool)
    if best is not None:
        mouth_mask = mc == best
        kk = max(3, int(fw * 0.03))
        near = cv2.dilate(mouth_mask.astype(np.uint8), np.ones((kk, kk), np.uint8)) > 0
        for i in range(1, n):
            if i != best and (near & (mc == i)).any():
                mouth_mask |= mc == i
        # a wide-open mouth reaches above the search window: take it whole (but not up into the nose)
        full = darkred_all.copy()
        full[:int(eye_y + 0.2 * fw)] = False
        n2, c2 = cv2.connectedComponents(full.astype(np.uint8), connectivity=8)
        ids = np.unique(c2[mouth_mask & full])
        grown = np.isin(c2, ids[ids > 0])
        if grown.sum() < 3 * max(mouth_mask.sum(), 1):
            mouth_mask |= grown
        ys, xs = np.nonzero(mouth_mask)
        mouth = ((xs.min() + xs.max()) / 2.0, (ys.min() + ys.max()) / 2.0, float(xs.max() - xs.min()), float(ys.max() - ys.min()))
    return dict(skin=skin, face=face, face_skin=face_skin, box=(fx0, fy0, fx1, fy1), eyes=eyes, eye_mask=eye_mask,
                mouth=mouth, mouth_mask=mouth_mask)


def mouth_part(rgba, margin=0.28):
    """The mouth of a phoneme drawing (lips, teeth, tongue) with a feathered
    skin margin. Returns (patch RGBA, centre in patch, mouth width)."""
    H, W = rgba.shape[:2]
    L = lab(rgba[..., :3])
    a = rgba[..., 3] > 128
    skin = skin_colour(rgba)
    # the lips' colour differs a little from skin; take everything non-skin in the middle band
    ns = a & (np.linalg.norm(L - skin, axis=2) > 13)
    ns = cv2.morphologyEx(ns.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
    band = np.zeros((H, W), bool)
    band[int(H * 0.28):int(H * 0.86), int(W * 0.18):int(W * 0.82)] = True
    n, cc, st, cen = cv2.connectedComponentsWithStats((ns & band).astype(np.uint8), connectivity=8)
    big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    m = cc == big
    near = cv2.dilate(m.astype(np.uint8), np.ones((31, 31), np.uint8)) > 0
    for i in range(1, n):
        if i != big and (near & (cc == i)).any() and st[i, cv2.CC_STAT_AREA] > 30:
            m |= cc == i
    ys, xs = np.nonzero(m)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    mw, mh = x1 - x0, y1 - y0
    pad = int(max(mw, mh) * margin)
    X0, X1, Y0, Y1 = max(0, x0 - pad), min(W, x1 + pad), max(0, y0 - pad), min(H, y1 + pad)
    patch = rgba[Y0:Y1, X0:X1].copy()
    # soft elliptical mask
    ph, pw = patch.shape[:2]
    yy, xx = np.mgrid[:ph, :pw]
    cx, cy = (x0 + x1) / 2 - X0, (y0 + y1) / 2 - Y0
    rx, ry = mw / 2 + pad * 0.8, mh / 2 + pad * 0.8
    d = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    alpha = np.clip((1.0 - d) / 0.35, 0, 1)
    alpha = np.maximum(alpha, m[Y0:Y1, X0:X1].astype(np.float32))
    # fade out before the drawing's own edge (the sheet's mouth drawings are cut flat)
    dist = cv2.distanceTransform(np.pad(a, 1).astype(np.uint8), cv2.DIST_L2, 5)[1:-1, 1:-1]
    alpha *= np.clip(dist[Y0:Y1, X0:X1] / max(2.0, pad * 0.6), 0, 1)
    patch[..., 3] = (alpha * (patch[..., 3] / 255.0) * 255).astype(np.uint8)
    return patch, (cx, cy), float(mw), float(mh)


def face_interior(info, shape):
    """Inside the face's outline: skin plus what it encloses (eyes, nose, mouth),
    with gaps where an open mouth breaks the skin closed. Mouth erases and pastes
    stay inside it, so the jaw line is never painted over."""
    if info.get('_interior') is not None:
        return info['_interior']
    fs = info.get('face_skin')
    if fs is None or not fs.any():
        return None
    fw = info['box'][2] - info['box'][0]
    if info.get('lips_box') is not None:
        # a hand-located mouth: the skin's own outline (its convex hull, just inside the ink line),
        # so neither the jaw line nor a sleeve, a hand or the jacket beside it is ever painted
        hull = np.zeros(fs.shape, np.uint8)
        cv2.fillConvexPoly(hull, cv2.convexHull(cv2.findNonZero(fs.astype(np.uint8))), 1)
        k = max(5, int(fw * 0.07)) | 1
        m = fill_holes(cv2.morphologyEx(fs.astype(np.uint8), cv2.MORPH_CLOSE,
                                        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))) > 0)
        m |= info['mouth_mask']
        m &= cv2.erode(hull, np.ones((3, 3), np.uint8)) > 0
        soft = cv2.GaussianBlur(m.astype(np.float32), (0, 0), max(0.8, fw * 0.003))
        info['_interior'] = soft
        return soft
    k = max(5, int(fw * 0.07)) | 1
    # the drawn mouth is inside the face even where a wide-open one breaks through the skin
    mm = info.get('mouth_mask')
    base = fs.astype(np.uint8)
    if mm is not None and mm.any():
        base = base | cv2.dilate(mm.astype(np.uint8), np.ones((k, k), np.uint8))
    m = cv2.morphologyEx(base, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    m = fill_holes(m > 0)
    hull = np.zeros(m.shape, np.uint8)
    cv2.fillConvexPoly(hull, cv2.convexHull(cv2.findNonZero(base)), 1)
    m &= hull > 0
    # the skin's own anti-aliased rim, but not the ink line beyond it
    m = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    soft = cv2.GaussianBlur(m.astype(np.float32), (0, 0), max(0.8, fw * 0.004))
    info['_interior'] = soft
    return soft


def mouth_marks(rgba, info, box):
    """The drawn mouth inside a hand-placed box: its ink, lips, teeth, tongue and
    the dark inside, as the pieces that reach the middle of the box (a cheek
    fold or a sleeve at the box's edge isn't the mouth)."""
    H, W = rgba.shape[:2]
    x0, x1, y0, y1 = [int(v) for v in box]
    fw = info['box'][2] - info['box'][0]
    mg = max(3, int(0.02 * fw))
    X0, X1, Y0, Y1 = max(0, x0 - mg), min(W, x1 + mg), max(0, y0 - mg), min(H, y1 + mg)
    L = lab(rgba[Y0:Y1, X0:X1, :3])
    fs = info['face_skin'][Y0:Y1, X0:X1]
    ink = L[..., 0] < 42
    lips = (L[..., 1] > 17) & (L[..., 0] < 80)
    teeth = (L[..., 0] > 84) & (np.hypot(L[..., 1], L[..., 2]) < 12)
    inbox = np.zeros(L.shape[:2], bool)
    inbox[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0] = True
    cand = (ink | lips | teeth | ((np.linalg.norm(L - info['skin'], axis=2) > 22) & inbox)) & ~fs & \
        (rgba[Y0:Y1, X0:X1, 3] > 128)
    n, cc = cv2.connectedComponents(cand.astype(np.uint8), connectivity=8)
    core = np.zeros_like(cand)
    bw = x1 - x0
    core[y0 - Y0:y1 - Y0, int(x0 + 0.25 * bw) - X0:int(x1 - 0.25 * bw) - X0] = True
    ids = np.unique(cc[core & cand])
    m = np.isin(cc, ids[ids > 0]) & inbox | (np.isin(cc, ids[ids > 0]) & ~inbox & (ink | teeth))
    out = np.zeros((H, W), bool)
    out[Y0:Y1, X0:X1] = m
    return out


def erase_mouth(rgba, info):
    """Paint out a drawn mouth located by hand (info['lips_box'], info['allow']):
    only the mouth's own marks inside the box - ink, lips, teeth, tongue, the dark
    of an open mouth - are removed, never anything above the nose line, and the
    hole is filled from the skin and shading around it (inpainted, with the ink
    just above the nose line kept out of the fill's sources)."""
    H, W = rgba.shape[:2]
    x0, x1, y0, y1 = info['lips_box']
    fw = info['box'][2] - info['box'][0]
    mg = max(3, int(0.02 * fw))
    X0, X1, Y0, Y1 = max(0, int(x0) - 3 * mg), min(W, int(x1) + 3 * mg), max(0, int(y0) - 4 * mg), min(H, int(y1) + 3 * mg)
    crop = rgba[Y0:Y1, X0:X1]
    L = lab(crop[..., :3])
    box = np.zeros(crop.shape[:2], np.uint8)
    cv2.rectangle(box, (int(x0) - X0 - mg, int(y0) - Y0 - mg), (int(x1) - X0 + mg, int(y1) - Y0 + mg), 1, -1)
    box = box > 0
    ink = L[..., 0] < 42
    lips = (L[..., 1] > 17) & (L[..., 0] < 80)                    # red/pink lips, tongue, gums
    teeth = (L[..., 0] > 84) & (np.hypot(L[..., 1], L[..., 2]) < 12)
    mouth = info['mouth_mask'][Y0:Y1, X0:X1] | ((ink | lips | teeth) & box & ~info['face_skin'][Y0:Y1, X0:X1])
    k = max(3, int(0.014 * fw)) | 1
    hole = cv2.dilate(mouth.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))) > 0
    allow = info['allow'][Y0:Y1, X0:X1]
    inside = face_interior(info, (H, W))
    inside = inside[Y0:Y1, X0:X1] if inside is not None else np.ones(crop.shape[:2], np.float32)
    hole &= (allow > 0.02) & (inside > 0.5) & (crop[..., 3] > 0)
    # the fill samples skin only: never the nose's ink, the jaw line, clothes, a hand or a phone
    far = (np.linalg.norm(L - info['skin'], axis=2) > 30) | ink | (crop[..., 3] < 200) | (inside < 0.5) | \
        (L[..., 0] > info['skin'][0] + 7)                      # no highlights / pale rims either
    src_mask = hole | (cv2.dilate(far.astype(np.uint8), np.ones((k, k), np.uint8)) > 0)
    # a smooth fill from the surrounding skin tones only (normalised convolution at two scales,
    # the finer one wherever it has enough skin nearby): keeps the soft shading of the cheeks
    rgb = crop[..., :3].astype(np.float32)
    w = (~src_mask).astype(np.float32)
    filled = None
    for sig in (0.12 * fw, 0.045 * fw):
        num = cv2.GaussianBlur(rgb * w[..., None], (0, 0), sig)
        den = cv2.GaussianBlur(w, (0, 0), sig)[..., None]
        est = num / np.maximum(den, 1e-6)
        if filled is None:
            filled = est
        else:
            a = np.clip(den / 0.25, 0, 1)
            filled = est * a + filled * (1 - a)
    soft = cv2.GaussianBlur(hole.astype(np.float32), (0, 0), max(1.0, 0.004 * fw))
    soft = np.maximum(soft, hole.astype(np.float32)) * allow * np.clip(inside, 0, 1)
    out = rgba.copy()
    region = out[Y0:Y1, X0:X1, :3].astype(np.float32)
    out[Y0:Y1, X0:X1, :3] = (region * (1 - soft[..., None]) + filled.astype(np.float32) * soft[..., None]).astype(np.uint8)
    return out


def without_mouth(rgba, info, grow=0.18):
    """Paint the drawn mouth out with the skin around it (a flat fill with a
    soft edge, like the flat-shaded art; inpainting smears the ink)."""
    if info is None or info['mouth'] is None:
        return rgba
    out = rgba.copy()
    cx, cy, w, h = info['mouth']
    m = info['mouth_mask'].astype(np.uint8)
    r = int(max(w, h) * grow) | 1
    m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (r, r))) > 0
    ell = np.zeros(m.shape, np.uint8)
    cv2.ellipse(ell, (int(cx), int(cy)), (int(w * 0.62 + r * 0.5), int(h * 0.68 + r * 0.5)), 0, 0, 360, 1, -1)
    m |= ell > 0
    # and every non-skin mark round the mouth - line ends, teeth, lips - so no second mouth shows
    L = lab(rgba[..., :3])
    fw = info['box'][2] - info['box'][0]
    big = np.zeros(m.shape, np.uint8)
    cv2.ellipse(big, (int(cx), int(cy)), (int(max(w * 0.62, fw * 0.21) + r * 0.5), int(max(h * 0.72, fw * 0.075) + r * 0.5)),
                0, 0, 360, 1, -1)
    ink = (big > 0) & (np.linalg.norm(L - info['skin'], axis=2) > 14)
    k = max(3, int(fw * 0.012)) | 1
    m |= cv2.dilate(ink.astype(np.uint8), np.ones((k, k), np.uint8)) > 0
    m &= rgba[..., 3] > 0
    # the skin just outside the mouth: its median colour fills the hole
    ring = (cv2.dilate(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (r * 2 + 1, r * 2 + 1))) > 0) & ~m
    skin = info['skin']
    ringskin = ring & (np.linalg.norm(L - skin, axis=2) < 18)
    col = np.median(rgba[..., :3][ringskin], axis=0) if ringskin.sum() > 20 else \
        (cv2.cvtColor(np.float32([[skin]]), cv2.COLOR_LAB2BGR)[0, 0] * 255)
    soft = cv2.GaussianBlur(m.astype(np.float32), (0, 0), max(1.0, r * 0.25))
    soft = np.maximum(soft, m.astype(np.float32))
    inside = face_interior(info, m.shape)
    if inside is not None:
        soft = soft * inside
    soft = soft[..., None]
    out[..., :3] = (out[..., :3] * (1 - soft) + np.array(col, np.float32) * soft).astype(np.uint8)
    return out


def paste(dst, src, x0, y0, clip=None):
    """Alpha-over RGBA src onto RGBA dst at (x0, y0), in place (only inside `clip`, a 0..1 mask of dst)."""
    h, w = src.shape[:2]
    H, W = dst.shape[:2]
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
    if xa >= xb or ya >= yb:
        return
    s = src[ya - y0:yb - y0, xa - x0:xb - x0].astype(np.float32)
    d = dst[ya:yb, xa:xb].astype(np.float32)
    al = s[..., 3:4] / 255 * (d[..., 3:4] / 255)          # never paint outside the drawing
    if clip is not None:
        al = al * clip[ya:yb, xa:xb, None]
    d[..., :3] = s[..., :3] * al + d[..., :3] * (1 - al)
    dst[ya:yb, xa:xb] = d.clip(0, 255).astype(np.uint8)


def with_mouth(base, info, part, width, dx=0.0, dy=0.0, squash_x=1.0, angle=0.0):
    """Paste a mouth part so its width is `width` px, centred on the base
    drawing's mouth (plus an offset)."""
    patch, (pcx, pcy), pw = part[:3]
    s = width / max(pw, 1e-6)
    M = cv2.getRotationMatrix2D((pcx, pcy), angle, 1.0)
    M[0] *= s * squash_x
    M[1] *= s
    ph, pwid = patch.shape[:2]
    Wn, Hn = int(pwid * s * squash_x + 2), int(ph * s + 2)
    M[0, 2] = M[0, 2] * 1 + 0
    warped = cv2.warpAffine(patch, M, (Wn, Hn), flags=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC,
                            borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    cx, cy = info['mouth'][0] + dx, info['mouth'][1] + dy
    out = base.copy()
    clip = face_interior(info, base.shape[:2])
    if info.get('allow') is not None:
        clip = info['allow'] if clip is None else clip * info['allow']
    paste(out, warped, int(round(cx - pcx * s * squash_x)), int(round(cy - pcy * s)), clip=clip)
    return out


def blink(rgba, info, amount=1.0, lash=(40, 30, 30)):
    """Close the eyes: skin lids over the whites (and pupils), with a lash line."""
    if info is None or not info['eyes'] or amount <= 0:
        return rgba
    out = rgba.copy()
    skin_bgr = cv2.cvtColor(np.float32([[info['skin']]]), cv2.COLOR_LAB2BGR)[0, 0] * 255
    for (cx, cy, rx, ry, _) in info['eyes']:
        rx2, ry2 = rx * 1.15, ry * 1.2
        lid = np.zeros(out.shape[:2], np.uint8)
        cut = cy - ry2 + 2 * ry2 * min(amount, 1.0)
        cv2.ellipse(lid, (int(cx), int(cy)), (int(rx2), int(ry2)), 0, 0, 360, 1, -1)
        lid[int(cut):] = 0
        lid = lid.astype(bool) & (out[..., 3] > 0)
        out[lid, :3] = skin_bgr.astype(np.uint8)
        if amount >= 0.95:
            t = max(2, int(ry * 0.18))
            cv2.ellipse(out, (int(cx), int(cy + ry * 0.1)), (int(rx * 1.05), int(ry * 0.35)), 0, 10, 170,
                        (*lash, 255), t, cv2.LINE_AA)
        else:
            cv2.line(out, (int(cx - rx), int(cut)), (int(cx + rx), int(cut)), (*lash, 255), max(2, int(ry * 0.12)), cv2.LINE_AA)
    return out


def paste_over(dst, src, x0, y0):
    """Alpha-composite RGBA src over RGBA dst (grows dst's alpha), in place."""
    h, w = src.shape[:2]
    H, W = dst.shape[:2]
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
    if xa >= xb or ya >= yb:
        return
    s = src[ya - y0:yb - y0, xa - x0:xb - x0].astype(np.float32)
    d = dst[ya:yb, xa:xb].astype(np.float32)
    sa, da = s[..., 3:4] / 255, d[..., 3:4] / 255
    oa = sa + da * (1 - sa)
    rgb = (s[..., :3] * sa + d[..., :3] * da * (1 - sa)) / np.maximum(oa, 1e-6)
    dst[ya:yb, xa:xb, :3] = rgb.clip(0, 255).astype(np.uint8)
    dst[ya:yb, xa:xb, 3:4] = (oa * 255).clip(0, 255).astype(np.uint8)
