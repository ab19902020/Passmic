"""Render a vector episode scene.

    python3 tools/render_episode.py episode/scenes/cartman_room.py            # 4K (3840x2160) 24 fps
    python3 tools/render_episode.py episode/scenes/cartman_room.py 1080p      # quick 1920x1080 preview
    python3 tools/render_episode.py episode/scenes/cartman_room.py still 12 40.5   # out/<scene>_<t>.jpg (4K)

Frames are drawn as vector art straight at the output size, rendered in
parallel segments (JOBS=n to limit), then joined and muxed with the mixed
dialogue + effects track -> out/<scene>_<quality>.mp4.
"""
import importlib.util, os, subprocess, sys, time
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'vec'))
import engine  # noqa: E402
import cv2     # noqa: E402

SIZES = {'4k': (3840, 2160), '1080p': (1920, 1080), '720p': (1280, 720)}
_R = None


def load(scene, size):
    spec = importlib.util.spec_from_file_location('scene', scene)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    tl = mod.build()
    return engine.Renderer(tl, size)


def _init(scene, size):
    global _R
    _R = load(scene, size)


def _segment(args):
    f0, f1, path = args
    r = _R
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', '%dx%d' % (r.tl.W, r.tl.H),
           '-r', str(r.tl.fps), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-threads', '1',
           '-pix_fmt', 'yuv420p', path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(f0, f1):
        p.stdin.write(r.render(f / r.tl.fps).tobytes())
    p.stdin.close()
    p.wait()
    return path


def main():
    a = sys.argv[1:]
    scene = a[0]
    name = os.path.splitext(os.path.basename(scene))[0]
    mode = a[1] if len(a) > 1 else '4k'
    out_dir = os.path.join(ROOT, 'out')
    os.makedirs(out_dir, exist_ok=True)
    if mode == 'still':
        r = load(scene, SIZES['4k'])
        for t in a[2:]:
            path = os.path.join(out_dir, '%s_%s.jpg' % (name, t))
            cv2.imwrite(path, r.render(float(t)), [cv2.IMWRITE_JPEG_QUALITY, 93])
            print(path)
        return
    size = SIZES[mode]
    r = load(scene, size)
    n = r.frames()
    print('%s: %.1f s, %d frames at %dx%d' % (name, r.tl.duration, n, size[0], size[1]), flush=True)
    seg_dir = os.path.join(out_dir, '%s_%s_seg' % (name, mode))
    os.makedirs(seg_dir, exist_ok=True)
    jobs = int(os.environ.get('JOBS', os.cpu_count() or 4))
    nseg = max(jobs * 3, 1)
    bounds = [round(i * n / nseg) for i in range(nseg + 1)]
    tasks = [(bounds[i], bounds[i + 1], os.path.join(seg_dir, 'seg%03d.mp4' % i)) for i in range(nseg)]
    t0 = time.time()
    with Pool(jobs, initializer=_init, initargs=(scene, size)) as pool:
        for i, path in enumerate(pool.imap(_segment, tasks)):
            print('  segment %d/%d done (%.0f s)' % (i + 1, nseg, time.time() - t0), flush=True)
    lst = os.path.join(seg_dir, 'list.txt')
    with open(lst, 'w') as fh:
        fh.writelines("file '%s'\n" % os.path.basename(p) for _, _, p in tasks)
    audio = os.path.join(out_dir, '%s_mix.wav' % name)
    r.write_audio(audio)
    out = os.path.join(out_dir, '%s_%s.mp4' % (name, mode))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-i', audio,
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-shortest', '-movflags', '+faststart', out], check=True)
    print(out)


if __name__ == '__main__':
    main()
