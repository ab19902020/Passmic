import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
ASSETS = _os.path.join(ROOT, 'assets'); MASKS = _os.path.join(ROOT, 'masks'); DATA = _os.path.join(ROOT, 'data'); SOURCE = _os.path.join(ROOT, 'source'); OUTDIR = _os.path.join(ROOT, 'out'); TOOLS = _os.path.join(ROOT, 'tools')
# (img, cx, cy, rx, ry, neck_x, neck_y)
HEADS={
 'carra1':('18306',805,418,110,142,800,552),
 'nev1':('18306',1072,405,128,153,1082,552),
 'keane1':('18306',1468,432,116,152,1470,578),
 'carra2':('18307',537,248,113,152,536,396),
 'keane2':('18307',874,300,118,157,876,452),
 'nev2':('18307',1256,302,113,155,1258,452),
 'carra5':('18346',620,452,72,95,622,545),
 'keane5':('18346',838,468,75,98,840,562),
 'nev5':('18346',1095,466,76,96,1098,558),
 'carra4':('18349',556,466,75,90,556,550),
 'keane4':('18349',790,500,72,93,792,588),
 'nev4':('18349',1064,492,72,96,1068,582)
}
