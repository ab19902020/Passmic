"""Review sheet for cut-out sprites: every sprite of a character laid out per
panel on a flat colour, so fringes, holes and stray bits show up.

    python3 tools/sprite_review.py kyle [bg] [scale]   -> out/review_kyle.png
    bg: magenta (default) | dark | white | check
"""
import json, os, sys
import cv2, numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EP = os.path.join(ROOT, 'episode')
BGS = {'magenta': (200, 40, 200), 'dark': (40, 40, 40), 'white': (255, 255, 255), 'green': (60, 190, 60)}


def over(rgba, bg):
    h, w = rgba.shape[:2]
    if bg == 'check':
        yy, xx = np.mgrid[:h, :w]
        base = np.where((((yy // 8) + (xx // 8)) % 2)[..., None] == 0, 235, 190).astype(np.float32) * np.ones(3)
    else:
        base = np.ones((h, w, 3), np.float32) * np.array(BGS[bg], np.float32)
    a = rgba[..., 3:4].astype(np.float32) / 255
    return (rgba[..., :3] * a + base * (1 - a)).astype(np.uint8)


def review(char, bg='magenta', scale=2.0, width=1900):
    idx = json.load(open(os.path.join(EP, 'characters', char, 'index.json')))
    rows = []
    for panel, sprites in idx['sprites'].items():
        tiles = []
        for key, s in sprites.items():
            rgba = cv2.imread(os.path.join(EP, s['file']), cv2.IMREAD_UNCHANGED)
            rgba = cv2.resize(rgba, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
            t = over(rgba, bg)
            lab = np.full((16, t.shape[1], 3), 255, np.uint8)
            cv2.putText(lab, key[:max(4, t.shape[1] // 7)], (2, 12), cv2.FONT_HERSHEY_PLAIN, 0.8, (0, 0, 0), 1)
            tiles.append(np.vstack([t, lab]))
        # wrap tiles into lines
        line, lines, wsum = [], [], 0
        for t in tiles:
            if line and wsum + t.shape[1] + 6 > width:
                lines.append(line); line, wsum = [], 0
            line.append(t); wsum += t.shape[1] + 6
        lines.append(line)
        head = np.full((22, width, 3), 50, np.uint8)
        cv2.putText(head, panel, (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        rows.append(head)
        for ln in lines:
            hmax = max(t.shape[0] for t in ln)
            canvas = np.full((hmax + 6, width, 3), 128, np.uint8)
            x = 3
            for t in ln:
                canvas[hmax - t.shape[0] + 3:hmax + 3, x:x + t.shape[1]] = t
                x += t.shape[1] + 6
            rows.append(canvas)
    out = os.path.join(ROOT, 'out', 'review_%s.png' % char)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cv2.imwrite(out, np.vstack(rows))
    return out


if __name__ == '__main__':
    a = sys.argv
    print(review(a[1], a[2] if len(a) > 2 else 'magenta', float(a[3]) if len(a) > 3 else 2.0))
