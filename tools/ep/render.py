"""Render the episode.

    python3 tools/ep/render.py still 12 40.5 ...   -> out/ep01/still_<t>.jpg (4K)
    python3 tools/ep/render.py 1080p               -> out/ep01/ep01_1080p.mp4
    python3 tools/ep/render.py 4k                  -> out/ep01/ep01_4k.mp4
    python3 tools/ep/render.py sheet 0 300 5       -> out/ep01/sheet.jpg (contact sheet)
    python3 tools/ep/render.py timings             -> print the line timeline

JOBS=n sets the parallel workers (by default as many as memory allows: ~4.5 GB per 4K worker).
Segments are resumable: a finished one is kept as out/ep01/seg_<mode>/f<first>-<end>.mp4
(written under a temporary name and renamed when complete), so re-running
renders only what is missing. Delete the folder after changing the episode.
"""
import os, subprocess, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool
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
    tmp = path[:-4] + '.part.mp4'
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', '%dx%d' % (w, h), '-r', str(E.FPS),
           '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-threads', '1',
           '-x264-params', 'rc-lookahead=20', '-pix_fmt', 'yuv420p', tmp]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(f0, f1):
        p.stdin.write(R.render(f / E.FPS).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError('ffmpeg failed on ' + path)
    os.replace(tmp, path)
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
    # each 4K worker peaks around 4.5 GB (the high-res drawings and their face masks): by default
    # run as many as the memory allows
    try:
        mem = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
        cg = '/sys/fs/cgroup/memory.max'
        if os.path.exists(cg) and open(cg).read().strip().isdigit():
            mem = min(mem, int(open(cg).read()))
    except (ValueError, OSError):
        mem = 16e9
    per = 4.5e9 if size[0] > 2000 else 2.5e9
    jobs = int(os.environ.get('JOBS', max(1, min(os.cpu_count() or 4, int(mem // per)))))
    nseg = 12                          # fixed, so a resumed render (any JOBS) reuses the same pieces
    b = [round(i * n / nseg) for i in range(nseg + 1)]
    segd = os.path.join(OUTD, 'seg_' + mode)
    os.makedirs(segd, exist_ok=True)
    # named by frame range: a changed episode length never reuses a stale piece
    tasks = [(b[i], b[i + 1], os.path.join(segd, 'f%06d-%06d.mp4' % (b[i], b[i + 1]))) for i in range(nseg)]
    todo = [t for t in tasks if not os.path.exists(t[2])]
    t0 = time.time()
    print('%d frames at %dx%d, %d workers, %d of %d segments to render' % (n, size[0], size[1], jobs, len(todo), nseg),
          flush=True)
    if todo:
        # a worker killed from outside (out of memory) breaks the pool at once instead of hanging it
        try:
            with ProcessPoolExecutor(min(jobs, len(todo)), initializer=_init, initargs=(size,)) as ex:
                futs = [ex.submit(_segment, t) for t in todo]
                for i, fu in enumerate(as_completed(futs)):
                    print('  segment %s done, %d/%d (%.0f s)' % (os.path.basename(fu.result()), i + 1, len(todo),
                                                                  time.time() - t0), flush=True)
        except BrokenProcessPool:
            left = [os.path.basename(t[2]) for t in tasks if not os.path.exists(t[2])]
            sys.exit('a render worker died (out of memory?) - run again to finish: ' + ' '.join(left))
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
