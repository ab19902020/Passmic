import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# Builds data/mouth_curve.npz: syllable-timed mouth opening at 24 fps.
# Needs data/song22.wav (mono 22050) and data/subs.srt, extracted from the song:
#   ffmpeg -i source/Gary__Pass_The_Microphone__.m4a -map 0:a -ac 1 -ar 22050 data/song22.wav
#   ffmpeg -i source/Gary__Pass_The_Microphone__.m4a -map 0:s:0 data/subs.srt
import numpy as np, wave, re
from scipy.signal import find_peaks
from scipy.ndimage import uniform_filter1d
D = _os.path.join(ROOT, 'data')
w = wave.open(_os.path.join(D, 'song22.wav')); sr = w.getframerate()
x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
hop, nfft = 220, 1024; n = (len(x) - nfft) // hop; win = np.hanning(nfft).astype(np.float32)
band = (np.fft.rfftfreq(nfft, 1 / sr) > 250) & (np.fft.rfftfreq(nfft, 1 / sr) < 3500)
S = np.array([np.abs(np.fft.rfft(x[i * hop:i * hop + nfft] * win))[band] for i in range(n)], np.float32)
L = np.log1p(S * 20); flux = uniform_filter1d(np.maximum(0, np.diff(L, axis=0, prepend=L[:1])).sum(1), 3)
energy = uniform_filter1d(L.mean(1), 5); fps_a = sr / hop
def ts(v):
    h, m, r = v.split(':'); s_, ms = r.split(','); return int(h) * 3600 + int(m) * 60 + int(s_) + int(ms) / 1000
cues = []
for b in [b for b in open(_os.path.join(D, 'subs.srt')).read().strip().split('\n\n') if '-->' in b]:
    ls = b.split('\n'); tl = [l for l in ls if '-->' in l][0]; a, c = [ts(v.strip()) for v in tl.split('-->')]
    cues.append((a, c, ' '.join(ls[ls.index(tl) + 1:]).lower()))
def syllables(t):
    out = []
    for wd in re.findall(r"[a-z']+", t):
        wd2 = re.sub(r"e$", "", wd) if len(wd) > 3 else wd
        out += [g[0] for g in (re.findall(r"[aeiouy]+", wd2) or ['a'])]
    return out
SHAPE = {'a': (1.0, 1.0), 'o': (0.95, 0.8), 'e': (0.75, 1.0), 'i': (0.55, 1.0), 'y': (0.55, 1.0), 'u': (0.65, 0.78)}
FPS = 24; N = int(226 * FPS) + 2; op = np.zeros(N, np.float32); wf = np.ones(N, np.float32); tt = np.arange(N) / FPS
for (a, c, txt) in cues:
    syl = syllables(txt); k = len(syl); i0, i1 = int(max(0, (a - 0.06) * fps_a)), int(min(len(flux) - 1, (c - 0.05) * fps_a)); seg = flux[i0:i1]
    if len(seg) < 3 or k == 0: continue
    pk, _ = find_peaks(seg, distance=max(1, int(0.085 * fps_a))); pk = pk[np.argsort(seg[pk])[::-1][:k]]; times = sorted((i0 + p) / fps_a for p in pk)
    while len(times) < k:
        edges = [a] + times + [c]; gi = int(np.argmax(np.diff(edges))); times = sorted(times + [(edges[gi] + edges[gi + 1]) / 2])
    loud = np.clip((energy[i0:i1].mean() - energy.mean()) * 1.5 + 0.85, 0.6, 1.15)
    for j, (ti, v) in enumerate(zip(times[:k], syl)):
        tn = times[j + 1] if j + 1 < len(times) else min(c, ti + 0.45); amp, wid = SHAPE.get(v, (0.8, 1.0)); amp *= loud; hold = min(ti + 0.55 * (tn - ti), ti + 0.28)
        for f in range(max(0, int((ti - 0.06) * FPS)), min(N, int(tn * FPS) + 1)):
            t = tt[f]; v_ = amp * max(0, (t - (ti - 0.06)) / 0.06) if t < ti else amp if t <= hold else amp * max(0.08, 1 - (t - hold) / max(0.04, tn - 0.02 - hold))
            if v_ > op[f]: op[f] = v_; wf[f] = wid
np.savez(_os.path.join(D, 'mouth_curve.npz'), open=op, width=wf); print('saved data/mouth_curve.npz')
