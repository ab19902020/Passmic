"""Timeline engine for vector episode scenes.

A scene script builds a Timeline: it lays voice clips and silent beats end to
end (tl.say / tl.wait), cuts cameras (tl.shot), keys Cartman's pose
(tl.key: numbers tween, everything else steps) and the room (tl.set), and
drops sound effects (tl.sfx). render() draws any frame straight at the
output resolution; render_video() renders segments in parallel and muxes
the dialogue + effects track.
"""
import bisect, math, os, subprocess, sys, json
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import draw as D          # noqa: E402
import cartman as C       # noqa: E402
import room as R          # noqa: E402
import screens            # noqa: E402

SR = 44100
VIS2MOUTH = {'a_ah': 'a', 'e_eh': 'e', 'i_ee': 'i', 'o_oh': 'o', 'u_oo': 'u', 'm_closed': None,
             'l_tongue': 'l', 'f_v': 'f', 'th_teeth': 'th', 'w_rounded': 'w'}


def ease(u, kind='inout'):
    u = min(1.0, max(0.0, u))
    if kind == 'linear':
        return u
    if kind == 'out':
        return 1 - (1 - u) ** 2
    if kind == 'in':
        return u * u
    if kind == 'back':          # overshoot a touch, for snappy cartoon moves
        c = 1.6
        return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2
    return u * u * (3 - 2 * u)


def load_clip(path):
    tmp = os.path.join(ROOT, 'out', 'audio', os.path.basename(path) + '.%d.wav' % SR)
    if not os.path.exists(tmp):
        os.makedirs(os.path.dirname(tmp), exist_ok=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', path, '-ac', '1', '-ar', str(SR), tmp], check=True)
    x, _ = sf.read(tmp, dtype='float32')
    return x


class Track:
    """Keyframes for one parameter."""

    def __init__(self):
        self.t, self.v, self.e = [], [], []

    def add(self, t, v, e):
        i = bisect.bisect_right(self.t, t)
        self.t.insert(i, t); self.v.insert(i, v); self.e.insert(i, e)

    def at(self, t, default=None):
        if not self.t:
            return default
        i = bisect.bisect_right(self.t, t) - 1
        if i < 0:
            return self.v[0]
        v0 = self.v[i]
        if i + 1 >= len(self.t) or not isinstance(v0, (int, float, tuple)) or isinstance(v0, bool):
            return v0
        v1, t0, t1 = self.v[i + 1], self.t[i], self.t[i + 1]
        kind = self.e[i + 1]
        if kind == 'step' or t1 <= t0:
            return v0
        u = ease((t - t0) / (t1 - t0), kind)
        if isinstance(v0, tuple):
            return tuple(a + (b - a) * u for a, b in zip(v0, v1))
        return v0 + (v1 - v0) * u


class Timeline:
    def __init__(self, fps=24, size=(3840, 2160)):
        self.fps, self.W, self.H = fps, size[0], size[1]
        self.t = 0.0
        self.voice = []          # (start, samples)
        self.fx = []             # (start, samples, gain)
        self.shots = []          # (t, dict)
        self.ck = {}             # cartman tracks
        self.wk = {}             # world tracks
        self.cues = {}

    # -- time
    def wait(self, d):
        s = self.t
        self.t += d
        return s

    def say(self, clip, a=0.0, b=None, gap=0.45, label=None):
        """Place clip[a:b]; returns f(tc) mapping clip time to scene time."""
        x = load_clip(clip)
        b = len(x) / SR if b is None else b
        s = self.t
        self.voice.append((s, x[int(a * SR):int(b * SR)]))
        self.t = s + (b - a) + gap
        f = lambda tc, s=s, a=a: s + (tc - a)
        if label:
            self.cues[label] = s
        return f

    # -- keys
    def key(self, t, e='inout', **kw):
        for k, v in kw.items():
            self.ck.setdefault(k, Track()).add(t, v, e)

    def hold(self, t, *names):
        """Re-key the current values at t (so the next key tweens from here)."""
        for n in names:
            v = self.ck[n].at(t) if n in self.ck else C.DEFAULT.get(n)
            self.ck.setdefault(n, Track()).add(t, v, 'step')

    def set(self, t, e='inout', **kw):
        for k, v in kw.items():
            self.wk.setdefault(k, Track()).add(t, v, e)

    def shot(self, t, kind, **kw):
        d = dict(kw, kind=kind, t=t)
        i = bisect.bisect_right([s[0] for s in self.shots], t)
        self.shots.insert(i, (t, d))

    def sfx(self, t, name, gain=1.0, **kw):
        self.fx.append((t, SFX[name](**kw), gain))

    # -- evaluation
    def cartman(self, t):
        p = dict(C.DEFAULT)
        for k, tr in self.ck.items():
            p[k] = tr.at(t, p.get(k))
        return p

    def world(self, t):
        return {k: tr.at(t) for k, tr in self.wk.items()}

    def shot_at(self, t):
        i = bisect.bisect_right([s[0] for s in self.shots], t) - 1
        s0 = self.shots[max(i, 0)][1]
        t1 = self.shots[i + 1][0] if i + 1 < len(self.shots) else self.duration
        return s0, t1


# ------------------------------------------------------------------ sound effects
def _env(n, a=0.002, r=0.05):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / r)


def sfx_click(**kw):
    n = int(0.05 * SR)
    rng = np.random.RandomState(kw.get('seed', 1))
    return (rng.randn(n) * _env(n, 0.0005, 0.006) * 0.5).astype(np.float32)


def sfx_type(dur=2.0, rate=11, seed=2, **kw):
    rng = np.random.RandomState(seed)
    out = np.zeros(int(dur * SR), np.float32)
    t = 0.0
    while t < dur - 0.06:
        c = sfx_click(seed=rng.randint(1e6)) * rng.uniform(0.5, 1.0)
        i = int(t * SR)
        out[i:i + len(c)] += c[:len(out) - i]
        t += rng.uniform(0.6, 1.4) / rate
    return out


def sfx_thud(**kw):
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    rng = np.random.RandomState(3)
    body = np.sin(2 * np.pi * 70 * t) * np.exp(-t / 0.08) + rng.randn(n) * np.exp(-t / 0.02) * 0.3
    return (body * 0.7).astype(np.float32)


def sfx_step(seed=4, **kw):
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    rng = np.random.RandomState(seed)
    return ((np.sin(2 * np.pi * 110 * t) * 0.6 + rng.randn(n) * 0.25) * np.exp(-t / 0.025) * 0.35).astype(np.float32)


def sfx_crowd(dur=3.0, cheer=0.0, **kw):
    n = int(dur * SR)
    rng = np.random.RandomState(5)
    w = rng.randn(n)
    # pinkish murmur: smooth white noise, a slow swell, optional cheer
    from scipy.signal import lfilter
    y = lfilter([0.05], [1, -0.95], w)
    swell = 0.6 + 0.4 * np.sin(np.linspace(0, 3, n))
    if cheer:
        swell += cheer * np.clip(np.linspace(-1, 3, n), 0, 1)
    y = y / (np.abs(y).max() + 1e-9) * swell * 0.18
    fade = np.minimum(1, np.minimum(np.arange(n), n - np.arange(n)) / (0.3 * SR))
    return (y * fade).astype(np.float32)


def sfx_creak(**kw):
    n = int(0.7 * SR)
    t = np.arange(n) / SR
    f = 380 + 120 * np.sin(t * 9)
    y = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.08 * np.sin(np.pi * t / t[-1])
    return y.astype(np.float32)


def sfx_whoosh(**kw):
    n = int(0.4 * SR)
    rng = np.random.RandomState(6)
    from scipy.signal import lfilter
    y = lfilter([0.1], [1, -0.9], rng.randn(n)) * np.sin(np.pi * np.arange(n) / n) ** 2 * 0.25
    return y.astype(np.float32)


SFX = dict(click=sfx_click, type=sfx_type, thud=sfx_thud, step=sfx_step, crowd=sfx_crowd, creak=sfx_creak, whoosh=sfx_whoosh)


# ------------------------------------------------------------------ renderer
class Renderer:
    def __init__(self, tl, size=None):
        self.tl = tl
        if size:
            tl.W, tl.H = size
        self.scale_out = tl.W / 3840.0
        self.mix()
        self.lipsync()
        self.blinks = self.plan_blinks()

    def mix(self):
        tl = self.tl
        tl.duration = tl.t
        n = int(tl.duration * SR) + SR
        v = np.zeros(n, np.float32)
        for s, x in tl.voice:
            i = int(s * SR)
            v[i:i + len(x)] += x[:n - i]
        self.voice = v
        m = v.copy()
        for s, x, g in tl.fx:
            i = int(s * SR)
            m[i:i + len(x)] += x[:n - i] * g
        peak = np.abs(m).max()
        self.audio = m / max(peak, 1.0) * 0.98 if peak > 1 else m

    def lipsync(self):
        sys.path.insert(0, os.path.join(ROOT, 'tools'))
        from render_scene import mouth_track
        spans = [(s, s + len(x) / SR) for s, x in self.tl.voice]
        # 22 kHz analysis is plenty
        x = self.voice[::2]
        self.vis, self.env = mouth_track(x, SR // 2, self.tl.fps, spans)
        self.spans = spans

    def plan_blinks(self):
        rng = np.random.RandomState(11)
        t, out = 2.0, []
        while t < self.tl.duration:
            out.append(t)
            t += rng.uniform(2.2, 4.8)
        return out

    def blink(self, t):
        for b in self.blinks:
            k = (t - b) * self.tl.fps
            if 0 <= k < 4:
                return [0.5, 1.0, 1.0, 0.45][int(k)]
        return 0.0

    def camera(self, t, p):
        """World rect (x0, y0, w) for the shot at t."""
        s, t1 = self.tl.shot_at(t)
        k = s['kind']
        W, H = 3840.0, 2160.0
        s_c = p['s']
        if 'rect' in s:
            x0, y0, w = s['rect']
            cx, cy = x0 + w / 2, y0 + w * H / W / 2
        elif k == 'wide':
            cx, cy, w = W / 2, H / 2, W
        elif k == 'follow':
            w = s.get('w', 2400)
            cx, cy = p['x'] + s.get('dx', 0), p['y'] - 85 * s_c + s.get('dy', 0)
        elif k == 'medium':
            w = s.get('w', 1500)
            cx, cy = p['x'] + s.get('dx', 60), p['y'] - 95 * s_c + s.get('dy', 0)
        elif k == 'close':
            w = s.get('w', 900)
            cx, cy = p['x'] + s.get('dx', 0), p['y'] - 100 * s_c + s.get('dy', 0)
        else:
            cx, cy, w = W / 2, H / 2, W
        if k in ('close', 'medium') and p['view'] in ('right', 'side'):
            cx += 48 * s_c                      # in profile, frame the face, not the back of the head
        if s.get('lock') and 'anchor' in s:
            cx, cy = s['anchor']
        u = (t - s['t']) / max(t1 - s['t'], 1e-3)
        push = s.get('push', 0.0)
        w = w * (1 - push * ease(u, 'inout'))
        if s.get('shake'):
            amp = s['shake'] * math.exp(-4 * max(0, t - s['t']))
            cx += math.sin(t * 90) * amp * w
            cy += math.cos(t * 77) * amp * w
        h = w * H / W
        cx = min(max(cx, w / 2), W - w / 2)
        cy = min(max(cy, h / 2), H - h / 2)
        return cx - w / 2, cy - h / 2, w, s

    def puppet(self, t):
        tl = self.tl
        p = tl.cartman(t)
        f = min(int(t * tl.fps), len(self.vis) - 1)
        speaking = any(a <= t < b for a, b in self.spans)
        env = float(self.env[f]) if speaking else 0.0
        mood = p['mouth']
        if speaking and p.get('talk', True):
            m = VIS2MOUTH.get(self.vis[f])
            if m:
                if p.get('loud_mouth') and m in ('a', 'e', 'o') and env > 0.8:
                    m = p['loud_mouth']
                p['mouth'] = m
                p['mouth_amt'] = 0.8 + 0.45 * env
            p['head_dy'] = p['head_dy'] - env * 2.2
            p['head_tilt'] = p['head_tilt'] + math.sin(t * 2.3) * 1.2 * p.get('tilt_talk', 1.0)
        p['blink'] = max(p['blink'], self.blink(t)) if p['lid_top'] < 0.9 else p['blink']
        if p.get('nod'):
            p['head_dy'] += math.sin(t * 9) * 2.5 * p['nod']
        if p.get('shakehead'):
            p['head_dx'] += math.sin(t * 16) * 6 * p['shakehead']
        if p.get('jitter'):
            p['x'] += math.sin(t * 43) * p['jitter']
        if p['body'] == 'walk':
            p['walk'] = (abs(p['x']) + abs(p['y']) * 0.5) / p.get('stride', 150.0)
        if p['body'] != 'walk' and p['body'] != 'sit':
            p['squash'] = p['squash'] + 0.012 * math.sin(t * 2.2)          # breathing
        return p

    def draw_world(self, pen, t, p, st):
        R.draw_back(pen, t, st)
        if p.get('visible', True):
            pen.save()
            pen.translate(p['x'], p['y'])
            if p.get('lean'):
                pen.rotate(p['lean'])
            pen.scale(p['s'])
            C.draw(pen, p)
            pen.restore()
        R.draw_front(pen, t, st)

    def draw_screen_insert(self, pen, t, st, s):
        W, H = 3840, 2160
        pen.rect(0, 0, W, H, (16, 16, 20))
        sw = 3300
        sh = sw * screens.SH / screens.SW
        x0, y0 = (W - sw) / 2, (H - sh) / 2
        pen.rect(x0 - 70, y0 - 70, x0 + sw + 70, y0 + sh + 70, (34, 34, 40), r=40)
        pen.save()
        pen.translate(x0, y0)
        pen.scale(sw / screens.SW)
        screens.draw(pen, st.get('screen', 'off'), t, st.get('screen_p', {}))
        pen.restore()
        pen.fill(D.polyline([(x0, y0), (x0 + 700, y0), (x0 + 200, y0 + sh), (x0, y0 + sh)], close=True), (255, 255, 255), alpha=10)

    def draw_title(self, pen, t, s):
        W, H = 3840, 2160
        u = t - s['t']
        pen.rect(0, 0, W, H, (14, 12, 18))
        a = int(255 * min(1.0, u / 0.6))
        import skia
        tf = skia.Typeface.MakeFromFile(os.path.join(ROOT, 'fonts', 'Poppins-Bold.ttf'))
        for dx, dy, col in ((14, 14, (120, 10, 20)), (0, 0, (250, 250, 250))):
            pen.text(s.get('text', 'SOUTH MANCHESTER'), W / 2 + dx, H / 2 + 110 + dy, 300, col, font=tf, alpha=a)
        pen.rect(W / 2 - 1100 * min(1, u / 0.8), H / 2 + 200, W / 2 + 1100 * min(1, u / 0.8), H / 2 + 225, (218, 32, 44), alpha=a)

    def render(self, t):
        import skia
        tl = self.tl
        surf, c = D.surface(tl.W, tl.H)
        pen = D.Pen(c)
        pen.scale(self.scale_out)
        p = self.puppet(t)
        st = tl.world(t)
        x0, y0, w, s = self.camera(t, p)
        if s['kind'] == 'screen':
            self.draw_screen_insert(pen, t, st, s)
        elif s['kind'] == 'title':
            self.draw_title(pen, t, s)
        else:
            k = 3840.0 / w
            pen.save()
            pen.scale(k)
            pen.translate(-x0, -y0)
            self.draw_world(pen, t, p, st)
            pen.restore()
        fade = st.get('fade', 0.0) or 0.0
        if fade > 0:
            pen.rect(0, 0, 3840, 2160, (0, 0, 0), alpha=int(255 * min(1, fade)))
        return D.to_bgr(surf)

    # -- output
    def write_audio(self, path):
        sf.write(path, self.audio[:int(self.tl.duration * SR)], SR)

    def frames(self):
        return int(self.tl.duration * self.tl.fps)
