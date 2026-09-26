"""Cartman's bedroom, painted flat in the show's style.

    python3 tools/draw_room.py   -> episode/backgrounds/cartman_room.png (3840x2160)

Drawn at 2x and box-filtered down, so every edge is anti-aliased. World
coordinates below are in the 3840x2160 output space; the floor meets the wall
at y=1350 and characters stand around y=1850.
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'episode', 'backgrounds', 'cartman_room.png')
FONT = os.path.join(ROOT, 'fonts', 'Poppins-Bold.ttf')
W, H, SS = 3840, 2160, 2

WALL = (150, 178, 214)
WALL_DARK = (126, 154, 194)
TRIM = (236, 232, 222)
CARPET = (196, 160, 112)
CARPET_DARK = (176, 140, 94)
WOOD = (132, 84, 50)
WOOD_DARK = (98, 60, 34)
INK = (28, 24, 26)


class P:
    """ImageDraw wrapper that takes world coordinates."""
    def __init__(self, im):
        self.d = ImageDraw.Draw(im)

    def s(self, v):
        return [round(x * SS) for x in v]

    def rect(self, box, fill, outline=None, width=0, r=0):
        if r:
            self.d.rounded_rectangle(self.s(box), r * SS, fill=fill, outline=outline, width=width * SS)
        else:
            self.d.rectangle(self.s(box), fill=fill, outline=outline, width=width * SS)

    def ellipse(self, box, fill, outline=None, width=0):
        self.d.ellipse(self.s(box), fill=fill, outline=outline, width=width * SS)

    def poly(self, pts, fill, outline=None, width=0):
        self.d.polygon([(x * SS, y * SS) for x, y in pts], fill=fill)
        if outline:
            self.d.line([(x * SS, y * SS) for x, y in pts + pts[:1]], fill=outline, width=width * SS, joint='curve')

    def line(self, pts, fill, width):
        self.d.line([(x * SS, y * SS) for x, y in pts], fill=fill, width=round(width * SS), joint='curve')

    def text(self, xy, s, size, fill, anchor='mm'):
        f = ImageFont.truetype(FONT, size * SS)
        self.d.text((xy[0] * SS, xy[1] * SS), s, font=f, fill=fill, anchor=anchor)


def window(p):
    x0, y0, x1, y1 = 1480, 290, 2360, 920
    p.rect((x0 - 30, y0 - 30, x1 + 30, y1 + 30), TRIM)
    # daytime sky over snowy mountains and a pine-dotted town edge
    for i in range(12):
        t = i / 11
        c = tuple(round(a + (b - a) * t) for a, b in zip((120, 176, 236), (196, 226, 250)))
        p.rect((x0, y0 + (y1 - y0) * i / 12, x1, y0 + (y1 - y0) * (i + 1) / 12 + 1), c)
    p.poly([(x0, 760), (1640, 520), (1790, 700), (1960, 470), (2150, 690), (2260, 580), (x1, 660), (x1, y1), (x0, y1)], (122, 138, 170))
    p.poly([(1640, 520), (1700, 580), (1665, 575), (1640, 600), (1612, 568), (1585, 575)], (250, 250, 252))
    p.poly([(1960, 470), (2030, 545), (1990, 540), (1960, 565), (1930, 538), (1890, 545)], (250, 250, 252))
    p.poly([(2260, 580), (2310, 625), (2280, 622), (2258, 640), (2235, 620)], (250, 250, 252))
    p.poly([(x0, 820), (1800, 780), (2100, 800), (x1, 770), (x1, y1), (x0, y1)], (244, 246, 250))
    for tx, th in ((1530, 120), (1600, 90), (2190, 110), (2270, 140), (2320, 95)):
        p.poly([(tx, 860 - th), (tx + 36, 860), (tx - 36, 860)], (46, 92, 64))
        p.rect((tx - 6, 860, tx + 6, 880), (90, 60, 40))
    # glazing bars and sill
    p.rect(((x0 + x1) / 2 - 12, y0, (x0 + x1) / 2 + 12, y1), TRIM)
    p.rect((x0, (y0 + y1) / 2 - 12, x1, (y0 + y1) / 2 + 12), TRIM)
    p.rect((x0 - 70, y1 + 20, x1 + 70, y1 + 62), (226, 220, 206))
    # curtains with tie-backs
    for side in (-1, 1):
        cx = x0 - 20 if side < 0 else x1 + 20
        outer = cx + side * 200
        p.poly([(cx - side * 60, 240), (outer, 240), (outer + side * 10, 1000), (cx + side * 60, 1000), (cx + side * 115, 640)], (190, 40, 52))
        p.line([(cx + side * 70, 640), (cx + side * 150, 640)], (238, 200, 60), 18)
    p.rect((x0 - 280, 222, x1 + 280, 248), WOOD_DARK, r=10)


def bed(p):
    # headboard against the wall, bed running toward the camera
    p.rect((120, 760, 1120, 1260), WOOD, r=40)
    p.rect((160, 800, 1080, 1220), WOOD_DARK, r=30)
    for x in (320, 520, 720, 920):
        p.rect((x - 14, 820, x + 14, 1200), WOOD, r=8)
    # mattress side, blanket top and fold
    p.poly([(60, 1090), (1180, 1090), (1260, 1560), (0, 1560)], (104, 78, 160))
    p.poly([(60, 1040), (1180, 1040), (1190, 1110), (50, 1110)], (126, 100, 184))
    p.rect((0, 1530, 1270, 1600), WOOD_DARK, r=12)
    p.poly([(60, 1100), (1185, 1100), (1215, 1210), (40, 1210)], (238, 236, 246))
    p.ellipse((200, 930, 560, 1090), (250, 250, 250), INK, 4)
    p.ellipse((600, 930, 960, 1090), (250, 250, 250), INK, 4)
    # a plush bear and a plush frog propped on the pillows
    p.ellipse((250, 830, 470, 1060), (150, 102, 62))
    p.ellipse((240, 800, 310, 870), (150, 102, 62)); p.ellipse((410, 800, 480, 870), (150, 102, 62))
    p.ellipse((310, 930, 410, 1000), (214, 176, 130))
    p.ellipse((318, 880, 342, 904), INK); p.ellipse((378, 880, 402, 904), INK)
    p.ellipse((345, 936, 375, 956), INK)
    p.ellipse((680, 880, 900, 1060), (98, 176, 76))
    p.ellipse((690, 850, 770, 920), (98, 176, 76)); p.ellipse((810, 850, 890, 920), (98, 176, 76))
    p.ellipse((705, 862, 755, 910), (250, 250, 250)); p.ellipse((825, 862, 875, 910), (250, 250, 250))
    p.ellipse((722, 878, 740, 896), INK); p.ellipse((842, 878, 860, 896), INK)
    p.line([(730, 990), (790, 1010), (850, 990)], INK, 6)


def nightstand(p):
    p.rect((1180, 1020, 1400, 1400), WOOD, r=10)
    p.rect((1200, 1080, 1380, 1210), WOOD_DARK, r=8)
    p.ellipse((1275, 1130, 1305, 1160), (220, 190, 80))
    p.rect((1270, 900, 1310, 1030), (220, 190, 80))
    p.poly([(1200, 910), (1380, 910), (1340, 760), (1240, 760)], (250, 226, 150))


def tv_corner(p):
    # stand, television and a games console
    p.rect((2700, 1120, 3480, 1470), WOOD, r=16)
    p.rect((2740, 1170, 3080, 1430), WOOD_DARK, r=10)
    p.rect((3100, 1170, 3440, 1430), WOOD_DARK, r=10)
    p.rect((2780, 640, 3400, 1100), (34, 34, 40), r=26)
    p.rect((2820, 680, 3360, 1060), (58, 70, 86), r=14)
    p.poly([(2860, 700), (2990, 700), (2880, 1030), (2840, 1030)], (74, 88, 106))
    p.rect((3050, 1100, 3130, 1125), (34, 34, 40))
    p.rect((2800, 1260, 3010, 1330), (230, 230, 234), r=12)
    p.rect((2820, 1285, 2900, 1300), (70, 180, 90), r=6)
    for cx in (3180, 3340):
        p.ellipse((cx - 60, 1300, cx + 60, 1370), (44, 44, 50))
        p.ellipse((cx - 36, 1318, cx - 14, 1340), (200, 50, 50)); p.ellipse((cx + 14, 1318, cx + 36, 1340), (60, 120, 210))
    p.line([(3010, 1300), (3080, 1360), (3150, 1330)], (44, 44, 50), 8)


def wall_decor(p):
    # wallpaper border under the ceiling
    p.rect((0, 0, W, 40), (120, 146, 186))
    p.rect((0, 120, W, 190), WALL_DARK)
    for x in range(0, W, 120):
        p.ellipse((x + 40, 138, x + 80, 172), (170, 196, 228))
    # football poster
    p.rect((2710, 250, 3190, 600), (250, 248, 240), INK, 6, r=6)
    p.rect((2740, 280, 3160, 470), (200, 36, 48))
    p.ellipse((2870, 300, 3030, 460), (250, 250, 250), INK, 6)
    p.poly([(2950, 350), (2985, 375), (2972, 415), (2928, 415), (2915, 375)], INK)
    p.text((2950, 525), 'SOUTH MANCHESTER', 42, INK)
    p.text((2950, 575), 'CHAMPIONS', 32, (200, 36, 48))
    # pennant
    p.poly([(3260, 280), (3480, 330), (3260, 380)], (238, 200, 60), INK, 5)
    p.text((3330, 331), 'No.1', 30, INK)
    # shelf over the bed with a trophy and a toy robot
    p.rect((380, 520, 960, 548), WOOD_DARK, r=6)
    p.poly([(520, 520), (600, 520), (590, 480), (530, 480)], (216, 176, 60))
    p.rect((545, 420, 575, 482), (216, 176, 60))
    p.poly([(505, 340), (615, 340), (595, 420), (525, 420)], (236, 196, 70))
    p.line([(505, 350), (470, 360), (480, 395), (515, 395)], (236, 196, 70), 12)
    p.line([(615, 350), (650, 360), (640, 395), (605, 395)], (236, 196, 70), 12)
    p.rect((740, 390, 860, 520), (160, 170, 186), r=12)
    p.rect((760, 330, 840, 392), (160, 170, 186), r=10)
    p.ellipse((770, 348, 795, 373), (240, 70, 70)); p.ellipse((805, 348, 830, 373), (240, 70, 70))
    p.line([(800, 330), (800, 296)], INK, 6); p.ellipse((790, 284, 810, 304), (240, 70, 70))
    # door on the far right
    p.rect((3560, 330, 3840, 1360), TRIM)
    p.rect((3600, 370, 3840, 1360), (170, 116, 72))
    p.rect((3640, 420, 3840, 820), (150, 100, 60), r=10)
    p.rect((3640, 880, 3840, 1300), (150, 100, 60), r=10)
    p.ellipse((3620, 850, 3660, 890), (230, 200, 90))


def floor(p):
    p.rect((0, 1350, W, H), CARPET)
    p.rect((0, 1318, W, 1356), TRIM)
    p.line([(0, 1356), (W, 1356)], (160, 150, 136), 4)
    # a round rug where Cartman stands, and a few toys on the floor
    p.ellipse((1080, 1640, 2840, 2080), (170, 50, 60))
    p.ellipse((1180, 1680, 2740, 2040), (196, 72, 76))
    p.ellipse((1290, 1720, 2630, 2000), (170, 50, 60))
    p.rect((3200, 1700, 3420, 1790), (60, 120, 210), r=14)
    p.ellipse((3220, 1770, 3270, 1820), INK); p.ellipse((3350, 1770, 3400, 1820), INK)
    p.poly([(250, 1900), (420, 1860), (460, 1920), (290, 1960)], (240, 200, 60))
    p.ellipse((600, 1760, 700, 1850), (230, 90, 60))
    for x, y in ((600, 1500), (1500, 1520), (2500, 1500), (3300, 1560), (900, 2050), (3000, 2060)):
        p.ellipse((x, y, x + 40, y + 12), CARPET_DARK)


def main():
    im = Image.new('RGB', (W * SS, H * SS), WALL)
    p = P(im)
    wall_decor(p)
    floor(p)
    window(p)
    bed(p)
    nightstand(p)
    tv_corner(p)
    # soft contact shadows where furniture meets the carpet
    sh = Image.new('L', im.size, 0)
    ds = ImageDraw.Draw(sh)
    for x0, x1, y in ((0, 1280, 1600), (1170, 1410, 1405), (2690, 3490, 1478)):
        ds.ellipse(((x0 - 20) * SS, (y - 20) * SS, (x1 + 20) * SS, (y + 26) * SS), 90)
    sh = sh.filter(ImageFilter.GaussianBlur(12 * SS))
    im = Image.composite(Image.new('RGB', im.size, (60, 40, 30)), im, sh)
    # redraw the furniture over its own shadow
    p = P(im)
    bed(p); nightstand(p); tv_corner(p)
    im = im.resize((W, H), Image.BOX)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    im.save(OUT, optimize=True)
    print(OUT)


if __name__ == '__main__':
    main()
