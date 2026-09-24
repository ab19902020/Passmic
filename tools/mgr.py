import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
ASSETS = _os.path.join(ROOT, 'assets'); MASKS = _os.path.join(ROOT, 'masks'); DATA = _os.path.join(ROOT, 'data'); SOURCE = _os.path.join(ROOT, 'source'); OUTDIR = _os.path.join(ROOT, 'out'); TOOLS = _os.path.join(ROOT, 'tools')
import cv2, numpy as np, sys
sys.path.insert(0,TOOLS); from trimap import cutout
def conv(px, s, ox, oy): return [(int(ox+x/s), int(oy+y/s)) for x,y in px]
M2px=[(0,190),(0,110),(8,95),(12,70),(22,35),(35,28),(45,60),(50,90),(58,72),(80,45),(125,40),(148,70),(150,110),(160,95),(185,95),(200,78),(245,75),(270,95),(275,130),(280,110),(290,95),(300,92),(315,100),(322,125),(328,80),(345,70),(385,68),(405,90),(410,130),(440,125),(450,100),(458,72),(470,68),(482,85),(478,110),(490,125),(505,85),(520,68),(570,65),(588,85),(595,125),(598,110),(583,60),(588,20),(600,12),(612,25),(615,60),(625,90),(640,110),(655,75),(670,58),(720,55),(738,80),(740,110),(760,110),(765,85),(775,75),(820,72),(842,95),(845,130),(880,125),(905,105),(935,108),(935,135),(925,145),(950,140),(955,95),(970,82),(1015,80),(1035,100),(1040,140),(1060,120),(1068,60),(1080,45),(1093,55),(1095,95),(1115,90),(1130,68),(1180,66),(1195,95),(1200,110),(1210,95),(1228,95),(1238,120),(1250,160),(1255,190)]
M1px=[(15,292),(15,265),(60,250),(95,215),(105,160),(115,110),(125,80),(140,68),(145,15),(248,15),(248,65),(252,110),(262,95),(280,85),(280,30),(385,30),(385,85),(362,92),(368,125),(412,112),(415,100),(415,52),(520,48),(522,100),(502,106),(508,142),(535,122),(535,72),(635,72),(636,120),(616,126),(642,152),(680,122),(682,65),(765,65),(765,110),(774,160),(808,122),(808,40),(912,45),(910,100),(916,150),(930,200),(945,230),(945,292)]
def colour_matte(img, poly, inner_erode=0):
    H,W=img.shape[:2]
    pm=np.zeros((H,W),np.uint8); cv2.fillPoly(pm,[np.array(poly,np.int32)],255)
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV); Hh=hsv[...,0].astype(int); S=hsv[...,1]/255.; V=hsv[...,2]/255.
    bg=(Hh>=100)&(Hh<=172)&(S>0.30)&(V>0.20)&(V<0.93)
    boa=(Hh>=150)&(S>0.45)&(V>0.70)
    lei=(Hh<=20)&(S>0.6)&(V>0.6)
    skin=(Hh>=5)&(Hh<=24)&(S>0.2)&(V>0.5)
    white=(S<0.18)&(V>0.75)
    dark=(V<0.20)
    mask=np.full((H,W),cv2.GC_BGD,np.uint8)
    mask[pm>0]=cv2.GC_PR_FGD
    mask[(pm>0)&bg&~boa]=cv2.GC_PR_BGD
    sure=((skin|white|boa|lei)&(pm>0)).astype(np.uint8)*255
    sure=cv2.erode(sure,np.ones((3,3),np.uint8)); mask[sure>0]=cv2.GC_FGD
    x,y,w,h=cv2.boundingRect(np.array(poly,np.int32))
    sub=mask[y:y+h,x:x+w].copy()
    b_=np.zeros((1,65)); f_=np.zeros((1,65))
    cv2.grabCut(img[y:y+h,x:x+w],sub,None,b_,f_,6,cv2.GC_INIT_WITH_MASK)
    m=np.zeros((H,W),np.uint8); m[y:y+h,x:x+w]=np.where((sub==1)|(sub==3),255,0)
    m[bg&~boa&~dark]=0; m[pm==0]=0
    m=cv2.morphologyEx(m,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(5,5)))
    m=cv2.morphologyEx(m,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(7,7)))
    nn,lab,st,_=cv2.connectedComponentsWithStats(m,8); keep=np.zeros_like(m)
    for i in range(1,nn):
        if st[i,cv2.CC_STAT_AREA]>2500: keep[lab==i]=255
    inv=255-keep; nn,lab,st,_=cv2.connectedComponentsWithStats(inv,4)
    for i in range(1,nn):
        xx,yy_,ww,hh,a=st[i]
        if a<300 and xx>0 and yy_>0: keep[lab==i]=255
    return keep
im4=cv2.imread(SOURCE + '/18349.png'); im5=cv2.imread(SOURCE + '/18346.png')
m2=colour_matte(im4, conv(M2px,0.78,0,120)); cv2.imwrite('mask_mgr4.png',m2)
m1=colour_matte(im5, conv(M1px,0.9,90,30)); cv2.imwrite('mask_mgr5.png',m1)
# pundits pose D from 18349
PD={'carra4':[(278,255),(300,262),(330,290),(372,300),(372,250),(385,215),(420,200),(470,205),(490,240),(492,300),(480,330),(500,315),(500,370),(515,395),(500,420),(512,470),(505,520),(515,590),(520,622),(435,625),(430,595),(445,560),(420,500),(390,540),(370,575),(378,610),(290,612),(285,585),(300,540),(300,480),(335,430),(345,380),(340,340),(310,305),(282,290)],
'keane4':[(560,250),(585,228),(640,225),(668,250),(672,300),(668,345),(700,330),(698,290),(720,282),(745,300),(742,335),(725,360),(735,420),(735,470),(752,530),(760,600),(765,625),(640,625),(640,590),(655,560),(635,500),(610,480),(585,500),(570,560),(605,590),(600,625),(515,625),(515,595),(520,540),(525,470),(528,420),(545,420),(540,380),(555,360),(560,330),(555,290)],
'nev4':[(780,245),(800,220),(860,215),(882,245),(885,300),(880,340),(900,320),(935,285),(945,250),(968,238),(975,265),(960,300),(930,340),(925,400),(930,480),(975,540),(985,585),(990,622),(895,625),(893,595),(905,570),(880,520),(850,500),(830,540),(855,585),(858,625),(775,625),(772,595),(790,540),(785,490),(760,470),(745,440),(742,400),(762,378),(770,380),(778,345),(775,300)]}
polys={n:conv(p,0.78,0,120) for n,p in PD.items()}
for n,p in polys.items(): open(f'poly_{n}.txt','w').write(repr(p))
hsv=cv2.cvtColor(im4,cv2.COLOR_BGR2HSV); S=hsv[...,1]/255.; V=hsv[...,2]/255.; yy=np.arange(im4.shape[0])[:,None]
for n,p in polys.items():
    m=cutout(im4,p,[q for k,q in polys.items() if k!=n],B=9)
    ytop={'carra4':720,'keane4':725,'nev4':745}[n]; yshoe={'carra4':850,'keane4':860,'nev4':860}[n]
    inner=np.zeros_like(m); cv2.fillPoly(inner,[np.array(p,np.int32)],255); inner=cv2.erode(inner,np.ones((21,21),np.uint8))
    bad=(yy>ytop)&(((S>0.42)&(V>0.40))|((V>0.55)&(yy<yshoe)))
    m[bad&(inner==0)]=0; m[bad&(yy>ytop+25)]=0
    m=cv2.morphologyEx(m,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(5,5)))
    nn,lab,st,_=cv2.connectedComponentsWithStats(m,8); big=1+np.argmax(st[1:,cv2.CC_STAT_AREA]); m=np.where(lab==big,255,0).astype(np.uint8)
    cv2.imwrite(f'maskc_{n}.png',m)
# contact sheets
def sheet(items,out,hgt):
    tiles=[]
    for img,m in items:
        ys,xs=np.where(m>0); y0,y1,x0,x1=ys.min(),ys.max(),xs.min(),xs.max()
        o=np.where(m[y0:y1,x0:x1,None]>0,img[y0:y1,x0:x1],np.array([60,220,60],np.uint8))
        tiles.append(cv2.resize(o,(int((x1-x0)*hgt/(y1-y0)),hgt)))
    W=sum(t.shape[1] for t in tiles); c=np.full((hgt,W,3),255,np.uint8); x=0
    for t in tiles: c[:,x:x+t.shape[1]]=t; x+=t.shape[1]
    return c
a=sheet([(im4,m2)],None,260); b=sheet([(im5,m1)],None,260)
p=sheet([(im4,cv2.imread(f'maskc_{n}.png',0)) for n in ['carra4','keane4','nev4']],None,380)
W=max(a.shape[1],b.shape[1],p.shape[1]); 
def padw(x): return np.hstack([x,np.full((x.shape[0],W-x.shape[1],3),255,np.uint8)])
cv2.imwrite('newcuts.jpg',np.vstack([padw(a),padw(b),padw(p)]))
