"""Render an episode scene from a scene file.

    python3 tools/render_scene.py episode/scenes/cartman_room.json            # -> out/<name>.mp4
    python3 tools/render_scene.py episode/scenes/cartman_room.json still 12.5  # -> out/<name>_12.5.jpg

A scene file lists the voice clips in order (with the shots, poses and faces
to use while each plays). The clips are laid end to end on one audio track;
the speaker's mouth is driven from that track (loudness, brightness and hiss
pick one of the ten drawn mouth shapes, held for at least two frames, as the
show does). Characters come from episode/characters_hd.
"""
import json, os, subprocess, sys
import cv2, numpy as np, soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EP = os.path.join(ROOT, 'episode')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import face  # noqa: E402

VISEMES = ['a_ah', 'e_eh', 'i_ee', 'o_oh', 'u_oo', 'm_closed', 'l_tongue', 'f_v', 'th_teeth', 'w_rounded']
DEFAULT_POSES = ['turnaround/front', 'poses/standing', 'poses/hands_on_hips', 'poses/lean_forward_talk',
                 'poses/crossed_arms']
# drawings cropped by their sheet cells: framed from the bottom of the screen
BUST_PANELS = ('gestures', 'expressions', 'mouths', 'head')


# ---------------------------------------------------------------- audio
def load_audio(path, sr=22050):
    tmp = os.path.join(ROOT, 'out', 'audio', os.path.basename(path) + '.wav')
    if not os.path.exists(tmp) or os.path.getmtime(tmp) < os.path.getmtime(path):
        os.makedirs(os.path.dirname(tmp), exist_ok=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', path, '-ac', '1', '-ar', str(sr), tmp], check=True)
    x, _ = sf.read(tmp, dtype='float32')
    return x


def build_track(scene, sr=22050):
    """Lay the clips end to end; returns the track and each line's start/end."""
    lead, gap, tail = scene.get('lead_in', 1.0), scene.get('gap', 0.6), scene.get('tail', 2.0)
    parts, spans, t = [np.zeros(int(lead * sr), np.float32)], [], lead
    for line in scene['lines']:
        x = load_audio(os.path.join(EP, line['clip']), sr)
        x = x[int(line.get('trim', 0) * sr):]
        spans.append((t, t + len(x) / sr))
        parts += [x, np.zeros(int(line.get('gap', gap) * sr), np.float32)]
        t += len(x) / sr + line.get('gap', gap)
    parts.append(np.zeros(int(tail * sr), np.float32))
    return np.concatenate(parts), spans


def mouth_track(x, sr, fps, spans, seed=7):
    """One viseme per frame from the voice."""
    n = int(len(x) / sr * fps) + 1
    win = int(sr / fps * 1.5)
    rms, zcr, cen = np.zeros(n), np.zeros(n), np.zeros(n)
    freqs = np.fft.rfftfreq(win, 1 / sr)
    hann = np.hanning(win)
    for f in range(n):
        c = int(f / fps * sr)
        seg = x[max(0, c - win // 2):c + win // 2]
        if len(seg) < win:
            seg = np.pad(seg, (0, win - len(seg)))
        rms[f] = np.sqrt(np.mean(seg ** 2))
        zcr[f] = np.mean(np.abs(np.diff(np.sign(seg)))) / 2
        spec = np.abs(np.fft.rfft(seg * hann))
        cen[f] = (spec * freqs).sum() / max(spec.sum(), 1e-9)
    db = 20 * np.log10(rms + 1e-6)
    loud = np.zeros(n)
    for a, b in spans:                       # normalise per clip
        fa, fb = int(a * fps), min(n, int(b * fps) + 1)
        ref = np.percentile(db[fa:fb], 95)
        loud[fa:fb] = np.clip((db[fa:fb] - (ref - 30)) / 30, 0, 1)
    rng = np.random.RandomState(seed)
    vis, last, held = [], 'm_closed', 99
    for f in range(n):
        l, z, c = loud[f], zcr[f], cen[f]
        if l < 0.28:
            v = 'm_closed'
        elif z > 0.22 and l < 0.75:
            v = 'th_teeth' if c > 3000 else 'f_v'
        elif l > 0.78:
            v = 'a_ah' if c < 1500 else 'e_eh'
        elif l > 0.55:
            v = 'o_oh' if c < 1000 else ('e_eh' if c < 2200 else 'i_ee')
        else:
            v = ['u_oo', 'w_rounded'][rng.randint(2)] if c < 900 else ['i_ee', 'l_tongue', 'e_eh'][rng.randint(3)]
        if v != last and held < 2:           # hold every mouth two frames
            v = last
        held = held + 1 if v == last else 1
        vis.append(v)
        last = v
    env = cv2.GaussianBlur(loud.reshape(1, -1).astype(np.float32), (0, 0), 1.2).ravel()
    return vis, env


# ---------------------------------------------------------------- character
class Character:
    """HD sprites of one character, with mouths removed and viseme mouths
    ready to paste onto any of its drawings."""

    def __init__(self, name):
        self.name = name
        self.idx = json.load(open(os.path.join(EP, 'characters_hd', name, 'index.json')))
        self.cache = {}
        self.vis = {}
        for v in VISEMES:
            rgba = self.sprite('mouths/' + v)
            fi = face.face_info(rgba)
            patch, c = face.mouth_patch(rgba, fi)
            self.vis[v] = dict(patch=patch, c=c, face_w=fi['face_w'], top=fi['mouth_top'], cy=fi['mouth_c'][1])

    def sprite(self, key):
        panel, k = key.split('/')
        if key not in self.cache:
            s = self.idx['sprites'][panel][k]
            self.cache[key] = cv2.imread(os.path.join(EP, s['file']), cv2.IMREAD_UNCHANGED)
        return self.cache[key]

    def meta(self, key):
        panel, k = key.split('/')
        return self.idx['sprites'][panel][k]

    def base(self, key):
        """(mouthless sprite, face info) for a drawing, cached."""
        ck = ('base', key)
        if ck not in self.cache:
            rgba = self.sprite(key)
            fi = face.face_info(rgba)
            self.cache[ck] = (face.mouthless(rgba, fi) if fi and fi['has_mouth'] else rgba, fi)
        return self.cache[ck]

    def drawing(self, key, viseme, blink=0.0, keep_mouth=False):
        """The drawing with the given mouth (and eyelids), full HD size."""
        ck = ('draw', key, viseme, round(blink, 2), keep_mouth)
        if ck in self.cache:
            return self.cache[ck]
        base, fi = self.base(key)
        if keep_mouth or not fi or not fi['has_mouth']:
            img = self.sprite(key).copy()
        else:
            img = base.copy()
            m = self.vis[viseme]
            s = fi['face_w'] / m['face_w']
            p = cv2.resize(m['patch'], None, fx=s, fy=s, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
            # upper lip stays put, the jaw drops: align the mouths' top edges
            cx = fi['mouth_c'][0]
            top = fi['mouth_top']
            x0 = int(round(cx - m['c'][0] * s))
            y0 = int(round(top - (m['top'] - (m['cy'] - m['c'][1])) * s))
            paste(img, p, x0, y0)
        if blink > 0 and fi:
            img = face.blink(img, fi, blink)
        if len(self.cache) > 400:
            self.cache = {k: v for k, v in self.cache.items() if k[0] != 'draw'}
        self.cache[ck] = img
        return img


def paste(dst, src, x0, y0):
    """Alpha-composite RGBA src onto RGBA dst in place."""
    h, w = src.shape[:2]
    H, W = dst.shape[:2]
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
    if xa >= xb or ya >= yb:
        return
    s = src[ya - y0:yb - y0, xa - x0:xb - x0].astype(np.float32)
    d = dst[ya:yb, xa:xb].astype(np.float32)
    a = s[..., 3:4] / 255
    out = s[..., :3] * a + d[..., :3] * (1 - a)
    da = a + d[..., 3:4] / 255 * (1 - a)
    dst[ya:yb, xa:xb, :3] = out.clip(0, 255).astype(np.uint8)
    dst[ya:yb, xa:xb, 3:4] = (da * 255).clip(0, 255).astype(np.uint8)


def over_frame(frame, rgba, x0, y0):
    """Composite RGBA onto a BGR frame in place."""
    h, w = rgba.shape[:2]
    H, W = frame.shape[:2]
    xa, ya, xb, yb = max(int(x0), 0), max(int(y0), 0), min(int(x0) + w, W), min(int(y0) + h, H)
    if xa >= xb or ya >= yb:
        return
    s = rgba[ya - int(y0):yb - int(y0), xa - int(x0):xb - int(x0)].astype(np.float32)
    a = s[..., 3:4] / 255
    d = frame[ya:yb, xa:xb].astype(np.float32)
    frame[ya:yb, xa:xb] = (s[..., :3] * a + d * (1 - a)).astype(np.uint8)


# ---------------------------------------------------------------- scene
class Scene:
    def __init__(self, path):
        self.path = path
        self.s = json.load(open(path))
        s = self.s
        self.name = os.path.splitext(os.path.basename(path))[0]
        self.fps = s.get('fps', 24)
        self.W, self.H = s.get('size', [1920, 1080])
        self.bg = cv2.imread(os.path.join(EP, s['background']))
        self.sr = 22050
        self.track, self.spans = build_track(s, self.sr)
        self.dur = len(self.track) / self.sr
        self.nframes = int(self.dur * self.fps)
        self.char = Character(s['character'])
        self.vis, self.env = mouth_track(self.track, self.sr, self.fps, self.spans)
        self.shots = self.plan_shots()
        self.blinks = self.plan_blinks()
        # face width of the reference drawing sets the character's world scale
        ref = s.get('reference_pose', 'turnaround/front')
        _, fi = self.char.base(ref)
        self.ref_face_w = fi['face_w']
        self.ref_h = self.char.meta(ref)['feet'][1]
        self.world_scale = s['height'] / self.ref_h

    def plan_shots(self):
        """Expand each line's shot list into absolute times; lines without
        explicit poses cycle through talking gestures on each phrase."""
        shots = []
        k = 0
        for li, (line, (a, b)) in enumerate(zip(self.s['lines'], self.spans)):
            for j, sh in enumerate(line.get('shots', [{'shot': 'wide'}])):
                t0 = a + sh.get('at', 0) if j else (a - (self.s.get('lead_in', 1.0) if li == 0 else self.s.get('gap', 0.6) * 0.5))
                d = dict(sh, t0=t0, line=li)
                if 'pose' not in d and 'poses' not in d:
                    d['poses'] = DEFAULT_POSES[k % len(DEFAULT_POSES):] + DEFAULT_POSES[:k % len(DEFAULT_POSES)]
                    k += 3
                shots.append(d)
        for i, sh in enumerate(shots):
            sh['t1'] = shots[i + 1]['t0'] if i + 1 < len(shots) else self.dur + 1
        return shots

    def plan_blinks(self):
        rng = np.random.RandomState(3)
        t, out = 1.5, []
        while t < self.dur:
            out.append(t)
            t += rng.uniform(2.5, 5.0)
        return out

    def blink_amount(self, t):
        for b in self.blinks:
            dt = (t - b) * self.fps
            if 0 <= dt < 3:
                return [0.6, 1.0, 0.6][int(dt)]
        return 0.0

    def shot_at(self, t):
        for sh in self.shots:
            if sh['t0'] <= t < sh['t1']:
                return sh
        return self.shots[-1]

    def phrase_index(self, t, sh):
        """Which phrase of the line we're in (pauses split phrases)."""
        a = max(sh['t0'], 0)
        f0, f1 = int(a * self.fps), int(t * self.fps)
        quiet, n = 0, 0
        for f in range(f0, f1):
            if self.env[f] < 0.15:
                quiet += 1
                if quiet == 6:
                    n += 1
            else:
                quiet = 0
        return n

    def camera(self, sh, t, bust=False):
        W, H = self.bg.shape[1], self.bg.shape[0]
        fx, fy = self.s['stand']
        hgt = self.s['height']
        kind = sh.get('shot', 'wide')
        cw = {'wide': W, 'medium': 2200, 'close': 1500}[kind]
        cw = sh.get('cam_w', cw)
        ch = cw * self.H / self.W
        if kind == 'wide':
            cx, cy = W / 2, H / 2
        elif bust:
            # waist-up / head-and-shoulders: the frame's bottom edge cuts the
            # character (belly for medium, chest for close), so we see the wall
            cut = fy - hgt * (0.3 if kind == 'medium' else 0.45)
            cx, cy = fx, cut - ch / 2
        else:
            cx, cy = fx, fy - hgt * 0.55
        push = sh.get('push', 0.03 if kind != 'wide' else 0.0)
        u = np.clip((t - sh['t0']) / max(sh['t1'] - sh['t0'], 1e-3), 0, 1)
        cw *= 1 - push * u
        ch = cw * self.H / self.W
        cx = np.clip(cx, cw / 2, W - cw / 2)
        cy = np.clip(cy, ch / 2, H - ch / 2)
        return cx - cw / 2, cy - ch / 2, cw, ch

    def render(self, f):
        t = f / self.fps
        sh = self.shot_at(t)
        poses = sh.get('poses') or [sh.get('pose') or sh.get('face')]
        key = poses[self.phrase_index(t, sh) % len(poses)]
        bust = key.split('/')[0] in BUST_PANELS
        x0, y0, cw, ch = self.camera(sh, t, bust)
        k = self.W / cw
        M = np.float32([[k, 0, -x0 * k], [0, k, -y0 * k]])
        frame = cv2.warpAffine(self.bg, M, (self.W, self.H), flags=cv2.INTER_AREA if k < 1 else cv2.INTER_LINEAR)
        speaking = any(a <= t < b for a, b in self.spans)
        vis = self.vis[min(f, len(self.vis) - 1)] if speaking else 'm_closed'
        env = self.env[min(f, len(self.env) - 1)] if speaking else 0.0
        blink = self.blink_amount(t)
        kind = sh.get('shot', 'wide')
        img = self.char.drawing(key, vis, blink, keep_mouth=sh.get('keep_mouth', False))
        _, fi = self.char.base(key)
        if bust:
            # busts (cropped by their sheet cells) sit on the bottom of the frame
            frac = sh.get('face_frac', 0.42 if kind == 'close' else 0.30)
            s = frac * self.W / fi['face_w']
            bob = -env * 10
            img2 = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
            cxf = sh.get('face_x', 0.5) * self.W
            over_frame(frame, img2, cxf - fi['eye_c'][0] * s, self.H - img2.shape[0] + 12 + bob)
        else:
            meta = self.char.meta(key)
            # same head size whichever drawing: scale by face width
            s = self.world_scale * (self.ref_face_w / fi['face_w']) * k
            squash = 1 + 0.012 * env
            img2 = cv2.resize(img, None, fx=s, fy=s * squash,
                              interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
            fx, fy = self.s['stand']
            fx += sh.get('dx', 0)
            px = (fx - x0) * k - meta['feet'][0] * s
            py = (fy - y0) * k - meta['feet'][1] * s * squash - env * 6 * k
            over_frame(frame, img2, px, py)
        return frame

    def write_audio(self):
        path = os.path.join(ROOT, 'out', self.name + '_audio.wav')
        sf.write(path, self.track, self.sr)
        return path

    def render_video(self, out=None, jobs=None):
        out = out or os.path.join(ROOT, 'out', self.name + '.mp4')
        audio = self.write_audio()
        cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', '%dx%d' % (self.W, self.H),
               '-r', str(self.fps), '-i', '-', '-i', audio, '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
               '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for f in range(self.nframes):
            p.stdin.write(self.render(f).tobytes())
            if f % 240 == 0:
                print('frame %d / %d' % (f, self.nframes), flush=True)
        p.stdin.close()
        p.wait()
        return out


if __name__ == '__main__':
    sc = Scene(sys.argv[1])
    if len(sys.argv) > 2 and sys.argv[2] == 'still':
        for t in sys.argv[3:]:
            path = os.path.join(ROOT, 'out', '%s_%s.jpg' % (sc.name, t))
            cv2.imwrite(path, sc.render(int(float(t) * sc.fps)), [cv2.IMWRITE_JPEG_QUALITY, 92])
            print(path)
    else:
        print(sc.render_video())
