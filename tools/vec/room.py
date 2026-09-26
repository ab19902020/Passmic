"""Cartman's bedroom as vector art (world = 3840x2160 at the wide shot).

draw_back(pen, t, st)  : everything behind Cartman (walls, door, window, bed,
                         desk, monitor with its live screen, chair back...)
draw_front(pen, t, st) : anything in front of him (nothing in the wide
                         layout yet, kept for foreground props)
st: dict with door (0 closed .. 1 open), screen (content name), screen_p
    (content parameters), chair_x.

Layout: back wall y<1300, floor below. Door on the left wall section
(x 170-600), bed, window, poster, computer desk on the right with the
monitor angled towards the chair, swivel chair at CHAIR_X.
"""
import math
import skia
from draw import Pen, rgb, ellipse, rrect, polyline, smooth, capsule, union, intersect, darker, mix
import screens

W, H = 3840, 2160
FLOOR_Y = 1300
WALL = (150, 178, 214)
WALL_DARK = (128, 156, 196)
TRIM = (238, 234, 224)
CARPET = (198, 160, 112)
CARPET_DARK = (180, 142, 96)
WOOD = (134, 86, 50)
WOOD_DARK = (100, 62, 36)
WOOD_LIGHT = (160, 108, 66)
INK = (30, 26, 28)
GREY = (70, 74, 84)

DOOR = (170, 330, 600, FLOOR_Y)            # frame outer box
# the computer corner (desk, monitor, chair) is drawn in its own coordinates
# and scaled up about CORNER_PIVOT so it fits a kid of Cartman's width
CORNER_PIVOT, CORNER_SCALE = (3700, 1780), 1.35
_CHAIR_X, _SEAT_Y = 2560, 1560             # seat top centre (corner coordinates)


def corner_to_world(x, y):
    px, py = CORNER_PIVOT
    return px + (x - px) * CORNER_SCALE, py + (y - py) * CORNER_SCALE


CHAIR_X, SEAT_Y = corner_to_world(_CHAIR_X, _SEAT_Y)
DESK = (2780, 1390, 3720, 1780)            # desktop left, top, right, feet
# screen quad TL, TR, BR, BL. The screen is turned towards the chair (on its
# left): its left edge is further away (shorter), its right edge nearer (taller)
MONITOR = [(2880, 995), (3330, 930), (3330, 1385), (2880, 1330)]


def wall(pen):
    pen.rect(0, 0, W, FLOOR_Y, WALL)
    pen.rect(0, 0, W, 46, (118, 144, 184))
    pen.rect(0, 118, W, 188, WALL_DARK)
    for x in range(0, W, 120):
        pen.ellipse(x + 60, 153, 20, 17, (172, 198, 230))
    pen.rect(0, FLOOR_Y - 34, W, FLOOR_Y + 4, TRIM)


def floor(pen):
    pen.rect(0, FLOOR_Y + 4, W, H, CARPET)
    pen.line([(0, FLOOR_Y + 5), (W, FLOOR_Y + 5)], (160, 150, 136), 4)
    pen.ellipse(1720, 1900, 820, 190, (168, 50, 60))
    pen.ellipse(1720, 1900, 740, 160, (196, 72, 76))
    pen.ellipse(1720, 1900, 640, 126, (168, 50, 60))
    for x, y in ((520, 1500), (1450, 1560), (2250, 1470), (3300, 1880), (900, 2080), (3000, 2090), (200, 1850)):
        pen.ellipse(x, y, 24, 7, CARPET_DARK)
    # toys on the floor
    pen.fill(polyline([(300, 1980), (470, 1940), (505, 2000), (335, 2040)], close=True), (240, 200, 60))
    pen.ellipse(3450, 2010, 48, 44, (230, 90, 60))


def door(pen, t, amount):
    x0, y0, x1, y1 = DOOR
    pen.rect(x0, y0, x1, y1, TRIM)
    ix0, iy0, ix1 = x0 + 36, y0 + 36, x1 - 36
    # hallway beyond
    pen.rect(ix0, iy0, ix1, y1, (214, 196, 150))
    pen.rect(ix0, y1 - 120, ix1, y1, (170, 150, 110))
    pen.rect(ix0 + 90, iy0 + 120, ix0 + 250, iy0 + 330, (190, 170, 120), r=8)
    # the door leaf, hinged on the left, swinging into the room
    a = max(0.0, min(1.0, amount))
    w = (ix1 - ix0) * (1 - 0.82 * a)
    grow = 70 * a                       # the opening edge comes towards us
    leaf = polyline([(ix0, iy0), (ix0 + w, iy0 - grow * 0.6), (ix0 + w, y1 + grow * 0.4), (ix0, y1)], close=True)
    col = mix((172, 118, 74), (150, 100, 60), a)
    pen.fill(leaf, col)
    pen.stroke(leaf, darker(col, 0.8), 3)
    if a < 0.6:
        k = 1 - a
        pen.rect(ix0 + 40 * k, iy0 + 60, ix0 + w - 40 * k, iy0 + 420, darker(col, 0.9), r=10)
        pen.rect(ix0 + 40 * k, iy0 + 500, ix0 + w - 40 * k, y1 - 70, darker(col, 0.9), r=10)
    kx = ix0 + w - 36 * (1 - a) - 10
    pen.ellipse(kx, (iy0 + y1) / 2 + 10, 20, 20, (232, 200, 90))
    pen.line([(x0, y1), (x1, y1)], darker(TRIM, 0.85), 5)


def window(pen, t):
    x0, y0, x1, y1 = 1720, 300, 2440, 860
    pen.rect(x0 - 30, y0 - 30, x1 + 30, y1 + 30, TRIM)
    for i in range(10):
        c = mix((120, 176, 236), (200, 228, 250), i / 9)
        pen.rect(x0, y0 + (y1 - y0) * i / 10, x1, y0 + (y1 - y0) * (i + 1) / 10 + 1, c)
    # drifting cloud
    cx = x0 + ((t * 18) % (x1 - x0 + 400)) - 200
    pen.save()
    pen.clip(rrect(x0, y0, x1, y1))
    for dx, dy, r in ((0, 0, 40), (45, -12, 48), (95, 0, 38), (45, 14, 40)):
        pen.ellipse(cx + dx, y0 + 110 + dy, r * 1.3, r, (250, 252, 255))
    pen.fill(polyline([(x0, 720), (1860, 520), (1990, 690), (2130, 470), (2300, 680), (x1, 600), (x1, y1), (x0, y1)], close=True), (122, 138, 170))
    for px, py, w in ((1860, 520, 60), (2130, 470, 70)):
        pen.fill(polyline([(px, py), (px + w * 0.8, py + w), (px + 10, py + w * 0.8), (px - 20, py + w * 1.05), (px - w * 0.8, py + w)], close=True), (250, 250, 252))
    pen.fill(polyline([(x0, 770), (1980, 745), (2200, 760), (x1, 735), (x1, y1), (x0, y1)], close=True), (244, 246, 250))
    for tx, th in ((1770, 110), (1830, 80), (2330, 120), (2400, 90)):
        pen.fill(polyline([(tx, 820 - th), (tx + 34, 820), (tx - 34, 820)], close=True), (46, 92, 64))
    pen.restore()
    pen.rect((x0 + x1) / 2 - 12, y0, (x0 + x1) / 2 + 12, y1, TRIM)
    pen.rect(x0, (y0 + y1) / 2 - 12, x1, (y0 + y1) / 2 + 12, TRIM)
    pen.rect(x0 - 70, y1 + 20, x1 + 70, y1 + 62, (226, 220, 206), r=6)
    for s in (-1, 1):
        cx = x0 - 20 if s < 0 else x1 + 20
        o = cx + s * 190
        pen.fill(smooth([(cx - s * 50, 250), (o, 250), (o + s * 8, 960), (cx + s * 50, 960), (cx + s * 105, 610)], tension=0.4), (190, 40, 52))
        pen.line([(cx + s * 60, 610), (cx + s * 140, 610)], (238, 200, 60), 18)
    pen.rect(x0 - 260, 232, x1 + 260, 258, WOOD_DARK, r=10)


def bed(pen):
    pen.save()
    pen.translate(1180, 0)
    pen.scale(0.86, 1)
    pen.translate(-1150, 0)
    pen.rect(700, 820, 1600, 1330, WOOD, r=40)
    pen.rect(740, 860, 1560, 1290, WOOD_DARK, r=30)
    for x in (880, 1060, 1240, 1420):
        pen.rect(x - 14, 880, x + 14, 1270, WOOD, r=8)
    pen.fill(polyline([(640, 1130), (1660, 1130), (1720, 1560), (590, 1560)], close=True), (104, 78, 160))
    pen.fill(polyline([(640, 1080), (1660, 1080), (1668, 1150), (632, 1150)], close=True), (126, 100, 184))
    pen.rect(580, 1540, 1730, 1600, WOOD_DARK, r=12)
    pen.fill(polyline([(640, 1140), (1665, 1140), (1690, 1240), (618, 1240)], close=True), (238, 236, 246))
    pen.ellipse(900, 1070, 190, 80, (250, 250, 250), line=INK, width=4)
    pen.ellipse(1350, 1070, 190, 80, (250, 250, 250), line=INK, width=4)
    # plush bear and plush frog on the pillows
    pen.ellipse(900, 985, 110, 115, (150, 102, 62))
    pen.ellipse(830, 890, 36, 36, (150, 102, 62)); pen.ellipse(970, 890, 36, 36, (150, 102, 62))
    pen.ellipse(900, 1020, 52, 36, (214, 176, 130))
    pen.ellipse(870, 960, 12, 12, INK); pen.ellipse(930, 960, 12, 12, INK); pen.ellipse(900, 1008, 15, 10, INK)
    pen.ellipse(1350, 1000, 110, 92, (98, 176, 76))
    pen.ellipse(1300, 912, 42, 36, (98, 176, 76)); pen.ellipse(1400, 912, 42, 36, (98, 176, 76))
    pen.ellipse(1300, 912, 25, 25, (250, 250, 250)); pen.ellipse(1400, 912, 25, 25, (250, 250, 250))
    pen.ellipse(1304, 916, 9, 9, INK); pen.ellipse(1404, 916, 9, 9, INK)
    pen.stroke(smooth([(1300, 1030), (1350, 1050), (1400, 1030)], close=False), INK, 6)
    # shelf with a trophy over the bed
    pen.rect(820, 560, 1400, 588, WOOD_DARK, r=6)
    pen.fill(polyline([(960, 560), (1040, 560), (1030, 520), (970, 520)], close=True), (216, 176, 60))
    pen.rect(985, 460, 1015, 522, (216, 176, 60))
    pen.fill(polyline([(945, 380), (1055, 380), (1035, 460), (965, 460)], close=True), (236, 196, 70))
    pen.rect(1180, 430, 1300, 560, (160, 170, 186), r=12)
    pen.rect(1200, 370, 1280, 432, (160, 170, 186), r=10)
    pen.ellipse(1222, 400, 12, 12, (240, 70, 70)); pen.ellipse(1258, 400, 12, 12, (240, 70, 70))
    pen.restore()


def poster(pen):
    x0, y0, x1, y1 = 2960, 250, 3420, 610
    pen.rect(x0, y0, x1, y1, (250, 248, 240), r=6, line=INK, width=6)
    pen.rect(x0 + 30, y0 + 30, x1 - 30, y0 + 230, (200, 36, 48))
    pen.ellipse((x0 + x1) / 2, y0 + 130, 80, 80, (250, 250, 250), line=INK, width=6)
    pen.fill(polyline([(3190, 102 + y0), (3225, 127 + y0), (3212, 167 + y0), (3168, 167 + y0), (3155, 127 + y0)], close=True), INK)
    pen.text('FOOTBALL', (x0 + x1) / 2, y0 + 300, 52, INK)


def chair_back(pen, x, seat_y, view='side'):
    """Swivel chair parts drawn behind the sitter: back rest, pole, base."""
    col, dark = (64, 70, 82), (44, 48, 58)
    pen.rect(x - 40, seat_y + 30, x + 40, seat_y + 190, (150, 154, 162))          # gas lift
    for dx in (-190, -95, 0, 95, 190):                                           # star base
        pen.line([(x, seat_y + 200), (x + dx, seat_y + 250)], dark, 26)
        pen.ellipse(x + dx, seat_y + 262, 26, 22, INK)
    if view == 'side':
        pen.rect(x - 230, seat_y - 390, x - 150, seat_y + 10, col, r=36)          # back rest behind him (left)
        pen.rect(x - 200, seat_y - 60, x - 120, seat_y + 20, dark, r=10)
    else:
        pen.rect(x - 200, seat_y - 420, x + 200, seat_y - 20, col, r=60)
    pen.rect(x - 210, seat_y - 10, x + 210, seat_y + 50, col, r=26)               # seat


def desk_back(pen, t, st):
    x0, top, x1, feet = DESK
    # legs and modesty panel
    pen.rect(x0 + 20, top + 40, x0 + 80, feet, WOOD_DARK)
    pen.rect(x1 - 80, top + 40, x1 - 20, feet, WOOD_DARK)
    pen.rect(x0 + 80, top + 40, x1 - 80, top + 260, darker(WOOD_DARK, 0.85))
    # drawer unit
    pen.rect(x1 - 330, top + 40, x1 - 40, feet, WOOD)
    for i in range(3):
        yy = top + 60 + i * 110
        pen.rect(x1 - 310, yy, x1 - 60, yy + 90, WOOD_LIGHT, r=8)
        pen.rect(x1 - 215, yy + 38, x1 - 155, yy + 52, (230, 200, 90), r=6)
    # desktop
    pen.rect(x0 - 20, top, x1 + 20, top + 48, WOOD_LIGHT, r=8)
    pen.line([(x0 - 10, top + 46), (x1 + 10, top + 46)], WOOD_DARK, 4)
    monitor(pen, t, st)
    # keyboard, mouse, soda can
    pen.fill(polyline([(2920, top + 6), (3230, top + 6), (3260, top + 34), (2890, top + 34)], close=True), (220, 222, 228))
    for i in range(3):
        y = top + 12 + i * 7
        pen.line([(2915 - i * 8, y), (3235 + i * 8, y)], (170, 172, 180), 3)
    pen.ellipse(3330, top + 20, 30, 16, (220, 222, 228), line=(170, 172, 180), width=3)
    pen.rect(3480, top - 110, 3540, top + 10, (200, 30, 40), r=10)
    pen.rect(3480, top - 80, 3540, top - 40, (240, 240, 240))


def monitor(pen, t, st):
    (ax, ay), (bx, by), (cx, cy), (dx, dy) = MONITOR
    # stand
    mx = (ax + bx) / 2
    pen.rect(mx - 35, 1330, mx + 35, DESK[1] + 4, (60, 62, 70))
    pen.fill(polyline([(mx - 125, DESK[1] + 2), (mx + 135, DESK[1] + 2), (mx + 105, DESK[1] - 24), (mx - 95, DESK[1] - 24)], close=True), (60, 62, 70))
    # the monitor's right side panel, receding away from the camera
    pen.fill(polyline([(bx + 40, by - 40), (bx + 78, by - 20), (cx + 78, cy + 20), (cx + 40, cy + 40)], close=True), (22, 22, 28))
    # bezel: the quad grown outwards (more on the nearer, right-hand side)
    bez = polyline([(ax - 28, ay - 28), (bx + 40, by - 40), (cx + 40, cy + 40), (dx - 28, dy + 28)], close=True)
    pen.fill(bez, (34, 34, 40))
    # screen content through a perspective map of the 1600x1000 screen space
    m = skia.Matrix()
    src = [skia.Point(0, 0), skia.Point(1600, 0), skia.Point(1600, 1000), skia.Point(0, 1000)]
    dst = [skia.Point(ax, ay), skia.Point(bx, by), skia.Point(cx, cy), skia.Point(dx, dy)]
    m.setPolyToPoly(src, dst)
    pen.save()
    pen.clip(polyline(MONITOR, close=True))
    pen.c.concat(m)
    screens.draw(pen, st.get('screen', 'off'), t, st.get('screen_p', {}))
    # a soft diagonal glare across the glass
    pen.fill(polyline([(180, 0), (420, 0), (160, 1000), (-80, 1000)], close=True), (255, 255, 255), alpha=16)
    pen.restore()


def draw_back(pen, t, st):
    wall(pen)
    floor(pen)
    door(pen, t, st.get('door', 0.0))
    window(pen, t)
    bed(pen)
    poster(pen)
    pen.ellipse(1180, 1585, 540, 40, (60, 40, 30), alpha=70)
    px, py = CORNER_PIVOT
    pen.save()
    pen.translate(px, py)
    pen.scale(CORNER_SCALE)
    pen.translate(-px, -py)
    pen.ellipse((DESK[0] + DESK[2]) / 2, DESK[3] + 8, 520, 28, (60, 40, 30), alpha=70)
    desk_back(pen, t, st)
    if st.get('chair', True):
        chair_back(pen, _CHAIR_X, _SEAT_Y, st.get('chair_view', 'side'))
    pen.restore()


def draw_front(pen, t, st):
    pass
