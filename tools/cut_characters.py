"""Cut every drawing out of the South Manchester character model sheets.

    python3 tools/cut_characters.py [character ...]      # default: all five

Reads episode/sheets/<character>.png + episode/sheets/layout.json and writes
episode/characters/<character>/<panel>/<label>.png (RGBA, trimmed, soft edges)
plus episode/characters/<character>/index.json (source rect, size, anchor).

How a sheet is cut:
  1. The panel background (a flat grey/slate with a gentle gradient) is modelled
     as a smooth colour field, so the white of the eyes, black shadows and every
     costume colour separate from it by colour distance, not by a hand-set key.
  2. Panel frames and cell dividers (long thin lines) and the printed labels
     (a row of small dark glyphs under the drawings) are dropped.
  3. What remains is grouped left to right into one drawing per label.
  4. Edges are matted against the background field: alpha comes from how far a
     pixel sits between the background and the nearby drawing colour, and the
     edge colour is replaced by the drawing colour, so there is no grey fringe.
Deterministic: the same sheets always give the same PNGs.
"""
import json, os, re, sys
import cv2, numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EP = os.path.join(ROOT, 'episode')
SHEETS = os.path.join(EP, 'sheets')
OUTDIR = os.path.join(EP, 'characters')

T_HARD = 11.0   # Lab distance from the background that is certainly drawing
T_SOFT = 4.5    # ... that may be drawing if it touches a certain pixel
PAD = 3         # transparent margin around each trimmed sprite


def slug(label):
    s = label.lower().replace('3/4', 'three_quarter').replace('/', ' ')
    return re.sub(r'[^a-z0-9]+', '_', s).strip('_')


def to_lab(bgr):
    return cv2.cvtColor(bgr.astype(np.float32) / 255, cv2.COLOR_BGR2LAB)


def smooth_fill(L, m, sigmas=(4, 10, 24, 60, 150)):
    """Normalised convolution: spread the colours under mask m over the whole
    image, fine where samples are dense, coarser to fill big gaps."""
    F = np.zeros_like(L)
    have = np.zeros(L.shape[:2], bool)
    for s in sigmas:
        num = cv2.GaussianBlur(L * m[..., None], (0, 0), s)
        den = cv2.GaussianBlur(m, (0, 0), s)
        ok = (den > 0.12) & ~have
        F[ok] = num[ok] / den[ok, None]
        have |= ok
    if not have.all():
        F[~have] = (L * m[..., None]).sum((0, 1)) / max(m.sum(), 1)
    return F


def grow_background(L, m, step=3.5, drift=7.0, iters=40):
    """Extend background samples along smooth colour paths into narrow gaps
    (next to a panel frame, between an arm and the body) that are too thin to
    seed. Each step may change colour a little, the whole path not much, so
    growth stops at a drawing edge, and white eyes on a light backdrop stay
    drawing."""
    grown = m > 0
    seed = np.where(grown[..., None], L, 0).astype(np.float32)
    lowc = np.hypot(L[..., 1], L[..., 2]) < 14
    for _ in range(iters):
        added = False
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            g2 = np.roll(grown, (dy, dx), axis=(0, 1))
            L2 = np.roll(L, (dy, dx), axis=(0, 1))
            s2 = np.roll(seed, (dy, dx), axis=(0, 1))
            cand = g2 & ~grown & lowc
            if not cand.any():
                continue
            ok = cand & (np.linalg.norm(L - L2, axis=2) < step) & (np.linalg.norm(L - s2, axis=2) < drift)
            if ok.any():
                grown |= ok
                seed[ok] = s2[ok]
                added = True
        if not added:
            break
    return grown


def background(L, iters=3, min_region=80):
    """Background colour field + per-pixel distance from it.

    Samples start from large, flat, grey stretches, grow once along smooth
    colour paths into narrow gaps, and are then refined against the field. A
    refined sample may never drift far from the first estimate, so the white
    of an eye on a light backdrop can't be absorbed a little at a time."""
    chroma = np.hypot(L[..., 1], L[..., 2])
    gx = cv2.Sobel(L[..., 0], cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(L[..., 0], cv2.CV_32F, 0, 1)
    flat = cv2.GaussianBlur(np.hypot(gx, gy), (0, 0), 1.5) < 6
    m = (chroma < 12) & (L[..., 0] > 25) & (L[..., 0] < 93) & flat
    m = cv2.erode(m.astype(np.uint8), np.ones((3, 3), np.uint8))

    def big_regions(m):
        n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=4)
        big = np.zeros(n, bool)
        big[1:] = st[1:, cv2.CC_STAT_AREA] >= min_region
        return big[lab]

    m = grow_background(L, big_regions(m))
    F0 = smooth_fill(L, m.astype(np.float32))
    near0 = np.linalg.norm(L - F0, axis=2) < 7
    for _ in range(iters):
        # the finest scale keeps sharp steps in the backdrop (label strips,
        # panel shading) instead of smearing them into a false fringe
        F = smooth_fill(L, m.astype(np.float32), sigmas=(1.5, 4, 10, 24, 60, 150))
        d = np.linalg.norm(L - F, axis=2)
        m = cv2.erode((d < 5.0).astype(np.uint8), np.ones((2, 2), np.uint8)) > 0
        m = big_regions(m & near0)
    return F, d


def hysteresis(d):
    soft = (d > T_SOFT).astype(np.uint8)
    hard = d > T_HARD
    n, lab = cv2.connectedComponents(soft, connectivity=8)
    keep = np.zeros(n, bool)
    keep[np.unique(lab[hard])] = True
    keep[0] = False
    return keep[lab]


def thin_lines(fg, H, W):
    """Long straight lines 1-4 px thick: panel frames and cell dividers."""
    u8 = fg.astype(np.uint8)
    thick = cv2.dilate(cv2.morphologyEx(u8, cv2.MORPH_OPEN, np.ones((6, 6), np.uint8)),
                       np.ones((5, 5), np.uint8))
    v = cv2.morphologyEx(u8, cv2.MORPH_OPEN, np.ones((40, 1), np.uint8))
    h = cv2.morphologyEx(u8, cv2.MORPH_OPEN, np.ones((1, 60), np.uint8))
    lines = ((v | h) > 0) & (thick == 0)
    return cv2.dilate(lines.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0


def dividers(dp):
    """Columns holding a cell divider: a thin ridge (a faint line a few levels
    off the background) running down most of the panel."""
    H, W = dp.shape
    l, r = np.roll(dp, 3, axis=1), np.roll(dp, -3, axis=1)
    ridge = (dp > 2.0) & (dp > l + 1.5) & (dp > r + 1.5) & (dp < 40)
    score = ridge.mean(0)
    score[:14] = score[-14:] = 0          # the panel's own frame
    cols = np.nonzero(score > 0.45)[0]
    runs = []
    for x in cols:
        if runs and x - runs[-1][1] <= 2:
            runs[-1][1] = x
        else:
            runs.append([x, x])
    return runs


def cut_dividers(fg, dp, runs, full=False):
    """Break the drawing mask along the dividers. When the dividers split the
    panel into exactly one cell per label, each cell is its own clipped
    picture and the cut is total; otherwise only where the line is visible
    (a drawing painted over a divider keeps its pixels there)."""
    fg = fg.copy()
    for xa, xb in runs:
        xs = slice(max(xa - 1, 0), xb + 2)
        if full:
            fg[:, xs] = False
        else:
            fg[:, xs] &= dp[:, xs] > T_HARD * 1.6
    return fg


def components(mask):
    n, lab, st, cen = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    return lab, [dict(i=i, x=st[i, 0], y=st[i, 1], w=st[i, 2], h=st[i, 3], a=st[i, 4],
                      cx=cen[i, 0], cy=cen[i, 1]) for i in range(1, n)]


def label_band(comps, Lp, lab, H):
    """y-range of the printed label line: the lowest horizontal run of small,
    dark, text-sized blobs in the panel."""
    glyphs = []
    for c in comps:
        if 5 <= c['h'] <= 18 and c['w'] <= 90 and c['a'] >= 6 and c['cy'] > H * 0.45:
            ys, xs = np.nonzero(lab[c['y']:c['y'] + c['h'], c['x']:c['x'] + c['w']] == c['i'])
            if np.percentile(Lp[c['y'] + ys, c['x'] + xs, 0], 15) < 35:
                glyphs.append(c)
    if len(glyphs) < 3:
        return None
    ys = np.array([g['cy'] for g in glyphs])
    # the densest 10-px window of glyph centres is the label line
    best = max(range(int(ys.min()), int(ys.max()) + 1),
               key=lambda y0: ((ys >= y0) & (ys < y0 + 10)).sum())
    sel = [g for g in glyphs if best - 3 <= g['cy'] < best + 13]
    return min(g['y'] for g in sel), max(g['y'] + g['h'] for g in sel)


def box_gap(a, b):
    dx = max(a['x0'] - b['x1'], b['x0'] - a['x1'], 0)
    dy = max(a['y0'] - b['y1'], b['y0'] - a['y1'], 0)
    return float(np.hypot(dx, dy))


def group_drawings(comps, n_expected, min_area=4, attach=30):
    """One group per drawing: every big blob starts a group, small detached bits
    join the nearest group, and the closest groups merge until the count
    matches the labels. Groups come back ordered left to right."""
    comps = [c for c in comps if c['a'] >= min_area]
    for c in comps:
        c.update(x0=c['x'], x1=c['x'] + c['w'], y0=c['y'], y1=c['y'] + c['h'])
    big = max(c['a'] for c in comps)
    groups = [dict(ids=[c['i']], a=c['a'], x0=c['x0'], x1=c['x1'], y0=c['y0'], y1=c['y1'])
              for c in comps if c['a'] >= big * 0.08]
    for c in comps:
        if c['a'] >= big * 0.08:
            continue
        g = min(groups, key=lambda g: box_gap(g, c))
        if box_gap(g, c) <= attach:
            g['ids'].append(c['i']); g['a'] += c['a']
            g['x0'], g['x1'] = min(g['x0'], c['x0']), max(g['x1'], c['x1'])
            g['y0'], g['y1'] = min(g['y0'], c['y0']), max(g['y1'], c['y1'])
    while len(groups) > n_expected:
        pairs = [(box_gap(groups[i], groups[j]) + 1e-6 * min(groups[i]['a'], groups[j]['a']), i, j)
                 for i in range(len(groups)) for j in range(i + 1, len(groups))]
        _, i, j = min(pairs)
        a, b = groups[i], groups[j]
        groups[i] = dict(ids=a['ids'] + b['ids'], a=a['a'] + b['a'],
                         x0=min(a['x0'], b['x0']), x1=max(a['x1'], b['x1']),
                         y0=min(a['y0'], b['y0']), y1=max(a['y1'], b['y1']))
        del groups[j]
    return sorted(groups, key=lambda g: (g['x0'] + g['x1']) / 2)


def fill_thin_holes(mask):
    """Enclosed gaps too thin to hold a 3x3 patch of background are the grey
    anti-aliasing between two drawn colours (round pupils, between the eyes),
    not real see-through gaps: fill them."""
    inv = (~mask).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(inv, connectivity=4)
    core = cv2.erode(inv, np.ones((3, 3), np.uint8))
    has_core = np.zeros(n, bool)
    has_core[np.unique(lab[core > 0])] = True
    Hm, Wm = mask.shape
    out = mask.copy()
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if x == 0 or y == 0 or x + w == Wm or y + h == Hm:
            continue                      # the outside
        if not has_core[i] or a <= 6:
            out[lab == i] = True
    return out


def matte(bgr, L, F, d, mask):
    """Soft alpha + clean edge colour for one drawing (mask = hard 0/1).

    Pixels near the silhouette are explained as a blend of the background field
    B and the nearby drawing colour Fg: alpha is the projection of I-B onto
    Fg-B. A pixel the blend cannot explain (a pupil or an outline right on the
    edge) keeps its own colour and the hard mask. White halos from the source's
    sharpening project to alpha ~0 and disappear."""
    m8 = mask.astype(np.uint8)
    k3 = np.ones((3, 3), np.uint8)
    inner = cv2.erode(m8, k3, iterations=2)
    ring = (cv2.dilate(m8, k3, iterations=1) > 0) & (inner == 0)
    Lf = smooth_fill(L, inner.astype(np.float32), sigmas=(1.5, 3, 6, 12, 24))
    diff = L - F
    fb = Lf - F
    den = (fb * fb).sum(2)
    a = np.clip((diff * fb).sum(2) / np.maximum(den, 1e-6), 0, 1)
    recon = F + a[..., None] * fb
    err = np.linalg.norm(L - recon, axis=2)
    blend = (den > 36) & (err < 12)
    a = np.where(blend, a, m8.astype(np.float32))
    alpha = np.where(inner > 0, 1.0, np.where(ring, a, 0.0))
    alpha[alpha < 0.05] = 0
    alpha[alpha > 0.96] = 1
    # specks left over from labels or noise
    n, lab, st, _ = cv2.connectedComponentsWithStats((alpha > 0).astype(np.uint8), connectivity=8)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < 15:
            alpha[lab == i] = 0
    col = bgr.astype(np.float32)
    edge = ring & blend & (alpha > 0)
    Fb = cv2.cvtColor(Lf, cv2.COLOR_LAB2BGR) * 255
    col[edge] = Fb[edge]
    return col.clip(0, 255).astype(np.uint8), (alpha * 255 + 0.5).astype(np.uint8)


def save_sprite(path, col, alpha, rect_in_sheet):
    ys, xs = np.nonzero(alpha)
    y0, y1 = max(ys.min() - PAD, 0), min(ys.max() + PAD + 1, alpha.shape[0])
    x0, x1 = max(xs.min() - PAD, 0), min(xs.max() + PAD + 1, alpha.shape[1])
    rgba = np.dstack([col[y0:y1, x0:x1], alpha[y0:y1, x0:x1]])
    rgba[rgba[..., 3] == 0, :3] = 0
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cv2.imwrite(path, rgba, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    ox, oy = rect_in_sheet
    return [int(ox + x0), int(oy + y0), int(x1 - x0), int(y1 - y0)], rgba


def anchors(rgba):
    """Feet anchor (bottom centre of the lowest solid rows) and centre."""
    a = rgba[..., 3] > 128
    ys, xs = np.nonzero(a)
    yb = ys.max()
    low = xs[ys >= yb - 3]
    return dict(feet=[int(round((low.min() + low.max()) / 2)), int(yb)],
                center=[int(round(xs.mean())), int(round(ys.mean()))])


def panel_rects(cfg, W, H):
    hd, split = cfg['headers'], cfg['split']
    bottoms = [h[0] for h in hd[1:]] + [H]
    rects = {}
    names = [['turnaround', 'head'], ['mouths'], ['expressions'], ['gestures'], ['poses', 'extras']]
    for r, row in enumerate(names):
        y0, y1 = hd[r][1] + 1, bottoms[r] - 1
        if len(row) == 1:
            rects[row[0]] = (0, y0, W, y1)
        else:
            sx = split[0] if r == 0 else split[1]
            rects[row[0]] = (0, y0, sx, y1)
            rects[row[1]] = (sx, y0, W, y1)
    return rects


def cut_panel(bgr, L, F, d, rect, labels, outdir, debug=None, clip_bottom=None):
    x0, y0, x1, y1 = rect
    if clip_bottom:
        y1 = min(y1, clip_bottom)
    sub = (slice(y0, y1), slice(x0, x1))
    Bp, Lp, Fp, dp = bgr[sub], L[sub], F[sub], d[sub]
    H, W = dp.shape
    fg = hysteresis(dp)
    fg[:4], fg[-4:], fg[:, :4], fg[:, -4:] = False, False, False, False   # panel frame
    runs = dividers(dp)
    fg = cut_dividers(fg, dp, runs, full=len(runs) == len(labels) - 1)
    fg &= ~thin_lines(fg, H, W)
    lab, comps = components(fg)
    band = label_band(comps, Lp, lab, H)
    if band:
        # label strokes that touch a drawing: thin dark strokes inside the band
        dark = ((Lp[..., 0] < 45) & (np.hypot(Lp[..., 1], Lp[..., 2]) < 20)).astype(np.uint8)
        solid = cv2.dilate(cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((4, 4), np.uint8)), np.ones((3, 3), np.uint8))
        rows = np.zeros_like(fg)
        rows[max(band[0] - 2, 0):band[1] + 3] = True
        text = (dark > 0) & (solid == 0) & rows
        halo = cv2.dilate(text.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        fg &= ~(text | (halo & (np.hypot(Lp[..., 1], Lp[..., 2]) < 20) & rows))
        lab, comps = components(fg)
    keep = []
    for c in comps:
        if band and band[0] - 2 <= c['cy'] <= band[1] + 2 and c['h'] <= 20 and c['a'] < 500:
            continue                      # a label glyph
        if min(c['w'], c['h']) <= 2:
            continue                      # frame / divider remains
        if min(c['w'], c['h']) <= 12:
            ys, xs = np.nonzero(lab[c['y']:c['y'] + c['h'], c['x']:c['x'] + c['w']] == c['i'])
            if np.percentile(dp[c['y'] + ys, c['x'] + xs], 90) < 16:
                continue                  # faint line scrap
        keep.append(c)
    if os.environ.get('CUT_DEBUG'):
        print('  %s: label band %s, %d blobs kept of %d' % (os.path.basename(outdir), band, len(keep), len(comps)))
    groups = group_drawings(keep, len(labels))
    if len(groups) != len(labels):
        raise SystemExit('%s: found %d drawings, expected %d' % (outdir, len(groups), len(labels)))
    out = {}
    for g, name in zip(groups, labels):
        mask = fill_thin_holes(np.isin(lab, g['ids']))
        col, alpha = matte(Bp, Lp, Fp, dp, mask)
        path = os.path.join(outdir, slug(name) + '.png')
        box, rgba = save_sprite(path, col, alpha, (x0, y0))
        out[slug(name)] = dict(label=name, file=os.path.relpath(path, EP), sheet_rect=box,
                               size=[box[2], box[3]], **anchors(rgba))
        if debug is not None:
            bx, by, bw, bh = box
            cv2.rectangle(debug, (bx, by), (bx + bw - 1, by + bh - 1), (0, 0, 255), 1)
            cv2.putText(debug, slug(name)[:14], (bx + 1, by + 9), cv2.FONT_HERSHEY_PLAIN, 0.7, (0, 0, 255), 1)
    if debug is not None and band:
        cv2.rectangle(debug, (x0, y0 + band[0]), (x1 - 1, y0 + band[1]), (255, 0, 255), 1)
    return out


def cut_parts(bgr, L, F, d, rect, parts, outdir, debug=None):
    """Extra Details panel: each named part is the blob(s) whose bounding box
    holds one of its points (the smallest such box, so a label never wins)."""
    x0, y0, x1, y1 = rect
    sub = (slice(y0, y1), slice(x0, x1))
    Bp, Lp, Fp, dp = bgr[sub], L[sub], F[sub], d[sub]
    H, W = dp.shape
    fg = hysteresis(dp)
    fg[:4], fg[-4:], fg[:, :4], fg[:, -4:] = False, False, False, False
    fg = cut_dividers(fg, dp, dividers(dp))
    fg &= ~thin_lines(fg, H, W)
    lab, comps = components(fg)
    out = {}
    for name, pts in parts.items():
        ids = []
        for px, py in pts:
            px, py = px - x0, py - y0
            hits = [c for c in comps if c['x'] <= px < c['x'] + c['w'] and c['y'] <= py < c['y'] + c['h'] and c['a'] >= 20]
            if not hits:
                raise SystemExit('%s: no blob at %s' % (name, (px + x0, py + y0)))
            ids.append(min(hits, key=lambda c: c['w'] * c['h'])['i'])
        mask = fill_thin_holes(np.isin(lab, ids))
        col, alpha = matte(Bp, Lp, Fp, dp, mask)
        path = os.path.join(outdir, name + '.png')
        box, rgba = save_sprite(path, col, alpha, (x0, y0))
        out[name] = dict(label=name.replace('_', ' '), file=os.path.relpath(path, EP), sheet_rect=box,
                         size=[box[2], box[3]], **anchors(rgba))
        if debug is not None:
            bx, by, bw, bh = box
            cv2.rectangle(debug, (bx, by), (bx + bw - 1, by + bh - 1), (0, 0, 255), 1)
    return out


def run(char, layout, only=None):
    cfg = layout['characters'][char]
    bgr = cv2.imread(os.path.join(SHEETS, cfg['sheet']))
    Hs, Ws = bgr.shape[:2]
    L = to_lab(bgr)
    F, d = background(L)
    rects = panel_rects(cfg, Ws, Hs)
    debug = bgr.copy()
    index = dict(name=cfg['name'], sheet='sheets/' + cfg['sheet'], sprites={})
    for panel, rect in rects.items():
        if only and panel not in only:
            continue
        if panel == 'extras':
            index['sprites']['parts'] = cut_parts(bgr, L, F, d, rect, cfg['parts'],
                                                  os.path.join(OUTDIR, char, 'parts'), debug)
            continue
        labels = cfg.get('labels', {}).get(panel) or layout['labels'][panel]
        index['sprites'][panel] = cut_panel(bgr, L, F, d, rect, labels,
                                            os.path.join(OUTDIR, char, panel), debug,
                                            cfg.get('clip_bottom', {}).get(panel))
        cv2.rectangle(debug, rect[:2], (rect[2] - 1, rect[3] - 1), (0, 255, 0), 1)
    os.makedirs(os.path.join(OUTDIR, char), exist_ok=True)
    with open(os.path.join(OUTDIR, char, 'index.json'), 'w') as f:
        json.dump(index, f, indent=1)
    os.makedirs(os.path.join(ROOT, 'out'), exist_ok=True)
    cv2.imwrite(os.path.join(ROOT, 'out', 'cut_%s.png' % char), debug)
    n = sum(len(v) for v in index['sprites'].values())
    print('%s: %d sprites' % (char, n))


if __name__ == '__main__':
    layout = json.load(open(os.path.join(SHEETS, 'layout.json')))
    chars = [a for a in sys.argv[1:] if a in layout['characters']] or list(layout['characters'])
    for c in chars:
        run(c, layout)
