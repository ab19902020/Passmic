import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
ASSETS = _os.path.join(ROOT, 'assets'); MASKS = _os.path.join(ROOT, 'masks'); DATA = _os.path.join(ROOT, 'data'); SOURCE = _os.path.join(ROOT, 'source'); OUTDIR = _os.path.join(ROOT, 'out'); TOOLS = _os.path.join(ROOT, 'tools')
import cv2, numpy as np, ast, sys
sys.path.insert(0,TOOLS)
from trimap import cutout
from ov import ov
name, path, others, B = sys.argv[1], sys.argv[2], sys.argv[3].split(','), int(sys.argv[4])
P=lambda n: ast.literal_eval(open(f'{MASKS}/poly_{n}.txt').read())
img=cv2.imread(path)
m=cutout(img,P(name),[P(o) for o in others if o],B=B)
cv2.imwrite(f'{MASKS}/mask_{name}.png',m)
ys,xs=np.where(m>0); y0,y1,x0,x1=ys.min(),ys.max(),xs.min(),xs.max()
c=img[y0:y1,x0:x1]; mm=m[y0:y1,x0:x1]
H,W=mm.shape; chk=(np.indices((H,W)).sum(0)//12)%2
bg=np.where(chk[...,None]==1,np.array([60,200,60]),np.array([200,60,200])).astype(np.uint8)
z=np.where(mm[...,None]>0,c,bg).copy()
for gx in range((x0//50+1)*50, x1, 50):
    cv2.line(z,(gx-x0,0),(gx-x0,y1-y0),(0,255,255) if gx%100==0 else (0,120,120),1)
    if gx%100==0: cv2.putText(z,str(gx),(gx-x0+2,12),cv2.FONT_HERSHEY_SIMPLEX,0.4,(0,0,0),2); cv2.putText(z,str(gx),(gx-x0+2,12),cv2.FONT_HERSHEY_SIMPLEX,0.4,(0,255,255),1)
for gy in range((y0//50+1)*50, y1, 50):
    cv2.line(z,(0,gy-y0),(x1-x0,gy-y0),(255,0,255) if gy%100==0 else (120,0,120),1)
    if gy%100==0: cv2.putText(z,str(gy),(2,gy-y0-2),cv2.FONT_HERSHEY_SIMPLEX,0.4,(0,0,0),2); cv2.putText(z,str(gy),(2,gy-y0-2),cv2.FONT_HERSHEY_SIMPLEX,0.4,(255,0,255),1)
cv2.imwrite(f'{MASKS}/z_{name}.jpg',z)
