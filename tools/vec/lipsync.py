"""Word-driven lip sync from a known script (no speech-recognition model needed).

align(wav, sr, text) -> list of (t0, t1, mouth) for one voice clip.

Every word is looked up in the CMU pronouncing dictionary (plus a few names
below) and split into syllables. The syllables are spread over the clip's
voiced time (pauses carry no syllables), then each syllable's vowel is snapped
onto the nearest loudness peak, so the open mouths land on the real vowels.
Each phoneme then gets the mouth that makes that sound: M/B/P close the lips,
F/V bite the lip, TH shows the tongue, OO/W round the lips, AH opens wide.

Words the script doesn't know (a laugh, an ad-lib) can be written as
<laugh:N> or <unk:N> (N syllables); they get open mouths on the peaks.
"""
import re
import numpy as np
import scipy.signal as ss

EXTRA = {
    'glazers': ['G', 'L', 'EY1', 'Z', 'ER0', 'Z'],
    'cantona': ['K', 'AE0', 'N', 'T', 'OW1', 'N', 'AH0'],
    'cartman': ['K', 'AA1', 'R', 'T', 'M', 'AH0', 'N'],
    "'92": ['N', 'AY1', 'N', 'T', 'IY0', 'T', 'UW1'],
    'badass': ['B', 'AE1', 'D', 'AE2', 'S'],
    'eric': ['EH1', 'R', 'IH0', 'K'],
    'gonna': ['G', 'AH1', 'N', 'AH0'],
}
VOWELS = {'AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'EH', 'ER', 'EY', 'IH', 'IY', 'OW', 'OY', 'UH', 'UW'}
MOUTH = {
    'AA': 'a', 'AE': 'a', 'AH': 'a', 'AW': 'a', 'AY': 'a', 'HH': 'e',
    'EH': 'e', 'EY': 'e', 'ER': 'w',
    'IH': 'i', 'IY': 'i', 'Y': 'i', 'S': 'i', 'Z': 'i', 'T': 'i', 'D': 'i', 'N': 'i', 'K': 'i', 'G': 'i',
    'NG': 'i', 'CH': 'i', 'JH': 'i', 'SH': 'u', 'ZH': 'u',
    'OW': 'o', 'AO': 'o', 'OY': 'o',
    'UW': 'u', 'UH': 'u', 'W': 'w', 'R': 'w',
    'M': 'm', 'B': 'm', 'P': 'm',
    'F': 'f', 'V': 'f',
    'TH': 'th', 'DH': 'th',
    'L': 'l',
}
_DICT = None


def cmu():
    global _DICT
    if _DICT is None:
        import cmudict
        _DICT = cmudict.dict()
    return _DICT


def phones(word):
    w = word.lower().strip(".,!?;:\"")
    if w in EXTRA:
        return EXTRA[w]
    d = cmu()
    if w in d:
        return d[w][0]
    w2 = w.replace("'", "")
    if w2 in d:
        return d[w2][0]
    # unknown: a rough spelling-based guess, one syllable per vowel group
    out = []
    for ch in re.findall(r'[aeiouy]+|[^aeiouy]', w2):
        if ch[0] in 'aeiouy':
            out.append({'a': 'AE1', 'e': 'EH1', 'i': 'IH1', 'o': 'OW1', 'u': 'AH1', 'y': 'IY1'}[ch[0]])
        else:
            out.append({'m': 'M', 'b': 'B', 'p': 'P', 'f': 'F', 'v': 'V', 'l': 'L', 'w': 'W', 'r': 'R'}.get(ch, 'T'))
    return out


def syllables(text):
    """[(phones_before_vowel, vowel, phones_after)] for the whole text, plus
    the index of the first syllable of each punctuation-separated phrase."""
    sylls, starts = [], []
    for phrase in re.split(r'(?<=[.!?,;:])\s+|\.\.\.', text):
        phrase = phrase.strip()
        if not phrase:
            continue
        starts.append(len(sylls))
        for word in phrase.split():
            m = re.match(r'<(laugh|unk):(\d+)>', word)
            if m:
                for _ in range(int(m.group(2))):
                    sylls.append(([], 'LAUGH' if m.group(1) == 'laugh' else 'AA', []))
                continue
            ph = [re.sub(r'\d', '', p) for p in phones(word)]
            vi = [i for i, p in enumerate(ph) if p in VOWELS]
            if not vi:
                continue
            for k, v in enumerate(vi):
                a = 0 if k == 0 else (vi[k - 1] + v) // 2 + 1
                b = len(ph) if k == len(vi) - 1 else (v + vi[k + 1]) // 2 + 1
                sylls.append((ph[a:v], ph[v], ph[v + 1:b]))
    return sylls, starts


def envelope(x, sr, rate=200):
    b, a = ss.butter(4, [300 / (sr / 2), 2500 / (sr / 2)], 'band')
    y = ss.filtfilt(b, a, x)
    hop = int(sr / rate)
    env = np.sqrt(np.convolve(y ** 2, np.ones(hop * 4) / (hop * 4), 'same'))[::hop]
    return ss.savgol_filter(env, 11, 2)


def align(x, sr, text, rate=200):
    env = envelope(x, sr, rate)
    db = 20 * np.log10(np.abs(env) + 1e-6)
    voiced = db > np.percentile(db, 95) - 28
    # close tiny gaps inside words, drop specks
    k = int(0.06 * rate)
    v = voiced.astype(np.uint8)
    v = np.convolve(v, np.ones(k), 'same') > 0
    sylls, _ = syllables(text)
    n = len(sylls)
    if n == 0:
        return []
    vt = np.nonzero(v)[0]
    if len(vt) == 0:
        return []
    # syllable centres spread evenly over voiced time
    pos = (np.arange(n) + 0.5) / n * len(vt)
    centres = vt[np.clip(pos.astype(int), 0, len(vt) - 1)].astype(float)
    # snap each vowel to a nearby unused loudness peak, keeping order
    pk, _ = ss.find_peaks(env, prominence=np.percentile(env, 90) * 0.12, distance=int(0.07 * rate))
    used = -1
    for i in range(n):
        lo, hi = centres[i] - 0.12 * rate, centres[i] + 0.12 * rate
        cand = pk[(pk > used) & (pk >= lo) & (pk <= hi)]
        if len(cand):
            c = cand[np.argmin(np.abs(cand - centres[i]))]
            centres[i] = c
            used = c
    centres = np.maximum.accumulate(centres)
    # syllable spans: halfway between neighbouring centres, clipped to voiced runs
    out = []
    for i, (pre, vow, post) in enumerate(sylls):
        c = centres[i]
        a = (centres[i - 1] + c) / 2 if i else c - 0.1 * rate
        b = (c + centres[i + 1]) / 2 if i + 1 < n else c + 0.12 * rate
        a = max(a, c - 0.16 * rate)
        b = min(b, c + 0.18 * rate)
        seq = pre + [vow] + post
        # vowel gets the middle, consonants share the edges
        w = [1.0] * len(pre) + [max(2.5, len(pre) + len(post))] + [1.0] * len(post)
        w = np.cumsum([0] + w) / sum(w)
        for j, ph in enumerate(seq):
            t0, t1 = a + (b - a) * w[j], a + (b - a) * w[j + 1]
            if ph == 'LAUGH':
                m = 'laugh'
            else:
                m = MOUTH.get(ph, 'i')
            out.append((t0 / rate, t1 / rate, m, ph in VOWELS or ph == 'LAUGH'))
    return out


def frames(events, dur, fps, hold=2):
    """Per-frame mouth list (None = closed) from aligned events, each mouth
    held for at least `hold` frames like the show's animation on twos. A
    closed-lip consonant always shows, however short."""
    n = int(dur * fps) + 1
    best = [None] * n
    weight = np.zeros(n)
    for t0, t1, m, is_vowel in events:
        f0, f1 = int(t0 * fps), max(int(t0 * fps) + 1, int(round(t1 * fps)))
        for f in range(max(f0, 0), min(f1, n)):
            w = (t1 - t0) + (0.2 if is_vowel else 0) + (0.3 if m == 'm' else 0)
            if w > weight[f]:
                weight[f] = w
                best[f] = None if m == 'm' else m
    out, last, held = [], None, 99
    for f in range(n):
        m = best[f]
        if m != last and held < hold:
            m = last
        held = held + 1 if m == last else 1
        out.append(m)
        last = m
    return out
