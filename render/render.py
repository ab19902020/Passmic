import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
ASSETS = _os.path.join(ROOT, 'assets'); MASKS = _os.path.join(ROOT, 'masks'); DATA = _os.path.join(ROOT, 'data'); SOURCE = _os.path.join(ROOT, 'source'); OUTDIR = _os.path.join(ROOT, 'out'); TOOLS = _os.path.join(ROOT, 'tools'); FONTS = _os.path.join(ROOT, 'fonts')
import cv2, numpy as np, json, math, sys
from PIL import Image, ImageDraw, ImageFont

A = ASSETS + ''
OUTD = OUTDIR + ''
RS = float(_os.environ.get('PASSMIC_SCALE', '1'))        # render scale: 1 = 1280x720, 1.5 = 1080p, 3 = 4K
OUT_FPS = float(_os.environ.get('PASSMIC_FPS', '24'))     # output frame rate (motion is continuous in time)
OW, OH = int(round(1280 * RS)), int(round(720 * RS))
FPS = 24  # rate of the analysis data (audio features, mouth curve)
BPM, PH, DUR = 145.0947, 0.15507, 225.54
P = 60 / BPM
beatT = lambda n: PH + n * P
SW, SH = 2229, 1254
BASE = OW / SW * 1.03

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def lerp(a, b, t): return a + (b - a) * t
def smooth(t): t = clamp(t); return t * t * (3 - 2 * t)
def ease(t): t = clamp(t); return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2
def frac(x): return x - math.floor(x)
def spike(b, s=6.0): return math.exp(-s * frac(b))
def hsh(n):
    n = (int(n) * 374761393 + 668265263) & 0xffffffff
    n = ((n ^ (n >> 13)) * 1274126177) & 0xffffffff
    return ((n ^ (n >> 16)) & 0xffffffff) / 4294967296

feat = np.load(DATA + '/audio_feat.npz')
VOC, EN = feat['voc'], feat['en']
def fval(arr, t):
    x = clamp(t * FPS, 0, len(arr) - 1.001); i = int(x); f = x - i
    return float(arr[i] * (1 - f) + arr[i + 1] * f)

meta = json.load(open(f'{A}/meta.json'))
def rgba(path):
    im = cv2.imread(path, -1).astype(np.float32)
    im[..., :3] *= im[..., 3:4] / 255.0
    return im
SPR = {n: dict(body=rgba(f'{A}/{n}_body.png'), head=rgba(f'{A}/{n}_head.png'), **meta[n]) for n in meta}
HAND = {'carra1': (895, 752), 'carra2': (690, 300), 'nev1': (1030, 600), 'nev2': (1455, 380), 'keane1': (1405, 630), 'keane2': (790, 525), 'carra5': (720, 645), 'keane5': (722, 522), 'nev5': (1050, 570), 'carra4': (385, 473), 'keane4': (923, 517), 'nev4': (1224, 456)}
for n, s in SPR.items():
    hx, hy = HAND[n]; s['hand'] = (hx - s['x0'], hy - s['y0'])

CAST = [dict(id='carra', name='CARRA', col=(75, 68, 224), A='carra1', B='carra2', C='carra5', D='carra4'),
        dict(id='nev', name='NEV', col=(197, 211, 25), A='nev1', B='nev2', C='nev5', D='nev4'),
        dict(id='keane', name='KEANE', col=(51, 178, 242), A='keane1', B='keane2', C='keane5', D='keane4')]
for c in CAST:
    a = SPR[c['A']]
    c['foot'] = (a['x0'] + a['foot'][0], a['y0'] + a['foot'][1])
    c['k'] = {'A': 1.0, 'B': a['ry'] / SPR[c['B']]['ry'], 'C': a['ry'] / SPR[c['C']]['ry'], 'D': a['ry'] / SPR[c['D']]['ry']}
CI = {c['id']: i for i, c in enumerate(CAST)}
MOUTH = json.load(open(f'{A}/mouths.json'))
def _ol_rim(img):
    a = img[..., 3]
    ol = cv2.GaussianBlur(cv2.dilate(a, np.ones((3, 3), np.uint8)), (0, 0), 0.8)
    o = np.zeros_like(img); o[..., 3] = np.clip(ol * 0.6, 0, 255)
    edge = np.clip(a - cv2.erode(a, np.ones((5, 5), np.uint8)), 0, 255)
    edge = cv2.GaussianBlur(edge, (0, 0), 1.0) * (a / 255)
    r = np.zeros_like(img); r[..., 0] = r[..., 1] = r[..., 2] = edge; r[..., 3] = edge
    return o, r
for n_, sp_ in SPR.items():
    sp_['body_ol'], sp_['body_rim'] = _ol_rim(sp_['body']); sp_['head_ol'], sp_['head_rim'] = _ol_rim(sp_['head'])
_yy, _xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
VIGNETTE = (1 - 0.3 * (((_xx - OW / 2) / (OW / 2)) ** 2 + ((_yy - OH / 2) / (OH / 2)) ** 2) * 0.55)[..., None]
HZ = 760
def _grid_back():
    img = np.zeros((SH, SW, 3), np.float32); ys = np.arange(SH, dtype=np.float32)[:, None, None]
    top = np.array([50, 6, 30], np.float32); mid = np.array([140, 30, 170], np.float32); hz = np.array([120, 105, 255], np.float32)
    t_ = np.clip(ys / HZ, 0, 1)
    img[:] = np.where(t_ < 0.62, top + (mid - top) * (t_ / 0.62), mid + (hz - mid) * ((t_ - 0.62) / 0.38))
    rng = np.random.RandomState(4)
    for _ in range(220):
        x, y = rng.randint(0, SW), rng.randint(0, int(HZ * 0.6)); v = 120 + rng.randint(0, 135)
        cv2.circle(img, (x, y), 1 + rng.randint(0, 2), (v, v, v), -1, cv2.LINE_AA)
    cx, cy, R = SW // 2, HZ - 70, 330
    yy, xx = np.mgrid[0:SH, 0:SW].astype(np.float32)
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2); inside = d < R
    tt = np.clip((yy - (cy - R)) / (2 * R), 0, 1)[..., None]
    sun = np.array([70, 225, 255], np.float32) * (1 - tt) + np.array([150, 50, 255], np.float32) * tt
    band = (yy > cy - 20) & ((((yy - (cy - 20)) / 30).astype(int) % 2) == 1) & ((yy - (cy - 20)) % 30 < 6 + (yy - cy) / 18)
    m = (inside & ~band)[..., None]
    img = np.where(m, sun, img)
    glow = np.clip(1 - d / (R * 2.2), 0, 1)[..., None] ** 2
    img += glow * np.array([120, 60, 255], np.float32) * 0.5
    for k, (amp, colr) in enumerate(((210, (70, 20, 60)), (140, (45, 12, 40)))):
        xs = np.arange(0, SW + 60, 60); pts = [(0, HZ)] + [(int(x), int(HZ - amp * (0.35 + 0.65 * abs(math.sin(x * 0.004 + k * 1.7) * math.cos(x * 0.0013 + k))))) for x in xs] + [(SW, HZ)]
        cv2.fillPoly(img, [np.array(pts, np.int32)], colr)
        cv2.polylines(img, [np.array(pts[1:-1], np.int32)], False, (220, 80, 255) if k == 0 else (255, 220, 60), 3, cv2.LINE_AA)
    img[HZ:] = np.array([30, 4, 38], np.float32)
    return img
GRID_BACK = _grid_back()
GT_W, GT_H = 1024, 640
G_SRC = np.float32([[0, 0], [GT_W, 0], [GT_W, GT_H], [0, GT_H]])
G_DST = np.float32([[SW / 2 - 8 * 110, HZ + 8], [SW / 2 + 8 * 110, HZ + 8], [SW / 2 + 1140 * 11, 1900], [SW / 2 - 1140 * 11, 1900]])
H_GRID = cv2.getPerspectiveTransform(G_SRC, G_DST)
GRID_BASE = np.zeros((GT_H, GT_W, 3), np.float32)
for gx in range(0, GT_W + 1, 32): cv2.line(GRID_BASE, (gx, 0), (gx, GT_H), (255, 60, 220), 3, cv2.LINE_AA)
def _pitch_back():
    img = np.zeros((SH, SW, 3), np.float32); ys = np.arange(SH, dtype=np.float32)[:, None, None]
    img[:] = np.array([45, 18, 8], np.float32) * (1 - np.clip(ys / 700, 0, 1)) + np.array([30, 28, 40], np.float32) * np.clip(ys / 700, 0, 1)
    rng = np.random.RandomState(7)
    for tier in range(9):
        y0 = 230 + tier * 48
        cv2.line(img, (0, y0), (SW, y0 + 6), (55, 50, 70), 3)
        for _ in range(170):
            x = rng.randint(0, SW); y = y0 + rng.randint(6, 44)
            c = [(60, 60, 200), (200, 200, 200), (60, 60, 220), (50, 140, 220), (150, 150, 150)][rng.randint(0, 5)]
            cv2.circle(img, (x, y), 5 + rng.randint(0, 3), tuple(v * (0.45 + 0.35 * rng.rand()) for v in c), -1, cv2.LINE_AA)
    cv2.fillPoly(img, [np.array([(0, 0), (SW, 0), (SW, 150), (SW // 2, 205), (0, 150)], np.int32)], (22, 18, 28))
    for tx in (230, SW - 230):
        cv2.rectangle(img, (tx - 8, 140), (tx + 8, 700), (40, 40, 50), -1)
        for r_ in range(3):
            for c_ in range(5): cv2.rectangle(img, (tx - 95 + c_ * 38, 70 + r_ * 24), (tx - 65 + c_ * 38, 88 + r_ * 24), (235, 245, 255), -1)
    return img
PITCH_BACK = _pitch_back()
PT_W, PT_H = 1600, 800
PITCH_TEX = np.zeros((PT_H, PT_W, 3), np.float32)
for i in range(12): PITCH_TEX[:, i * PT_W // 12:(i + 1) * PT_W // 12] = (40, 125, 45) if i % 2 else (32, 105, 36)
cv2.line(PITCH_TEX, (0, 40), (PT_W, 40), (235, 235, 235), 6); cv2.line(PITCH_TEX, (PT_W // 2, 40), (PT_W // 2, PT_H), (235, 235, 235), 6)
cv2.circle(PITCH_TEX, (PT_W // 2, 420), 190, (235, 235, 235), 6); cv2.circle(PITCH_TEX, (PT_W // 2, 420), 9, (235, 235, 235), -1)
H_PITCH = cv2.getPerspectiveTransform(np.float32([[0, 0], [PT_W, 0], [PT_W, PT_H], [0, PT_H]]), np.float32([[-900, 700], [3130, 700], [6200, 1560], [-3970, 1560]]))
def scene_for(b):
    s = section(b)
    if s == 'verse3': return 'grid'      # "Anger creates engagement": the online world
    if b >= BRIDGE_B: return 'pitch'     # "You and Keane at Old Trafford" through the final chorus
    return 'studio'
for n_, sp_ in SPR.items():
    sp_['name'] = n_
    if n_ in MOUTH: sp_['mouth'] = MOUTH[n_]
def jaw_open(img, mx, my, rx, open_px, mw=None, span=None, paint=True):
    """Stretch the lower face down by open_px (no tearing) and paint a mouth of half-width mw.
    A negative open_px squeezes the band [my, my+span] shut instead (paint=False)."""
    if abs(open_px) < 0.6: return img
    H_, W_ = img.shape[:2]
    mw = mw or 0.3 * rx; span = span or 1.2 * rx
    x0 = int(max(0, mx - rx)); x1 = int(min(W_, mx + rx + 1)); y0 = int(max(0, my))
    if x1 <= x0 or y0 >= H_ - 2: return img
    out = img.copy()
    xs = np.arange(x0, x1, dtype=np.float32); f = np.clip(1 - ((xs - mx) / rx) ** 2, 0, 1)
    D = (open_px * f)[None, :]
    ys = np.arange(y0, H_, dtype=np.float32)[:, None]
    rel = ys - my
    src = np.where(rel < span + D, my + rel * span / (span + D), ys - D)
    mapx = np.tile(xs, (H_ - y0, 1)).astype(np.float32); mapy = src.astype(np.float32)
    reg = cv2.remap(img, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    if not paint:
        out[y0:, x0:x1] = reg; return out
    d0 = open_px
    # anti-aliased mouth: dark interior + tongue (soft 1.5px edges so close-ups stay clean)
    ry_ = max(1.0, d0 * 0.55); cy_ = my + d0 * 0.45
    e = np.sqrt(((xs[None, :] - mx) / mw) ** 2 + ((ys - cy_) / ry_) ** 2)
    a_m = np.clip((1 - e) * min(mw, ry_) / 1.5, 0, 1) * np.clip((reg[..., 3] - 60) / 80, 0, 1)
    et = np.sqrt(((xs[None, :] - mx) / (0.62 * mw)) ** 2 + ((ys - (cy_ + ry_ * 0.75)) / (0.62 * ry_)) ** 2)
    a_t = np.clip((1 - et) * min(0.62 * mw, 0.62 * ry_) / 1.5, 0, 1) * a_m
    a_m = a_m[..., None]; a_t = a_t[..., None]
    reg[..., :3] = reg[..., :3] * (1 - a_m) + np.array((28, 16, 70), np.float32) * a_m
    reg[..., :3] = reg[..., :3] * (1 - a_t) + np.array((95, 85, 205), np.float32) * a_t
    reg[..., 3:4] = np.maximum(reg[..., 3:4], 255 * a_m)
    out[y0:, x0:x1] = reg
    return out
def _find_eyes(spr):
    """Eye whites of a head sprite (holes filled, grown over the outline) + per-column top/bottom."""
    h = np.clip(spr['head'][..., :3] * 255 / np.maximum(spr['head'][..., 3:4], 1), 0, 255).astype(np.uint8)
    a = spr['head'][..., 3]; hsv = cv2.cvtColor(h, cv2.COLOR_BGR2HSV); cx, cy = spr['headc']; ry = spr['ry']
    wht = ((hsv[..., 1] < 40) & (hsv[..., 2] > 215) & (a > 200)).astype(np.uint8)
    wht[int(cy + 0.25 * ry):] = 0; wht[:max(0, int(cy - 0.6 * ry))] = 0
    n_, lab, st, _ = cv2.connectedComponentsWithStats(wht, 8)
    if n_ < 2: return None
    m = np.zeros_like(wht)
    for i in sorted(range(1, n_), key=lambda i: -st[i, 4])[:2]:
        if st[i, 4] < 0.15 * st[1:, 4].max(): continue
        cs, _ = cv2.findContours((lab == i).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(m, cs, -1, 1, -1)
    m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    ys, xs = np.where(m > 0); x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    mc = m[y0:y1, x0:x1] > 0
    top = np.where(mc.any(0), mc.argmax(0), 0).astype(np.float32); bot = np.where(mc.any(0), mc.shape[0] - mc[::-1].argmax(0), 0).astype(np.float32)
    sk = (hsv[..., 0] >= 5) & (hsv[..., 0] <= 22) & (hsv[..., 1] > 70) & (hsv[..., 2] > 170) & (a > 250)
    sk[int(cy + 0.1 * ry):] = False
    skin = np.median(h[sk], axis=0).astype(np.float32) if sk.sum() > 30 else np.array((130, 170, 235), np.float32)
    return dict(x0=int(x0), y0=int(y0), m=mc, top=top, bot=bot, skin=skin)
def blink_eyes(img, ey, c):
    """Close the eyes by fraction c (0 open .. 1 shut): skin lid slides down with a dark lid line."""
    if ey is None or c < 0.05: return img
    out = img.copy(); x0, y0, mc = ey['x0'], ey['y0'], ey['m']; H_, W_ = mc.shape
    yy = np.arange(H_, dtype=np.float32)[:, None]
    edge = ey['top'][None, :] + c * (ey['bot'] - ey['top'])[None, :] * 1.05
    lid = np.clip(edge - yy + 0.5, 0, 1) * mc
    line = np.clip(1.6 - np.abs(yy - (edge - 3 * c)), 0, 1) * mc * min(1.0, c * 3)
    reg = out[y0:y0 + H_, x0:x0 + W_]
    reg[..., :3] = reg[..., :3] * (1 - lid[..., None]) + ey['skin'] * lid[..., None]
    reg[..., :3] = reg[..., :3] * (1 - line[..., None]) + np.array((32, 26, 40), np.float32) * line[..., None]
    return out
def _blink_times(seed):
    ts_, t_ = [], 0.8 + 2 * hsh(seed)
    for k in range(400):
        ts_.append(t_)
        if hsh(seed * 31 + k) < 0.18: ts_.append(t_ + 0.32)  # occasional double blink
        t_ += 2.0 + 3.2 * hsh(seed * 17 + k * 7 + 3)
    return np.array(ts_)
BLINKS = {cid: _blink_times(i * 101 + 7) for i, cid in enumerate(('carra', 'nev', 'keane'))}
def blink_amt(cid, t):
    bt = BLINKS[cid]; i = np.searchsorted(bt, t) - 1
    if i < 0: return 0.0
    u = (t - bt[i]) / 0.2
    return 0.0 if u >= 1 else (u / 0.35 if u < 0.35 else 1 - (u - 0.35) / 0.65)
MOUTH_REST = 0.35  # the artwork's drawn (half-open) mouth corresponds to this opening
def mouth_shape(img, mo, o, closed_art, wid):
    """Pose the mouth for opening o (0 = shut .. ~1.2 = wide). Carra/Gary are drawn mid-shout, so below
    MOUTH_REST the drawn mouth is squeezed shut (lower face lifts); above it the jaw drops open.
    Keane is drawn with his mouth closed, so he only ever opens."""
    h = 0.085 * mo['hh']
    if closed_art: return jaw_open(img, mo['mx'], mo['my'], 0.28 * mo['hw'], o * 0.12 * mo['hh'], mw=0.1 * mo['hw'] * wid, span=0.24 * mo['hh'])
    if o >= MOUTH_REST:
        return jaw_open(img, mo['mx'], mo['my'], 0.28 * mo['hw'], (o - MOUTH_REST) * 0.16 * mo['hh'], mw=0.1 * mo['hw'] * wid, span=0.24 * mo['hh'])
    c = 0.82 * (1 - o / MOUTH_REST)
    return jaw_open(img, mo['mx'], mo['my'] - 0.5 * h, 0.3 * mo['hw'], -c * h, span=h, paint=False)
_MC = np.load(DATA + '/mouth_curve.npz'); MOPEN, MWID = _MC['open'], _MC['width']
MWHO = _MC['who'] if 'who' in _MC else np.full(len(MOPEN), 2, np.int8)
WHO_ID = {3: 'nev', 4: 'carra', 5: 'keane'}
def mouth_val(t, cid_or_i, amp):
    return fval(MOPEN, t) * amp
def solo_voice(t, lead):
    """The one pundit voicing the vocal at t (None for choruses/instrumental)."""
    w = int(MWHO[int(clamp(t * FPS, 0, len(MWHO) - 1))])
    return lead if w == 1 else WHO_ID.get(w)
FOOT_X = {}
def listen_dir(cid, t, ms):
    """-1..1: the others tilt their heads towards whoever sings a solo line (eased over ~0.35 s)."""
    if not FOOT_X: FOOT_X.update({c['id']: c['foot'][0] for c in CAST})
    lead = ms.get('holder') or (ms.get('fly') or (0, 0, 'nev'))[2]; acc = 0.0
    for k in range(8):
        sp = solo_voice(t - k * 0.05, lead)
        if sp and sp != cid: acc += 1 if FOOT_X[sp] > FOOT_X[cid] else -1
    return acc / 8
def voice_amp(t, cid, lead):
    """How much pundit `cid` mouths the vocal at time t: the lead (mic holder) sings verses,
    everyone sings choruses, quoted/spoken lines belong to one pundit, everyone else keeps quiet."""
    w = int(MWHO[int(clamp(t * FPS, 0, len(MWHO) - 1))])
    if w == 1: return 1.0 if cid == lead else 0.0
    if w == 2: return 1.0 if cid == lead else 0.85
    return 1.0 if WHO_ID.get(w) == cid else 0.0
def mouth_w(t): return fval(MWID, t)
for n_, (ux_, uy_) in {'nev1': (1290, 335), 'nev2': (1082, 300), 'nev5': (1253, 447), 'nev4': (1224, 456)}.items(): SPR[n_]['up'] = (ux_ - SPR[n_]['x0'], uy_ - SPR[n_]['y0'])

plate = cv2.imread(f'{A}/plate_rows.png').astype(np.float32)
hole = cv2.imread(f'{A}/hole.png', 0).astype(np.float32) / 255
holeb = cv2.GaussianBlur(hole, (0, 0), 25)[..., None]
BACK = cv2.GaussianBlur(plate, (0, 0), 3.2) * (1 - holeb) + cv2.GaussianBlur(plate, (0, 0), 16) * holeb
BACK = np.clip(BACK * 0.86, 0, 255).astype(np.float32)

FLOOR_POLY = np.array([(0, 1000), (560, 874), (1800, 868), (2229, 965), (2229, 1254), (0, 1254)], np.float32)
FCOLS, FROWS, TPX = 16, 7, 48
yy, xx = np.mgrid[0:TPX, 0:TPX].astype(np.float32)
dd = np.maximum(np.abs(xx - TPX / 2 + 0.5), np.abs(yy - TPX / 2 + 0.5)) / (TPX / 2)
TILE = (np.clip((0.93 - dd) / 0.12, 0, 1) * (0.55 + 0.45 * (1 - dd ** 2)))[..., None].astype(np.float32)
FL_SRC = np.float32([[0, 0], [FCOLS * TPX, 0], [FCOLS * TPX, FROWS * TPX], [0, FROWS * TPX]])
FL_DST = np.float32([[-900, 868], [3130, 868], [5600, 1560], [-3370, 1560]])
H_FLOOR = cv2.getPerspectiveTransform(FL_SRC, FL_DST)
TILE_TEX = np.tile(TILE, (FROWS, FCOLS, 1))

def make_beam(L=700, W=200):
    y = np.arange(L, dtype=np.float32)[:, None]; x = np.arange(W, dtype=np.float32)[None, :] - W / 2
    half = 5 + (W / 2 - 5) * y / L
    b = np.clip(1 - np.abs(x) / half, 0, 1) ** 1.5 * (1 - y / L) ** 1.2
    return cv2.GaussianBlur(b.astype(np.float32), (0, 0), 3)
BEAM = make_beam()
LIGHTS = [((766, 15), (255, 110, 40)), ((877, 41), (40, 140, 255)), ((992, 73), (255, 60, 220)), ((1375, 77), (255, 220, 60)), ((1413, 43), (40, 160, 255)), ((1549, 26), (255, 110, 30))]
PAL = [(165, 62, 255), (214, 227, 25), (39, 182, 255), (255, 92, 139), (60, 255, 140)]

def to_bgra(im):
    a = np.array(im).astype(np.float32); a = a[..., [2, 1, 0, 3]]; a[..., :3] *= a[..., 3:4] / 255; return a
def make_mic():
    im = Image.new('RGBA', (60, 190), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    dr.rounded_rectangle((20, 70, 40, 186), 8, fill=(24, 24, 30, 255), outline=(8, 8, 10, 255), width=3)
    dr.rectangle((18, 62, 42, 80), fill=(255, 182, 39, 255), outline=(8, 8, 10, 255), width=3)
    dr.ellipse((6, 4, 54, 66), fill=(200, 205, 215, 255), outline=(8, 8, 10, 255), width=4)
    for i in range(12, 54, 9): dr.line((i, 10, i, 60), fill=(150, 155, 168, 255), width=2)
    for j in range(14, 62, 9): dr.line((10, j, 50, j), fill=(150, 155, 168, 255), width=2)
    dr.ellipse((14, 12, 26, 24), fill=(255, 255, 255, 200))
    return to_bgra(im)
MIC = make_mic()

def blend_into(dst, src, x, y):
    h, w = src.shape[:2]; X0, Y0 = max(0, x), max(0, y); X1, Y1 = min(dst.shape[1], x + w), min(dst.shape[0], y + h)
    if X1 <= X0 or Y1 <= Y0: return
    s = src[Y0 - y:Y1 - y, X0 - x:X1 - x]; a = s[..., 3:4] / 255
    dst[Y0:Y1, X0:X1] = dst[Y0:Y1, X0:X1] * (1 - a) + s[..., :3] if dst.shape[2] == 3 else dst[Y0:Y1, X0:X1] * (1 - a) + s
SCREEN_SRC = {k: cv2.imread(f'{SOURCE}/{k}.png').astype(np.float32) for k in ('18346', '18348', '18349')}
SCREENS = []
SCR_X, SCR_Y, SCR_W, SCR_H = 1130, 30, 780, 300
GROUPS = json.load(open(f'{A}/groups.json'))
GSPR = {n: dict(body=rgba(f'{A}/{n}_body.png'), hs=[rgba(f'{A}/{n}_h{i}.png') for i in range(len(g['heads']))], **g) for n, g in GROUPS.items() if n != 'siralex'}
for n_, G0 in GSPR.items():
    if 'slices' in G0: G0['slc'] = [(a_, G0['body'][:, a_:b_].copy()) for a_, b_ in zip(G0['slices'][:-1], G0['slices'][1:])]
SIRALEX = rgba(f'{A}/siralex.png')
_G4 = [(135,242,52,70),(292,264,50,62),(468,267,52,64),(699,264,52,64),(894,255,52,66),(1029,274,50,64),(1273,280,50,62),(1485,258,50,62)]
if 'mgr4' in GSPR:
    g4 = GSPR['mgr4']
    for i_, hd_ in enumerate(g4['heads']):
        cx_, cy_, rx_, ry_ = _G4[i_]
        hd_['mouth'] = (cx_ - g4['x0'] - hd_['x'], cy_ + 0.5 * ry_ - g4['y0'] - hd_['y'], rx_ * 0.7, ry_)
        g4['hs'][i_] = np.pad(g4['hs'][i_], ((0, 18), (0, 0), (0, 0)))
CHAMP = [(60.8, 63.75), (196.68, 199.79), (203.14, 204.73)]
def champ_state(t):
    for c0, c1 in CHAMP:
        if c0 - 1.0 <= t < c1 + 0.8: return dict(c0=c0, c1=c1, pop=c0 + 0.12)
    return None
def _bottle(with_cork):
    im = Image.new('RGBA', (70, 240), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    dr.rounded_rectangle((8, 96, 62, 236), 14, fill=(22, 78, 44, 255), outline=(6, 20, 10, 255), width=3)
    dr.polygon([(9, 104), (25, 60), (45, 60), (61, 104)], fill=(22, 78, 44, 255), outline=(6, 20, 10, 255))
    dr.rectangle((25, 18, 45, 66), fill=(22, 78, 44, 255), outline=(6, 20, 10, 255), width=2)
    dr.polygon([(23, 8), (47, 8), (49, 70), (21, 70)], fill=(214, 176, 60, 255), outline=(120, 90, 20, 255))
    for yy_ in (22, 36, 50): dr.line((24, yy_, 46, yy_), fill=(170, 130, 30, 255), width=2)
    dr.rectangle((15, 140, 55, 196), fill=(245, 236, 210, 255), outline=(120, 100, 60, 255), width=2)
    dr.rectangle((15, 150, 55, 160), fill=(200, 40, 50, 255))
    dr.line((18, 110, 18, 226), fill=(90, 160, 110, 255), width=4)
    if with_cork:
        dr.rounded_rectangle((26, 0, 44, 12), 5, fill=(220, 190, 140, 255), outline=(110, 80, 40, 255), width=2)
    return to_bgra(im)
BOTTLE, BOTTLE_OPEN = _bottle(True), _bottle(False)
def _cork():
    im = Image.new('RGBA', (26, 30), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    dr.ellipse((1, 1, 25, 14), fill=(220, 190, 140, 255), outline=(110, 80, 40, 255), width=2)
    dr.rectangle((7, 8, 19, 28), fill=(205, 170, 120, 255), outline=(110, 80, 40, 255), width=2)
    return to_bgra(im)
CORK = _cork()
NEV_UP = {'nev1': (1290, 335), 'nev2': (1082, 300), 'nev5': (1253, 447), 'nev4': (1224, 456)}
RAIL_Y, RAIL_H = 585, 90
TOSS_H = 240  # apex height of the mic toss arc (source px)
def _led_board():
    # stadium LED board: soft light blobs + LED dot mask (no text), tiles horizontally
    w = 600; yy, xx = np.mgrid[0:RAIL_H, 0:w].astype(np.float32)
    T = np.clip(0.5 + 0.5 * np.sin(xx / w * 2 * np.pi * 3) * np.cos((yy - RAIL_H / 2) / RAIL_H * np.pi), 0, 1) ** 1.5
    D = np.clip(1.6 - np.hypot((xx % 5) - 2, (yy % 5) - 2) / 1.6, 0.25, 1.0)
    return T, D
LED_T, LED_D = _led_board()
def led_strip(xs_src, ys_src, b, t, hot):
    """Colour of the LED board at source coords (1-D arrays for columns / rows)."""
    TW = LED_T.shape[1]
    tx = ((xs_src - 40 + b * 18) % TW).astype(np.int32); ty = np.clip(ys_src - RAIL_Y, 0, RAIL_H - 1).astype(np.int32)
    T = LED_T[ty][:, tx][..., None]; D = LED_D[ty][:, tx][..., None]
    blk = int(b // 8)
    fg = np.array(PAL[blk % 5], np.float32); bg = np.array((24, 8, 20), np.float32)
    pulse = 0.8 + 0.2 * ((1 + math.cos(2 * math.pi * b)) / 2) ** 2
    return (fg * T + bg * (1 - T)) * D * pulse
MGSC = {'mgr4': 1.5, 'mgr5': 1.8}
def mgr_layer(b):
    s = section(b)
    if s in ('chorus', 'big', 'outro'): return 'mgr5'
    if s == 'final': return 'mgr5' if int((b - FINAL_B) // 16) % 2 else 'mgr4'
    return 'mgr4'
# Sections follow the song's lyric structure (beats; 1 beat = 0.4135 s)
CH1_B, BIG_B, BRIDGE_B, DROP_B, FINAL_B, OUTRO_B = 112, 264, 392, 436, 443, 520
SECTIONS = [(0, 'intro'), (16, 'reveal'), (40, 'verse'), (96, 'dip'), (CH1_B, 'chorus'), (176, 'verse2'), (BIG_B, 'big'), (298, 'verse3'),
            (374, 'breakdown'), (BRIDGE_B, 'bridge'), (DROP_B, 'drop'), (FINAL_B, 'final'), (OUTRO_B, 'outro'), (99999, 'end')]
HOT_SECTIONS = ('chorus', 'big', 'final')
def section(b):
    for i in range(len(SECTIONS) - 2, -1, -1):
        if b >= SECTIONS[i][0]: return SECTIONS[i][1]
    return 'intro'
def featured(b): return None
def _tb(t): return round((t - PH) / P * 2) / 2
# Mic passes follow who the lyric is about: Gary -> Carra for Jamie's lines, -> Keane for Roy's,
# back to Gary for the England days, then the outro handoffs. (start of throw in seconds)
TOSSES = [(72.25, 'nev', 'carra'), (86.15, 'carra', 'keane'), (99.3, 'keane', 'nev'), (219.15, 'nev', 'carra'), (221.4, 'carra', 'keane')]
MICEV = [(_tb(tt), a, b_) for tt, a, b_ in TOSSES]
GARY = [(77.4, 80.2), (143.5, 146.7), (155.2, 157.8), (160.0, 161.0), (162.2, 163.0), (220.1, 222.3)]
CUES = [(6.8, 16.8), (17.0, 222.3)]
def gary_amt(t):
    a = 0.0
    for g0, g1 in GARY: a = max(a, min(smooth((t - g0) / 0.3), smooth((g1 + 0.4 - t) / 0.4)))
    return a
def singing(t): return any(c0 <= t <= c1 for c0, c1 in CUES)
def mic_state(b):
    h = 'nev'
    for (eb, fr, to) in MICEV:
        if b < eb + 0.45: return dict(holder=h, ev=(eb, fr, to) if b >= eb - 0.2 else None)
        if b < eb + 2: return dict(holder=None, fly=(eb, fr, to), u=(b - (eb + 0.45)) / 1.55)
        h = to
    return dict(holder=h)
HOT_MOVES = ['pump', 'point', 'shuffle', 'headbang', 'wave', 'twist', 'kick', 'march', 'clap', 'stomp', 'swap']
CALM_MOVES = ['sway', 'step', 'cheers', 'bounce', 'lean', 'groove', 'shimmy', 'slide', 'handsup']
IDS = ['carra', 'nev', 'keane']
def block_moves(s, bs):
    hot = s in HOT_SECTIONS
    pool = HOT_MOVES if hot else CALM_MOVES
    first = lambda x: int(hsh(int(x * 13 + 5)) * len(pool))
    i0 = first(bs)
    if i0 == first(bs - 8): i0 = (i0 + 1) % len(pool)
    if hsh(int(bs * 7 + 3)) < 0.45 or pool[i0] == 'swap': return {c: pool[i0] for c in IDS}
    alt = lambda j: pool[j % len(pool)] if pool[j % len(pool)] != 'swap' else pool[(j + 1) % len(pool)]
    return {c: (alt(i0) if k == 1 else alt(i0 + k * 2 + 1)) for k, c in enumerate(IDS)}
# Breakdance breaks: toprock, then windmills (Carra, Keane) and a headspin (Gary), an upside-down freeze,
# and a flip back onto their feet. (start beat; each break is 12 beats)
BREAKS = (356, 500)   # "Anger creates engagement..." in verse 3 (synthwave) and in the final chorus (pitch)
def break_u(b):
    for b0 in BREAKS:
        if b0 <= b < b0 + 12: return b - b0
    return None
def breakdance(cid, u, p):
    ci = CI[cid]; hop = abs(math.sin(math.pi * u)); dip = ((1 + math.cos(2 * math.pi * u)) / 2) ** 1.6
    hc = 0.5 * (HEAD_H[cid] + 150)                     # foot -> body centre (source px)
    if u < 4:                                           # toprock: crossing side-steps
        p.update(pose=[1, 2][int(u / 2) % 2], x=55 * math.sin(math.pi * u) * (1 if ci % 2 else -1), y=16 * hop,
                 roll=0.09 * math.sin(math.pi * u), sy=1 - 0.04 * dip, sx=1 + 0.02 * dip, hr=0.1 * math.sin(math.pi * u))
        return p
    if cid == 'nev':                                    # headspin
        th = math.pi * ease(clamp((u - 4) / 0.75))
        if u >= 11.5: th = math.pi + math.pi * ease(clamp((u - 11.5) / 0.5))
        sx = 1.0 if u < 4.75 or u >= 10 else 0.2 + 0.8 * abs(math.cos(2 * math.pi * 1.25 * (u - 4.75)))
        pz = 1 if 4.75 <= u < 10 else 2
    else:                                               # windmill: two full turns, then the freeze
        d_ = 1 if cid == 'carra' else -1; st = 4 if cid == 'carra' else 4.5
        th = d_ * 4 * math.pi * ease(clamp((u - st) / (10 - st)))
        if u >= 10: th = d_ * (4 * math.pi + math.pi * ease(clamp((u - 10) / 0.5)) + (math.pi * ease(clamp((u - 11.5) / 0.5)) if u >= 11.5 else 0))
        sx = 1.0; pz = 1 if u < 10 else 2
    if 10 <= u < 11.5: pz = 2                           # freeze
    low = smooth(clamp((u - 4) / 0.6)) * (1 - smooth(clamp((u - 11.4) / 0.6)))
    Hc = hc * (1 - 0.12 * low)
    sz = 1 - 0.14 * low * (1 if 4.8 < u < 9.8 else 0.4)          # a touch smaller mid-spin so the three overlap less
    p.update(pose=pz, roll=th, x=-math.sin(th) * hc * sz, y=Hc * sz - math.cos(th) * hc * sz, sx=sx * sz, sy=sz, hr=0.0, hy=0.0)
    return p
def move_for(cid, b):
    s = section(b); f = featured(b)
    # Recovered Work-mode upgrade: deliberately awkward Inbetweeners-style
    # trio routine near the start, with a short callback in the build.
    if break_u(b) is not None: return 'breakdance'
    if 16 <= b < 32 or 368 <= b < 376:
        return {'nev': 'inbet_nev', 'carra': 'inbet_carra', 'keane': 'inbet_keane'}[cid]
    if s == 'intro': return 'standby'
    if s == 'drop': return 'crouch'
    if s in ('outro', 'end'): return 'finalpose'
    if s == 'final' and b < FINAL_B + 1.6: return 'jump'
    if s == 'breakdown': return 'groove' if cid == 'nev' else 'sway'
    return block_moves(s, math.floor(b / 8) * 8)[cid]
def pose(cid, move, b, k, t):
    ci = CI[cid]; p = dict(x=0.0, y=0.0, roll=0.0, sx=1.0, sy=1.0, hr=0.0, hy=0.0, pose=0)
    dip = ((1 + math.cos(2 * math.pi * b)) / 2) ** 1.6
    sw = math.sin(math.pi * b); hop = abs(sw); br = math.sin(t * 2.1 + ci * 1.7) * 0.006
    if move == 'standby': p.update(sy=1 + br, hr=0.03 * math.sin(t * 0.9 + ci))
    elif move == 'breakdance':
        u_ = break_u(b)
        if u_ is None: u_ = 0.0 if min(abs(b - b0) for b0 in BREAKS) < min(abs(b - b0 - 12) for b0 in BREAKS) else 12.0  # blending in/out
        return breakdance(cid, min(u_, 11.999), p)
    elif move == 'inbet_nev':
        # Gary: stiff side shuffle, knee dip and over-confident arm-swing pose changes.
        q = math.sin(math.pi * b); q2 = math.sin(2 * math.pi * b)
        p.update(pose=[1, 3, 1, 2][int(b * 2) % 4], x=72 * math.sin(math.pi * b / 2),
                 y=18 * abs(q), roll=0.075 * q2, hr=-0.11 * q,
                 sy=0.94 + 0.06 * abs(q), sx=1.04 - 0.03 * abs(q))
    elif move == 'inbet_carra':
        # Carra: intentionally over-enthusiastic shoulder/hip shuffle.
        q = math.sin(math.pi * (b + 0.33)); q2 = math.sin(2 * math.pi * b + 1.1)
        p.update(pose=[2, 0, 3, 0][int(b * 2 + 1) % 4], x=-58 * math.sin(math.pi * b / 2),
                 y=11 * abs(q2), roll=-0.095 * q, hr=0.14 * q2,
                 sy=0.96 - 0.035 * abs(q), sx=1.03 + 0.025 * abs(q))
    elif move == 'inbet_keane':
        # Roy: reluctant deadpan version of the same routine, half a beat late.
        q = math.sin(math.pi * (b - 0.5)); q2 = math.sin(2 * math.pi * (b - 0.5))
        p.update(pose=[0, 3, 0, 2][int((b - 0.5) * 2) % 4], x=34 * math.sin(math.pi * b / 2),
                 y=7 * abs(q), roll=0.045 * q, hr=-0.055 * q2,
                 sy=0.98 - 0.02 * abs(q), sx=1.015)
    elif move == 'bounce': p.update(pose=[0, 2, 1, 3][int(b / 2 + ci * 0.5) % 4], y=(18 + 34 * k) * hop, sy=1 - 0.05 * dip, sx=1 + 0.03 * dip, roll=0.035 * sw, hr=0.08 * sw, hy=6 * dip)
    elif move == 'step':
        q = math.sin(math.pi * b / 2)
        p.update(pose=[0, 1, 3, 1][int(b) % 4], x=120 * q, roll=0.05 * math.cos(math.pi * b / 2), y=14 * hop, sy=1 - 0.035 * dip, sx=1 + 0.02 * dip, hr=-0.07 * q)
    elif move == 'point':
        n = math.floor(b); side = 1 if n % 2 else -1; pop = spike(b, 9)
        p.update(pose=[0, 1, 2][n % 3], sx=1 + 0.045 * pop, sy=1 + 0.045 * pop, roll=0.045 * side * (1 - 0.6 * pop), y=18 * hop, hr=-0.1 * side, hy=5 * dip)
    elif move == 'shimmy':
        p.update(pose=2 if int(b / 4) % 2 else 0, roll=0.06 * math.sin(2 * math.pi * b), x=24 * math.sin(2 * math.pi * b), sy=1 - 0.025 * abs(math.sin(2 * math.pi * b)), hr=0.1 * math.sin(math.pi * b))
    elif move == 'robot':
        q = math.floor(b * 2)
        p.update(pose=int(hsh(q * 3 + ci * 11) * 4), roll=(hsh(q * 5 + ci) - 0.5) * 0.08, x=(hsh(q * 7 + ci) - 0.5) * 25, hr=(hsh(q * 11 + ci) - 0.5) * 0.2, sy=0.97 if frac(b * 2) < 0.15 else 1)
    elif move == 'pump':
        up = ((1 + math.cos(2 * math.pi * b)) / 2) ** 3
        p.update(pose=1 if up > 0.35 else 2, y=70 * up, sy=1 + 0.05 * up, sx=1 - 0.02 * up, hr=0.07 * sw, hy=-5 * up)
    elif move == 'spin':
        u = frac(b / 4) * 4
        if u < 2: p.update(sx=max(0.03, abs(math.cos(math.pi * u))), pose=[0, 2][int(u + 0.5) % 2], y=40 * math.sin(math.pi * u / 2))
        else: p.update(y=14 * hop, sy=1 - 0.04 * dip)
    elif move == 'sway':
        q = math.sin(math.pi * b / 2)
        p.update(pose=[3, 1, 3, 2][int(b / 4 + ci) % 4], roll=0.07 * q, x=50 * q, hr=0.12 * q, sy=1 + br)
    elif move == 'pose': p.update(pose=3, sy=1 + br, hr=0.04 * math.sin(t * 1.3 + ci))
    elif move == 'crouch':
        a = smooth((b - (FINAL_B - 1.7)) / 0.8); p.update(pose=2, sy=lerp(0.96, 0.9, a), sx=lerp(1.05, 1.08, a), hy=8)
    elif move == 'jump':
        u = clamp((b - FINAL_B) / 1.6); arc = 4 * u * (1 - u)
        p.update(pose=1, y=210 * arc, sy=1 + 0.1 * arc - (0.12 * (u - 0.92) / 0.08 if u > 0.92 else 0), sx=1 - 0.04 * arc)
    elif move == 'shuffle':
        p.update(pose=[0, 2][int(b * 2) % 2], x=55 * math.sin(2 * math.pi * b), y=10 * hop, roll=0.035 * math.sin(2 * math.pi * b), hr=0.08 * math.sin(2 * math.pi * b))
    elif move == 'headbang':
        hb_ = math.sin(2 * math.pi * b); p.update(pose=[2, 1][int(b / 2) % 2], hr=0.16 * hb_, hy=9 * abs(hb_), sy=1 - 0.03 * abs(hb_), y=8 * hop)
    elif move == 'wave':
        ph_ = b - ci * 0.33; w_ = abs(math.sin(math.pi * ph_)) ** 3
        p.update(pose=[0, 1][int(ph_) % 2], y=75 * w_, sy=1 + 0.05 * w_, roll=0.03 * math.sin(math.pi * ph_))
    elif move == 'twist':
        p.update(pose=[0, 2][int(b) % 2], sx=1 - 0.05 * abs(math.sin(2 * math.pi * b)), roll=0.06 * math.sin(2 * math.pi * b), y=8 * hop)
    elif move == 'march':
        m_ = math.sin(math.pi * b); p.update(pose=[0, 1][int(b) % 2], sx=1 + 0.045 * m_, sy=1 + 0.045 * m_, roll=0.03 * m_, y=10 * hop)
    elif move == 'kick':
        on = int(b) % 2 == ci % 2; kk_ = spike(b, 5) if on else 0.0
        p.update(pose=1 if on else 2, y=45 * kk_, roll=0.09 * kk_ * (1 if ci % 2 else -1), sy=1 - 0.03 * dip)
    elif move == 'cheers':
        dirc = {0: 1, 1: 0, 2: -1}[ci]; p.update(pose=3, x=70 * dirc * dip, roll=0.06 * dirc * dip, hr=0.1 * sw, y=8 * hop)
    elif move == 'lean':
        sd_ = 1 if int(b / 2) % 2 else -1; p.update(pose=[1, 3][int(b / 2) % 2], roll=0.13 * sd_ * ease(clamp(frac(b / 2) * 3)), hr=-0.08 * sd_, y=6 * hop)
    elif move == 'groove':
        p.update(pose=[0, 3, 2, 1][int(b / 2) % 4], y=12 * hop, roll=0.025 * sw, hr=0.1 * math.sin(math.pi * b / 2), sy=1 - 0.025 * dip)
    elif move == 'clap':
        pop_ = spike(b * 2, 8); p.update(pose=[1, 2][int(b * 2) % 2], sx=1 + 0.03 * pop_, sy=1 + 0.03 * pop_, y=12 * hop, roll=0.02 * sw)
    elif move == 'stomp':
        st_ = spike(b / 2, 3); p.update(pose=[2, 0][int(b / 2) % 2], sy=1 - 0.05 * st_, sx=1 + 0.03 * st_, y=30 * abs(math.sin(math.pi * b / 2)), roll=0.04 * math.sin(math.pi * b / 2))
    elif move == 'slide':
        q_ = math.sin(math.pi * b / 4); p.update(pose=[0, 3][int(b / 2) % 2], x=140 * q_, roll=-0.05 * math.cos(math.pi * b / 4), y=6 * hop)
    elif move == 'handsup':
        p.update(pose=1, y=22 * hop, roll=0.05 * math.sin(math.pi * b / 2), hr=0.08 * math.sin(math.pi * b / 2), sy=1 - 0.02 * dip)
    elif move == 'swap':
        e_ = smooth(frac(b / 8) * 4) * (1 - smooth(frac(b / 8) * 4 - 3)); dx_ = {0: 670, 1: 0, 2: -670}[ci]
        p.update(pose=[0, 1][int(b) % 2], x=dx_ * e_, y=25 * hop, roll=0.04 * sw)
    elif move == 'finalpose': p.update(pose=3, sy=1 + br, hr=0.03 * math.sin(t * 1.1 + ci))
    return p
def pose_at(cid, b, k, t):
    m = move_for(cid, b); back = 0
    for d in (0.1, 0.2, 0.3, 0.4, 0.5):
        if move_for(cid, b - d) != m: back = d; break
    p = pose(cid, m, b, k, t)
    if back:
        q = pose(cid, move_for(cid, b - back), b, k, t); w = smooth(back / 0.5)
        p = {kk: ((p[kk] if w >= 0.5 else q[kk]) if kk == 'pose' else lerp(q[kk], p[kk], w)) for kk in p}
    if m not in ('standby', 'finalpose', 'crouch', 'jump', 'breakdance') and not back:
        q_ = 2 if section(b) in HOT_SECTIONS else 4  # hold each drawn pose for 2 (choruses) or 4 beats
        p['pose'] = pose(cid, m, math.floor(b / q_) * q_ + 0.01, k, t)['pose']
    # verses move less than choruses: calmer verses, and the choruses feel bigger
    amt = 1.0 if section(b) in HOT_SECTIONS or m in ('jump', 'crouch', 'breakdance') else 0.68
    if amt < 1:
        for kk in ('x', 'y', 'roll', 'hr', 'hy'): p[kk] *= amt
        p['sx'] = 1 + (p['sx'] - 1) * amt; p['sy'] = 1 + (p['sy'] - 1) * amt
    return p
def feature_step(cid, b):
    if featured(b) != cid: return 0.0
    st = math.floor(b)
    while featured(st - 1) == cid and st > 0: st -= 1
    en = math.ceil(b)
    while featured(en) == cid: en += 1
    return smooth((b - st) / 1.5) * (1 - smooth((b - (en - 1.5)) / 1.5))

# ---- Edit decision list ------------------------------------------------------------------------------
# One shot per lyric line (cut on the line), framed on whoever the line is about. The song is about
# Gary, so he is the default; Jamie's lines are on Carra, Roy's lines on Keane.
#   (start_s, kind, who)   kinds: intro outro wide group mid close two mgr champ push
EDL = [
    (0.0, 'intro', 'nev'),
    (6.8, 'wide', 'nev'),     # "Gary, put the tactics board down, mate."
    (11.2, 'mid', 'carra'),   #   (Carra says it)
    (14.0, 'close', 'nev'),   #   (Gary's face)
    # Verse 1: all Gary
    (17.0, 'mid', 'nev'),     # Gary Neville underneath the studio lights
    (19.63, 'close', 'nev'),  # Telling Manchester United how to put the whole thing right
    (23.14, 'mid', 'nev'),    # "Sack him! Back him! ..."
    (26.89, 'mgr', 'nev'),    # Every Monday morning there's another man to blame
    (29.68, 'close', 'nev'),  # diagrams and arrows
    (33.19, 'mid', 'nev'),    # what the manager should've bloody done
    (36.3, 'group', 'nev'),   # Valencia gave him the clipboard
    (40.29, 'push', 'nev'),   # Turns out doing it yourself / was a little harder than that
    # Chorus 1
    (46.5, 'group', 'nev'),   # (downbeat) Oh Gary, Gary, pass the microphone
    (50.19, 'close', 'nev'),  # seventeen times from your phone
    (53.78, 'mid', 'nev'),    # Drama merchant, football sermon
    (57.29, 'group', 'nev'),  # managing it yourself didn't last
    (60.3, 'champ', 'nev'),   # Champagne socialist
    (63.75, 'mgr', 'nev'),    # Every manager's name goes on your little list
    (66.78, 'mid', 'nev'),    # You know the game, Gaz
    (70.45, 'close', 'nev'),  # talking like you'd fix it all?
    (72.05, 'group', 'nev'),  # We both know you probably won't
    # Verse 2: Jamie, then Roy, then Gary's England days
    (73.17, 'mid', 'carra'),  # Jamie's on The Overlap going
    (77.39, 'two', 'carra'),  # "Gary, here's the thing..." (mic toss Carra -> Gary)
    (80.19, 'close', 'carra'),  # Never managed at the top
    (82.9, 'mid', 'carra'),   # he'll explain absolutely everything
    (87.05, 'close', 'keane'),  # Keane gives the death stare / "Standards! Hunger! Pride!"
    (90.56, 'wide', 'nev'),   # Everybody on the sofa quietly shuffles to the side
    (93.59, 'mid', 'keane'),  # Roy's actually had the dugout
    (96.54, 'close', 'keane'),  # one misplaced five-yard pass / somebody's got to go
    (100.21, 'mid', 'nev'),   # somewhere in those England days
    (102.05, 'close', 'nev'),  # Kane's beside the flag / centre-forward taking corners
    (105.0, 'group', 'nev'),  # Still a pretty decent gag
    # Chorus 2
    (109.33, 'group', 'nev'),  # (downbeat) Oh Gary, Gary, pass the microphone
    (113.3, 'close', 'nev'),
    (116.81, 'mid', 'nev'),
    (120.32, 'wide', 'nev'),
    # Verse 3 (synthwave)
    (123.59, 'wide', 'nev'),  # Anger creates engagement
    (126.7, 'mid', 'nev'),    # Get the fans all raging
    (130.21, 'close', 'nev'),  # "United are in crisis!"
    (133.32, 'group', 'nev'),  # Manchester rage
    (137.15, 'mid', 'nev'),   # One bad game - emergency
    (140.43, 'close', 'nev'),  # Two bad games - catastrophe
    (143.46, 'close', 'nev'),  # Gary on the thumbnail looking absolutely stunned
    (146.73, 'wide', 'nev'),  # Anger creates engagement... (breakdance)
    (151.84, 'group', 'nev'),  # And watch those numbers run (sofa dance callback)
    # Comedy breakdown: whoever speaks
    (155.19, 'close', 'nev'),  # Gary: "They've lost the dressing room."
    (157.82, 'close', 'carra'),  # Jamie: "Absolutely."
    (159.02, 'close', 'keane'),  # Keane: "They're too soft."
    (159.97, 'close', 'nev'),  # Gary: "No leadership."
    (161.01, 'close', 'carra'),  # Jamie: "No mentality."
    # Bridge (the pitch)
    (162.21, 'wide', 'nev'),  # We remember '99, Gary / what you won
    (166.84, 'two', 'keane'),  # You and Keane at Old Trafford
    (168.59, 'group', 'nev'),  # Those nights were bloody fun
    (170.19, 'mid', 'nev'),   # So we know you love United
    (173.38, 'close', 'nev'),  # sometimes watching The Overlap
    (176.09, 'push', 'nev'),  # Feels like our funeral's playing (-> blackout)
    # Final chorus
    (183.35, 'wide', 'nev'),  # GARY! GARY! PASS THE MICROPHONE!
    (185.98, 'mid', 'nev'),   # rebuilt Manchester United seventeen times
    (189.73, 'close', 'carra'),  # Carragher is laughing
    (191.41, 'close', 'keane'),  # Keane is looking mad
    (193.25, 'mid', 'nev'),   # Another United crisis / still that bad
    (196.2, 'champ', 'nev'),  # Champagne socialist
    (199.79, 'group', 'nev'),  # Sunday-night philosopher
    (202.64, 'champ', 'nev'),  # Pour another champagne, Gaz
    (204.73, 'mgr', 'nev'),   # We know how this will end
    (206.41, 'wide', 'nev'),  # Anger creates engagement (breakdance)
    (211.9, 'group', 'nev'),  # So we'll see you next weekend
    # Outro (spoken)
    (214.79, 'close', 'nev'),  # "Serious questions need answering."
    (220.05, 'close', 'carra'),  # Gary...
    (222.29, 'outro', 'keane'),  # We haven't even kicked off yet.
]
def _with_tosses(edl):
    """Give each mic pass its own short two-shot, then return to the lyric's shot."""
    out = list(edl)
    for tt, fr, to in TOSSES:
        cur = [e for e in edl if e[0] <= tt + 1.25][-1]
        out = [e for e in out if not (tt - 0.25 <= e[0] < tt + 1.25)]
        out += [(tt - 0.25, 'toss', to), (tt + 1.25, cur[1], cur[2])]
        out.append((tt - 0.25, '_ev', (fr, to)))
    ev = {e[0]: e[2] for e in out if e[1] == '_ev'}
    out = sorted([e for e in out if e[1] != '_ev'], key=lambda e: e[0])
    return out, ev
EDL, _TOSS_EV = _with_tosses(EDL)
SHOTS = []
for i_, (t0_, kind_, who_) in enumerate(EDL):
    t1_ = EDL[i_ + 1][0] if i_ + 1 < len(EDL) else DUR + 5
    SHOTS.append(dict(b0=(t0_ - PH) / P, b1=(t1_ - PH) / P, t0=t0_, type=kind_, who=who_, side=1 if i_ % 2 else -1, seed=i_ * 7.31, idx=i_, ev=_TOSS_EV.get(t0_)))
def shot_at(b):
    t_ = PH + b * P; s = SHOTS[0]
    for x in SHOTS:
        if x['t0'] <= t_: s = x
        else: break
    return s
HEAD_H = {c['id']: max((SPR[c[k_]]['foot'][1] - SPR[c[k_]]['headc'][1]) * c['k'][k_] for k_ in 'ABCD') for c in CAST}  # tallest drawn pose
def cam_anchor(cid, t):
    """Where the camera looks for a pundit: his feet position smoothed over ~0.5 s and a fixed head
    height, so the framing never chases the bounce of the dance (the dance moves inside the frame)."""
    c = CAST[CI[cid]]; k = fval(EN, t); xs = 0.0
    for j in range(6):
        tj = t - j * 0.1; p_ = pose_at(cid, (tj - PH) / P, k, tj)
        if break_u((tj - PH) / P) is None:  # (breakdance spins stay centred: the camera doesn't follow them)
            xs += p_['x'] + math.sin(p_['roll']) * HEAD_H[cid] * 0.9  # the lean moves the head sideways
    return c['foot'][0] + xs / 6, c['foot'][1] - HEAD_H[cid]

def aff(scale_x, scale_y, rot, px, py, tx, ty):
    c, s = math.cos(rot), math.sin(rot)
    M = np.array([[c * scale_x, -s * scale_y, 0], [s * scale_x, c * scale_y, 0]], np.float64)
    M[:, 2] = np.array([tx, ty]) - M[:, :2] @ np.array([px, py])
    return M
def draw_sprite(frame, spr, M, gain=1.0, W=OW, H=OH, add=False):
    h, w = spr.shape[:2]
    corners = np.array([[0, 0, 1], [w, 0, 1], [0, h, 1], [w, h, 1]], np.float64) @ M.T
    x0, y0 = np.floor(corners.min(0)).astype(int); x1, y1 = np.ceil(corners.max(0)).astype(int)
    X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if X1 <= X0 or Y1 <= Y0: return
    M2 = M.copy(); M2[:, 2] -= [X0, Y0]
    out = cv2.warpAffine(spr, M2, (X1 - X0, Y1 - Y0), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    if add: frame[Y0:Y1, X0:X1] += out[..., :3] * gain; return
    a = out[..., 3:4] / 255
    frame[Y0:Y1, X0:X1] = frame[Y0:Y1, X0:X1] * (1 - a) + out[..., :3] * gain

def lighting(sec, b):
    L = dict(amb=1.0, beams=0.5, floor='checker', strobe=0, solo=None, back=1.0)
    if sec == 'intro':
        r = smooth((b - 2) / 12); L.update(amb=0.25 + 0.75 * r, back=0.18 + 0.82 * r, beams=0.5 * smooth((b - 8) / 4), floor='sweep')
    elif sec == 'reveal': L.update(beams=0.6)
    elif sec == 'dip': L.update(amb=0.8, back=0.7, beams=0.25, floor='calm')
    elif sec == 'chorus': L.update(beams=0.95, floor='ripple')
    elif sec in ('big', 'final'): L.update(beams=1.0, floor='rainbow', strobe=1)
    elif sec == 'verse3': L.update(beams=0.5, floor='calm')
    elif sec == 'bridge': L.update(amb=0.95, back=0.75, beams=0.4, floor='calm')
    elif sec == 'breakdown': L.update(amb=0.65, back=0.35, beams=0.2, floor='calm', solo='__holder')
    elif sec == 'build':
        r = smooth((b - 368) / 56); L.update(amb=0.85 + 0.15 * r, back=0.6 + 0.4 * r, beams=0.3 + 0.6 * r, floor='ripple' if r > 0.5 else 'checker')
    elif sec == 'drop': L.update(amb=0.25, back=0.08, beams=0, floor='off')
    elif sec == 'outro': L.update(beams=0.5, floor='rainbow')
    return L
HSV_CACHE = {}
def hue_bgr(h):
    key = int(h * 179)
    if key not in HSV_CACHE: HSV_CACHE[key] = cv2.cvtColor(np.uint8([[[key, 230, 255]]]), cv2.COLOR_HSV2BGR)[0, 0].astype(np.float32)
    return HSV_CACHE[key]
def floor_colors(L, b, t, solo_x):
    cols = np.zeros((FROWS, FCOLS, 3), np.float32)
    dip = ((1 + math.cos(2 * math.pi * b)) / 2) ** 2; m = L['floor']
    for j in range(FROWS):
        for i in range(FCOLS):
            if m == 'off': c = np.array((8, 4, 10), np.float32)
            elif m == 'sweep':
                on = smooth((b - 8) * 1.4 - abs(i - FCOLS / 2) * 0.9 - j * 0.2); c = np.array(PAL[(i + j) % 5], np.float32) * (0.1 + 0.9 * on)
            elif m == 'checker':
                on = 0.5 + 0.5 * math.cos(math.pi * (i + j) + math.pi * b / 2)  # checker that slowly swaps, no hard beat flips
                c = np.array(PAL[int(b // 8) % 5], np.float32) * (0.12 + on * (0.33 + 0.55 * dip))
            elif m == 'ripple':
                d_ = math.hypot(i - FCOLS / 2 + 0.5, (j - 1.5) * 1.6); on = max(0, 1 - abs(frac(b) * 9 - d_) * 0.7)
                c = np.array(PAL[(math.floor(b) + int(d_)) % 5], np.float32) * (0.25 + 0.75 * on)
            elif m == 'rainbow':
                c = hue_bgr(frac(i / FCOLS * 0.7 + j * 0.08 + t * 0.25)) * (0.4 + 0.6 * dip) * (1.1 if L['strobe'] and (math.floor(b) + i + j) % 3 == 0 else 1)
            elif m == 'calm':
                w = 0.5 + 0.5 * math.sin(t * 0.8 + i * 0.6 + j * 0.9); c = np.array((120 * w + 60, 30 + 20 * w, 60 + 50 * w), np.float32)
            elif m == 'solo':
                c = np.array(L['solo_col'], np.float32) * ((0.5 + 0.5 * dip) if abs(i - solo_x) < 2.2 else 0.12)
            else: c = np.array((60, 60, 60), np.float32)
            cols[j, i] = c
    return cols

def _render(t, force=None, shot=None, scene_=None):
    b = (t - PH) / P
    k = fval(EN, t); vocal = fval(VOC, t)
    sec = section(b); L = lighting(sec, b); ms = mic_state(b)
    dip = ((1 + math.cos(2 * math.pi * b)) / 2) ** 1.6
    champ = champ_state(t)

    chars = {}
    for c in CAST:
        cid = c['id']; p = pose_at(cid, b, k, t)
        if champ:
            pa_ = math.exp(-(t - champ['pop']) * 4) if t >= champ['pop'] else 0.0
            if cid == 'nev': p['pose'] = 0; p['y'] += 50 * pa_; p['roll'] *= 0.3
            else: p['roll'] += (-0.08 if cid == 'carra' else 0.08) * pa_
        key = 'ABCD'[int(p['pose'])]
        if key == 'D' and ms.get('holder') == cid and cid == 'nev': key = 'A'; p['pose'] = 0
        spr = SPR[c[key]]
        ga = gary_amt(t)
        if ga > 0 and cid != 'nev': p['roll'] += (0.09 if cid == 'carra' else -0.09) * ga
        if ga > 0 and cid == 'nev': p['y'] += 30 * ga * abs(math.sin(math.pi * b))
        y_extra = 0.0
        if ms.get('ev') and ms['ev'][1] == cid: y_extra += 60 * math.sin(math.pi * clamp((b - ms['ev'][0]) / 0.6))
        if ms.get('fly') and ms['fly'][2] == cid and ms['u'] > 0.85: y_extra += 50 * math.sin(math.pi * clamp((ms['u'] - 0.85) / 0.15))
        fs = feature_step(cid, b)
        hr, hy = p['hr'], p['hy']
        hr += 0.075 * listen_dir(cid, t, ms)
        if ms.get('holder') == cid and sec not in ('intro', 'drop') and singing(t):
            hr += (vocal - 0.25) * 0.14 * math.sin(t * 11 + CI[cid]); hy -= 7 * vocal
        prev_spr = prev_kk = None; pw = 1.0
        for d_, w_ in ((0.1, 0.33), (0.2, 0.66)):  # ~3-frame dissolve after a pose swap
            k2 = 'ABCD'[int(pose_at(cid, b - d_, k, t - d_ * P)['pose'])]
            if k2 == 'D' and ms.get('holder') == cid and cid == 'nev': k2 = 'A'
            if k2 != key and not champ: prev_spr, prev_kk, pw = SPR[c[k2]], c['k'][k2] * (1 + 0.08 * fs), w_; break
        chars[cid] = dict(prev_spr=prev_spr, prev_kk=prev_kk, pw=pw, p=p, spr=spr, kk=c['k'][key] * (1 + 0.08 * fs), fx=c['foot'][0] + p['x'], fy=c['foot'][1] + 60 * fs, lift=p['y'] + y_extra, hr=hr, hy=hy)
    def local_to_src(ch, px, py):
        spr = ch['spr']; p = ch['p']; kk = ch['kk']
        dx = (px - spr['foot'][0]) * kk * p['sx']; dy = (py - spr['foot'][1]) * kk * p['sy']
        c_, s_ = math.cos(p['roll']), math.sin(p['roll'])
        return (ch['fx'] + c_ * dx - s_ * dy, ch['fy'] - ch['lift'] + s_ * dx + c_ * dy)
    for ch in chars.values():
        ch['head'] = local_to_src(ch, *ch['spr']['headc']); ch['hand'] = local_to_src(ch, *ch['spr']['hand'])
        if 'up' in ch['spr']: ch['up'] = local_to_src(ch, *ch['spr']['up'])

    s = shot if shot is not None else (shot_at(b) if force is None else dict(type='forced', b0=b, b1=b + 1, seed=0))
    lt = t - beatT(s['b0']); u = clamp((b - s['b0']) / (s['b1'] - s['b0'])); side = s.get('side', 1)
    z, cx, cy = 1.0, SW / 2, SH / 2; typ = s['type']
    scene = scene_ or scene_for(b)
    if scene == 'grid' and typ == 'mgr': typ = 'group'
    who = s.get('who', 'nev'); ax, ay = cam_anchor(who, t) if typ not in ('forced',) else (0, 0)
    focus = [who]
    if typ == 'intro': e = ease(clamp((b - 1) / 14)); z, cx, cy = lerp(1.9, 1.0, e), lerp(1183, SW / 2, e), lerp(260, SH / 2, e)
    elif typ == 'outro': e = ease(clamp(lt / 3.5)); z, cx, cy = lerp(2.0, 1.25, e), lerp(ax, SW / 2, e), lerp(ay + 110, 620, e)
    elif typ == 'wide': z = 1.0 + 0.012 * lt; focus = IDS
    elif typ == 'group':
        z = 1.3 + 0.008 * lt; focus = IDS; cx = sum(cam_anchor(c_, t)[0] for c_ in IDS) / 3; cy = 640
    elif typ == 'mid': z = 1.55 + 0.012 * lt; cx, cy = ax - 50 * side, ay + 250
    elif typ == 'close': z = 2.0 + 0.014 * lt; cx, cy = ax + 30 * side, ay + 105
    elif typ == 'two':
        other = 'nev' if who != 'nev' else 'keane'; bx_, by_ = cam_anchor(other, t); focus = [who, other]
        z = 1.42 + 0.01 * lt; cx, cy = (ax + bx_) / 2, (ay + by_) / 2 + 250
    elif typ == 'push': z = 1.0 + 0.4 * ease(u); cy = lerp(SH / 2, 740, ease(u)); focus = IDS
    elif typ == 'mgr': z = 1.5 + 0.015 * lt; cx = lerp(620, 1610, 0.5 + 0.5 * math.sin(s['seed'] * 1.7)) + 45 * side * lt; cy = RAIL_Y - 90
    elif typ == 'toss':
        fr, to = s['ev']; f_ = cam_anchor(fr, t); g_ = cam_anchor(to, t); focus = [fr, to]
        z = 1.15; cx = (f_[0] + g_[0]) / 2
        cy = min(f_[1], g_[1]) + 150 - TOSS_H * 0.55 + OH / 2 / (BASE * z) - 250  # arc apex stays in frame
    elif typ == 'champ':
        e = ease(clamp(lt / 1.2)); z = lerp(1.3, 1.5, e); cx = ax + 110; cy = ay + 100
    elif typ == 'forced': z, cx, cy = force
    if typ not in ('forced', 'intro'):  # slow, gentle handheld drift instead of shake
        cx += 7 * math.sin(t * 0.45 + s.get('seed', 0)); cy += 4 * math.sin(t * 0.37 + 1.3 * s.get('seed', 0))
    if sec == 'final' and FINAL_B <= b < FINAL_B + 2: z *= 1 + 0.05 * spike(b - FINAL_B, 2)
    sc = BASE * z
    hw_, hh_ = OW / 2 / sc, OH / 2 / sc
    if typ in ('wide', 'group', 'mid', 'close', 'two', 'push', 'champ'):
        # keep the heads in (fixed head heights + dance allowance, so this never jitters)
        top_need = min(cam_anchor(c_, t)[1] if c_ != who else ay for c_ in focus) - max(SPR[CAST[CI[c_]]['A']]['ry'] for c_ in focus) * 1.25 - 75  # + room for hops
        if cy - hh_ > top_need: cy = top_need + hh_
    cx = clamp(cx, hw_, SW - hw_); cy = clamp(cy, hh_, SH - hh_)
    def to_out(x, y): return ((x - cx) * sc + OW / 2, (y - cy) * sc + OH / 2)

    zb = 1 + (z - 1) * 0.72; sb = BASE * zb
    bcx = clamp(lerp(SW / 2, cx, 0.8), OW / 2 / sb, SW - OW / 2 / sb); bcy = clamp(lerp(SH / 2, cy, 0.8), OH / 2 / sb, SH - OH / 2 / sb)
    Mb = np.array([[sb, 0, OW / 2 - bcx * sb], [0, sb, OH / 2 - bcy * sb]], np.float64)
    BG_ = GRID_BACK if scene == 'grid' else PITCH_BACK if scene == 'pitch' else BACK
    frame = cv2.warpAffine(BG_, Mb, (OW, OH), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    if scene == 'studio': frame *= L['back'] * (0.94 + 0.1 * dip * (1 if L['beams'] > 0.5 else 0))
    else: frame *= 0.35 + 0.65 * L['back'] ** 0.5
    if scene == 'pitch':
        for i_ in range(10):
            q_ = int(t * 3 + i_ * 0.37) * 31 + i_
            if hsh(q_) > 0.6:
                fx_, fy_ = to_out(hsh(q_ * 3) * SW, 240 + hsh(q_ * 7) * 420)
                cv2.circle(frame, (int(fx_), int(fy_)), max(1, int(5 * sc)), (255, 255, 255), -1, cv2.LINE_AA)

    for (s0, s1, img_id, (cx0, cy0, cx1, cy1)) in SCREENS:
        if s0 - 1 <= b < s1 + 1:
            drop = ease(clamp(b - (s0 - 1))) * ease(clamp((s1 + 1) - b))
            yoff = -(SCR_H + 80) * (1 - drop)
            ch_ = cy1 - cy0; cw_ = ch_ * SCR_W / SCR_H
            panx = cx0 + (cx1 - cx0 - cw_) * (0.5 - 0.5 * math.cos(math.pi * clamp((b - s0) / (s1 - s0))))
            X0s, Y0s = SCR_X - SCR_W / 2, SCR_Y + yoff
            ox0, oy0 = to_out(X0s - 14, Y0s - 14); ox1, oy1 = to_out(X0s + SCR_W + 14, Y0s + SCR_H + 14)
            cv2.rectangle(frame, (int(ox0), int(oy0)), (int(ox1), int(oy1)), (40, 20, 30), -1)
            pulse = 0.85 + 0.2 * dip
            glow_col = (165, 62, 255) if int(b // 2) % 2 else (214, 227, 25)
            cv2.rectangle(frame, (int(ox0), int(oy0)), (int(ox1), int(oy1)), tuple(v * pulse for v in glow_col), max(2, int(5 * sc)))
            for cxw in (X0s + 60, X0s + SCR_W - 60):
                p1 = to_out(cxw, -200); p2 = to_out(cxw, Y0s - 14)
                cv2.line(frame, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), (30, 30, 36), max(1, int(4 * sc)))
            sx_ = SCR_W / cw_ * sc
            ix0, iy0 = to_out(X0s, Y0s)
            Ms = np.array([[sx_, 0, ix0 - panx * sx_], [0, sx_, iy0 - cy0 * sx_]], np.float64)
            X0c, Y0c = max(0, int(ix0)), max(0, int(iy0)); X1c, Y1c = min(OW, int(ix0 + SCR_W * sc)), min(OH, int(iy0 + SCR_H * sc))
            if X1c > X0c and Y1c > Y0c:
                M2 = Ms.copy(); M2[:, 2] -= [X0c, Y0c]
                img_ = cv2.warpAffine(SCREEN_SRC[img_id], M2, (X1c - X0c, Y1c - Y0c), flags=cv2.INTER_LINEAR)
                frame[Y0c:Y1c, X0c:X1c] = img_ * pulse * L['back'] ** 0.3
    if scene != 'grid':
        # balcony: managers dancing behind a neon rail
        gname = mgr_layer(s['b0'] + 0.3); G_ = GSPR[gname]  # the balcony group only changes on a cut
        pop = 0.0
        gk = MGSC[gname]
        glift = (10 + 16 * k) * abs(math.sin(math.pi * b)) + 30 * pop
        groll = 0.012 * math.sin(math.pi * b)
        gslide = 190 * math.sin(math.pi * b / 8) if gname == 'mgr5' else 25 * math.sin(math.pi * b / 4)
        gsy = 1 - 0.025 * dip + 0.06 * pop
        gx, gy = to_out(SW / 2 + gslide, RAIL_Y + 22 - glift)
        Mg = aff(sc * gk, sc * gk * gsy, groll, G_['w'] / 2, G_['h'], gx, gy)
        ggain = (0.25 + 0.75 * L['back']) * (1.0 if sec != 'drop' else 0.35)
        if 'slc' in G_:
            Mg3 = np.vstack([Mg, [0, 0, 1]])
            for i_, (a_, sl_) in enumerate(G_['slc']):
                kick_ = 16 * spike(b, 5) if (int(b) + i_) % 3 == 0 else 0
                li_ = 12 * abs(math.sin(math.pi * (b - i_ * 0.3))) ** 2 + kick_
                draw_sprite(frame, sl_, (Mg3 @ np.array([[1, 0, a_], [0, 1, -li_], [0, 0, 1]], np.float64))[:2], ggain)
            sx_, sy_ = to_out(SW - 105 + 10 * math.sin(math.pi * b / 2), RAIL_Y + 30 - 10 * abs(math.sin(math.pi * b)))
            draw_sprite(frame, SIRALEX, aff(sc * 1.7, sc * 1.7, 0.035 * math.sin(math.pi * b), SIRALEX.shape[1] / 2, SIRALEX.shape[0], sx_, sy_), ggain)
        else:
            draw_sprite(frame, G_['body'], Mg, ggain)
        hmode = int(b // 8) % 3
        for i, hd in enumerate(G_['heads']):
            hs = G_['hs'][i]
            if hmode == 0: ang = 0.13 * math.sin(math.pi * b + i * 1.3); bob = -5 * abs(math.sin(math.pi * b + i * 0.7))
            elif hmode == 1: ang = 0.16 * math.sin(math.pi * (b - i * 0.25)); bob = -9 * abs(math.sin(math.pi * (b - i * 0.25))) ** 2
            else: ang = 0.1 * math.sin(2 * math.pi * b) * (1 if i % 2 else -1); bob = -7 * spike(b, 6)
            if singing(t): ang += 0.08 * (vocal - 0.3) * math.sin(t * 9 + i)
            nx_, ny_ = hd['neck']; ca_, sa_ = math.cos(ang), math.sin(ang)
            Mh = np.vstack([Mg, [0, 0, 1]]) @ np.array([[1, 0, nx_], [0, 1, ny_ + bob], [0, 0, 1]], np.float64) @ np.array([[ca_, -sa_, 0], [sa_, ca_, 0], [0, 0, 1]], np.float64) @ np.array([[1, 0, -nx_ + hd['x']], [0, 1, -ny_ + hd['y']], [0, 0, 1]], np.float64)
            if False and 'mouth' in hd:  # background managers do not lip sync
                mx_, my_, rxm, rym = hd['mouth']; hs = jaw_open(hs, mx_, my_, rxm, mouth_val(t, i + 10, 0.7) * 0.18 * rym, mw=0.32 * rxm * mouth_w(t), span=0.55 * rym)
            draw_sprite(frame, hs, Mh[:2], ggain)
        # the rail itself
        p0 = to_out(40, RAIL_Y); p1 = to_out(SW - 40, RAIL_Y + RAIL_H)
        y0r, y1r = int(max(0, p0[1])), int(min(OH, p1[1])); x0r, x1r = int(max(0, p0[0])), int(min(OW, p1[0]))
        if y1r > y0r and x1r > x0r:
            grad = np.linspace(1.0, 0.55, y1r - y0r, dtype=np.float32)[:, None, None]
            frame[y0r:y1r, x0r:x1r] = frame[y0r:y1r, x0r:x1r] * 0.08 + np.array([34, 16, 30], np.float32) * grad * (0.5 + 0.5 * L['back'])
            if scene == 'pitch':
                xs_ = cx + (np.arange(x0r, x1r, dtype=np.float32) + 0.5 - OW / 2) / sc; ys_ = cy + (np.arange(y0r, y1r, dtype=np.float32) + 0.5 - OH / 2) / sc
                frame[y0r:y1r, x0r:x1r] = led_strip(xs_, ys_, b, t, sec in HOT_SECTIONS)
            ncol = np.array(PAL[int(b // 2) % 5], np.float32) * (0.55 + 0.45 * dip) * (0.3 + 0.7 * L['back'])
            th = max(2, int(7 * sc)); frame[y0r:min(OH, y0r + th), x0r:x1r] = ncol
            glow = max(3, int(18 * sc)); ys_ = np.arange(glow, dtype=np.float32)[:, None, None]
            if y0r + th + glow < OH: frame[y0r + th:y0r + th + glow, x0r:x1r] += ncol * 0.35 * (1 - ys_ / glow)
            for j in range(0, 36):
                lx_, ly_ = to_out(90 + j * (SW - 180) / 35, RAIL_Y + RAIL_H * 0.55)
                on = 0.5 + 0.5 * math.sin(t * 6 + j * 0.9 + b)
                cv2.circle(frame, (int(lx_), int(ly_)), max(1, int(4 * sc)), tuple(float(v) for v in np.array(PAL[j % 5]) * on * (0.3 + 0.7 * L['back'])), -1, cv2.LINE_AA)
    lead_ = ms.get('holder') or (ms.get('fly') or (0, 0, 'nev'))[2]
    solo_id = L['solo'] if L['solo'] != '__holder' else (solo_voice(t, lead_) or lead_)
    solo_x = -99
    if solo_id:
        L['solo_col'] = CAST[CI[solo_id]]['col']
        inv = np.linalg.inv(H_FLOOR) @ np.array([chars[solo_id]['fx'], 1000, 1.0])
        solo_x = inv[0] / inv[2] / TPX - 0.5
    if scene == 'studio':
     cols = floor_colors(L, b, t, solo_x)
     tex = np.repeat(np.repeat(cols, TPX, 0), TPX, 1) * TILE_TEX
     Mc = np.array([[sc, 0, OW / 2 - cx * sc], [0, sc, OH / 2 - cy * sc], [0, 0, 1]], np.float64)
     fl = cv2.warpPerspective(tex, Mc @ H_FLOOR, (OW, OH), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
     fmask = np.zeros((OH, OW), np.float32)
     cv2.fillPoly(fmask, [np.array([to_out(x, y) for x, y in FLOOR_POLY], np.int32)], 1.0)
     fmask = cv2.GaussianBlur(fmask, (0, 0), 3 * z * RS)[..., None]
     frame = frame * (1 - fmask) + (np.array([26, 12, 20], np.float32) + fl) * fmask
     frame += cv2.GaussianBlur(cv2.resize(fl, (OW // 4, OH // 4)), (0, 0), 4 * RS).repeat(4, 0).repeat(4, 1)[:OH, :OW] * fmask * 0.35
    else:
     Mc = np.array([[sc, 0, OW / 2 - cx * sc], [0, sc, OH / 2 - cy * sc], [0, 0, 1]], np.float64)
     if scene == 'grid':
        gt = GRID_BASE.copy(); off = int(frac(b) * 64)
        for gy in range(-64, GT_H + 64, 64): cv2.line(gt, (0, gy + off), (GT_W, gy + off), (255, 200, 60) if (gy // 64) % 2 else (255, 60, 220), 3, cv2.LINE_AA)
        fl = cv2.warpPerspective(gt, Mc @ H_GRID, (OW, OH), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
        fl *= 0.8 + 0.4 * dip
        frame += fl + cv2.resize(cv2.GaussianBlur(cv2.resize(fl, (OW // 4, OH // 4)), (0, 0), 3 * RS), (OW, OH)) * 0.9
     else:
        pv = cv2.warpPerspective(PITCH_TEX, Mc @ H_PITCH, (OW, OH), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
        pm_ = cv2.warpPerspective(np.ones((PT_H, PT_W), np.float32), Mc @ H_PITCH, (OW, OH), flags=cv2.INTER_NEAREST)[..., None]
        frame = frame * (1 - pm_) + pv * pm_ * (0.75 + 0.25 * L['back'])

    shm = np.zeros((OH // 2, OW // 2), np.float32)
    for ch in chars.values():
        ox, oy = to_out(ch['fx'], ch['fy'])
        r = 190 * sc * max(0.45, 1 - ch['lift'] / 420) / 2
        cv2.ellipse(shm, (int(ox / 2), int(oy / 2 - 2)), (max(1, int(r)), max(1, int(r * 0.2))), 0, 0, 360, 1, -1)
    shm = cv2.resize(cv2.GaussianBlur(shm, (0, 0), 4 * RS), (OW, OH))[..., None]
    frame *= 1 - 0.6 * shm

    add = np.zeros((OH // 2, OW // 2, 3), np.float32)
    if scene == 'pitch':
        for i, tx0 in enumerate((230, SW - 230)):
            ox, oy = to_out(tx0, 100); tx2, ty2 = to_out(SW / 2 + (tx0 - SW / 2) * 0.2 + 150 * math.sin(t * 0.4 + i), 1150)
            ang = math.atan2(tx2 - ox, ty2 - oy); length = math.hypot(tx2 - ox, ty2 - oy); sy_ = length / BEAM.shape[0] / 2
            bm = cv2.warpAffine(BEAM, aff(sy_ * 2.2, sy_, -ang, BEAM.shape[1] / 2, 0, ox / 2, oy / 2), (OW // 2, OH // 2), flags=cv2.INTER_LINEAR)
            add += bm[..., None] * np.array((235, 245, 255), np.float32) * 0.28
    if L['beams'] > 0.01 and scene == 'studio':
        for i, ((lx, ly), col) in enumerate(LIGHTS):
            if L['solo'] and L['solo'] != '__holder': tx = chars[L['solo']]['fx'] + 120 * math.sin(math.pi * b + i); ty = 1050
            elif L['strobe']: tx = SW / 2 - (lx - SW / 2) * 1.6 + 500 * math.sin(math.pi * b / 2 + i * 0.8); ty = 1100
            else: tx = lx + 450 * math.sin(t * 0.6 + i); ty = 1080
            ox, oy = to_out(lx, ly); tx2, ty2 = to_out(tx, ty)
            ang = math.atan2(tx2 - ox, ty2 - oy); length = math.hypot(tx2 - ox, ty2 - oy)
            sy_ = length / BEAM.shape[0] / 2
            M = aff(sy_ * 1.25, sy_, -ang, BEAM.shape[1] / 2, 0, ox / 2, oy / 2)
            bm = cv2.warpAffine(BEAM, M, (OW // 2, OH // 2), flags=cv2.INTER_LINEAR)
            ccol = PAL[(i + int(b // 4)) % 5] if L['beams'] > 0.5 else col[::-1]
            strobe = (1.08 + 0.1 * spike(b, 6)) if L['strobe'] else 1
            add += bm[..., None] * np.array(ccol, np.float32) * (0.4 * L['beams'] * strobe * (0.75 + 0.25 * dip))
    if L['back'] > 0.3 and scene == 'studio':
        for i in range(60):
            a0 = hsh(i * 3 + 1) * 6.283 + t * 0.35; rr = 300 + hsh(i * 7 + 2) * 900
            ox, oy = to_out(1183 + math.cos(a0) * rr * 1.3, 84 + abs(math.sin(a0 * 0.7 + i)) * rr * 0.75)
            if 0 <= ox < OW and 0 <= oy < OH:
                tw = (0.5 + 0.5 * math.sin(t * 7 + i)) * L['back']
                cv2.circle(add, (int(ox / 2), int(oy / 2)), max(1, int(round(2 * RS))), (230 * tw, 230 * tw, 255 * tw), -1, cv2.LINE_AA)
    bx, by = to_out(1183, 90)
    for i in range(5 if scene == 'studio' else 0):
        q = int(t * 2.5)
        if hsh(q * 5 + i) > 0.6:
            px = bx + (hsh(q * 7 + i) - 0.5) * 220 * sc; py = by + (hsh(q * 11 + i) - 0.5) * 150 * sc; L2 = 36 * sc
            cv2.line(add, (int((px - L2) / 2), int(py / 2)), (int((px + L2) / 2), int(py / 2)), (255, 255, 255), max(1, int(RS)), cv2.LINE_AA)
            cv2.line(add, (int(px / 2), int((py - L2) / 2)), (int(px / 2), int((py + L2) / 2)), (255, 255, 255), max(1, int(RS)), cv2.LINE_AA)
    frame += cv2.resize(cv2.GaussianBlur(add, (0, 0), 1.2 * RS), (OW, OH))

    def draw_char(dst, cid, refl=None):
        ch = chars[cid]
        if ch.get('prev_spr') is not None and ch['pw'] < 1:  # dissolve from the previous drawn pose
            keep = (ch['spr'], ch['kk'])
            ch['spr'], ch['kk'] = ch['prev_spr'], ch['prev_kk']; ch['fade'] = 1 - ch['pw']
            _draw_char(dst, cid, refl)
            ch['spr'], ch['kk'] = keep; ch['fade'] = ch['pw']
            _draw_char(dst, cid, refl); ch['fade'] = 1.0
            return
        _draw_char(dst, cid, refl)
    def _draw_char(dst, cid, refl=None):
        ch = chars[cid]; spr = ch['spr']; p = ch['p']; fd = ch.get('fade', 1.0)
        amb = L['amb']
        if s['type'] in ('close', 'mid') and s.get('who') and s['who'] != cid: amb *= 0.78
        if L['solo'] == '__holder': amb = 1.0 if cid == solo_id else 0.5
        elif L['solo']: amb = 1.05 if cid == L['solo'] else 0.65
        if sec == 'drop' and b > FINAL_B - 1.5: amb = 1.0
        ga = gary_amt(t)
        if ga > 0: amb = lerp(amb, 1.08 if cid == 'nev' else 0.72, ga)
        gain = amb * (1 + (0.05 * dip if L['strobe'] else 0))
        ox, oy = to_out(ch['fx'], ch['fy'] - ch['lift'])
        s_ = sc * ch['kk']
        Mbody = aff(s_ * p['sx'], s_ * p['sy'], p['roll'], spr['foot'][0], spr['foot'][1], ox, oy)
        if refl is not None: Mbody = np.array([[1, 0, 0], [0, -1, 2 * refl]], np.float64) @ np.vstack([Mbody, [0, 0, 1]])
        rimc = np.array(PAL[int(b // 2) % 5] if scene != 'pitch' else (235, 245, 255), np.float32) / 255 * (0.18 + 0.12 * dip)
        if refl is None: draw_sprite(dst, spr['body_ol'] * fd, Mbody, 1.0)
        draw_sprite(dst, spr['body'] * fd if fd < 1 else spr['body'], Mbody, gain)
        if refl is None: draw_sprite(dst, spr['body_rim'], Mbody, rimc * fd, add=True)
        nx, ny = spr['neck']
        n_out = Mbody @ np.array([nx, ny + ch['hy'] / ch['kk'], 1.0])
        ang_h = p['roll'] + ch['hr']; ca_, sa_ = math.cos(ang_h), math.sin(ang_h); sq = s_ * (0.5 * (p['sx'] + p['sy']))
        Mh = np.array([[ca_ * sq, -sa_ * sq, n_out[0]], [sa_ * sq, ca_ * sq, n_out[1]], [0, 0, 1]], np.float64) @ np.array([[1, 0, -nx], [0, 1, -ny], [0, 0, 1]], np.float64)
        if refl is not None:
            Mh = np.array([[ca_ * sq, -sa_ * sq, n_out[0]], [-sa_ * sq, -ca_ * sq, n_out[1]], [0, 0, 1]], np.float64) @ np.array([[1, 0, -nx], [0, 1, -ny], [0, 0, 1]], np.float64)
        hs_img = spr['head']
        amp = voice_amp(t, cid, ms.get('holder') or (ms.get('fly') or (0, 0, 'nev'))[2])
        if refl is not None: amp = 0.0
        if 'eyes' not in spr: spr['eyes'] = _find_eyes(spr)
        hs_img = blink_eyes(hs_img, spr['eyes'], blink_amt(cid, t))
        if 'mouth' in spr and amp > 0:
            mo = spr['mouth']
            hs_img = mouth_shape(hs_img, mo, mouth_val(t, cid, amp), cid == 'keane', mouth_w(t))
        elif 'mouth' in spr: hs_img = mouth_shape(hs_img, spr['mouth'], 0.0, cid == 'keane', 1.0)
        if refl is None: draw_sprite(dst, spr['head_ol'] * fd, Mh[:2], 1.0)
        draw_sprite(dst, hs_img * fd if fd < 1 else hs_img, Mh[:2], gain)
        if refl is None: draw_sprite(dst, spr['head_rim'], Mh[:2], rimc * 0.8 * fd, add=True)
        if ms.get('holder') == cid and refl is None:
            hx, hy_ = ch['hand']; hx2, hy2 = ch['head']
            ang = math.atan2(hx2 - hx, -(hy2 - hy_)) * 0.35
            hox, hoy = to_out(hx, hy_)
            draw_sprite(dst, MIC, aff(sc * 0.9, sc * 0.9, -ang, 30, 130, hox, hoy), gain)
    if scene in ('studio', 'grid'):
        # glossy floor: faded mirror image of the pundits below their feet
        gys = [to_out(ch['fx'], ch['fy'])[1] for ch in chars.values()]
        gy0 = min(gys)
        if gy0 < OH:
            ref = frame.copy()
            for cid in ('carra', 'keane', 'nev'): draw_char(ref, cid, refl=to_out(chars[cid]['fx'], chars[cid]['fy'])[1])
            yy_ = np.arange(OH, dtype=np.float32)[:, None, None]
            w_ = np.clip(1 - (yy_ - gy0) / (260 * sc), 0, 1) ** 1.5 * (yy_ > gy0 - 4) * (0.3 if scene == 'studio' else 0.4)
            if scene == 'studio': w_ = w_ * fmask
            frame += (ref - frame) * w_
    for cid in ('carra', 'keane', 'nev'): draw_char(frame, cid)
    if champ and 'up' in chars['nev']:
        ux, uy = chars['nev']['up']; pt_ = champ['pop']
        rot = 0.38 + (0.15 * math.sin(t * 40) if pt_ - 0.6 <= t < pt_ else 0) + (-0.12 * math.exp(-(t - pt_) * 6) if t >= pt_ else 0)
        gx_, gy_ = to_out(ux, uy)
        draw_sprite(frame, BOTTLE if t < pt_ else BOTTLE_OPEN, aff(sc * 0.95, sc * 0.95, rot, 35, 180, gx_, gy_), 1.0)
        mx_src, my_src = ux + math.sin(rot) * 168, uy - math.cos(rot) * 168
        if t >= pt_:
            age = t - pt_
            if age < 0.3:
                fx0, fy0 = to_out(mx_src, my_src); R_ = int((20 + 160 * age) * sc)
                for kk in range(10):
                    a_ = kk * math.pi / 5 + 0.3
                    cv2.line(frame, (int(fx0 + math.cos(a_) * R_ * 0.3), int(fy0 + math.sin(a_) * R_ * 0.3)), (int(fx0 + math.cos(a_) * R_), int(fy0 + math.sin(a_) * R_)), (255, 255, 255), max(1, int(4 * sc)), cv2.LINE_AA)
            if age < 1.6:
                cxs = mx_src + (math.sin(rot) * 900 + 250) * age; cys = my_src - math.cos(rot) * 1500 * age + 0.5 * 1600 * age * age
                cox, coy = to_out(cxs, cys)
                draw_sprite(frame, CORK, aff(sc * 1.1, sc * 1.1, age * 18, 13, 15, cox, coy), 1.0)
            spray = np.zeros((OH, OW, 3), np.float32); sa_ = np.zeros((OH, OW), np.float32)
            for i_ in range(320):
                birth = pt_ + (i_ / 320) * 1.4; ag = t - birth; life = 0.85
                if 0 <= ag < life:
                    d_ = rot + (hsh(i_ * 5 + 1) - 0.5) * 0.9; sp_ = 700 + 600 * hsh(i_ * 3 + 2)
                    px_ = mx_src + math.sin(d_) * sp_ * ag; py_ = my_src - math.cos(d_) * sp_ * ag + 0.5 * 1300 * ag * ag
                    ox_, oy_ = to_out(px_, py_); r_ = max(2, int((4 + 8 * hsh(i_ * 7)) * sc * 1.7 * (1 - 0.5 * ag / life)))
                    colp = (235, 250, 255) if i_ % 3 else (150, 220, 255)
                    cv2.circle(spray, (int(ox_), int(oy_)), r_, colp, -1, cv2.LINE_AA); cv2.circle(sa_, (int(ox_), int(oy_)), r_, 0.85 * (1 - ag / life), -1, cv2.LINE_AA)
            if sa_.max() > 0:
                sa_ = cv2.GaussianBlur(sa_, (0, 0), RS)[..., None]; spray = cv2.GaussianBlur(spray, (0, 0), RS)
                frame = frame * (1 - sa_) + spray * sa_
    if ms.get('fly'):
        (eb, fr, to) = ms['fly']; u2 = clamp(ms['u'])
        ax, ay = chars[fr]['hand']; bx_, by_ = chars[to]['hand']
        mox, moy = to_out(lerp(ax, bx_, u2), lerp(ay, by_, u2) - TOSS_H * 4 * u2 * (1 - u2))
        # sparkle trail behind the flying mic
        tr_ = np.zeros((OH // 2, OW // 2, 3), np.float32)
        for j in range(1, 15):
            uj = u2 - j * 0.028
            if uj <= 0: break
            px_, py_ = to_out(lerp(ax, bx_, uj), lerp(ay, by_, uj) - TOSS_H * 4 * uj * (1 - uj))
            px_ += 10 * sc * math.sin(j * 2.1 + t * 20); py_ += 10 * sc * math.cos(j * 1.7 + t * 17)
            fade_ = (1 - j / 15) ** 1.3
            cv2.circle(tr_, (int(px_ / 2), int(py_ / 2)), max(2, int((16 - j * 0.7) * sc)), tuple(float(v) * fade_ for v in PAL[j % 5]), -1, cv2.LINE_AA)
        frame += cv2.resize(cv2.GaussianBlur(tr_, (0, 0), 2.5 * RS), (OW, OH)) * 2.4
        draw_sprite(frame, MIC, aff(sc * 0.9, sc * 0.9, u2 * math.pi * 4, 30, 95, mox, moy))

    for bt in [beatT(x) for x in (FINAL_B, BIG_B, CH1_B)]:
        if t >= bt:
            age = t - bt
            if age < 9:
                for i in range(260):
                    r1, r2, r3, r4 = hsh(i * 3 + 1), hsh(i * 7 + 2), hsh(i * 11 + 3), hsh(i * 13 + 5)
                    a = age - r4 * 1.2
                    if a < 0: continue
                    x = r1 * SW + math.sin(a * (1.5 + r2 * 2) + i) * 60; y = -40 + a * (130 + r3 * 110)
                    if y > SH + 40: continue
                    ox, oy = to_out(x, y)
                    if not (-20 < ox < OW + 20 and -20 < oy < OH + 20): continue
                    ang = a * (3 + r1 * 4) + i; w_ = 7 * z * RS; h_ = 11 * z * RS * abs(math.cos(a * (2 + r2 * 3) + i)) + 1
                    ca, sa = math.cos(ang), math.sin(ang)
                    pts = np.array([[ox + ca * dx - sa * dy, oy + sa * dx + ca * dy] for dx, dy in ((-w_, -h_), (w_, -h_), (w_, h_), (-w_, h_))], np.int32)
                    cv2.fillConvexPoly(frame, pts, [(255, 62, 165), (25, 227, 214), (39, 182, 255), (255, 255, 255), (255, 92, 139)][i % 5], cv2.LINE_AA)
            break

    br_ = np.clip(frame - 215, 0, None)
    frame += cv2.resize(cv2.GaussianBlur(cv2.resize(br_, (OW // 4, OH // 4), interpolation=cv2.INTER_AREA), (0, 0), 5 * RS), (OW, OH)) * 0.35
    frame *= VIGNETTE
    fl_ = 0.0
    for bt in (CH1_B, BIG_B, FINAL_B):  # a soft flash where the choruses hit
        tt = beatT(bt)
        if t >= tt: fl_ = max(fl_, math.exp(-(t - tt) * 6))
    if fl_ > 0.003: frame = frame * (1 - 0.35 * fl_) + 255 * 0.35 * fl_
    fade = max(1 - smooth(t / 1.4), smooth((t - (DUR - 1.8)) / 1.6))
    if fade > 0.003: frame *= 1 - fade
    return np.clip(frame, 0, 255).astype(np.uint8)

XF_CUT, XF_SCENE = 0.16, 0.6
def render(t, force=None):
    """One frame. Cuts get a short crossfade; scene changes (studio/grid/pitch) a longer dissolve."""
    if force is not None: return _render(t, force)
    b = (t - PH) / P; s = shot_at(b); i = s['idx']; sc1 = shot_scene(s)
    if i > 0:
        prev = SHOTS[i - 1]; dt = t - s['t0']; sc0 = shot_scene(prev)
        xf = XF_SCENE if sc0 != sc1 else XF_CUT
        if 0 <= dt < xf:
            A_ = _render(t, shot=prev, scene_=sc0).astype(np.float32); B_ = _render(t, shot=s, scene_=sc1).astype(np.float32)
            w = smooth(dt / xf)
            return np.clip(A_ * (1 - w) + B_ * w, 0, 255).astype(np.uint8)
    return _render(t, shot=s, scene_=sc1)
def shot_scene(s): return scene_for(s['b0'] + 0.3)

if __name__ == '__main__':
    if sys.argv[1] == 'test':
        for ts in sys.argv[2:]: cv2.imwrite(f'{OUTD}/f_{ts}.jpg', render(float(ts)), [cv2.IMWRITE_JPEG_QUALITY, 88])
    elif sys.argv[1] == 'time':
        import time; t0 = time.time()
        for i in range(12): render(120 + i * 0.37)
        print('ms/frame', round((time.time() - t0) / 12 * 1000))
    elif sys.argv[1] == 'raw':
        f0, f1 = int(sys.argv[2]), int(sys.argv[3]); out = sys.stdout.buffer
        for f in range(f0, f1): out.write(render(f / OUT_FPS).tobytes())
