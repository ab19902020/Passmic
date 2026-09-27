"""Render the episode.

    python3 tools/ep/render.py still 12 40.5 ...   -> out/ep01/still_<t>.jpg (4K)
    python3 tools/ep/render.py 1080p               -> out/ep01/ep01_1080p.mp4
    python3 tools/ep/render.py 4k                  -> out/ep01/ep01_4k.mp4
    python3 tools/ep/render.py sheet 0 300 5       -> out/ep01/sheet.jpg (contact sheet)
    python3 tools/ep/render.py timings             -> print the line timeline

JOBS=n limits parallel workers.
"""
import os, subprocess, sys, time
from multiprocessing import Pool
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'series', 'ep01'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'vec'))
import cv2
import epengine as E
OUTD = os.path.join(ROOT, 'out', 'ep01')
SIZES = {'4k': (3840, 2160), '1080p': (1920, 1080), '720p': (1280, 720)}
_R = None


def load(size=E.OUT):
    import align
    if align.align_episode(quiet=True):          # a newly dropped-in recording
        E.ALIGN.clear()
        E.load_alignment()
    import episode
    tl = episode.build()
    return E.Renderer(tl, size)


def mix(R):
    import soundfile as sf
    import sfx as SFX
    tl = R.tl
    n = int((tl.t + 1) * E.SR)
    v = np.zeros(n, np.float32)
    for ln in tl.lines:
        if not ln['audio']:
            continue
        x = E.load_audio(ln['audio'])
        loud = x[np.abs(x) > 0.02]
        rms = np.sqrt(np.mean(loud ** 2)) if len(loud) else 0.1
        x = x * min(0.12 / max(rms, 1e-4), 4.0)
        i = int(ln['start'] * E.SR)
        v[i:i + len(x)] += x[:n - i]
    fx = np.zeros(n, np.float32)
    for t, name, gain, kw in tl.fx:
        x = SFX.SFX[name](**kw)
        i = int(t * E.SR)
        fx[i:i + len(x)] += x[:n - i] * gain
    # footsteps: two per walk cycle (8 drawings a second -> a step every 4 drawings)
    k = 0
    for who in ('gary', 'roy', 'mark'):
        prev = None
        for j in range(int(tl.t * 100)):
            t = j / 100
            walking = tl.get(who, 'loc', t) == 'walk'
            step = int(t * 8) // 2 if walking else None
            if walking and prev is not None and step != prev:
                x = SFX.step(seed=k, surface='carpet', heavy=1.2)
                k += 1
                i = int(t * E.SR)
                fx[i:i + len(x)] += x[:n - i] * 1.2
            prev = step
    m = v + fx
    f = int(0.3 * E.SR)
    m[:f] *= np.linspace(0, 1, f)
    peak = np.abs(m).max()
    if peak > 0.95:
        m = m / peak * 0.95
    path = os.path.join(OUTD, 'ep01_mix.wav')
    sf.write(path, m[:int(tl.t * E.SR)], E.SR)
    return path


def _init(size):
    global _R
    _R = load(size)


def _segment(args):
    f0, f1, path = args
    R = _R
    w, h = R.size
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', '%dx%d' % (w, h), '-r', str(E.FPS),
           '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-threads', '1', '-pix_fmt', 'yuv420p', path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(f0, f1):
        p.stdin.write(R.render(f / E.FPS).tobytes())
    p.stdin.close()
    p.wait()
    return path


def main():
    a = sys.argv[1:]
    os.makedirs(OUTD, exist_ok=True)
    mode = a[0] if a else '1080p'
    if mode == 'timings':
        R = load((640, 360))
        for ln in R.tl.lines:
            print('%7.2f %5.2f %s %s %s' % (ln['start'], ln['dur'], ln['id'], 'REC' if ln['audio'] else '---', ln['text'][:60]))
        print('total %.1f s' % R.tl.t)
        return
    if mode == 'still':
        R = load()
        for t in a[1:]:
            p = os.path.join(OUTD, 'still_%s.jpg' % t)
            cv2.imwrite(p, R.render(float(t)), [cv2.IMWRITE_JPEG_QUALITY, 92])
            print(p)
        return
    if mode == 'sheet':
        R = load((480, 270))
        t0, t1, step = float(a[1]), float(a[2]), float(a[3])
        tiles, t = [], t0
        while t < min(t1, R.tl.t):
            im = R.render(t).copy()
            cv2.putText(im, '%.1f' % t, (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
            tiles.append(im)
            t += step
        while len(tiles) % 5:
            tiles.append(np.zeros_like(tiles[0]))
        out = a[4] if len(a) > 4 else os.path.join(OUTD, 'sheet.jpg')
        cv2.imwrite(out, np.vstack([np.hstack(tiles[i:i + 5]) for i in range(0, len(tiles), 5)]))
        print(out)
        return
    size = SIZES[mode]
    R = load(size)
    n = int(R.tl.t * E.FPS)
    jobs = int(os.environ.get('JOBS', os.cpu_count() or 4))
    nseg = jobs * 4
    b = [round(i * n / nseg) for i in range(nseg + 1)]
    segd = os.path.join(OUTD, 'seg_' + mode)
    os.makedirs(segd, exist_ok=True)
    tasks = [(b[i], b[i + 1], os.path.join(segd, 'seg%03d.mp4' % i)) for i in range(nseg)]
    t0 = time.time()
    print('%d frames at %dx%d, %d workers' % (n, size[0], size[1], jobs), flush=True)
    with Pool(jobs, initializer=_init, initargs=(size,)) as pool:
        for i, _ in enumerate(pool.imap(_segment, tasks)):
            print('  segment %d/%d (%.0f s)' % (i + 1, nseg, time.time() - t0), flush=True)
    lst = os.path.join(segd, 'list.txt')
    with open(lst, 'w') as f:
        f.writelines("file '%s'\n" % os.path.basename(p) for _, _, p in tasks)
    audio = mix(R)
    out = os.path.join(OUTD, 'ep01_%s.mp4' % mode)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-i', audio, '-c:v', 'copy',
                    '-c:a', 'aac', '-b:a', '256k', '-shortest', '-movflags', '+faststart', out], check=True)
    print(out)


if __name__ == '__main__':
    main()
