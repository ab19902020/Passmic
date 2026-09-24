import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
ASSETS = _os.path.join(ROOT, 'assets'); MASKS = _os.path.join(ROOT, 'masks'); DATA = _os.path.join(ROOT, 'data'); SOURCE = _os.path.join(ROOT, 'source'); OUTDIR = _os.path.join(ROOT, 'out'); TOOLS = _os.path.join(ROOT, 'tools')
import cv2, numpy as np, json
OUT=ASSETS + ''
G={'mgr4':('18349',[(135,242,52,70),(292,264,50,62),(468,267,52,64),(699,264,52,64),(894,255,52,66),(1029,274,50,64),(1273,280,50,62),(1485,258,50,62)]),
   'mgr5':('18346',[(321,166,42,53),(443,182,42,53),(607,202,42,53),(762,210,42,53),(910,197,42,55),(1057,219,42,53)])}
gm={}
for n,(iid,heads) in G.items():
    img=cv2.imread(f'{SOURCE}/{iid}.png'); m=cv2.imread(f'{MASKS}/maskc_{n}.png',0)
    ys,xs=np.where(m>0); x0,y0=max(0,xs.min()-4),max(0,ys.min()-4); x1,y1=min(m.shape[1],xs.max()+5),min(m.shape[0],ys.max()+2)
    crop=img[y0:y1,x0:x1]; mm=m[y0:y1,x0:x1]; H,W=mm.shape
    alpha=cv2.GaussianBlur(mm.astype(np.float32)/255,(0,0),0.9)
    body_a=alpha.copy(); hl=[]
    for i,(cx,cy,rx,ry) in enumerate(heads):
        hm=np.zeros((H,W),np.uint8); cv2.ellipse(hm,(cx-x0,cy-y0),(int(rx*1.08),int(ry*1.08)),0,0,360,255,-1)
        neck=int(cy-y0+ry*0.95); hm[neck:,:]=0; hm=cv2.bitwise_and(hm,mm)
        hs=cv2.GaussianBlur(hm.astype(np.float32)/255,(0,0),1.0)
        ycut=int(cy-y0+ry*0.3)
        hd=cv2.GaussianBlur(cv2.dilate(hm,np.ones((9,9),np.uint8)).astype(np.float32)/255,(0,0),1.2)
        ramp=np.clip((ycut+14-np.arange(H,dtype=np.float32))/14,0,1)[:,None]
        body_a=body_a*(1-hd*ramp)
        hy_,hx_=np.where(hm>0); a0,a1,b0,b1=hy_.min(),hy_.max()+1,hx_.min(),hx_.max()+1
        head=np.dstack([crop,(np.clip(alpha*hs,0,1)*255).astype(np.uint8)])[a0:a1,b0:b1]
        cv2.imwrite(f'{OUT}/{n}_h{i}.png',head)
        hl.append(dict(x=int(b0),y=int(a0),neck=[int(cx-x0),int(cy-y0+ry*0.9)]))
    body=np.dstack([crop,(np.clip(body_a,0,1)*255).astype(np.uint8)]); cv2.imwrite(f'{OUT}/{n}_body.png',body)
    gm[n]=dict(src=iid,x0=int(x0),y0=int(y0),w=W,h=H,heads=hl)
json.dump(gm,open(f'{OUT}/groups.json','w'))
tiles=[]
for n in gm:
    b=cv2.imread(f'{OUT}/{n}_body.png',-1).astype(np.float32); can=np.full(b.shape[:2]+(3,),(50,30,60),np.float32)
    a=b[...,3:4]/255; can=can*(1-a)+b[...,:3]*a
    for i,h in enumerate(gm[n]['heads']):
        hs=cv2.imread(f'{OUT}/{n}_h{i}.png',-1).astype(np.float32); ang=8 if i%2 else -8
        M=cv2.getRotationMatrix2D((h['neck'][0]-h['x'],h['neck'][1]-h['y']),ang,1.0)
        hr=cv2.warpAffine(hs,M,(hs.shape[1],hs.shape[0]),borderValue=(0,0,0,0))
        a=hr[...,3:4]/255; reg=can[h['y']:h['y']+hs.shape[0],h['x']:h['x']+hs.shape[1]]
        can[h['y']:h['y']+hs.shape[0],h['x']:h['x']+hs.shape[1]]=reg*(1-a)+hr[...,:3]*a
    tiles.append(cv2.resize(can.astype(np.uint8),(1100,int(can.shape[0]*1100/can.shape[1]))))
meta=json.load(open(f'{OUT}/meta.json')); pt=[]
for n in ['carra4','keane4','nev4']:
    md=meta[n]; can=np.full((md['h'],md['w'],3),(50,30,60),np.float32)
    for part in ('body','head'):
        s=cv2.imread(f'{OUT}/{n}_{part}.png',-1).astype(np.float32); a=s[...,3:4]/255; can=can*(1-a)+s[...,:3]*a
    pt.append(cv2.resize(can.astype(np.uint8),(int(md['w']*300/md['h']),300)))
row=np.hstack(pt); row=np.hstack([row,np.full((300,max(0,1100-row.shape[1]),3),255,np.uint8)])[:, :1100]
cv2.imwrite(DATA + '/groups_prev.jpg',np.vstack(tiles+[row]))
