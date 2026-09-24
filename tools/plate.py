import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
ASSETS = _os.path.join(ROOT, 'assets'); MASKS = _os.path.join(ROOT, 'masks'); DATA = _os.path.join(ROOT, 'data'); SOURCE = _os.path.join(ROOT, 'source'); OUTDIR = _os.path.join(ROOT, 'out'); TOOLS = _os.path.join(ROOT, 'tools')
import cv2, numpy as np
img=cv2.imread(SOURCE + '/18306.png').astype(np.float32)
H,W=img.shape[:2]
hole=np.zeros((H,W),np.uint8)
for n in ['carra1','nev1','keane1']: hole|=cv2.imread(f'{MASKS}/maskc_{n}.png',0)
hole=cv2.dilate(hole,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(17,17)))
out=img.copy()
for y in range(H):
    row=hole[y]>0
    if not row.any(): continue
    xs=np.where(row)[0]
    # segments
    br=np.where(np.diff(xs)>1)[0]
    starts=np.r_[xs[0],xs[br+1]]; ends=np.r_[xs[br],xs[-1]]
    for a,b in zip(starts,ends):
        L=img[max(0,y-2):y+3, max(0,a-8):max(1,a-1)].reshape(-1,3).mean(0) if a>1 else None
        R=img[max(0,y-2):y+3, b+2:min(W,b+9)].reshape(-1,3).mean(0) if b<W-3 else None
        if L is None: L=R
        if R is None: R=L
        t=np.linspace(0,1,b-a+1)[:,None]
        out[y,a:b+1]=L*(1-t)+R*t
# vertical smoothing inside the hole
sm=cv2.GaussianBlur(out,(0,0),sigmaX=2,sigmaY=9)
hf=cv2.GaussianBlur(hole.astype(np.float32)/255,(0,0),3)[...,None]
out=out*(1-hf)+sm*hf
cv2.imwrite('assets/plate_rows.png',out.astype(np.uint8))
cv2.imwrite('assets/hole.png',hole)
cv2.imwrite('plate_prev.jpg',cv2.resize(out.astype(np.uint8),(1280,720)))
