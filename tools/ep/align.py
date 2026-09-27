"""Forced alignment of known dialogue to voice audio (pocketsphinx, offline).

align(wav16k_path, text) -> list of words: {'word', 't0', 't1', 'phones': [(ph, t0, t1), ...]}

The pocketsphinx English acoustic model ships inside the pip package, so this
works without downloading anything. Words missing from its dictionary get a
pronunciation from the CMU dictionary or the EXTRA table below.
"""
import os, re, subprocess
import numpy as np

EXTRA = {
    'goldbridge': 'G OW L D B R IH JH',
    'ryvita': 'R AY V IY T AH',
    'youtube': 'Y UW T UW B',
    'hypothetically': 'HH AY P AH TH EH T IH K L IY',
    'hypothetical': 'HH AY P AH TH EH T IH K AH L',
    'accountability': 'AH K AW N T AH B IH L IH T IY',
    'overseeing': 'OW V ER S IY IH NG',
}
_DEC = None


def decoder():
    global _DEC
    if _DEC is None:
        from pocketsphinx import Decoder
        _DEC = Decoder(samprate=16000, bestpath=False, loglevel='FATAL')
    return _DEC


def words_of(text):
    t = text.lower().replace('’', "'").replace('-', ' ')
    t = re.sub(r"[^a-z' ]", ' ', t)
    return [w.strip("'") if w not in ("'92",) else w for w in t.split() if w.strip("'")]


def ensure_word(d, w):
    if d.lookup_word(w):
        return w
    if w in EXTRA:
        d.add_word(w, EXTRA[w], True)
        return w
    try:
        import cmudict
        pr = cmudict.dict().get(w)
    except Exception:
        pr = None
    if pr:
        d.add_word(w, ' '.join(re.sub(r'\d', '', p) for p in pr[0]), True)
        return w
    # spelling guess
    guess = []
    for ch in re.findall(r'[aeiouy]+|[^aeiouy]', w):
        guess.append({'a': 'AE', 'e': 'EH', 'i': 'IH', 'o': 'OW', 'u': 'AH', 'y': 'IY'}.get(ch[0], None) or
                     {'b': 'B', 'c': 'K', 'd': 'D', 'f': 'F', 'g': 'G', 'h': 'HH', 'j': 'JH', 'k': 'K', 'l': 'L',
                      'm': 'M', 'n': 'N', 'p': 'P', 'q': 'K', 'r': 'R', 's': 'S', 't': 'T', 'v': 'V', 'w': 'W',
                      'x': 'K', 'z': 'Z'}.get(ch, 'T'))
    d.add_word(w, ' '.join(guess), True)
    return w


def to16k(path, out):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', path, '-ac', '1', '-ar', '16000', '-sample_fmt', 's16', out],
                   check=True)
    return out


def read_raw(wav):
    import soundfile as sf
    x, sr = sf.read(wav, dtype='int16')
    assert sr == 16000
    return x.tobytes()


def align(wav16k, text):
    d = decoder()
    ws = [ensure_word(d, w) for w in words_of(text)]
    raw = read_raw(wav16k)
    d.set_align_text(' '.join(ws))
    d.start_utt(); d.process_raw(raw, full_utt=True); d.end_utt()
    d.set_alignment()
    d.start_utt(); d.process_raw(raw, full_utt=True); d.end_utt()
    out = []
    for w in d.get_alignment():
        name = w.name
        if name in ('<s>', '</s>', '<sil>', '[NOISE]'):
            continue
        ph = [(p.name, p.start / 100.0, (p.start + p.duration) / 100.0) for p in w]
        out.append(dict(word=name, t0=w.start / 100.0, t1=(w.start + w.duration) / 100.0, phones=ph))
    return out


def score(wav16k, text):
    """Average acoustic score per frame of the forced alignment (higher = better fit)."""
    d = decoder()
    ws = [ensure_word(d, w) for w in words_of(text)]
    d.set_align_text(' '.join(ws))
    d.start_utt(); d.process_raw(read_raw(wav16k), full_utt=True); d.end_utt()
    h = d.hyp()
    return (h.score / max(d.n_frames(), 1)) if h else -1e9
