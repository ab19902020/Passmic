import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
ASSETS = _os.path.join(ROOT, 'assets'); MASKS = _os.path.join(ROOT, 'masks'); DATA = _os.path.join(ROOT, 'data'); SOURCE = _os.path.join(ROOT, 'source'); OUTDIR = _os.path.join(ROOT, 'out'); TOOLS = _os.path.join(ROOT, 'tools'); FONTS = _os.path.join(ROOT, 'fonts')
import cv2, numpy as np, json, sys
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0,TOOLS); from mgr import colour_matte
A=ASSETS + ''
g=json.load(open(f'{A}/groups_orig.json')); m5=g['mgr5']; x0,y0=m5['x0'],m5['y0']
body=cv2.imread(f'{A}/mgr5_body_orig.png',-1)
H,W=body.shape[:2]
img5=cv2.imread(SOURCE + '/18346.png')
# 1) Carrick placard: 2024 -> 2026
card=img5[88:146,990:1096].reshape(-1,3); bright=card[card.mean(1)>200]; ccol=np.median(bright,axis=0)
cx0,cy0,cx1,cy1=1003-x0,116-y0,1078-x0,142-y0
body[cy0:cy1,cx0:cx1,:3]=ccol
F=FONTS + '/Poppins-Bold.ttf'
def text_img(txt,h_px,sq=0.8,col=(20,20,24)):
    f=ImageFont.truetype(F,int(h_px*1.45)); bb=f.getbbox(txt)
    im=Image.new('RGBA',(bb[2]-bb[0]+6,bb[3]-bb[1]+6),(0,0,0,0)); ImageDraw.Draw(im).text((3-bb[0],3-bb[1]),txt,font=f,fill=col+(255,))
    a=np.array(im); a=cv2.resize(a,(int(a.shape[1]*sq),a.shape[0]),interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(a,cv2.COLOR_RGBA2BGRA)
def paste(dst,src,x,y):
    h,w=src.shape[:2]; X0,Y0=max(0,x),max(0,y); X1,Y1=min(dst.shape[1],x+w),min(dst.shape[0],y+h)
    s=src[Y0-y:Y1-y,X0-x:X1-x].astype(np.float32); a=s[...,3:4]/255
    d=dst[Y0:Y1,X0:X1].astype(np.float32)
    out=d.copy(); out[...,:3]=d[...,:3]*(1-a)+s[...,:3]*a; out[...,3:4]=np.maximum(d[...,3:4],s[...,3:4])
    dst[Y0:Y1,X0:X1]=out.astype(np.uint8)
t26=text_img('2026',21); paste(body,t26,(cx0+cx1)//2-t26.shape[1]//2,(cy0+cy1)//2-t26.shape[0]//2+1)
# 2) Amorim from the dancing-managers image
img4=cv2.imread(SOURCE + '/18349.png')
poly=[(1246,250),(1252,222),(1262,205),(1285,195),(1315,195),(1340,204),(1357,228),(1359,270),(1351,318),(1372,334),(1381,350),(1386,372),(1385,390),(1362,398),(1360,430),(1362,466),(1240,466),(1238,440),(1242,400),(1242,380),(1252,340),(1256,322),(1248,290)]
am=np.zeros(img4.shape[:2],np.uint8); cv2.fillPoly(am,[np.array(poly,np.int32)],255)
hsv4=cv2.cvtColor(img4,cv2.COLOR_BGR2HSV); Hh=hsv4[...,0].astype(int); S_=hsv4[...,1]/255.; V_=hsv4[...,2]/255.
face=np.zeros_like(am); cv2.ellipse(face,(1300,268),(52,72),0,0,360,255,-1)
bgc=((Hh>=118)&(Hh<=172)&(S_>0.28)&(V_>0.2)&(V_<0.93)) | ((Hh<=26)&(S_>0.6)&(V_>0.5)&(face==0))
am[bgc]=0
am=cv2.morphologyEx(am,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(5,5)))
nn,lab,st,_=cv2.connectedComponentsWithStats(am,8); big=1+np.argmax(st[1:,cv2.CC_STAT_AREA]); am=np.where(lab==big,255,0).astype(np.uint8)
inv=255-am; nn,lab,st,_=cv2.connectedComponentsWithStats(inv,4)
for i in range(1,nn):
    x_,y_,w_,h_,a_=st[i]
    if a_<400 and x_>0 and y_>0: am[lab==i]=255
ys,xs=np.where(am>0); a0,a1,b0,b1=ys.min(),min(ys.max(),465),xs.min(),xs.max()+1
am_rgba=np.dstack([img4[a0:a1,b0:b1],(cv2.GaussianBlur(am[a0:a1,b0:b1].astype(np.float32)/255,(0,0),0.9)*255).astype(np.uint8)])
sc=53/62
am_rgba=cv2.resize(am_rgba,None,fx=sc,fy=sc,interpolation=cv2.INTER_AREA)
ha,wa=am_rgba.shape[:2]
# 3) new conga canvas: everyone up to Ten Hag, then Amorim, then Carrick
xs_split=975-x0; ins=wa+4
canvas=np.zeros((H+80,W+ins,4),np.uint8); off=80
canvas[off:,:xs_split]=body[:,:xs_split]
ax=xs_split-4; ay=off+H-ha
# placard + stick behind Amorim
cw,chh=112,60
cardimg=np.zeros((chh,cw,4),np.uint8); cardimg[...,:3]=ccol; cardimg[...,3]=255
cv2.rectangle(cardimg,(0,0),(cw-1,chh-1),(90,90,95,255),2)
t1=text_img('AMORIM',19); t2=text_img('2024-2026',17)
paste(cardimg,t1,cw//2-t1.shape[1]//2,6); paste(cardimg,t2,cw//2-t2.shape[1]//2,32)
headtop=ay+2; pcx=ax+wa//2-6; pby=headtop-18
cv2.line(canvas,(pcx,pby),(pcx+2,headtop+6),(60,70,80,255),4)
paste(canvas,cardimg,pcx-cw//2,pby-chh)
paste(canvas,am_rgba,ax,ay)
right=body[:,xs_split:]
paste(canvas,np.ascontiguousarray(right),xs_split+ins,off)
ys,xs=np.where(canvas[...,3]>0); top=ys.min()
canvas=canvas[top:]
cv2.imwrite(f'{A}/mgr5_body.png',canvas)
g['mgr5'].update(w=int(canvas.shape[1]),h=int(canvas.shape[0]),heads=[])
json.dump(g,open(f'{A}/groups.json','w'))
prev=np.full(canvas.shape[:2]+(3,),(50,30,60),np.float32); a=canvas[...,3:4]/255; prev=prev*(1-a)+canvas[...,:3]*a
cv2.imwrite(DATA + '/conga_fixed.jpg',cv2.resize(prev.astype(np.uint8),None,fx=1.0,fy=1.0))
print(canvas.shape)
