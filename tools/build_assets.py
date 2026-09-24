import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
ASSETS = _os.path.join(ROOT, 'assets'); MASKS = _os.path.join(ROOT, 'masks'); DATA = _os.path.join(ROOT, 'data'); SOURCE = _os.path.join(ROOT, 'source'); OUTDIR = _os.path.join(ROOT, 'out'); TOOLS = _os.path.join(ROOT, 'tools')
import cv2, numpy as np, json, sys
sys.path.insert(0,TOOLS); from heads import HEADS
C=MASKS; OUT=ASSETS
imgs={k:cv2.imread(f'{SOURCE}/{k}.png') for k in ('18306','18307','18346','18349')}
masks={n:cv2.imread(f'{C}/maskc_{n}.png',0) for n in HEADS}

# --- give Carra (pose A) his hidden right shoe, borrowed from pose B ---
i1=imgs['18306'].copy(); m1=masks['carra1'].copy()
i2=imgs['18307']; m2=masks['carra2']
sx0,sy0,sx1,sy1=600,895,752,972
shoe=i2[sy0:sy1,sx0:sx1]; smask=m2[sy0:sy1,sx0:sx1].copy()
# keep only the shoe (white/black low-saturation or white) below the jeans
hsv=cv2.cvtColor(shoe,cv2.COLOR_BGR2HSV)
jeans=(hsv[...,0]>100)&(hsv[...,0]<130)&(hsv[...,1]>80)&(hsv[...,2]<140)
smask[jeans]=0
sc=142/152
shoe=cv2.resize(shoe,None,fx=sc,fy=sc,interpolation=cv2.INTER_AREA); smask=cv2.resize(smask,None,fx=sc,fy=sc,interpolation=cv2.INTER_NEAREST)
px,py=878,1022
h,w=smask.shape
reg=m1[py:py+h,px:px+w]; put=(smask>0)&(reg==0)
i1[py:py+h,px:px+w][put]=shoe[put]; reg[put]=255
masks['carra1']=m1; imgs_carra1=i1

meta={}
for n,(iid,cx,cy,rx,ry,nx,ny) in HEADS.items():
    img=imgs_carra1 if n=='carra1' else imgs[iid]
    m=masks[n]
    ys,xs=np.where(m>0); x0,y0,x1,y1=xs.min()-6,ys.min()-6,xs.max()+7,ys.max()+7
    crop=img[y0:y1,x0:x1]; mm=m[y0:y1,x0:x1]
    H,W=mm.shape
    alpha=cv2.GaussianBlur(mm.astype(np.float32)/255,(0,0),0.9)
    # head mask
    hm=np.zeros((H,W),np.uint8)
    k={'carra2':1.04,'nev1':1.22,'nev2':1.32,'nev5':1.32,'nev4':1.32}.get(n,1.16)
    cv2.ellipse(hm,(cx-x0,cy-y0),(int(rx*k),int(ry*k)),0,0,360,255,-1)
    hm[(ny+4-y0):,:]=0
    EXCL={'nev1':('x>',1218),'nev2':('x<',1138),'nev5':('x>',1188),'nev4':('x>',1150)}
    if n in EXCL:
        op,v=EXCL[n]; xx=np.arange(W)[None,:]+x0
        hm[np.broadcast_to((xx>v) if op=='x>' else (xx<v),hm.shape)]=0
    hm=cv2.bitwise_and(hm,mm)
    # drop stray bits of the head mask not connected to the main blob
    nn,lab,st,_=cv2.connectedComponentsWithStats(hm,8)
    if nn>1: big=1+np.argmax(st[1:,cv2.CC_STAT_AREA]); hm=np.where(lab==big,255,0).astype(np.uint8)
    hsoft=cv2.GaussianBlur(hm.astype(np.float32)/255,(0,0),1.0)
    head=np.dstack([crop, (np.clip(alpha*hsoft,0,1)*255).astype(np.uint8)])
    # body: remove head, fill the lower head area with shirt colour so a tilted head never shows a hole
    # body: whole head removed; the neck/collar area under the head is filled with shirt colour
    hd=cv2.dilate(hm,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(9,9)))
    hd=cv2.bitwise_and(hd,cv2.dilate(mm,np.ones((3,3),np.uint8)))
    hdsoft=cv2.GaussianBlur(hd.astype(np.float32)/255,(0,0),1.0)
    body_a=alpha*(1-hdsoft)
    sb=crop[min(H-1,ny-y0+25):min(H,ny-y0+75), max(0,nx-x0-40):nx-x0+40].reshape(-1,3)
    shirt=np.median(sb,axis=0) if len(sb) else np.array([30,30,34])
    fill=cv2.bitwise_and(hd,cv2.erode(mm,np.ones((9,9),np.uint8)))
    fill[:int(cy-y0+ry*0.15),:]=0
    bcol=crop.copy(); bcol[fill>0]=shirt.astype(np.uint8)
    body_a=np.maximum(body_a,fill.astype(np.float32)/255)
    if n.startswith('nev'):
        zone=np.zeros((H,W),np.uint8); cv2.ellipse(zone,(cx-x0,cy-y0),(int(rx*1.6),int(ry*1.45)),0,0,360,255,-1)
        zone[int(cy-y0):,:]=0
        if n in EXCL:
            op,v=EXCL[n]; xx=np.arange(W)[None,:]+x0
            zone[np.broadcast_to((xx>v) if op=='x>' else (xx<v),zone.shape)]=0
        body_a[zone>0]=0
    body=np.dstack([bcol,(np.clip(body_a,0,1)*255).astype(np.uint8)])
    cv2.imwrite(f'{OUT}/{n}_body.png',body); cv2.imwrite(f'{OUT}/{n}_head.png',head)
    meta[n]=dict(src=iid,x0=int(x0),y0=int(y0),w=int(W),h=int(H),neck=[int(nx-x0),int(ny-y0)],foot=[int(nx-x0),int(ys.max()-y0)],ry=ry,headc=[int(cx-x0),int(cy-y0)])
json.dump(meta,open(f'{OUT}/meta.json','w'),indent=1)
print(json.dumps(meta))
