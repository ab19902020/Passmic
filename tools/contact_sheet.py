# Contact sheet: python3 tools/contact_sheet.py <t0> <t1> <step_s> <out.jpg>
# One labelled 320x180 thumbnail (time, beat, section, shot type) per step, rendered on all cores.
import os, sys, cv2, numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'render')); ARGS = sys.argv[1:]
import render as R
from concurrent.futures import ProcessPoolExecutor
def one(t):
    b = (t - R.PH) / R.P
    f = cv2.resize(R.render(t), (320, 180), interpolation=cv2.INTER_AREA)
    s_ = R.shot_at(b); cv2.putText(f, f'{t:.1f}s {R.section(b)} {s_["type"]} {s_.get("who", "")}', (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 255), 1)
    return f
if __name__ == '__main__':
    t0, t1, st, out = float(ARGS[0]), float(ARGS[1]), float(ARGS[2]), ARGS[3]
    with ProcessPoolExecutor(os.cpu_count()) as ex: fr = list(ex.map(one, list(np.arange(t0, t1, st))))
    while len(fr) % 6: fr.append(np.zeros_like(fr[0]))
    cv2.imwrite(out, np.vstack([np.hstack(fr[i:i + 6]) for i in range(0, len(fr), 6)]), [cv2.IMWRITE_JPEG_QUALITY, 85])
