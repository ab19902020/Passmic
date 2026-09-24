import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
ASSETS = _os.path.join(ROOT, 'assets'); MASKS = _os.path.join(ROOT, 'masks'); DATA = _os.path.join(ROOT, 'data'); SOURCE = _os.path.join(ROOT, 'source'); OUTDIR = _os.path.join(ROOT, 'out'); TOOLS = _os.path.join(ROOT, 'tools')
import cv2, numpy as np, ast
def polymask(shape, poly):
    m=np.zeros(shape,np.uint8); cv2.fillPoly(m,[np.array(poly,np.int32)],255); return m
def cutout(img, poly, others, B=16, it=5):
    H,W=img.shape[:2]
    pm=polymask((H,W),poly)
    k=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*B+1,2*B+1))
    inner=cv2.erode(pm,k); outer=cv2.dilate(pm,k)
    mask=np.full((H,W),cv2.GC_BGD,np.uint8)
    mask[outer>0]=cv2.GC_PR_BGD
    mask[pm>0]=cv2.GC_PR_FGD
    mask[inner>0]=cv2.GC_FGD
    for o in others:
        om=cv2.erode(polymask((H,W),o),cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(9,9)))
        mask[(om>0)&(inner==0)]=cv2.GC_BGD
    ys,xs=np.where(outer>0); y0,y1,x0,x1=max(0,ys.min()-5),min(H,ys.max()+5),max(0,xs.min()-5),min(W,xs.max()+5)
    sub=mask[y0:y1,x0:x1].copy(); crop=img[y0:y1,x0:x1].copy()
    bgd=np.zeros((1,65),np.float64); fgd=np.zeros((1,65),np.float64)
    cv2.grabCut(crop,sub,None,bgd,fgd,it,cv2.GC_INIT_WITH_MASK)
    m=np.where((sub==cv2.GC_FGD)|(sub==cv2.GC_PR_FGD),255,0).astype(np.uint8)
    # largest component + fill holes
    n,lab,st,_=cv2.connectedComponentsWithStats(m,8)
    if n>1:
        big=1+np.argmax(st[1:,cv2.CC_STAT_AREA]); m=np.where(lab==big,255,0).astype(np.uint8)
    inv=255-m; n,lab,st,_=cv2.connectedComponentsWithStats(inv,4)
    for i in range(1,n):
        x,y,w,h,a=st[i]
        if a<250 and x>0 and y>0 and x+w<m.shape[1] and y+h<m.shape[0]: m[lab==i]=255
    m=cv2.morphologyEx(m,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3)))
    full=np.zeros((H,W),np.uint8); full[y0:y1,x0:x1]=m
    return full
