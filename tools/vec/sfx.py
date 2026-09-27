"""Synthesised sound effects for episode scenes (mono float32 at SR).

Everything is generated, so there are no sample files to license. The aim is
the show's sound: small, dry, close-miked foley (kid footsteps on carpet,
a door latch, a chair cushion), computer-speaker audio from the monitor, a
quiet room tone under everything, and an acoustic-guitar sting on the title.
"""
import numpy as np
from scipy.signal import butter, lfilter, sosfilt

SR = 44100


def _t(dur):
    return np.arange(int(dur * SR)) / SR


def _band(x, lo, hi, order=2):
    sos = butter(order, [lo / (SR / 2), min(hi, SR / 2 - 100) / (SR / 2)], 'band', output='sos')
    return sosfilt(sos, x)


def _lp(x, hi, order=2):
    return sosfilt(butter(order, hi / (SR / 2), 'low', output='sos'), x)


def _hp(x, lo, order=2):
    return sosfilt(butter(order, lo / (SR / 2), 'high', output='sos'), x)


def _decay(n, attack, tau):
    t = np.arange(n) / SR
    return np.minimum(1.0, t / max(attack, 1e-4)) * np.exp(-t / tau)


def _f32(x, gain=1.0):
    return (np.asarray(x) * gain).astype(np.float32)


# ------------------------------------------------------------------ foley
def step(seed=0, surface='carpet', heavy=1.0, **kw):
    """One kid footstep: a soft heel pat and a scuff (carpet), or a harder
    tap (wood). Every step is a little different."""
    rng = np.random.RandomState(seed)
    n = int(0.16 * SR)
    t = np.arange(n) / SR
    f = rng.uniform(95, 130) * (1.15 if surface == 'wood' else 1.0)
    thump = np.sin(2 * np.pi * f * t * (1 - 0.35 * t / t[-1])) * _decay(n, 0.002, 0.03)
    pat = _band(rng.randn(n), 350, 2600 if surface == 'carpet' else 4500) * _decay(n, 0.001, 0.012 if surface == 'carpet' else 0.008)
    scuff = np.zeros(n)
    if surface == 'carpet':
        k = int(rng.uniform(0.025, 0.045) * SR)
        m = int(0.07 * SR)
        scuff[k:k + m] = _band(rng.randn(m), 900, 5000) * np.hanning(m) * 0.25
    y = thump * 0.55 * heavy + pat * 0.5 + scuff
    return _f32(y, rng.uniform(0.75, 1.0) * 0.55)


def door_open(**kw):
    """Handle turn, latch release, and a short hinge creak."""
    rng = np.random.RandomState(21)
    out = np.zeros(int(1.0 * SR))
    n = int(0.12 * SR)
    handle = _band(rng.randn(n), 1500, 7000) * _decay(n, 0.002, 0.03) * 0.35
    out[:n] += handle
    k = int(0.14 * SR)
    latch = _band(rng.randn(int(0.04 * SR)), 2000, 9000) * _decay(int(0.04 * SR), 0.0005, 0.004) * 0.9
    out[k:k + len(latch)] += latch
    t = _t(0.55)
    freq = 520 + 180 * np.sin(2 * np.pi * 2.3 * t) + 60 * np.sin(2 * np.pi * 7 * t)
    creak = np.sign(np.sin(2 * np.pi * np.cumsum(freq) / SR)) * np.sin(np.pi * t / t[-1]) ** 1.5
    creak = _band(creak, 400, 3500) * 0.06
    k = int(0.3 * SR)
    out[k:k + len(creak)] += creak
    return _f32(out)


def door_close(**kw):
    """Air push, the door thumping into its frame, and the latch clicking."""
    rng = np.random.RandomState(22)
    out = np.zeros(int(0.8 * SR))
    n = int(0.18 * SR)
    whoosh = _lp(rng.randn(n), 800) * np.sin(np.pi * np.arange(n) / n) ** 2 * 0.08
    out[:n] += whoosh
    k = int(0.16 * SR)
    t = _t(0.45)
    thump = (np.sin(2 * np.pi * 62 * t) * 0.9 + np.sin(2 * np.pi * 131 * t) * 0.35) * _decay(len(t), 0.001, 0.07)
    thump += _band(rng.randn(len(t)), 150, 1800) * _decay(len(t), 0.0005, 0.02) * 0.6
    out[k:k + len(t)] += thump * 0.8
    m = int(0.035 * SR)
    latch = _band(rng.randn(m), 2500, 9000) * _decay(m, 0.0005, 0.005) * 0.7
    k2 = k + int(0.04 * SR)
    out[k2:k2 + m] += latch
    return _f32(out)


def cushion(**kw):
    """Plopping onto a padded chair seat: soft fwump plus a little creak."""
    rng = np.random.RandomState(23)
    t = _t(0.5)
    fwump = _lp(rng.randn(len(t)), 500) * _decay(len(t), 0.004, 0.06) * 0.9
    fwump += np.sin(2 * np.pi * 85 * t) * _decay(len(t), 0.003, 0.05) * 0.5
    freq = 700 + 90 * np.sin(2 * np.pi * 5 * t)
    creak = _band(np.sign(np.sin(2 * np.pi * np.cumsum(freq) / SR)), 500, 3000) * 0.03 * np.clip((t - 0.08) / 0.05, 0, 1) * np.exp(-np.maximum(t - 0.08, 0) / 0.12)
    return _f32(fwump * 0.6 + creak)


def chair_creak(**kw):
    """A swivel chair shifting under someone."""
    t = _t(0.6)
    freq = 430 + 140 * np.sin(2 * np.pi * 3.1 * t) + 40 * np.sin(2 * np.pi * 11 * t)
    y = _band(np.sign(np.sin(2 * np.pi * np.cumsum(freq) / SR)), 300, 2500) * np.sin(np.pi * t / t[-1]) ** 2
    return _f32(y, 0.05)


def click(seed=1, **kw):
    """Mouse button: a crisp tick then a tiny release."""
    rng = np.random.RandomState(seed)
    out = np.zeros(int(0.1 * SR))
    m = int(0.012 * SR)
    for k, g in ((0, 1.0), (int(0.055 * SR), 0.45)):
        out[k:k + m] += _band(rng.randn(m), 2500, 10000) * _decay(m, 0.0002, 0.0018) * g
        out[k:k + m] += np.sin(2 * np.pi * 1800 * np.arange(m) / SR) * _decay(m, 0.0002, 0.001) * 0.3 * g
    return _f32(out, 0.8)


def key(seed=0, **kw):
    """One keyboard key: plasticky tick with a low thock."""
    rng = np.random.RandomState(seed)
    n = int(0.05 * SR)
    t = np.arange(n) / SR
    tick = _band(rng.randn(n), 1800, 8000) * _decay(n, 0.0002, 0.003)
    thock = np.sin(2 * np.pi * rng.uniform(220, 320) * t) * _decay(n, 0.0005, 0.008) * 0.6
    return _f32(tick * 0.7 + thock, rng.uniform(0.5, 0.9) * 0.5)


def typing(dur=2.0, rate=9.0, seed=2, **kw):
    """A burst of typing: bursts of keys with little hesitations, a space bar now and then."""
    rng = np.random.RandomState(seed)
    out = np.zeros(int(dur * SR) + SR // 10, np.float32)
    t = 0.0
    while t < dur:
        k = key(seed=rng.randint(1 << 30))
        if rng.rand() < 0.15:
            k = k * 1.4
        i = int(t * SR)
        out[i:i + len(k)] += k[:len(out) - i]
        t += rng.uniform(0.55, 1.5) / rate + (0.18 if rng.rand() < 0.08 else 0)
    return out


def whoosh(**kw):
    rng = np.random.RandomState(6)
    n = int(0.35 * SR)
    y = _band(rng.randn(n), 300, 3000) * np.sin(np.pi * np.arange(n) / n) ** 2
    return _f32(y, 0.18)


def hop(**kw):
    """Scrambling up / jumping: cloth rustle plus a small grunt-less thump."""
    rng = np.random.RandomState(8)
    n = int(0.3 * SR)
    rustle = _band(rng.randn(n), 1500, 7000) * np.sin(np.pi * np.arange(n) / n) ** 3 * 0.12
    return _f32(rustle)


# ------------------------------------------------------------------ beds
def room_tone(dur):
    """A quiet, slightly warm room: soft air noise and a faint mains hum."""
    rng = np.random.RandomState(31)
    t = _t(dur)
    air = _lp(rng.randn(len(t)), 700) * 0.006
    hum = (np.sin(2 * np.pi * 50 * t) * 0.6 + np.sin(2 * np.pi * 100 * t) * 0.4) * 0.0012
    return _f32(air + hum)


def crowd_bed(dur, seed=5):
    """Stadium crowd murmur with chants and swells (full band)."""
    rng = np.random.RandomState(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    base = _band(rng.randn(n), 250, 3500) * 0.5
    swell = 0.7 + 0.3 * np.sin(2 * np.pi * 0.13 * t + 1.3) + 0.15 * np.sin(2 * np.pi * 0.37 * t)
    # chant: a rhythmic formant-ish throb, two claps a bar
    chant = _band(rng.randn(n), 400, 1100) * (0.5 + 0.5 * np.sin(2 * np.pi * 1.1 * t) ** 8) * 0.25
    claps = np.zeros(n)
    for c in np.arange(0.4, dur, 0.9):
        k = int(c * SR)
        m = min(int(0.06 * SR), n - k)
        if m > 0:
            claps[k:k + m] += _band(rng.randn(m), 800, 5000) * _decay(m, 0.001, 0.02) * 0.35
    return _f32(base * swell + chant + claps)


def cheer(dur, seed=6):
    """A goal: the crowd erupts and slowly settles."""
    rng = np.random.RandomState(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    env = np.clip(t / 0.35, 0, 1) * np.exp(-np.maximum(t - 0.8, 0) / 2.2)
    roar = _band(rng.randn(n), 300, 5000) * env * 1.6
    return _f32(roar)


def speaker(x):
    """Make audio sound like it's coming out of small computer speakers."""
    y = _band(np.asarray(x, np.float64), 380, 5200, order=3)
    return _f32(np.tanh(y * 1.5) / 1.5)


def guitar_sting(**kw):
    """A short, bright acoustic-guitar strum-and-riff (Karplus-Strong plucks),
    like the show's scene bumpers."""
    def pluck(freq, dur, seed):
        rng = np.random.RandomState(seed)
        n = int(dur * SR)
        p = int(SR / freq)
        buf = rng.uniform(-1, 1, p)
        out = np.empty(n)
        for i in range(n):
            out[i] = buf[i % p]
            buf[i % p] = 0.996 * 0.5 * (buf[i % p] + buf[(i + 1) % p])
        return out * _decay(n, 0.001, dur * 0.5)
    notes = []
    # strum of an open G chord, then a quick riff up the G major pentatonic
    for i, f in enumerate((98.0, 123.5, 146.8, 196.0, 246.9, 392.0)):
        notes.append((0.0 + i * 0.018, f, 1.6))
    for i, f in enumerate((293.7, 329.6, 392.0, 440.0, 493.9, 587.3)):
        notes.append((0.55 + i * 0.11, f, 0.6))
    for i, f in enumerate((98.0, 146.8, 196.0, 246.9, 293.7, 392.0)):
        notes.append((1.3 + i * 0.02, f, 1.8))
    out = np.zeros(int(3.3 * SR))
    for k, (t0, f, d) in enumerate(notes):
        y = pluck(f, d, k)
        i = int(t0 * SR)
        out[i:i + len(y)] += y[:len(out) - i]
    out = _hp(out, 70)
    return _f32(out / (np.abs(out).max() + 1e-9), 0.35)


def land(**kw):
    """Feet landing on a padded seat after a hop: a soft double thump."""
    a = step(seed=91, heavy=1.6)
    b = step(seed=92, heavy=1.3)
    out = np.zeros(len(a) + int(0.05 * SR), np.float32)
    out[:len(a)] += a
    out[int(0.05 * SR):int(0.05 * SR) + len(b)] += b * 0.8
    return out


def marker(seed=3, **kw):
    """A dry-wipe marker squeaking across a whiteboard."""
    rng = np.random.RandomState(seed)
    t = _t(0.5)
    f = 900 + 250 * np.sin(2 * np.pi * 7 * t) + 150 * rng.randn(len(t)).cumsum() / len(t) * 5
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR)
    fric = _band(rng.randn(len(t)), 2000, 7000)
    env = np.clip(t / 0.03, 0, 1) * np.clip((0.5 - t) / 0.08, 0, 1)
    return _f32((tone * 0.25 + fric * 0.35) * env, 0.12)


SFX = dict(step=step, land=land, marker=marker, door_open=door_open, door_close=door_close, cushion=cushion, chair_creak=chair_creak,
           click=click, key=key, typing=typing, type=typing, whoosh=whoosh, hop=hop, sting=guitar_sting)
