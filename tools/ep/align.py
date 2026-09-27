"""Forced alignment of known dialogue to voice audio (pocketsphinx, offline).

align(wav16k_path, text) -> list of words: {'word', 't0', 't1', 'phones': [(ph, t0, t1), ...]}

    python3 tools/ep/align.py            # align every voice file in series/ep01/audio not yet in alignment.json
    python3 tools/ep/align.py RK_01 ...  # (re)align just these lines

The renderer runs the first form itself, so a new recording (say RK_05.wav)
only needs dropping into series/ep01/audio/.

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
_DEC = {}


def decoder(wide=False):
    """wide: much wider search beams, for takes the default search loses track of."""
    if wide not in _DEC:
        from pocketsphinx import Decoder
        kw = dict(beam=1e-100, wbeam=1e-80, pbeam=1e-100) if wide else {}
        _DEC[wide] = Decoder(samprate=16000, bestpath=False, loglevel='FATAL', **kw)
    return _DEC[wide]


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


def align(wav16k, text, wide=False):
    try:
        return _align(wav16k, text, wide)
    except Exception:
        if wide:
            raise
        return _align(wav16k, text, True)


def _align(wav16k, text, wide):
    d = decoder(wide)
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


AUDIO_EXT = ('.wav', '.mp3', '.m4a', '.aac', '.flac', '.ogg')


def align_episode(ids=None, force=False, quiet=False):
    """Align the episode's voice files into series/ep01/audio/alignment.json.
    Returns the IDs aligned."""
    import json, sys, tempfile
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ep = os.path.join(root, 'series', 'ep01')
    sys.path.insert(0, ep)
    import script
    adir = os.path.join(ep, 'audio')
    path = os.path.join(adir, 'alignment.json')
    al = json.load(open(path)) if os.path.exists(path) else {}
    done = []
    for lid in (ids or script.LINES):
        src = next((os.path.join(adir, lid + e) for e in AUDIO_EXT if os.path.exists(os.path.join(adir, lid + e))), None)
        if src is None or (lid in al and not force and not ids):
            continue
        with tempfile.TemporaryDirectory() as td:
            w16 = os.path.join(td, lid + '.wav')
            to16k(src, w16)
            al[lid] = align(w16, script.LINES[lid])
        done.append(lid)
        if not quiet:
            print('aligned', lid, ' '.join(w['word'] for w in al[lid]), flush=True)
    if done:
        with open(path, 'w') as f:
            json.dump(al, f, indent=0)
    return done


if __name__ == '__main__':
    import sys
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    align_episode(args or None, force='--force' in sys.argv)
