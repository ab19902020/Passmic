import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
ASSETS = _os.path.join(ROOT, 'assets'); MASKS = _os.path.join(ROOT, 'masks'); DATA = _os.path.join(ROOT, 'data'); SOURCE = _os.path.join(ROOT, 'source'); OUTDIR = _os.path.join(ROOT, 'out'); TOOLS = _os.path.join(ROOT, 'tools')
import cv2, numpy as np, json, sys
def show(path, poly, x0,y0,x1,y1, out, scale=1.0):
    img=cv2.imread(path)[y0:y1,x0:x1].copy()
    p=np.array([[x-x0,y-y0] for x,y in poly],np.int32)
    cv2.polylines(img,[p],True,(0,255,0),2)
    for i,(x,y) in enumerate(p): cv2.circle(img,(int(x),int(y)),3,(0,0,255),-1)
    if scale!=1: img=cv2.resize(img,None,fx=scale,fy=scale)
    cv2.imwrite(out,img)
