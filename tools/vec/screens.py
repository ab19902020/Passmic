"""What's on Cartman's computer screen. Every screen is drawn in a 1600x1000
space; the room maps it onto the monitor, a screen insert fills the frame.

Nothing here reproduces a real club crest or anyone's likeness: players and
people are generic cartoon figures, and names appear only as captions.
"""
import math
import skia
from draw import Pen, rgb, ellipse, rrect, polyline, smooth, capsule, union, darker, mix

SW, SH = 1600, 1000
RED = (200, 22, 40)
UNITED_RED = (218, 32, 44)
INK = (24, 24, 28)
FONT = None


import os
_FONTS = {}


def font(bold=True):
    """Poppins Bold (vendored) for headings, DejaVu Sans for body text."""
    if bold not in _FONTS:
        here = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(here, '..', '..', 'fonts', 'Poppins-Bold.ttf')
        _FONTS[bold] = (skia.Typeface.MakeFromFile(path) if bold and os.path.exists(path)
                        else skia.Typeface('DejaVu Sans', skia.FontStyle.Normal()))
    return _FONTS[bold]


def text(pen, s, x, y, size, color, align='center', bold=True, alpha=255):
    return pen.text(s, x, y, size, color, font=font(bold), align=align, alpha=alpha)


def player(pen, x, y, s, shirt, shorts, phase, face=1):
    """Tiny cartoon footballer, feet at (x, y)."""
    leg = math.sin(phase) * 10
    pen.line([(x - 6, y - 40), (x - 6 + leg, y)], (240, 200, 160), 7)
    pen.line([(x + 6, y - 40), (x + 6 - leg, y)], (240, 200, 160), 7)
    pen.rect(x - 16, y - 62, x + 16, y - 38, shorts, r=6)
    pen.rect(x - 20, y - 110, x + 20, y - 58, shirt, r=10)
    pen.ellipse(x, y - 128, 18, 20, (240, 200, 160))
    pen.ellipse(x, y - 142, 18, 10, (60, 40, 30))


def match(pen, t, p):
    """A broadcast of United playing: pitch, crowd, players chasing the ball."""
    for i in range(8):
        pen.rect(0, 250 + i * 94, SW, 250 + (i + 1) * 94, (52, 150, 64) if i % 2 else (60, 164, 72))
    pen.rect(0, 0, SW, 250, (40, 40, 52))
    for i in range(160):                      # crowd, bobbing
        x = (i * 97) % SW
        y = 40 + (i * 53) % 190
        bob = math.sin(t * 6 + i) * 4 * (1 + p.get('roar', 0) * 3)
        pen.ellipse(x, y + bob, 12, 12, [(220, 40, 50), (240, 240, 240), (230, 200, 60), (200, 40, 50)][i % 4])
    pen.rect(0, 238, SW, 262, (240, 240, 240))
    pen.line([(800, 262), (800, SH)], (235, 245, 235), 6)
    pen.ellipse(800, 640, 170, 110, (0, 0, 0), alpha=0, line=(235, 245, 235), width=6)
    # the ball zips about, players follow it
    bx = 800 + math.sin(t * 1.3) * 520
    by = 600 + math.sin(t * 2.1) * 220
    for k in range(5):
        a = t * 1.1 + k * 1.3
        px = bx - 260 + k * 130 + math.sin(a) * 60
        py = by + 60 + math.cos(a * 1.3) * 90
        player(pen, px, py, 1, UNITED_RED, (250, 250, 250), t * 12 + k)
    for k in range(4):
        a = t * 0.9 + k * 1.7
        px = bx - 200 + k * 150 + math.cos(a) * 80
        py = by + 20 + math.sin(a * 1.1) * 110
        player(pen, px, py, 1, (240, 240, 245), (40, 40, 60), t * 12 + k * 2)
    pen.ellipse(bx, by + 40, 13, 13, (250, 250, 250), line=INK, width=3)
    # score bug
    pen.rect(40, 30, 560, 110, (20, 20, 28), r=12, alpha=230)
    pen.rect(40, 30, 120, 110, UNITED_RED, r=12)
    text(pen, p.get('score', 'MAN UTD  2 - 1  BAYERN'), 330, 84, 34, (250, 250, 250))
    text(pen, p.get('clock', "90+3'"), 1500, 84, 34, (250, 250, 250), align='right')
    if p.get('caption'):
        pen.rect(0, SH - 130, SW, SH, (20, 20, 28), alpha=225)
        pen.rect(0, SH - 130, 26, SH, UNITED_RED)
        text(pen, p['caption'], 70, SH - 48, 56, (250, 250, 250), align='left')


def devil(pen, t, p):
    """A generic grinning red devil cartoon (not the club crest)."""
    pen.rect(0, 0, SW, SH, (30, 20, 26))
    for i in range(14):
        a = t * 0.5 + i * math.tau / 14
        pen.fill(polyline([(800, 500), (800 + math.cos(a) * 1400, 500 + math.sin(a) * 1400),
                           (800 + math.cos(a + 0.12) * 1400, 500 + math.sin(a + 0.12) * 1400)], close=True), (60, 24, 30))
    bob = math.sin(t * 3) * 12
    cy = 470 + bob
    pen.fill(polyline([(700, cy - 190), (650, cy - 330), (760, cy - 230)], close=True), (150, 10, 24))
    pen.fill(polyline([(900, cy - 190), (950, cy - 330), (840, cy - 230)], close=True), (150, 10, 24))
    pen.ellipse(800, cy, 230, 210, (214, 26, 40))
    pen.ellipse(730, cy - 40, 50, 42, (255, 255, 255)); pen.ellipse(870, cy - 40, 50, 42, (255, 255, 255))
    pen.ellipse(742, cy - 34, 18, 18, INK); pen.ellipse(858, cy - 34, 18, 18, INK)
    pen.line([(680, cy - 100), (770, cy - 70)], INK, 16); pen.line([(920, cy - 100), (830, cy - 70)], INK, 16)
    pen.fill(smooth([(680, cy + 60), (800, cy + 150), (920, cy + 60), (800, cy + 100)]), (60, 10, 16))
    pen.fill(polyline([(700, cy + 70), (730, cy + 105), (760, cy + 82)], close=True), (255, 255, 255))
    pen.fill(polyline([(900, cy + 70), (870, cy + 105), (840, cy + 82)], close=True), (255, 255, 255))
    # trident
    tx = 1110 + math.sin(t * 3) * 10
    pen.line([(tx, 860), (tx, 330)], (230, 200, 60), 18)
    for dx in (-60, 0, 60):
        pen.line([(tx + dx, 330), (tx + dx, 250)], (230, 200, 60), 16)
    pen.line([(tx - 60, 335), (tx + 60, 335)], (230, 200, 60), 16)
    text(pen, 'RED DEVILS', 800, 940, 86, (250, 220, 80))


def legends(pen, t, p):
    """Five shirts on a wall of fame; `n` of them lit (counting on fingers)."""
    pen.rect(0, 0, SW, SH, (26, 22, 30))
    names = ['CANTONA', 'ROONEY', 'RONALDO', 'BECKHAM', 'KEANE']
    nums = ['7', '10', '7', '7', '16']
    n = p.get('n', 5)
    for i, (nm, no) in enumerate(zip(names, nums)):
        x = 180 + i * 310
        on = i < n
        col = UNITED_RED if on else (70, 60, 70)
        pen.fill(polyline([(x - 110, 330), (x - 50, 290), (x + 50, 290), (x + 110, 330), (x + 150, 420), (x + 95, 450),
                           (x + 85, 700), (x - 85, 700), (x - 95, 450), (x - 150, 420)], close=True), col)
        text(pen, no, x, 560, 130, (250, 250, 250) if on else (110, 100, 110))
        text(pen, nm, x, 800, 50, (250, 230, 120) if on else (90, 80, 90))
    text(pen, p.get('title', 'UNITED LEGENDS'), 800, 170, 90, (250, 250, 250))


def manager(pen, t, p):
    """A generic furious manager cartoon tapping his watch, with a caption."""
    pen.rect(0, 0, SW, SH, (38, 110, 60))
    for i in range(6):
        pen.rect(0, i * 180, SW, i * 180 + 90, (44, 124, 66))
    shout = 0.5 + 0.5 * math.sin(t * 9)
    x, y = 700, 640
    pen.rect(x - 230, y - 40, x + 230, y + 420, (30, 30, 40), r=90)          # big coat
    pen.ellipse(x, y - 200, 190, 210, (236, 178, 150))                        # red-faced head
    pen.ellipse(x, y - 200, 190, 210, (230, 60, 60), alpha=int(90 + 80 * shout))
    pen.ellipse(x - 70, y - 250, 30, 22, (255, 255, 255)); pen.ellipse(x + 70, y - 250, 30, 22, (255, 255, 255))
    pen.ellipse(x - 66, y - 248, 11, 11, INK); pen.ellipse(x + 66, y - 248, 11, 11, INK)
    pen.line([(x - 120, y - 310), (x - 30, y - 280)], INK, 14); pen.line([(x + 120, y - 310), (x + 30, y - 280)], INK, 14)
    pen.ellipse(x, y - 110, 70, 30 + 45 * shout, (70, 10, 20))
    pen.ellipse(x, y - 330, 160, 60, (240, 240, 240))                        # white hair
    # arm up, tapping a watch
    pen.fill(capsule(x + 200, y + 40, x + 360, y - 140, 55), (30, 30, 40))
    pen.ellipse(x + 380, y - 170, 55, 55, (236, 178, 150))
    pen.rect(x + 330, y - 150, x + 400, y - 100, (230, 200, 60), r=8)
    for i in range(3):
        a = t * 5 + i
        pen.line([(x - 260 - i * 40, y - 200 + i * 60), (x - 330 - i * 50, y - 230 + i * 60)], (255, 255, 255), 10)
    text(pen, p.get('caption', 'SIR ALEX FERGUSON'), 800, 940, 64, (250, 250, 250))


def news(pen, t, p):
    """News page: headline, a chart or a silhouette, a caption."""
    pen.rect(0, 0, SW, SH, (242, 242, 246))
    pen.rect(0, 0, SW, 110, (30, 34, 50))
    text(pen, 'FOOTY NEWS', 60, 76, 52, (250, 250, 250), align='left')
    text(pen, p.get('headline', ''), 60, 220, 70, INK, align='left')
    kind = p.get('kind', 'chart')
    if kind == 'chart':
        pen.rect(80, 280, 980, 900, (255, 255, 255), line=(200, 200, 210), width=4)
        for i in range(5):
            y = 860 - i * 130
            pen.line([(100, y), (960, y)], (225, 225, 232), 3)
        k = min(1.0, p.get('grow', 1.0))
        pts = [(120 + i * 70, 840 - (i ** 1.6) * 16 - math.sin(i) * 20) for i in range(13)]
        n = max(2, int(1 + k * (len(pts) - 1)))
        pen.line(pts[:n], (210, 30, 40), 12)
        text(pen, p.get('label', 'CLUB DEBT'), 530, 340, 44, (210, 30, 40))
        pen.rect(1040, 300, 1540, 520, (210, 30, 40), r=16)
        text(pen, p.get('banner', 'GLAZERS OUT'), 1290, 430, 64, (250, 250, 250))
        text(pen, p.get('sub', 'Fans protest again'), 1290, 620, 40, (90, 90, 100))
    else:
        # silhouette profile card
        pen.rect(80, 280, 700, 900, (220, 222, 230), r=20)
        pen.ellipse(390, 520, 130, 150, (150, 154, 166))
        pen.ellipse(390, 900, 240, 200, (150, 154, 166))
        text(pen, p.get('name', ''), 1100, 380, 64, INK)
        for i, line in enumerate(p.get('facts', [])):
            text(pen, line, 800, 500 + i * 90, 44, (80, 80, 92), align='left')


def monaco(pen, t, p):
    """A yacht bobbing off a sunny harbour."""
    for i in range(10):
        pen.rect(0, i * 60, SW, (i + 1) * 60 + 1, mix((120, 190, 250), (200, 230, 255), i / 9))
    pen.ellipse(1350, 150, 90, 90, (255, 230, 120))
    for i, x in enumerate(range(0, SW, 120)):
        h = 140 + (i * 37) % 120
        pen.rect(x, 600 - h, x + 100, 620, [(240, 220, 200), (250, 240, 230), (230, 200, 180)][i % 3])
        for wy in range(600 - h + 20, 600, 40):
            pen.rect(x + 20, wy, x + 40, wy + 20, (120, 160, 200)); pen.rect(x + 60, wy, x + 80, wy + 20, (120, 160, 200))
    pen.rect(0, 600, SW, SH, (30, 120, 200))
    for i in range(12):
        y = 650 + i * 30
        pen.line([(-100 + (t * 40 + i * 70) % 300 + k * 300, y) for k in range(7)], (90, 170, 230), 4)
    bob = math.sin(t * 2) * 8
    y = 760 + bob
    pen.fill(polyline([(420, y), (1200, y), (1110, y + 110), (520, y + 110)], close=True), (250, 250, 252))
    pen.rect(560, y - 120, 1030, y, (245, 245, 250), r=16)
    pen.rect(660, y - 210, 950, y - 120, (240, 240, 245), r=16)
    for x in range(600, 1000, 70):
        pen.rect(x, y - 95, x + 45, y - 60, (40, 70, 110), r=6)
    pen.line([(420, y + 30), (1200, y + 30)], (30, 60, 110), 8)
    text(pen, p.get('caption', 'MONACO'), 800, 120, 110, (255, 255, 255))


def document(pen, t, p):
    """Word processor: lines typed out; `chars` = how many are visible."""
    pen.rect(0, 0, SW, SH, (210, 214, 222))
    pen.rect(0, 0, SW, 70, (44, 86, 160))
    text(pen, 'Document1 - Word Processor', 30, 48, 32, (250, 250, 250), align='left', bold=False)
    pen.rect(0, 70, SW, 140, (236, 238, 242))
    for i, lab in enumerate(['File', 'Edit', 'View', 'Insert', 'Format']):
        text(pen, lab, 40 + i * 130, 116, 30, (60, 60, 70), align='left', bold=False)
    pen.rect(180, 170, 1420, SH + 40, (255, 255, 255))
    lines = p.get('lines', [])
    left = p.get('chars', 10 ** 6)
    y = 300
    cur = None
    for i, ln in enumerate(lines):
        shown = ln[:max(0, left)]
        left -= len(ln)
        size = 56 if i == 0 else 44
        w = text(pen, shown, 260, y, size, INK, align='left') if shown else 0
        if 0 <= left + len(ln) <= len(ln) and cur is None:
            cur = (260 + w + 6, y, size)
        if i == 0:
            y += 50
            if len(shown) == len(ln):
                pen.line([(260, y - 20), (260 + w, y - 20)], INK, 5)
        y += 120
        if left <= 0:
            break
    if cur is None:
        cur = (260, y, 48)
    if int(t * 2.5) % 2 == 0:
        pen.rect(cur[0], cur[1] - cur[2] * 0.85, cur[0] + 5, cur[1] + 8, INK)


def title(pen, t, p):
    pen.rect(0, 0, SW, SH, (20, 20, 24))


def off(pen, t, p):
    pen.rect(0, 0, SW, SH, (18, 20, 26))


def desktop(pen, t, p):
    for i in range(10):
        pen.rect(0, i * 100, SW, (i + 1) * 100 + 1, mix((40, 90, 170), (90, 150, 220), i / 9))
    pen.rect(0, SH - 70, SW, SH, (30, 34, 44))
    for i in range(4):
        pen.rect(60, 60 + i * 150, 160, 160 + i * 150, (240, 240, 245), r=12)


SCREENS = dict(match=match, devil=devil, legends=legends, manager=manager, news=news, monaco=monaco,
               document=document, title=title, off=off, desktop=desktop)


def draw(pen, name, t, p):
    pen.save()
    pen.clip(rrect(0, 0, SW, SH))
    SCREENS.get(name, off)(pen, t, p or {})
    pen.restore()
