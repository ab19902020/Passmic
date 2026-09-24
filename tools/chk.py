import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
ASSETS = _os.path.join(ROOT, 'assets'); MASKS = _os.path.join(ROOT, 'masks'); DATA = _os.path.join(ROOT, 'data'); SOURCE = _os.path.join(ROOT, 'source'); OUTDIR = _os.path.join(ROOT, 'out'); TOOLS = _os.path.join(ROOT, 'tools')
import cv2, numpy as np, sys, ast
name,path,x0,y0,x1,y1=sys.argv[1],sys.argv[2],*map(int,sys.argv[3:7])
sc=float(sys.argv[7]) if len(sys.argv)>7 else 1.0
img=cv2.imread(path); m=cv2.imread(f'{MASKS}/mask_{name}.png',0)
c=img[y0:y1,x0:x1].copy(); mm=m[y0:y1,x0:x1]
# tint outside-mask
out=c.copy(); out[mm==0]=(out[mm==0]*0.35+np.array([0,80,0])).astype(np.uint8)
cnts,_=cv2.findContours(mm,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
cv2.drawContours(out,cnts,-1,(0,255,255),1)
poly=ast.literal_eval(open(f'{MASKS}/poly_{name}.txt').read())
p=np.array([[x-x0,y-y0] for x,y in poly],np.int32); cv2.polylines(out,[p],True,(0,0,255),1)
out=cv2.resize(out,None,fx=sc,fy=sc,interpolation=cv2.INTER_NEAREST)
for gx in range((x0//50+1)*50,x1,50):
    X=int((gx-x0)*sc); cv2.line(out,(X,0),(X,out.shape[0]),(255,255,0),1); cv2.putText(out,str(gx),(X+2,12),cv2.FONT_HERSHEY_SIMPLEX,0.4,(255,255,0),1)
for gy in range((y0//50+1)*50,y1,50):
    Y=int((gy-y0)*sc); cv2.line(out,(0,Y),(out.shape[1],Y),(255,0,255),1); cv2.putText(out,str(gy),(2,Y-2),cv2.FONT_HERSHEY_SIMPLEX,0.4,(255,0,255),1)
cv2.imwrite(f'{MASKS}/chk_{name}.jpg',out)
