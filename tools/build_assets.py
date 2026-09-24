import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
ASSETS = _os.path.join(ROOT, 'assets'); MASKS = _os.path.join(ROOT, 'masks'); DATA = _os.path.join(ROOT, 'data'); SOURCE = _os.path.join(ROOT, 'source'); OUTDIR = _os.path.join(ROOT, 'out'); TOOLS = _os.path.join(ROOT, 'tools')
import cv2, numpy as np, json, sys
sys.path.insert(0,TOOLS); from heads import HEADS
CLEAN=json.load(open(f'{MASKS}/clean.json'))  # hand-cleanup polygons in sprite-local px
RIG=json.load(open(f'{MASKS}/rig.json'))      # arm polygons also protect hands from being captured by the head split
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
    crop=img[y0:y1,x0:x1].copy(); mm=m[y0:y1,x0:x1]
    for poly in CLEAN.get(n, {}).get('retouch', []):  # paint over art details that read wrong in motion
        rm=np.zeros(crop.shape[:2],np.uint8); cv2.fillPoly(rm,[np.array(poly,np.int32)],255)
        crop=cv2.inpaint(crop,rm,5,cv2.INPAINT_TELEA)
    H,W=mm.shape
    # head mask
    hm=np.zeros((H,W),np.uint8)
    k={'carra2':1.04,'nev1':1.22,'nev2':1.32,'nev5':1.32,'nev4':1.32}.get(n,1.16)
    cv2.ellipse(hm,(cx-x0,cy-y0),(int(rx*k),int(ry*k)),0,0,360,255,-1)
    # Carra's old split ended too high: the bottom of his beard/chin stayed on the body layer and
    # appeared to be sliced off whenever his head rotated. Give all four Carra drawings a deeper
    # head tail; the later neck/collar fill still hides the seam underneath.
    head_tail=int(0.16*ry) if n.startswith('carra') else 4
    hm[(ny+head_tail-y0):,:]=0
    EXCL={'nev1':('x>',1218),'nev2':('x<',1138),'nev5':('x>',1188),'nev4':('x>',1150)}
    if n in EXCL:
        op,v=EXCL[n]; xx=np.arange(W)[None,:]+x0
        hm[np.broadcast_to((xx>v) if op=='x>' else (xx<v),hm.shape)]=0
    hm=cv2.bitwise_and(hm,mm)
    # Gary's raised/pointing hands can enter the broad face ellipse in some drawings. They must
    # remain on the body/arm layer, otherwise they move with his head. Subtract the traced arm
    # polygons before selecting the connected head blob.
    if n.startswith('nev') and n in RIG:
        for arm in RIG[n]:
            am=np.zeros((H,W),np.uint8)
            cv2.fillPoly(am,[np.array(arm['poly'],np.int32)],255)
            hm[am>0]=0
    # drop stray bits of the head mask not connected to the main blob
    nn,lab,st,_=cv2.connectedComponentsWithStats(hm,8)
    if nn>1: big=1+np.argmax(st[1:,cv2.CC_STAT_AREA]); hm=np.where(lab==big,255,0).astype(np.uint8)
    # background scraps stuck to the cut-out (chairs, bar clutter, studio blue): erase by hand-traced polygons
    mm=mm.copy()
    for poly in CLEAN.get(n, {}).get('head', []):
        cv2.fillPoly(mm, [np.array(poly, np.int32)], 0); cv2.fillPoly(hm, [np.array(poly, np.int32)], 0)
    alpha=cv2.GaussianBlur(mm.astype(np.float32)/255,(0,0),0.9)
    for poly in CLEAN.get(n, {}).get('body', []): cv2.fillPoly(mm, [np.array(poly, np.int32)], 0)
    alpha_b=cv2.GaussianBlur(mm.astype(np.float32)/255,(0,0),0.9)
    hsoft=cv2.GaussianBlur(hm.astype(np.float32)/255,(0,0),1.0)
    # the head reaches ~5px into the body so the head/body seam never shows a gap (and no dark ring)
    hext=cv2.bitwise_and(cv2.dilate(hm,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(11,11))),cv2.erode(mm,np.ones((3,3),np.uint8)))
    hext[:int(cy-y0),:]=hm[:int(cy-y0),:]
    hsoft=np.maximum(hsoft,cv2.GaussianBlur(hext.astype(np.float32)/255,(0,0),1.2))
    head=np.dstack([crop, (np.clip(alpha*hsoft,0,1)*255).astype(np.uint8)])
    # body: whole head removed; under it a short skin-toned neck (plus collar in shirt colour) so a
    # tilted head shows a neck, not a dark block beside the face
    hd=cv2.dilate(hm,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(13,13)))
    hd=cv2.bitwise_and(hd,cv2.dilate(mm,np.ones((5,5),np.uint8)))
    hdsoft=cv2.GaussianBlur(hd.astype(np.float32)/255,(0,0),1.0)
    body_a=alpha_b*np.clip(1-2*hdsoft,0,1)
    # thin slivers of hair/outline left around the head would ghost when the head moves: open them away
    rest=cv2.bitwise_and(mm,cv2.bitwise_not(hd))
    op=cv2.morphologyEx(rest,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(9,9)))
    op=cv2.dilate(op,np.ones((3,3),np.uint8))
    op[int(ny-y0):,:]=255
    body_a*=cv2.GaussianBlur(op.astype(np.float32)/255,(0,0),0.8)
    sb=crop[min(H-1,ny-y0+25):min(H,ny-y0+75), max(0,nx-x0-40):nx-x0+40].reshape(-1,3)
    shirt=np.median(sb,axis=0) if len(sb) else np.array([30,30,34])
    hsv=cv2.cvtColor(crop,cv2.COLOR_BGR2HSV)
    sk=(hm>0)&(hsv[...,0]>=5)&(hsv[...,0]<=22)&(hsv[...,1]>70)&(hsv[...,2]>170)
    skin=np.median(crop[sk],axis=0) if sk.sum()>50 else np.array([130,170,235])
    fill=cv2.bitwise_and(cv2.dilate(hd,np.ones((7,7),np.uint8)),cv2.erode(mm,np.ones((9,9),np.uint8)))
    neck=np.zeros((H,W),np.uint8); cv2.ellipse(neck,(nx-x0,int(ny-y0-0.22*ry)),(int(0.36*rx),int(0.42*ry)),0,0,360,255,-1)
    collar=np.zeros((H,W),np.uint8); collar[int(ny-y0-0.1*ry):,:]=255
    fill=cv2.bitwise_and(fill,cv2.bitwise_or(neck,collar))
    bcol=crop.copy()
    ys_=np.arange(H,dtype=np.float32)[:,None,None]; shade=np.clip(1-(ys_-(ny-y0-0.45*ry))/(0.5*ry)*0.25,0.72,1.0)
    neckcol=np.broadcast_to(skin[None,None,:]*shade,(H,W,3))
    bcol[fill>0]=np.where((collar[fill>0]>0)[:,None],shirt[None,:],neckcol[fill>0]).astype(np.uint8)
    body_a=np.maximum(body_a,cv2.GaussianBlur(fill.astype(np.float32)/255,(0,0),0.8))
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
