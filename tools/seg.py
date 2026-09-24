import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
ASSETS = _os.path.join(ROOT, 'assets'); MASKS = _os.path.join(ROOT, 'masks'); DATA = _os.path.join(ROOT, 'data'); SOURCE = _os.path.join(ROOT, 'source'); OUTDIR = _os.path.join(ROOT, 'out'); TOOLS = _os.path.join(ROOT, 'tools')
import cv2, numpy as np, sys, json
from PIL import Image
def grab(img, rect, fg_hints=(), bg_hints=(), it=6, prior=None):
    x0,y0,x1,y1 = rect
    pad=30
    H,W=img.shape[:2]
    cx0,cy0,cx1,cy1=max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad)
    crop=img[cy0:cy1,cx0:cx1].copy()
    mask=np.zeros(crop.shape[:2],np.uint8)
    mask[:]=cv2.GC_BGD
    mask[y0-cy0:y1-cy0, x0-cx0:x1-cx0]=cv2.GC_PR_FGD
    for (px,py,r) in bg_hints: cv2.circle(mask,(px-cx0,py-cy0),r,cv2.GC_BGD,-1)
    for (px,py,r) in fg_hints: cv2.circle(mask,(px-cx0,py-cy0),r,cv2.GC_FGD,-1)
    if prior is not None:
        pm=prior[cy0:cy1,cx0:cx1]; mask[pm>0]=cv2.GC_BGD
    bgd=np.zeros((1,65),np.float64); fgd=np.zeros((1,65),np.float64)
    cv2.grabCut(crop,mask,None,bgd,fgd,it,cv2.GC_INIT_WITH_MASK)
    m=np.where((mask==cv2.GC_FGD)|(mask==cv2.GC_PR_FGD),255,0).astype(np.uint8)
    full=np.zeros((H,W),np.uint8); full[cy0:cy1,cx0:cx1]=m
    return full
