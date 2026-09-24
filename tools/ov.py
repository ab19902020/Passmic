import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
ASSETS = _os.path.join(ROOT, 'assets'); MASKS = _os.path.join(ROOT, 'masks'); DATA = _os.path.join(ROOT, 'data'); SOURCE = _os.path.join(ROOT, 'source'); OUTDIR = _os.path.join(ROOT, 'out'); TOOLS = _os.path.join(ROOT, 'tools')
import cv2, numpy as np, ast, sys
def ov(path, name, pad=20, step=50, out=None, sub=None):
    img=cv2.imread(path); poly=ast.literal_eval(open(f'{MASKS}/poly_{name}.txt').read())
    xs=[p[0] for p in poly]; ys=[p[1] for p in poly]
    x0,y0,x1,y1=min(xs)-pad,min(ys)-pad,max(xs)+pad,max(ys)+pad
    if sub: x0,y0,x1,y1=sub
    c=img[y0:y1,x0:x1].copy()
    for gx in range((x0//step+1)*step, x1, step):
        cv2.line(c,(gx-x0,0),(gx-x0,y1-y0),(0,255,255) if gx%100==0 else (0,140,140),1)
        if gx%100==0: cv2.putText(c,str(gx),(gx-x0+2,12),cv2.FONT_HERSHEY_SIMPLEX,0.4,(0,255,255),1)
    for gy in range((y0//step+1)*step, y1, step):
        cv2.line(c,(0,gy-y0),(x1-x0,gy-y0),(255,0,255) if gy%100==0 else (140,0,140),1)
        if gy%100==0: cv2.putText(c,str(gy),(2,gy-y0-2),cv2.FONT_HERSHEY_SIMPLEX,0.4,(255,0,255),1)
    p=np.array([[x-x0,y-y0] for x,y in poly],np.int32)
    cv2.polylines(c,[p],True,(0,255,0),1)
    for i,(x,y) in enumerate(p):
        cv2.circle(c,(int(x),int(y)),3,(0,0,255),-1); cv2.putText(c,str(i),(int(x)+3,int(y)-3),cv2.FONT_HERSHEY_SIMPLEX,0.35,(255,255,255),1)
    cv2.imwrite(out or f'{MASKS}/ov_{name}.jpg',c)
if __name__=='__main__':
    a=sys.argv; ov(a[1],a[2])
