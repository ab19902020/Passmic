import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# Builds data/mouth_curve.npz at 24 fps:
#   open  - mouth opening 0..~1.1, driven by the isolated vocal stem (real syllables, closes between them)
#   width - mouth width factor (wide for a/e/i, narrower and rounder for o/u), from the vocal spectrum
#   who   - who is voicing the line at each frame (see WHO below), from the lyric cues in data/subs.srt
# Needs (none of these are committed; regenerate from the song):
#   ffmpeg -i source/Gary__Pass_The_Microphone__.m4a -map 0:s:0 data/subs.srt
#   ffmpeg -i source/Gary__Pass_The_Microphone__.m4a -ac 2 -ar 44100 data/song.wav
#   pip install demucs && python3 -m demucs --two-stems=vocals -n htdemucs -o data/sep data/song.wav
#   (-> data/sep/htdemucs/song/vocals.wav)
import numpy as np, re, sys
import soundfile as sf
from scipy.ndimage import uniform_filter1d, maximum_filter1d
from scipy.signal import find_peaks
D = _os.path.join(ROOT, 'data')
VOC = sys.argv[1] if len(sys.argv) > 1 else _os.path.join(D, 'sep', 'htdemucs', 'song', 'vocals.wav')
FPS = 24; N = int(226 * FPS) + 2

# ---- vocal envelope at 100 fps -------------------------------------------------------------
x, sr = sf.read(VOC); x = x.mean(1) if x.ndim > 1 else x
AF = 100; hop = sr // AF; nfft = 2048; win = np.hanning(nfft)
nfr = (len(x) - nfft) // hop
fr = np.fft.rfftfreq(nfft, 1 / sr)
bands = {'speech': (fr > 150) & (fr < 4000), 'low': (fr > 250) & (fr < 900), 'high': (fr > 1400) & (fr < 3500)}
E = {k: np.zeros(nfr) for k in bands}
for i in range(nfr):
    sp = np.abs(np.fft.rfft(x[i * hop:i * hop + nfft] * win)) ** 2
    for k, m in bands.items(): E[k][i] = sp[m].sum()
db = 10 * np.log10(E['speech'] + 1e-10)
db = uniform_filter1d(db, 3)
# loudness relative to the local loud level (so quiet verses and shouted choruses both articulate)
ref = uniform_filter1d(maximum_filter1d(db, AF * 2), AF * 2)
lev = np.clip((db - (ref - 26)) / 22, 0, 1)
# syllable articulation: emphasise envelope peaks, force a short closure in the dips between syllables
fast = uniform_filter1d(db, 5); slow = uniform_filter1d(db, 25)
art = np.clip(0.75 + (fast - slow) / 10, 0.35, 1.25)
op100 = lev ** 1.2 * art
pk, _ = find_peaks(-fast, prominence=3.0, distance=6)
for p in pk:
    if lev[p] > 0.05: op100[max(0, p - 1):p + 2] *= 0.25
# vowel colour -> width: bright (high formant energy) = wide, dark = round
bright = 10 * np.log10(E['high'] + 1e-10) - 10 * np.log10(E['low'] + 1e-10)
wid100 = np.clip(0.85 + (uniform_filter1d(bright, 7) + 8) / 40, 0.72, 1.05)

# ---- lyric cues -> who is singing ------------------------------------------------------------
# WHO codes: 0 nobody, 1 lead (whoever holds the mic), 2 everyone (chorus), 3 nev, 4 carra, 5 keane
def ts(v):
    h, m, r = v.split(':'); s_, ms = r.split(','); return int(h) * 3600 + int(m) * 60 + int(s_) + int(ms) / 1000
cues = []; section = ''
for blk in [b for b in open(_os.path.join(D, 'subs.srt'), encoding='utf-8').read().strip().split('\n\n') if '-->' in b]:
    ls = blk.split('\n'); tl = [l for l in ls if '-->' in l][0]; a, c = [ts(v.strip()) for v in tl.split('-->')]
    txt = ' '.join(ls[ls.index(tl) + 1:]).strip()
    if txt.startswith('['): section = txt.lower(); continue
    cues.append((a, c, txt, section))
SPEAKER = {'gary': 3, 'jamie': 4, 'keane': 5}
LINE = [  # lines voiced by one pundit (lower-case substring match)
    ('welcome back', 3), ('put the tactics board down', 4),          # spoken intro: Gary hosts, Carra heckles
    ('sack him', 3),                                                   # Gary's own rant
    ("here's the thing", 4), ('standards! hunger! pride', 5),          # Jamie's catchphrase, Keane's creed
    ('serious questions', 3), ('gary…', 4), ("haven't even kicked off", 5),  # spoken outro
]
who100 = np.zeros(nfr, np.int8)
for a, c, txt, sec in cues:
    low = txt.lower(); w = 2 if 'chorus' in sec else 1
    m_ = re.match(r'(\w+):', low)
    if m_ and m_.group(1) in SPEAKER: w = SPEAKER[m_.group(1)]
    for key, code in LINE:
        if key in low: w = code
    who100[int(max(0, a - 0.08) * AF):int((c + 0.12) * AF)] = w
op100[who100 == 0] = 0

# ---- to 24 fps (peak-preserving) + light smoothing --------------------------------------------
tt = np.arange(N) / FPS
idx = np.clip((tt * AF).astype(int), 0, nfr - 1)
op = np.array([op100[max(0, i - 2):i + 3].max() for i in idx], np.float32)
op = np.convolve(op, [0.2, 0.6, 0.2], 'same').astype(np.float32)
width = wid100[idx].astype(np.float32); who = who100[idx]
np.savez(_os.path.join(D, 'mouth_curve.npz'), open=op, width=width, who=who)
print('saved data/mouth_curve.npz  open>0.3: %.2f  who counts:' % (op > 0.3).mean(), np.bincount(who, minlength=6))
