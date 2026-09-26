"""Face analysis on (HD) character sprites, for lip sync and blinks.

face_info(rgba) finds the skin, the face (skin with its holes filled), the eye
whites, and the drawn mouth. mouthless(rgba, info) paints the mouth out with
skin. mouth_patch(rgba, info) lifts the mouth (with a skin margin that blends
invisibly into another face of the same palette).
"""
import cv2, numpy as np


def lab(bgr):
    return cv2.cvtColor(bgr.astype(np.float32) / 255, cv2.COLOR_BGR2LAB)


def fill_holes(m):
    m = m.astype(np.uint8)
    h, w = m.shape
    ff = np.pad(m, 1).copy()
    mask = np.zeros((h + 4, w + 4), np.uint8)
    cv2.floodFill(ff, mask, (0, 0), 2)
    return (ff[1:-1, 1:-1] != 2)


def skin_colour(rgba):
    """Most common peach colour among the opaque pixels (Lab)."""
    L = lab(rgba[..., :3])
    a = rgba[..., 3] > 250
    peach = a & (L[..., 0] > 62) & (L[..., 0] < 95) & (L[..., 1] > 2) & (L[..., 1] < 30) & (L[..., 2] > 12) & (L[..., 2] < 45)
    px = rgba[..., :3][peach].reshape(-1, 3)
    if len(px) == 0:
        return None
    key = (px[:, 0].astype(np.int32) << 16) | (px[:, 1].astype(np.int32) << 8) | px[:, 2]
    v, c = np.unique(key, return_counts=True)
    k = v[np.argmax(c)]
    bgr = np.array([k >> 16, (k >> 8) & 255, k & 255], np.uint8)
    return bgr


def face_info(rgba, skin_bgr=None):
    skin_bgr = skin_colour(rgba) if skin_bgr is None else skin_bgr
    L = lab(rgba[..., :3])
    Ls = lab(skin_bgr[None, None])[0, 0]
    a = rgba[..., 3] > 128
    skin = a & (np.linalg.norm(L - Ls, axis=2) < 10)
    n, cc, st, _ = cv2.connectedComponentsWithStats(skin.astype(np.uint8), connectivity=8)
    if n < 2:
        return None
    big = 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])
    skin1 = cc == big
    # eyes often touch the hat, so they aren't holes in the skin: look for
    # the whites inside the skin's convex hull instead
    hull = np.zeros(skin1.shape, np.uint8)
    pts = cv2.findNonZero(skin1.astype(np.uint8))
    cv2.fillConvexPoly(hull, cv2.convexHull(pts), 1)
    white = (hull > 0) & a & (L[..., 0] > 88) & (np.hypot(L[..., 1], L[..., 2]) < 8)
    face = fill_holes(skin1 | white) & a
    ys, xs = np.nonzero(face)
    fx0, fx1, fy0, fy1 = xs.min(), xs.max(), ys.min(), ys.max()
    n, ec, st, cen = cv2.connectedComponentsWithStats(white.astype(np.uint8), connectivity=8)
    eyes = [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 0.004 * face.sum()]
    eyes = sorted(eyes, key=lambda i: -st[i, cv2.CC_STAT_AREA])[:2]
    eye_mask = np.isin(ec, eyes) if eyes else np.zeros_like(face)
    if eyes:
        eys, exs = np.nonzero(eye_mask)
        eye_c = (float(exs.mean()), float(eys.mean()))
        eye_bottom = eys.max()
        # pupils sit inside the eye whites; include them for blinks
        eye_region = fill_holes(cv2.dilate(eye_mask.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0) & face
    else:
        eye_c, eye_bottom, eye_region = ((fx0 + fx1) / 2, fy0 + 0.45 * (fy1 - fy0)), fy0 + 0.55 * (fy1 - fy0), np.zeros_like(face)
    row = int(eye_c[1])
    fw_row = np.nonzero(face[row])[0]
    face_w = float(fw_row.max() - fw_row.min()) if len(fw_row) else float(fx1 - fx0)
    # mouth: the biggest non-skin blob inside the face, below the eyes, near the middle
    cand = face & ~skin1 & ~eye_region
    cand[:int(eye_bottom + 0.03 * face_w)] = False
    n, mc, st, cen = cv2.connectedComponentsWithStats(cand.astype(np.uint8), connectivity=8)
    best, score = None, 0
    for i in range(1, n):
        x, y, w, h, ar = st[i]
        if abs(cen[i][0] - eye_c[0]) > 0.2 * face_w or w > 0.45 * face_w:
            continue
        if ar > score:
            best, score = i, ar
    mouth = (mc == best) if best is not None else np.zeros_like(face)
    if best is not None:
        # gather nearby pieces of the same mouth (teeth, tongue split by ink)
        near = cv2.dilate(mouth.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
        for i in range(1, n):
            if i != best and (near & (mc == i)).any() and st[i, 2] < 0.3 * face_w:
                mouth |= mc == i
        mys, mxs = np.nonzero(mouth)
        mouth_c = (float(mxs.mean()), float(mys.mean()))
        mouth_top = float(mys.min())
    else:
        mouth_c = (eye_c[0], eye_c[1] + 0.45 * face_w)
        mouth_top = mouth_c[1]
    return dict(skin=skin_bgr, face=face, eyes=eye_region, eye_c=eye_c, face_w=face_w,
                mouth=mouth, mouth_c=mouth_c, mouth_top=mouth_top, has_mouth=best is not None)


def mouthless(rgba, info, grow=3):
    out = rgba.copy()
    m = cv2.dilate(info['mouth'].astype(np.uint8), np.ones((2 * grow + 1, 2 * grow + 1), np.uint8)) > 0
    m &= info['face']
    out[m, :3] = info['skin']
    return out


def mouth_patch(rgba, info, margin=4):
    """RGBA patch of the mouth plus a skin margin, and the mouth centre in it."""
    m = cv2.dilate(info['mouth'].astype(np.uint8), np.ones((2 * margin + 1, 2 * margin + 1), np.uint8)) > 0
    m &= info['face']
    ys, xs = np.nonzero(m)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    p = rgba[y0:y1, x0:x1].copy()
    alpha = m[y0:y1, x0:x1].astype(np.float32)
    alpha = cv2.GaussianBlur(alpha, (0, 0), 1.0) * (p[..., 3] / 255.0)
    p[..., 3] = (alpha * 255).astype(np.uint8)
    cx, cy = info['mouth_c']
    return p, (cx - x0, cy - y0)


def blink(rgba, info, amount=1.0):
    """Close the eyes: skin lids over the whites, with a lash line."""
    out = rgba.copy()
    if not info['eyes'].any():
        return out
    e = info['eyes']
    ys, xs = np.nonzero(e)
    y0, y1 = ys.min(), ys.max()
    cut = y0 + (y1 - y0) * amount
    lid = e & (np.arange(e.shape[0])[:, None] <= cut)
    out[lid, :3] = info['skin']
    if amount >= 0.95:
        n, cc, st, cen = cv2.connectedComponentsWithStats(e.astype(np.uint8))
        for i in range(1, n):
            x, y, w, h, ar = st[i]
            if ar < 20:
                continue
            # two eyes drawn touching come out as one blob: one lash each
            parts = [(x, w)] if w < 1.4 * h else [(x, w / 2), (x + w / 2, w / 2)]
            t = max(2, int(h * 0.06))
            for px, pw in parts:
                cv2.ellipse(out, (int(px + pw / 2), int(y + h * 0.43)), (int(pw * 0.40), int(h * 0.13)), 0, 20, 160,
                            (30, 26, 28, 255), t, cv2.LINE_AA)
    return out
