"""Redraw cut-out sprites at a higher resolution as clean flat-colour artwork.

    python3 tools/hd_sprites.py cartman [face_px]      # default 800
    -> episode/characters_hd/<name>/<panel>/<sprite>.png  (+ index.json, anchors scaled)

Each panel is redrawn at its own whole-number scale so that the character's
face comes out about face_px wide everywhere (the sheet draws gestures and
poses much smaller than head close-ups); index.json records each scale.

The sheets are small, soft, AI-drawn images; blowing them up blurs every edge.
South Park art is flat colour, so each sprite is rebuilt instead:
  1. every character gets a palette of its flat colours (clustered from all its
     sprites, ignoring anti-aliased edge pixels);
  2. each pixel of a sprite is labelled with its nearest palette colour
     (transparent is a label too);
  3. every label's coverage map is smoothed a touch and upscaled, and each
     output pixel takes the label that covers it most, at 2x the target size;
  4. that is box-filtered down to the target, which anti-aliases every edge.
Thin lines (mouths, brows, chin lines) survive because a line's own coverage
always beats its neighbours' along its centre. Deterministic.
"""
import json, os, sys
import cv2, numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EP = os.path.join(ROOT, 'episode')


def to_lab(bgr):
    return cv2.cvtColor(bgr.astype(np.float32) / 255, cv2.COLOR_BGR2LAB)


def palette(sprites, k=28, merge=5.0):
    """Flat colours of one character: k-means over non-edge opaque pixels,
    then clusters closer than `merge` (Lab) are merged."""
    samples = []
    for rgba in sprites:
        a = rgba[..., 3] == 255
        L = to_lab(rgba[..., :3])
        g = cv2.morphologyEx(L[..., 0], cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
        flat = a & (g < 6)
        samples.append(L[flat])
        # keep every dark or saturated detail pixel too, however thin
        detail = a & ((L[..., 0] < 30) | (np.hypot(L[..., 1], L[..., 2]) > 45))
        samples.append(L[detail])
    X = np.concatenate(samples).astype(np.float32)
    rng = np.random.RandomState(0)
    if len(X) > 200000:
        X = X[rng.choice(len(X), 200000, replace=False)]
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.2)
    cv2.setRNGSeed(0)
    _, lab, C = cv2.kmeans(X, k, None, crit, 3, cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(lab.ravel(), minlength=k)
    order = np.argsort(-counts)
    keep = []
    for i in order:
        if counts[i] < 30:
            continue
        if all(np.linalg.norm(C[i] - C[j]) >= merge for j in keep):
            keep.append(i)
    return C[keep]


def redraw(rgba, pal, scale=4, soften=0.55):
    h, w = rgba.shape[:2]
    pad = 2
    rgba = cv2.copyMakeBorder(rgba, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
    L = to_lab(rgba[..., :3])
    a = rgba[..., 3].astype(np.float32) / 255
    d = np.linalg.norm(L[:, :, None, :] - pal[None, None], axis=3)   # H x W x P
    nearest = np.argmin(d, axis=2)
    labels = np.where(a >= 0.5, nearest + 1, 0)                        # 0 = transparent
    # thin drawn lines (chin, closed eyes, mouth lines) are anti-aliased into
    # the colour around them; find them as narrow dark valleys and ink them
    valley = cv2.morphologyEx(L[..., 0], cv2.MORPH_BLACKHAT,
                              cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    ink = int(np.argmin(pal[:, 0])) + 1
    line = ((valley > 10) & (a >= 0.5) & (labels != ink)).astype(np.uint8)
    n, cc, st, _ = cv2.connectedComponentsWithStats(line, connectivity=8)
    keep = np.zeros(n, bool)
    keep[1:] = st[1:, cv2.CC_STAT_AREA] >= 4           # specks on colour seams are not lines
    labels[keep[cc]] = ink
    used = np.unique(labels)
    S = scale * 2
    H2, W2 = rgba.shape[0] * S, rgba.shape[1] * S
    best = np.full((H2, W2), -1.0, np.float32)
    lab2 = np.zeros((H2, W2), np.int32)
    # the silhouette comes from the (continuous) alpha, the inside from labels
    sil = cv2.resize(cv2.GaussianBlur(a, (0, 0), 0.8), (W2, H2), interpolation=cv2.INTER_CUBIC) > 0.5
    for u in used:
        if u == 0:
            continue
        m = (labels == u).astype(np.float32)
        # big flat areas get smoother borders; thin details stay sharp
        thin = cv2.erode((m > 0).astype(np.uint8), np.ones((3, 3), np.uint8)).sum() < 0.35 * m.sum()
        m = cv2.GaussianBlur(m, (0, 0), soften if thin else soften * 2.0)
        up = cv2.resize(m, (W2, H2), interpolation=cv2.INTER_CUBIC)
        better = up > best
        best[better] = up[better]
        lab2[better] = u
    lab2[~sil] = 0
    # inside the silhouette every pixel needs a colour label
    hole = sil & (lab2 == 0)
    if hole.any():
        near = cv2.distanceTransformWithLabels((lab2 == 0).astype(np.uint8), cv2.DIST_L2, 3,
                                               labelType=cv2.DIST_LABEL_PIXEL)[1]
        src = np.zeros(near.max() + 1, np.int32)
        ys, xs = np.nonzero(lab2 > 0)
        src[near[ys, xs]] = lab2[ys, xs]
        lab2[hole] = src[near[hole]]
    cols = np.zeros((len(pal) + 1, 3), np.float32)
    cols[1:] = cv2.cvtColor(pal[None].astype(np.float32), cv2.COLOR_LAB2BGR)[0] * 255
    rgb = cols[lab2]
    alpha = (lab2 > 0).astype(np.float32)
    # 2x2 box filter -> target size, premultiplied so edges don't darken
    pre = rgb * alpha[..., None]
    Ht, Wt = H2 // 2, W2 // 2
    pre = cv2.resize(pre, (Wt, Ht), interpolation=cv2.INTER_AREA)
    alpha = cv2.resize(alpha, (Wt, Ht), interpolation=cv2.INTER_AREA)
    rgb = pre / np.maximum(alpha[..., None], 1e-4)
    out = np.dstack([rgb, alpha * 255]).clip(0, 255).astype(np.uint8)
    out[out[..., 3] == 0, :3] = 0
    p = pad * scale
    return out[p:p + h * scale, p:p + w * scale]


def panel_scales(sprites, face_px):
    """Whole-number redraw scale per panel from the widest face in it."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import face
    widths = {}
    for (p, k), rgba in sprites.items():
        if p == 'parts':
            continue
        try:
            fi = face.face_info(rgba)
        except Exception:
            fi = None
        if fi and fi['face_w'] > 10:
            widths.setdefault(p, []).append(fi['face_w'])
    # the widest face in a panel is a front view (side and back views read narrower)
    scales = {p: int(np.clip(round(face_px / np.max(w)), 2, 12)) for p, w in widths.items()}
    # separate parts are drawn at head close-up size
    scales['parts'] = scales.get('head', 4)
    return scales


def build(char, face_px=800, only=None):
    idx = json.load(open(os.path.join(EP, 'characters', char, 'index.json')))
    items = [(panel, key, s) for panel, v in idx['sprites'].items() for key, s in v.items()
             if not only or panel in only]
    sprites = {(p, k): cv2.imread(os.path.join(EP, s['file']), cv2.IMREAD_UNCHANGED) for p, k, s in items}
    pal = palette(list(sprites.values()))
    scales = panel_scales(sprites, face_px)
    out_idx = dict(idx, face_px=face_px, scales=scales,
                   palette=cv2.cvtColor(pal[None], cv2.COLOR_LAB2RGB)[0].__mul__(255).round().astype(int).tolist(),
                   sprites={})
    for p, k, s in items:
        scale = scales.get(p, 4)
        hd = redraw(sprites[(p, k)], pal, scale)
        rel = os.path.join('characters_hd', char, p, k + '.png')
        os.makedirs(os.path.dirname(os.path.join(EP, rel)), exist_ok=True)
        cv2.imwrite(os.path.join(EP, rel), hd, [cv2.IMWRITE_PNG_COMPRESSION, 9])
        e = dict(s, file=rel, size=[hd.shape[1], hd.shape[0]], scale=scale,
                 feet=[v * scale for v in s['feet']], center=[v * scale for v in s['center']])
        out_idx['sprites'].setdefault(p, {})[k] = e
    with open(os.path.join(EP, 'characters_hd', char, 'index.json'), 'w') as f:
        json.dump(out_idx, f, indent=1)
    print('%s: %d sprites, scales %s, palette of %d colours' % (char, len(items), scales, len(pal)))


if __name__ == '__main__':
    a = sys.argv[1:]
    face_px = int(a[1]) if len(a) > 1 and a[1].isdigit() else 800
    build(a[0], face_px)
