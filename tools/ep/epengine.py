"""Episode engine: rigs, lip sync, timeline and the 4K compositor for the
bitmap cut-out series (Mark Goldbridge, Gary Neville, Roy Keane).

Coordinates: every background has a "1x" space (the supplied 1672x941 art);
its AI-upscaled 4x copy and foreground matte are what gets rendered.
A camera is (background, x0, y0, width) in 1x space, 16:9; frames come out at
OUT (3840x2160). Characters are anchored by their face (face centre + face
width in 1x space) or by their feet, so any drawing of a character can be
swapped in at the same place and size.
"""
import bisect, json, math, os, re, subprocess, sys
from functools import lru_cache
import cv2, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
EP = os.path.join(ROOT, 'series', 'ep01')
sys.path.insert(0, HERE)
import face_rig as F   # noqa: E402

FPS = 24
OUT = (3840, 2160)
K = 4                      # background upscale factor
SR = 44100
MOUTH_KEYS = ['rest', 'a', 'e', 'i', 'o', 'u', 'smile', 'frown', 'wide_shout']
OPEN_SCALE = 0.88          # open mouths a touch smaller than the sheet's: the show's delivery is played straight


def _nbytes(v):
    if isinstance(v, np.ndarray):
        return v.nbytes
    if isinstance(v, tuple):
        return sum(_nbytes(x) for x in v)
    return 64


def trim(cache, budget, keep=lambda k: False):
    """Drop the oldest entries of a dict cache until its arrays fit in `budget` bytes."""
    total = sum(_nbytes(v) for v in cache.values())
    for k in list(cache):
        if total <= budget:
            break
        if not keep(k):
            total -= _nbytes(cache.pop(k))


# ------------------------------------------------------------------ backgrounds
class Background:
    def __init__(self, name):
        self.name = name
        self.cfg = json.load(open(os.path.join(EP, 'backgrounds', name + '.json')))
        self._img = self._fg = None
        self.cache = {}

    def img(self):
        if self._img is None:
            self._img = cv2.imread(os.path.join(EP, 'x4', self.cfg['image']))
            fg = os.path.join(ROOT, 'out', 'ep01', 'bg', self.name + '_fg.png')
            if not os.path.exists(fg):             # the desk matte is built from backgrounds/<name>.json
                import bgmatte
                bgmatte.build(self.name)
            self._fg = cv2.imread(fg, cv2.IMREAD_UNCHANGED)
        return self._img, self._fg

    def view(self, rect, dof=0.0):
        """(bg BGR, fg RGBA) at output size for a camera rect in 1x coords."""
        key = (tuple(round(v, 2) for v in rect), round(dof, 2))
        if key in self.cache:
            return self.cache[key]
        img, fg = self.img()
        x0, y0, w = rect
        h = w * OUT[1] / OUT[0]
        k = OUT[0] / (w * K)
        M = np.float32([[k, 0, -x0 * K * k], [0, k, -y0 * K * k]])
        interp = cv2.INTER_AREA if k < 1 else cv2.INTER_CUBIC
        bg = cv2.warpAffine(img, M, OUT, flags=interp, borderMode=cv2.BORDER_REPLICATE)
        fgv = cv2.warpAffine(fg, M, OUT, flags=interp, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        if dof > 0:
            bg = cv2.GaussianBlur(bg, (0, 0), dof)
        if len(self.cache) > 3:
            self.cache.pop(next(iter(self.cache)))
        self.cache[key] = (bg, fgv)
        return bg, fgv


# ------------------------------------------------------------------ rigs
class Rig:
    """All drawings of one character, with face info, mouth swaps and blinks."""

    def __init__(self, name):
        self.name = name
        self.idx = json.load(open(os.path.join(EP, 'characters', name, 'index.json')))
        p = os.path.join(EP, 'characters', name, 'rig.json')
        self.over = json.load(open(p)) if os.path.exists(p) else {}
        self.info = {}
        self.imgs = {}
        self.parts = None
        self.cache = {}

    # -- drawings
    def image(self, key):
        if key not in self.imgs:
            panel, name = key.split('/')
            hi = os.path.join(EP, 'characters_x16', self.name, panel, name + '.png')
            path = hi if os.path.exists(hi) else os.path.join(EP, self.idx[panel][name]['file'])
            self.imgs[key] = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        return self.imgs[key]

    def face(self, key):
        """Face info for a drawing: centre, width, mouth box, eyes."""
        if key in self.info:
            return self.info[key]
        img = self.image(key)
        H, W = img.shape[:2]
        panel = key.split('/')[0]
        hf = {'upper': 0.6, 'body': 0.35, 'turnaround': 0.35, 'closeup': 0.6}.get(panel, 1.0)
        info = F.find_face(img, head_frac=hf)
        ov = self.over.get(key, {})
        if info is None:
            info = dict(box=(0, 0, W, H), eyes=[], mouth=None, mouth_mask=np.zeros((H, W), bool),
                        face=np.zeros((H, W), bool), skin=np.array([75, 15, 25], np.float32))
        if 'mouth' in ov:        # [cx, cy, w(, h)] as fractions of the drawing size
            cx, cy, mw = ov['mouth'][:3]
            mh = ov['mouth'][3] * H if len(ov['mouth']) > 3 else mw * W * 0.3
            info['mouth'] = (cx * W, cy * H, mw * W, mh)
            m = np.zeros((H, W), np.uint8)
            cv2.ellipse(m, (int(cx * W), int(cy * H)), (int(mw * W * 0.55), int(max(mh * 0.55, mw * W * 0.2))), 0, 0, 360, 1, -1)
            info['mouth_mask'] = m > 0
        if ov.get('auto_mouth') and len(info['eyes']) == 2:
            # detection misses (a hand or prop over the chin): place the mouth from the eyes
            fwid = info['box'][2] - info['box'][0]
            (ex0, ey0), (ex1, ey1) = info['eyes'][0][:2], info['eyes'][1][:2]
            mw = fwid * 0.22
            mx, my = (ex0 + ex1) / 2 + (ex1 - ex0) * 0.1, (ey0 + ey1) / 2 + 0.46 * fwid
            info['mouth'] = (mx, my, mw, mw * 0.3)
            m = np.zeros((H, W), np.uint8)
            cv2.ellipse(m, (int(mx), int(my)), (int(mw * 0.55), int(mw * 0.2)), 0, 0, 360, 1, -1)
            info['mouth_mask'] = m > 0
        if ov.get('no_mouth'):
            info['mouth'] = None
        fx0, fy0, fx1, fy1 = info['box']
        if info['eyes'] and len(info['eyes']) == 2:
            cx = (info['eyes'][0][0] + info['eyes'][1][0]) / 2
            cy = (info['eyes'][0][1] + info['eyes'][1][1]) / 2
        else:
            cx, cy = (fx0 + fx1) / 2, fy0 + (fy1 - fy0) * 0.45
        info['center'] = (float(cx), float(cy))
        info['width'] = float(ov.get('face_w', 1.0) * (fx1 - fx0))
        ys, xs = np.nonzero(img[..., 3] > 128)
        yb = ys.max()
        low = xs[ys >= yb - max(4, int(H * 0.01))]
        info['feet'] = (float((low.min() + low.max()) / 2), float(yb))
        info['size'] = (W, H)
        self.info[key] = info
        return info

    # -- mouths
    def mouth_parts(self):
        if self.parts is None:
            self.parts = {}
            for k in MOUTH_KEYS:
                if k in self.idx.get('mouths', {}):
                    hi = os.path.join(EP, 'characters_x16', self.name, 'mouths', k + '.png')
                    path = hi if os.path.exists(hi) else os.path.join(EP, self.idx['mouths'][k]['file'])
                    self.parts[k] = F.mouth_part(cv2.imread(path, cv2.IMREAD_UNCHANGED))
        return self.parts

    def mouth_ratio(self):
        """Closed-mouth width / face width, from the front head close-up."""
        r = self.over.get('_mouth_ratio')
        if r:
            return r
        try:
            info = self.face('head/front')
            return max(0.2, min(0.4, info['mouth'][2] / info['width']))
        except Exception:
            return 0.3

    def drawing(self, key, mouth=None, blink=0.0, flip=False):
        """RGBA of a drawing with the given mouth (None = as drawn) and eyelids."""
        ck = (key, mouth, round(blink, 1), flip)
        if ck in self.cache:
            return self.cache[ck]
        img = self.image(key)
        info = self.face(key)
        out = img
        if mouth is not None and info['mouth'] is not None:
            base = self.cache.get(('nomouth', key))
            if base is None and self.name != 'roy':
                base = F.without_mouth(img, info)
                self.cache[('nomouth', key)] = base
            if self.name == 'roy':
                out = synth_mouth(img, info, mouth)
            else:
                parts = self.mouth_parts()
                part = parts.get(mouth) or parts.get('rest')
                rest_w = parts['rest'][2]
                width = self.mouth_ratio() * info['width'] * part[2] / rest_w
                if mouth != 'rest':
                    width *= OPEN_SCALE
                part = recolor_part(part, info['skin'])
                sq = self.over.get(key, {}).get('squash', 1.0)
                out = F.with_mouth(base, info, part, width, squash_x=sq)
        if blink > 0:
            out = F.blink(out, info, blink)
        if flip:
            out = out[:, ::-1].copy()
        self.cache[ck] = out
        trim(self.cache, 250e6, keep=lambda k: k[0] == 'nomouth')
        return out


@lru_cache(maxsize=64)
def _skin_of_part(pid):
    return None


def recolor_part(part, skin_lab):
    """Shift a mouth part's skin tone to the target face's skin."""
    patch, c, w = part
    key = (id(patch), tuple(np.round(skin_lab, 1)))
    hit = _RECOLOR.get(key)
    if hit is not None:
        return hit
    L = cv2.cvtColor(patch[..., :3].astype(np.float32) / 255, cv2.COLOR_BGR2LAB)
    ps = F.skin_colour(patch)
    if ps is None:
        return part
    d = np.array(skin_lab, np.float32) - ps
    near = np.linalg.norm(L - ps, axis=2) < 18
    wgt = near.astype(np.float32)[..., None]
    L2 = L + d * wgt
    bgr = (cv2.cvtColor(L2, cv2.COLOR_LAB2BGR) * 255).clip(0, 255).astype(np.uint8)
    out = (np.dstack([bgr, patch[..., 3]]), c, w)
    _RECOLOR[key] = out
    return out


_RECOLOR = {}
SYNTH = {'rest': (0.8, 0.0), 'a': (0.95, 0.42), 'e': (1.0, 0.26), 'i': (0.95, 0.15), 'o': (0.62, 0.4),
         'u': (0.48, 0.28), 'smile': (0.8, 0.0), 'frown': (0.8, 0.0), 'wide_shout': (1.05, 0.62)}


def synth_mouth(img, info, key):
    """A drawn mouth opening for a character without a phoneme set (Roy).
    His beard and moustache stay: the opening is drawn over his own lips,
    hanging from the upper lip, with teeth, tongue and a lower lip."""
    ws, hs = SYNTH.get(key, (0.8, 0.0))
    if hs <= 0:
        return img                                  # closed: his own drawn mouth
    out = img.copy()
    cx, cy, mw, mh = info['mouth']
    fw = info['width']
    mw = min(max(mw, fw * 0.26), fw * 0.32)      # the found box can take in the moustache
    w = mw * ws / 2
    h = mw * hs / 2
    top = cy - mh * 0.35
    ccy = top + h
    ss = 4                                         # draw supersampled for clean edges
    x0, y0 = int(cx - w * 1.4), int(top - h * 0.6)
    x1, y1 = int(cx + w * 1.4) + 1, int(ccy + h * 1.6) + 1
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(out.shape[1], x1), min(out.shape[0], y1)
    if x1 <= x0 or y1 <= y0:
        return out
    Wp, Hp = (x1 - x0) * ss, (y1 - y0) * ss
    P = lambda x, y: (int((x - x0) * ss), int((y - y0) * ss))
    A = lambda a, b: (max(1, int(a * ss)), max(1, int(b * ss)))
    lip = np.zeros((Hp, Wp), np.uint8)
    hole = np.zeros((Hp, Wp), np.uint8)
    teeth = np.zeros((Hp, Wp), np.uint8)
    tongue = np.zeros((Hp, Wp), np.uint8)
    lt = fw * 0.022
    cv2.ellipse(lip, P(cx, ccy), A(w + lt * 0.6, h + lt * 1.3), 0, 0, 360, 255, -1, cv2.LINE_AA)
    cv2.ellipse(hole, P(cx, ccy), A(w, h), 0, 0, 360, 255, -1, cv2.LINE_AA)
    cv2.ellipse(teeth, P(cx, ccy - h * 0.95), A(w * 0.8, h * 0.42), 0, 0, 360, 255, -1, cv2.LINE_AA)
    cv2.ellipse(tongue, P(cx + w * 0.08, ccy + h * 0.95), A(w * 0.62, h * 0.55), 0, 0, 360, 255, -1, cv2.LINE_AA)
    teeth = np.minimum(teeth, hole)
    tongue = np.minimum(tongue, hole)
    col = np.zeros((Hp, Wp, 3), np.float32)
    col[:] = (70, 92, 176)                          # lip
    for m, c in ((hole, (38, 26, 58)), (tongue, (92, 96, 196)), (teeth, (228, 236, 240))):
        a = m[..., None] / 255.0
        col = col * (1 - a) + np.array(c, np.float32) * a
    # ink outline round the opening
    edge = cv2.morphologyEx(hole, cv2.MORPH_GRADIENT, np.ones((max(3, int(fw * 0.012 * ss)),) * 2, np.uint8))
    a = cv2.GaussianBlur(edge, (0, 0), ss * 0.5)[..., None] / 255.0
    col = col * (1 - a) + np.array((28, 30, 44), np.float32) * a
    alpha = cv2.resize(lip, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA)[..., None] / 255.0
    col = cv2.resize(col, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA)
    alpha = alpha * (out[y0:y1, x0:x1, 3:4] / 255.0)
    region = out[y0:y1, x0:x1, :3].astype(np.float32)
    out[y0:y1, x0:x1, :3] = (region * (1 - alpha) + col * alpha).astype(np.uint8)
    return out


# ------------------------------------------------------------------ lip sync
VOWEL = {'AA': 'a', 'AE': 'a', 'AH': 'e', 'AY': 'a', 'AW': 'a', 'EH': 'e', 'EY': 'e', 'ER': 'e',
         'IH': 'i', 'IY': 'i', 'OW': 'o', 'AO': 'o', 'OY': 'o', 'UW': 'u', 'UH': 'u'}
CONS = {'M': 'rest', 'B': 'rest', 'P': 'rest', 'F': 'i', 'V': 'i', 'W': 'u', 'R': 'u', 'Y': 'i',
        'SH': 'u', 'ZH': 'u', 'CH': 'i', 'JH': 'i', 'S': 'i', 'Z': 'i', 'T': 'i', 'D': 'i', 'N': 'i',
        'TH': 'e', 'DH': 'e', 'L': 'e', 'K': 'e', 'G': 'e', 'NG': 'e', 'HH': 'e'}


def phones_to_frames(words, dur, fps=FPS, loud=False):
    """Per-frame mouth keys from aligned words/phones; held on twos."""
    n = int(dur * fps) + 2
    best = [None] * n
    wgt = np.zeros(n)
    for w in words:
        for ph, a, b in w['phones']:
            ph = re.sub(r'\d', '', ph)
            key = VOWEL.get(ph) or CONS.get(ph, 'i')
            if key == 'a' and loud:
                key = 'wide_shout'
            isv = ph in VOWEL
            for f in range(max(0, int(a * fps)), min(n, max(int(a * fps) + 1, int(round(b * fps))))):
                sc = (b - a) + (0.15 if isv else 0) + (0.3 if key == 'rest' else 0)
                if sc > wgt[f]:
                    wgt[f], best[f] = sc, key
    out, last, held = [], 'rest', 9
    for f in range(n):
        m = best[f] or 'rest'
        if m != last and held < 2:
            m = last
        held = held + 1 if m == last else 1
        out.append(m)
        last = m
    return out


def synth_words(text, dur):
    """Evenly timed phones for a line with no recording yet."""
    sys.path.insert(0, HERE)
    import align as A
    words = A.words_of(text)
    phs = []
    for w in words:
        A.ensure_word(A.decoder(), w)
        p = A.decoder().lookup_word(w) or 'AH'
        phs.append(p.split())
    total = sum(len(p) for p in phs) or 1
    t = 0.05
    step = (dur - 0.1) / total
    out = []
    for w, p in zip(words, phs):
        t0 = t
        pp = []
        for ph in p:
            pp.append((ph, t, t + step))
            t += step
        out.append(dict(word=w, t0=t0, t1=t, phones=pp))
    return out


def load_audio(path):
    tmp = os.path.join(ROOT, 'out', 'ep01', 'wav44', os.path.basename(path) + '.wav')
    if not os.path.exists(tmp) or os.path.getmtime(tmp) < os.path.getmtime(path):
        os.makedirs(os.path.dirname(tmp), exist_ok=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', path, '-ac', '1', '-ar', str(SR), tmp], check=True)
    import soundfile as sf
    x, _ = sf.read(tmp, dtype='float32')
    return x


def find_audio(lid):
    for ext in ('.wav', '.mp3', '.m4a', '.aac', '.ogg', '.flac'):
        p = os.path.join(EP, 'audio', lid + ext)
        if os.path.exists(p):
            return p
    return None


def estimate_duration(text):
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'vec'))
    import lipsync as LS
    sy, _ = LS.syllables(text)
    return 0.35 + 0.2 * len(sy) + 0.25 * text.count('.')


# ------------------------------------------------------------------ timeline
class Track:
    def __init__(self):
        self.t, self.v, self.e = [], [], []

    def add(self, t, v, e='step'):
        i = bisect.bisect_right(self.t, t)
        self.t.insert(i, t); self.v.insert(i, v); self.e.insert(i, e)

    def at(self, t, default=None):
        if not self.t:
            return default
        i = bisect.bisect_right(self.t, t) - 1
        if i < 0:
            return self.v[0] if self.e[0] != 'step' else default
        v0 = self.v[i]
        if i + 1 < len(self.t) and isinstance(v0, (int, float)) and not isinstance(v0, bool) and self.e[i + 1] != 'step':
            t0, t1, v1 = self.t[i], self.t[i + 1], self.v[i + 1]
            u = min(1.0, max(0.0, (t - t0) / max(t1 - t0, 1e-6)))
            if self.e[i + 1] == 'ease':
                u = u * u * (3 - 2 * u)
            return v0 + (v1 - v0) * u
        return v0


class Timeline:
    def __init__(self, script):
        self.script = script
        self.t = 0.0
        self.lines = []            # dict(id, who, start, dur, audio, text, words)
        self.tracks = {}
        self.shots = []            # (t, dict)
        self.fx = []               # (t, name, gain, kw)
        self.blinks = {}           # who -> [t]: blinks the staging asks for (the rest are random)
        self.cues = {}

    def key(self, t, who, e='step', **kv):
        for k, v in kv.items():
            self.tracks.setdefault((who, k), Track()).add(t, v, e)

    def get(self, who, k, t, default=None):
        tr = self.tracks.get((who, k))
        return tr.at(t, default) if tr else default

    def wait(self, d):
        s = self.t
        self.t += d
        return s

    def say(self, lid, gap=0.35, lead=0.0):
        who = self.script.SPEAKER[lid[:2]]
        text = self.script.LINES[lid]
        path = find_audio(lid)
        self.t += lead
        start = self.t
        if path:
            x = load_audio(path)
            dur = len(x) / SR
            words = None
            al = ALIGN.get(lid)
            if al:
                words = al
            else:
                import align as A
                w16 = os.path.join(ROOT, 'out', 'ep01', 'wav16', lid + '.wav')
                os.makedirs(os.path.dirname(w16), exist_ok=True)
                A.to16k(path, w16)
                try:
                    words = A.align(w16, text)
                except Exception:
                    words = synth_words(text, dur)
        else:
            dur = estimate_duration(text)
            words = synth_words(text, dur)
        ln = dict(id=lid, who=who, start=start, dur=dur, audio=path, text=text, words=words)
        self.lines.append(ln)
        self.t = start + dur + gap
        return ln

    def shot(self, t, bg, rect=None, **kw):
        d = dict(kw, bg=bg, rect=rect, t=t)
        i = bisect.bisect_right([s[0] for s in self.shots], t)
        self.shots.insert(i, (t, d))

    def sfx(self, t, name, gain=1.0, **kw):
        self.fx.append((t, name, gain, kw))

    def shot_at(self, t):
        i = bisect.bisect_right([s[0] for s in self.shots], t) - 1
        s = self.shots[max(i, 0)][1]
        t1 = self.shots[i + 1][0] if i + 1 < len(self.shots) else self.t
        return s, t1


ALIGN = {}


def load_alignment():
    p = os.path.join(EP, 'audio', 'alignment.json')
    if os.path.exists(p):
        ALIGN.update(json.load(open(p)))


# ------------------------------------------------------------------ compositing
def over(frame, rgba, x, y):
    """Alpha-composite RGBA onto BGR frame at float position (x, y)."""
    h, w = rgba.shape[:2]
    H, W = frame.shape[:2]
    xi, yi = int(round(x)), int(round(y))
    xa, ya, xb, yb = max(xi, 0), max(yi, 0), min(xi + w, W), min(yi + h, H)
    if xa >= xb or ya >= yb:
        return
    s = rgba[ya - yi:yb - yi, xa - xi:xb - xi]
    a = s[..., 3:4].astype(np.float32) * (1 / 255)
    d = frame[ya:yb, xa:xb]
    frame[ya:yb, xa:xb] = (s[..., :3] * a + d * (1 - a)).astype(np.uint8)


def over_full(frame, rgba):
    a = rgba[..., 3]
    ys, xs = np.nonzero(a[::8, ::8])
    if len(ys) == 0:
        return
    y0, y1 = max(0, ys.min() * 8 - 8), min(a.shape[0], ys.max() * 8 + 16)
    x0, x1 = max(0, xs.min() * 8 - 8), min(a.shape[1], xs.max() * 8 + 16)
    over(frame, rgba[y0:y1, x0:x1], x0, y0)


# body poses whose hands come up round the face: a close-up puts a calmer body under the head
CU_BODY = {'upper/fist_pump': 'upper/arms_down', 'upper/holding_phone': 'upper/arms_down'}


class Renderer:
    def __init__(self, tl, size=OUT):
        self.tl = tl
        self.size = size
        self.bgs = {}
        self.rigs = {c: Rig(c) for c in ('mark', 'gary', 'roy')}
        self.scaled = {}
        self.blinks = self.plan_blinks()
        self.face_px = {}              # who -> (x, y, face width, drawing) of the last frame drawn
        self.mouth_frames = {}
        for ln in tl.lines:
            loud = ln['id'] in getattr(tl.script, 'LOUD', ())
            self.mouth_frames[ln['id']] = phones_to_frames(ln['words'], ln['dur'], loud=loud)

    def bg(self, name):
        if name not in self.bgs:
            self.bgs[name] = Background(name)
        return self.bgs[name]

    def plan_blinks(self):
        out = {}
        for i, c in enumerate(('mark', 'gary', 'roy')):
            rng = np.random.RandomState(20 + i)
            t, lst = 1.0 + i * 0.7, []
            while t < self.tl.t + 5:
                lst.append(t)
                t += rng.uniform(2.4, 5.0)
            forced = sorted(self.tl.blinks.get(c, []))
            lst = [b for b in lst if all(abs(b - f) > 1.2 for f in forced)]
            out[c] = sorted(lst + forced)
        return out

    def blink(self, who, t):
        for b in self.blinks[who]:
            k = (t - b) * FPS
            if 0 <= k < 4:
                return [0.6, 1.0, 1.0, 0.6][int(k)]
        return 0.0

    def speaking(self, who, t):
        for ln in self.tl.lines:
            if ln['who'] == who and ln['start'] <= t < ln['start'] + ln['dur']:
                f = int((t - ln['start']) * FPS)
                fr = self.mouth_frames[ln['id']]
                return fr[min(f, len(fr) - 1)], ln
        return None, None

    # -- where a character is in a given background
    def placement(self, who, t, bgname):
        tl = self.tl
        loc = tl.get(who, 'loc', t, 'off')
        if loc == 'off':
            return None
        cfg = self.bg(bgname).cfg
        body = tl.get(who, 'body', t, 'upper/arms_down')
        flip = tl.get(who, 'flip', t, False)
        if loc == 'seat':
            back = cfg.get('spots', {}).get(who + '_back')
            if back:
                return dict(kind='back', spot=back)
            seat = cfg.get('seats', {}).get(who)
            if not seat:
                return None
            dy = tl.get(who, 'dy', t, 0.0) or 0.0
            return dict(kind='face', pos=(seat['face'][0], seat['face'][1] + dy * seat['face_w']), fw=seat['face_w'],
                        body=body, flip=flip)
        if loc in ('stand', 'walk'):
            path = tl.get(who, 'path', t)
            if not path:
                return None
            a, b = path
            sa, sb = cfg.get('spots', {}).get(a), cfg.get('spots', {}).get(b)
            if not sa or not sb:
                return None
            u = tl.get(who, 'u', t, 0.0) if loc == 'walk' else 1.0
            fx = sa['feet'][0] + (sb['feet'][0] - sa['feet'][0]) * u
            fy = sa['feet'][1] + (sb['feet'][1] - sa['feet'][1]) * u
            fw = sa['face_w'] + (sb['face_w'] - sa['face_w']) * u
            if loc == 'walk':
                cyc = tl.get(who, 'cycle', t, ['body/walk_1', 'body/walk_2', 'body/walk_3', 'body/walk_4'])
                body = cyc[int(t * 8) % len(cyc)]          # 8 drawings a second: the show's brisk walk
                fy -= abs(math.sin(t * 8 * math.pi / 2)) * fw * 0.04
            return dict(kind='feet', pos=(fx, fy), fw=fw, body=body, flip=flip)
        return None

    def camera(self, t):
        s, t1 = self.tl.shot_at(t)
        rect = s['rect']
        if callable(rect):
            key = ('cam', s['t'])
            if key not in self.scaled:
                self.scaled[key] = rect(self, s['t'] + 0.2)
            rect = self.scaled[key]
        return s, rect

    def sprite_scaled(self, rig, key, mouth, blink, flip, scale):
        sq = round(math.log(scale) * 60) / 60
        ck = (rig.name, key, mouth, round(blink, 1), flip, sq)
        hit = self.scaled.get(ck)
        if hit is not None:
            return hit
        img = rig.drawing(key, mouth, blink, flip)
        s = math.exp(sq)
        res = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
        self.scaled[ck] = (res, s)
        trim(self.scaled, 600e6, keep=lambda k: k[0] == 'cam')
        return res, s

    def draw_char(self, frame, who, t, bgname, rect, shot):
        pl = self.placement(who, t, bgname)
        if pl is None:
            return
        rig = self.rigs[who]
        x0, y0, cw = rect
        k1 = OUT[0] / cw                        # output px per 1x px
        if pl['kind'] == 'back':
            sp = pl['spot']
            key = 'turnaround/back'
            info = rig.face(key)
            img = rig.image(key)
            W, H = info['size']
            head_w = W * 0.62                         # the back view's head is ~62% of the drawing width
            s = sp['head_w'] * k1 / head_w
            res = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)
            res = cv2.GaussianBlur(res, (0, 0), 3.0)
            over(frame, res, (sp['head'][0] - x0) * k1 - res.shape[1] / 2, (sp['head'][1] - y0) * k1 - res.shape[0] * 0.2)
            return
        mouth, ln = self.speaking(who, t)
        talk = mouth is not None and self.tl.get(who, 'talk', t, True)
        env = 1.0 if (talk and mouth not in ('rest', None)) else 0.0
        key = pl['body']
        fw_out = pl['fw'] * k1
        cu = None
        if fw_out > (700 if pl['kind'] == 'face' else 400):
            # seen large: a close-up drawing (expression bust / high-res head) supplies the head
            cu = self.tl.get(who, 'face', t, 'expressions/neutral' if pl['kind'] == 'face' else None)
        blink = self.blink(who, t) if not self.tl.get(who, 'eyes_shut', t, False) else 1.0
        nod = self.tl.get(who, 'nod', t, 0.0) or 0.0
        bob = (-env * fw_out * 0.012 + nod * fw_out * 0.035) if pl['kind'] == 'face' else 0.0
        # the body drawing, anchored by its face (seated) or its feet (standing)
        info = rig.face(key)
        W, H = info['size']
        body_mouth = (mouth if talk else None) if cu is None else None
        res, s = self.sprite_scaled(rig, key, body_mouth, blink if cu is None else 0.0, pl['flip'], fw_out / max(info['width'], 1))
        cx, cy = info['center']
        if pl['flip']:
            cx = W - cx
        if pl['kind'] == 'face':
            px = (pl['pos'][0] - x0) * k1 - cx * s
            py = (pl['pos'][1] - y0) * k1 - cy * s + bob
        else:
            fy = info['feet'][1]
            px = (pl['pos'][0] - x0) * k1 - cx * s
            py = (pl['pos'][1] - y0) * k1 - fy * s
        self.face_px[who] = (px + cx * s, py + cy * s, fw_out, cu or key)
        if cu is None:
            over(frame, res, px, py)
            return
        # close-up: the body from just under its chin, then the close-up head blended on at the same face
        calm = CU_BODY.get(key)
        if calm and calm in rig.idx.get(calm.split('/')[0], {}):
            key = calm
            info = rig.face(key)
            W, H = info['size']
            res, s = self.sprite_scaled(rig, key, None, 0.0, pl['flip'], fw_out / max(info['width'], 1))
            cx, cy = info['center']
            if pl['flip']:
                cx = W - cx
            px = (pl['pos'][0] - x0) * k1 - cx * s
            py = (pl['pos'][1] - y0) * k1 - cy * s + bob
        chin = int((info['box'][3] - 0.1 * info['width']) * s)
        chin = max(0, min(res.shape[0], chin))
        over(frame, res[chin:], px, py + chin)
        fcx, fcy = px + cx * s, py + cy * s
        cinfo = rig.face(cu)
        cs = fw_out / max(cinfo['width'], 1)
        cres, cs = self.sprite_scaled(rig, cu, mouth if talk else None, blink, pl['flip'], cs)
        ccx, ccy = cinfo['center']
        if pl['flip']:
            ccx = cinfo['size'][0] - ccx
        mk = ('cumask', who, cu, pl['flip'], cres.shape)
        m = self.scaled.get(mk)
        if m is None:
            m = self.cu_mask(rig, cu, pl['flip'], cres.shape[1], cres.shape[0])
            self.scaled[mk] = m
        cres = cres.copy()
        cres[..., 3] = (cres[..., 3] * m).astype(np.uint8)
        over(frame, cres, fcx - ccx * cs, fcy - ccy * cs)

    def cu_mask(self, rig, key, flip, w, h):
        """Keeps a close-up drawing's head and neck; its cut-off chest and
        shoulders fade out over the body drawn underneath."""
        info = rig.face(key)
        W, H = info['size']
        fx0, fy0, fx1, fy1 = info['box']
        fw = fx1 - fx0
        m = np.zeros((H, W), np.float32)
        below = 0.12 + rig.over.get('_cu_chin', 0.0)       # Roy: down to the bottom of his beard
        m[:int(fy1 - 0.3 * fw)] = 1.0                        # the whole head, ears and hair
        m[:int(fy1 + below * fw), max(0, int(fx0 - 0.06 * fw)):int(fx1 + 0.06 * fw)] = 1.0
        m = cv2.GaussianBlur(m, (0, 0), fw * 0.07)
        if flip:
            m = m[:, ::-1]
        return cv2.resize(m, (w, h), interpolation=cv2.INTER_LINEAR)

    def render(self, t):
        shot, rect = self.camera(t)
        if shot['bg'] in INSERTS:
            return INSERTS[shot['bg']](self, t, shot)
        bgo = self.bg(shot['bg'])
        bgimg, fg = bgo.view(rect, shot.get('dof', 0.0))
        frame = bgimg.copy()
        order = shot.get('order', ('gary', 'mark', 'roy'))
        self.face_px = {}
        for who in order:
            self.draw_char(frame, who, t, shot['bg'], rect, shot)
        over_full(frame, fg)
        fade = self.tl.get('world', 'fade', t, 0.0) or 0.0
        if fade > 0:
            frame = (frame * (1 - min(fade, 1.0))).astype(np.uint8)
        if self.size != OUT:
            frame = cv2.resize(frame, self.size, interpolation=cv2.INTER_AREA)
        return frame


INSERTS = {}
