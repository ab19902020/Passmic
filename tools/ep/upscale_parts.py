"""Second 4x AI pass (16x the original sheets) for the drawings seen large:
expressions, heads, busts and standing/walking bodies of Mark and Gary, and
Roy's expressions, head, poses and mouth shapes.

    python3 tools/ep/upscale_parts.py      -> series/ep01/characters_x16/<char>/<panel>/<name>.png

The RGB is re-upscaled from the x4 sheet (with its own background around the
drawing, so edges don't pick up a dark fringe); the alpha is upscaled with a
smooth filter and re-sharpened. Resumable: existing outputs are skipped.
"""
import json, os, sys
import cv2, numpy as np
from realesrgan_ncnn_py import Realesrgan

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import face_rig as F     # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EP = os.path.join(ROOT, 'series', 'ep01')


def up_alpha(a, k=4):
    big = cv2.resize(a.astype(np.float32) / 255, None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC)
    big = cv2.GaussianBlur(big, (0, 0), 1.0)
    big = np.clip((big - 0.5) * 2.5 + 0.5, 0, 1)
    return (big * 255).astype(np.uint8)


def main():
    r = Realesrgan(gpuid=-1, model=3, tilesize=256)
    jobs = []
    # Roy first (his sheet came last), then Mark's and Gary's
    for ch, panels in (('roy', ('expressions', 'head', 'body', 'mouths')), ('gary', ('head', 'expressions', 'upper', 'body')),
                       ('mark', ('head', 'expressions', 'upper', 'body'))):
        idx = json.load(open(os.path.join(EP, 'characters', ch, 'index.json')))
        sheet = cv2.imread(os.path.join(EP, 'x4', ch + '.png'))
        for panel in panels:
            for name, s in idx.get(panel, {}).items():
                if 'sheet_rect_x4' not in s:
                    continue            # built from other drawings (Roy's walk), not cut from a sheet
                if ch == 'mark' and panel == 'body' and not name.startswith('stand'):
                    continue            # Mark never walks
                jobs.append((ch, panel, name, s, sheet))
    for ch, panel, name, s, sheet in jobs:
        out = os.path.join(EP, 'characters_x16', ch, panel, name + '.png')
        if os.path.exists(out):
            continue
        x, y, w, h = s['sheet_rect_x4']
        rgba = cv2.imread(os.path.join(EP, s['file']), cv2.IMREAD_UNCHANGED)
        rgb = sheet[y:y + h, x:x + w]
        big = r.process_cv2(np.ascontiguousarray(rgb))
        a = up_alpha(rgba[..., 3], big.shape[0] // h)
        a = cv2.resize(a, (big.shape[1], big.shape[0]))
        res = np.dstack([big, a])
        res[a == 0, :3] = 0
        os.makedirs(os.path.dirname(out), exist_ok=True)
        if panel != 'mouths':
            res = F.drop_intrusions(res)[0]
        cv2.imwrite(out, res, [cv2.IMWRITE_PNG_COMPRESSION, 4])
        print(out, res.shape, flush=True)


if __name__ == '__main__':
    main()
