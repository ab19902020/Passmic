import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
ASSETS = _os.path.join(ROOT, 'assets'); MASKS = _os.path.join(ROOT, 'masks'); DATA = _os.path.join(ROOT, 'data'); SOURCE = _os.path.join(ROOT, 'source'); OUTDIR = _os.path.join(ROOT, 'out'); TOOLS = _os.path.join(ROOT, 'tools')
import cv2, sys
def grid(path, x0,y0,x1,y1, out, step=50, scale=1.0):
    img=cv2.imread(path)[y0:y1,x0:x1].copy()
    for gx in range((x0//step+1)*step, x1, step):
        c=(0,255,255) if gx%100==0 else (0,160,160)
        cv2.line(img,(gx-x0,0),(gx-x0,y1-y0),c,1)
        if gx%100==0: cv2.putText(img,str(gx),(gx-x0+2,14),cv2.FONT_HERSHEY_SIMPLEX,0.45,(0,255,255),1)
    for gy in range((y0//step+1)*step, y1, step):
        c=(255,0,255) if gy%100==0 else (160,0,160)
        cv2.line(img,(0,gy-y0),(x1-x0,gy-y0),c,1)
        if gy%100==0: cv2.putText(img,str(gy),(2,gy-y0-3),cv2.FONT_HERSHEY_SIMPLEX,0.45,(255,0,255),1)
    if scale!=1: img=cv2.resize(img,None,fx=scale,fy=scale)
    cv2.imwrite(out,img)
if __name__=='__main__':
    a=sys.argv; grid(a[1],*map(int,a[2:6]),a[6],scale=float(a[7]) if len(a)>7 else 1.0)
