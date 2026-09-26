"""Eric Cartman as a vector puppet, built from the proportions and colours of
his South Manchester model sheet (episode/sheets/cartman.png).

Units are the sheet's front-view pixels (he is ~170 units tall); the origin is
on the ground between his feet, y pointing down. draw(pen, pose) draws him
there; the caller sets position and scale with the pen's transform.

A pose is a dict (see DEFAULT): view front|side|back, body stand|sit|walk,
arm angles and hand shapes, brows, eyelids, pupils, mouth, head offsets.
"""
import math
import skia
from draw import (Pen, ellipse, rrect, polyline, smooth, capsule, union, intersect, difference, darker)

TEAL = (11, 156, 187)
YELLOW = (251, 209, 25)
SKIN = (247, 203, 154)
WHITE = (243, 243, 245)
RED = (189, 17, 48)
BROWN = (74, 46, 40)
BLACK = (22, 20, 24)
MOUTH = (38, 14, 20)
TONGUE = (226, 92, 118)
LINE = (70, 56, 52)
CHIN = (206, 156, 112)

DEFAULT = dict(
    view='front', body='stand', walk=0.0, squash=0.0,
    head_dx=0.0, head_dy=0.0, head_tilt=0.0,
    # arm angle in degrees: 0 = hanging straight down, + = out to the side, 90 = horizontal, 160 = up
    arm_l=58.0, arm_r=58.0, hand_l='mitten', hand_r='mitten', hand_rot_l=0.0, hand_rot_r=0.0,
    bend_l=0.0, bend_r=0.0, hand_abs_l=None, hand_abs_r=None,
    arms_front=False,
    brows='none', brow_amt=1.0, lid_top=0.0, lid_bot=0.0, blink=0.0,
    look=(0.0, 0.0), pupil=1.0,
    mouth='rest', mouth_amt=1.0,
)


def pose(**kw):
    p = dict(DEFAULT)
    p.update(kw)
    return p


# ------------------------------------------------------------------ hands
def hand_path(shape):
    """Yellow mitten shapes, wrist at the origin, pointing along +y (down)."""
    palm = ellipse(0, 11, 13.5, 12.5)
    if shape == 'mitten':
        return union(palm, ellipse(-11, 6, 5.5, 7.5, -25))
    if shape == 'fist':
        return union(rrect(-12.5, 0, 12.5, 22, 9), ellipse(-10, 8, 5, 6))
    if shape == 'open':
        parts = [ellipse(0, 9, 12, 10)]
        for i, a in enumerate((-24, -8, 8, 24)):
            r = math.radians(a)
            x, y = math.sin(r) * 10, 12 + math.cos(r) * 10
            parts.append(capsule(x * 0.6, 12, x + math.sin(r) * 7, y + math.cos(r) * 7, 3.6))
        parts.append(capsule(-9, 6, -17, 13, 3.8))
        return union(*parts)
    if shape == 'point':
        return union(rrect(-11, 0, 11, 18, 8), capsule(2, 14, 3, 33, 3.8), ellipse(-9, 7, 4.5, 5.5))
    if shape == 'thumb':
        return union(rrect(-11, 2, 11, 21, 8), capsule(-9, 8, -20, -2, 4.2))
    if shape.startswith('count'):
        n = int(shape[5:])
        parts = [rrect(-11, 2, 11, 20, 8)]
        xs = [-7.5, -2.5, 2.5, 7.5]
        for i in range(min(n, 4)):
            parts.append(capsule(xs[i], 14, xs[i] * 1.15, 30, 3.2))
        if n >= 5:
            parts.append(capsule(-9, 8, -19, 16, 3.6))
        return union(*parts)
    return palm


REST = 58.0              # arm angle of the model sheet's "arms down": mittens out at his sides
SHOULDER = (60.0, -50.0)  # where the sleeve leaves the side of his jacket, below the head


def draw_arm(pen, sx, sy, angle, side, hand, hand_rot, length=20, width=12.0, bend=0.0, hand_abs=None):
    """Stubby sleeve from the side of his body at (sx, sy); side -1 = his right
    (screen left). angle: 0 hangs down, 90 sticks straight out, 150 is up.
    Raised arms reach a little further so the mitten clears his head. bend > 0
    folds the forearm back in front of his belly (degrees)."""
    length += max(0.0, angle - 90) * 0.3
    if bend:
        l1, l2 = length * 0.55, length * 0.62
        a = math.radians(angle)
        ex, ey = sx + side * math.sin(a) * l1, sy + math.cos(a) * l1
        a2deg = angle - bend
        a2 = math.radians(a2deg)
        hx, hy = ex + side * math.sin(a2) * l2, ey + math.cos(a2) * l2
        pen.fill(union(capsule(sx, sy, ex, ey, width), capsule(ex, ey, hx, hy, width * 0.92)), RED)
        angle = a2deg
    else:
        a = math.radians(angle)
        hx, hy = sx + side * math.sin(a) * length, sy + math.cos(a) * length
        pen.fill(capsule(sx, sy, hx, hy, width), RED)
    pen.save()
    pen.translate(hx, hy)
    # hand_abs: fixed on-screen angle (0 = fingers down, 180 = up, -90 = pointing right)
    pen.rotate(hand_abs if hand_abs is not None else -side * angle + hand_rot * -side)
    if side > 0:
        pen.scale(-1, 1)
    pen.fill(hand_path(hand), YELLOW)
    pen.stroke(hand_path(hand), darker(YELLOW, 0.82), 0.9)
    pen.restore()


# ------------------------------------------------------------------ face parts
def mouth_path(kind, amt=1.0):
    """Returns (outer dark shape or None, teeth, tongue, line) paths, centred at 0,0."""
    k = amt
    if kind in ('rest', 'closed', 'm'):
        return None, None, None, smooth([(-8, 1), (0, -1), (8, 1)], close=False)
    if kind == 'frown':
        return None, None, None, smooth([(-9, 2.5), (0, -1.5), (9, 2.5)], close=False)
    if kind == 'smile':
        return None, None, None, smooth([(-10, -2), (0, 2.5), (10, -2)], close=False)
    if kind == 'smirk':
        return None, None, None, smooth([(-9, 1.5), (0, 1), (10, -3)], close=False)
    if kind == 'grin':      # big closed smile with teeth
        o = smooth([(-13, -3), (0, -1.5), (13, -3), (7, 6), (0, 8), (-7, 6)])
        return o, intersect(o, rrect(-14, -4, 14, 1.5)), None, None
    if kind in ('a', 'shout', 'laugh'):
        w, h = {'a': (10, 9), 'shout': (15, 17), 'laugh': (13, 11)}[kind]
        h *= k
        o = smooth([(-w, -1), (0, -3), (w, -1), (w * 0.6, h * 0.7), (0, h), (-w * 0.6, h * 0.7)])
        tongue = intersect(o, ellipse(0, h, w * 0.6, h * 0.45))
        teeth = intersect(o, rrect(-w, -4, w, 0.5)) if kind != 'a' else None
        return o, teeth, tongue, None
    if kind == 'e':
        o = smooth([(-11, -2), (0, -3), (11, -2), (6, 5 * k), (0, 6.5 * k), (-6, 5 * k)])
        return o, intersect(o, rrect(-12, -4, 12, 0.8)), intersect(o, ellipse(0, 7 * k, 5, 3)), None
    if kind == 'i':
        o = smooth([(-10, -1.5), (0, -2.5), (10, -1.5), (6, 3), (0, 3.8), (-6, 3)])
        return o, intersect(o, rrect(-11, -3, 11, 0.6)), None, None
    if kind == 'o':
        return ellipse(0, 2, 6 * k, 7.5 * k), None, None, None
    if kind in ('u', 'w'):
        s = 4.2 if kind == 'u' else 4.8
        return ellipse(0, 1.5, s * k, s * 1.15 * k), None, None, None
    if kind == 'l':
        o = smooth([(-9, -1.5), (0, -2.5), (9, -1.5), (5, 5), (0, 6.5), (-5, 5)])
        return o, None, intersect(o, ellipse(0, 0.5, 4.2, 4)), None
    if kind in ('f', 'th'):
        o = smooth([(-9, -2), (0, -3), (9, -2), (6, 3), (0, 4), (-6, 3)])
        teeth = intersect(o, rrect(-10, -4, 10, 2.2))
        tongue = intersect(o, ellipse(0, 4, 4, 2.2)) if kind == 'th' else None
        return o, teeth, tongue, None
    return None, None, None, smooth([(-8, 1), (0, -1), (8, 1)], close=False)


def draw_mouth(pen, x, y, kind, amt=1.0, scale=1.0):
    o, teeth, tongue, line = mouth_path(kind, amt)
    pen.save()
    pen.translate(x, y)
    pen.scale(scale)
    if o is not None:
        pen.fill(o, MOUTH)
        if tongue is not None:
            pen.fill(tongue, TONGUE)
        if teeth is not None:
            pen.fill(teeth, WHITE)
            # gaps between teeth
            b = teeth.getBounds()
            n = 5
            for i in range(1, n):
                xx = b.left() + b.width() * i / n
                pen.line([(xx, b.top()), (xx, b.bottom())], MOUTH, 0.55)
        pen.stroke(o, MOUTH, 0.9)
    if line is not None:
        pen.stroke(line, LINE, 1.7)
    pen.restore()


BROWS = {   # (inner dy, outer dy) relative to the resting brow line; + = lower
    'none': None,
    'angry': (6, -5),
    'determined': (4, -2),
    'sad': (-5, 4),
    'worried': (-4, 2),
    'raised': (-6, -6),
    'flat': (0, 0),
}


def draw_eyes(pen, cx, cy, p, profile=False):
    """Two touching eye whites (one in profile), lids, pupils."""
    blink = max(p['blink'], p['lid_top'])
    eyes = [(cx + 15, cy, 1)] if profile else [(cx - 17.5, cy, -1), (cx + 18.5, cy, 1)]
    rx, ry = (13.5, 20.5) if profile else (19.5, 21)
    for ex, ey, s in eyes:
        eye = ellipse(ex, ey, rx, ry, 0 if profile else s * 6)
        pen.fill(eye, WHITE)
        # pupils
        if blink < 0.95:
            lx, ly = p['look']
            if profile:
                px, py = ex + 8 + lx * 2.5, ey + 1 + ly * 5
            else:
                px, py = ex - s * 5 + lx * 7, ey + 1 + ly * 7
            pen.save()
            pen.clip(eye)
            pen.ellipse(px, py, 2.9 * p['pupil'], 3.1 * p['pupil'], BLACK)
            pen.restore()
        # eyelids: skin coming down from the top / up from the bottom
        top = max(p['lid_top'], p['blink'])
        if top > 0.01:
            pen.save()
            pen.clip(eye)
            ycut = ey - ry + 2 * ry * top
            lid = rrect(ex - rx - 2, ey - ry - 2, ex + rx + 2, ycut)
            pen.fill(lid, SKIN)
            pen.line([(ex - rx, ycut), (ex + rx, ycut)], LINE, 1.6 if top < 0.95 else 2.2)
            pen.restore()
        if p['lid_bot'] > 0.01:
            pen.save()
            pen.clip(eye)
            ycut = ey + ry - 2 * ry * p['lid_bot']
            pen.fill(smooth([(ex - rx - 2, ycut + 3), (ex, ycut - 3), (ex + rx + 2, ycut + 3), (ex + rx + 2, ey + ry + 2), (ex - rx - 2, ey + ry + 2)]), SKIN)
            pen.stroke(smooth([(ex - rx, ycut + 3), (ex, ycut - 3), (ex + rx, ycut + 3)], close=False), LINE, 1.4)
            pen.restore()
        pen.stroke(eye, (150, 148, 152), 0.7)


def draw_brows(pen, cx, cy, p, profile=False):
    b = BROWS.get(p['brows'])
    if not b:
        return
    k = p['brow_amt']
    inner, outer = b[0] * k, b[1] * k
    sides = [1] if profile else [-1, 1]
    for s in sides:
        if profile:
            pts = [(cx + 6, cy + outer), (cx + 26, cy + inner)]
        else:
            pts = [(cx + s * 3.5, cy + inner), (cx + s * 31, cy + outer)]
        pen.line(pts, BLACK, 4.2)


# ------------------------------------------------------------------ body parts
def front_body(pen, p):
    sq = 1 + p['squash']
    pen.save()
    pen.scale(1 + 0.4 * p['squash'], 1 / sq)
    # jacket: shoulders under the head, belly widest near the hem
    body = smooth([(-60, -78), (-70, -58), (-73, -42), (-85, -28), (-74, -17), (0, -15), (74, -17), (85, -28),
                   (73, -42), (70, -58), (60, -78), (0, -84)])
    pen.fill(body, RED)
    pen.line([(0.5, -44), (0.5, -16)], darker(RED, 0.75), 1.3)
    for by in (-37, -25):
        pen.ellipse(2.5, by, 2.0, 2.0, BLACK)
    pen.restore()


def front_legs(pen, p):
    if p['body'] == 'sit':
        # thighs toward the camera, big soles facing us
        for s in (-1, 1):
            pen.ellipse(s * 34, -4, 30, 13, BROWN)
            pen.ellipse(s * 36, 6, 20, 17, BLACK)
        return
    lift = [0.0, 0.0]
    if p['body'] == 'walk':
        ph = p['walk'] * 2 * math.pi
        lift = [max(0.0, math.sin(ph)) * 7, max(0.0, -math.sin(ph)) * 7]
    pen.fill(smooth([(-79, -26), (0, -28), (79, -26), (77, -12), (73, -5), (0, -4.5), (-73, -5), (-77, -12)]), BROWN)
    pen.line([(0, -16), (0, -5)], darker(BROWN, 0.7), 1.4)
    for s, l in zip((-1, 1), lift):
        pen.ellipse(s * 37, -3.2 - l, 39, 4.6, BLACK)


def front_head(pen, p):
    hx, hy = p['head_dx'], p['head_dy']
    pen.save()
    pen.translate(hx, hy)
    pen.rotate(p['head_tilt'], 0, -70)
    head = ellipse(0, -100, 72.5, 57.5)
    pen.fill(head, SKIN)
    # double chin
    pen.stroke(smooth([(-54, -60), (-28, -49.5), (0, -46.5), (28, -49.5), (54, -60)], close=False), CHIN, 1.3)
    # hat: dome over the head above the brim arc, brim band, pom-pom
    hat_clip = ellipse(0, -100.5, 73.5, 58.5)
    brim_top = [(-80, -99), (-40, -120), (0, -127), (40, -120), (80, -99)]
    brim_bot = [(80, -91), (40, -113), (0, -120.5), (-40, -113), (-80, -91)]
    dome = smooth(brim_top + [(80, -170), (-80, -170)], tension=0.9)
    pen.fill(intersect(hat_clip, dome), TEAL)
    band = smooth(brim_top + brim_bot, tension=0.9)
    pen.fill(intersect(hat_clip, band), YELLOW)
    pom = union(*[ellipse(x, y, r, r * 0.86) for x, y, r in
                  ((-11, -157, 6), (-3.5, -161, 6), (4.5, -161, 6), (11.5, -157, 6), (0, -156, 7.5),
                   (-16, -154, 4.5), (16.5, -154, 4.5))])
    pen.fill(pom, YELLOW)
    pen.stroke(pom, darker(YELLOW, 0.8), 0.9)
    # face
    draw_eyes(pen, 0.5, -97, p)
    draw_brows(pen, 0, -113, p)
    kind, amt = p['mouth'], p['mouth_amt']
    draw_mouth(pen, 2, -64, kind, amt)
    pen.restore()


def draw_front(pen, p):
    if p['body'] != 'sit':
        pen.ellipse(0, 1, 88, 8, (0, 0, 0), alpha=60)      # contact shadow (not when he's up on a chair)
    walking = p['body'] == 'walk'
    if walking:                                            # South Park walk: a bouncy trot
        bob = -abs(math.sin(p['walk'] * 2 * math.pi)) * 4
        front_legs(pen, p)
        pen.save()
        pen.translate(0, bob)
    else:
        front_legs(pen, p)
    if p['body'] == 'sit':
        pen.save()
        pen.translate(0, -6)
    front_body(pen, p)
    sx, sy = SHOULDER
    arm_l = lambda: draw_arm(pen, -sx, sy, p['arm_l'], -1, p['hand_l'], p['hand_rot_l'], bend=p['bend_l'], hand_abs=p['hand_abs_l'])
    arm_r = lambda: draw_arm(pen, sx, sy, p['arm_r'], 1, p['hand_r'], p['hand_rot_r'], bend=p['bend_r'], hand_abs=p['hand_abs_r'])
    # raised arms pass behind the head; everything else is in front of the body
    raised_l, raised_r = p['arm_l'] > 110 and not p['bend_l'], p['arm_r'] > 110 and not p['bend_r']
    if raised_l:
        arm_l()
    if raised_r:
        arm_r()
    front_head(pen, p)
    if not raised_l:
        arm_l()
    if not raised_r:
        arm_r()
    if p['body'] == 'sit':
        pen.restore()
    if walking:
        pen.restore()


# ------------------------------------------------------------------ side view (facing right)
def draw_side(pen, p):
    """Profile facing right, matched to the sheet's SIDE (RIGHT) drawing: big
    round head sitting low over a rounded jacket, a tall eye flush with the
    face edge, a small mouth tucked inside the face, the mitten resting on the
    belly with its sleeve hidden under the head, buttons down the front."""
    walking = p['body'] == 'walk'
    ph = p['walk'] * 2 * math.pi if walking else 0.0
    bob = -abs(math.sin(ph)) * 4 if walking else 0.0          # South Park walk: a bouncy trot
    if p['body'] != 'sit':
        pen.ellipse(6, 1, 60, 6, (0, 0, 0), alpha=55)
    if p['body'] == 'stand':
        pen.fill(rrect(-50, -24, 48, -5, 8), BROWN)                   # trousers, as on the sheet
        pen.ellipse(2, -4, 56, 5, BLACK)
    elif walking:
        for k, ph_off, shade in ((0, math.pi, 0.72), (1, 0.0, 1.0)):
            dx = math.sin(ph + ph_off) * 15 if walking else (k - 0.5) * 18
            lift = max(0.0, math.cos(ph + ph_off)) * 6 if walking else 0.0
            pen.fill(rrect(dx - 14, -24 - lift, dx + 12, -5 - lift, 6), darker(BROWN, shade))
            pen.ellipse(dx + 4, -4 - lift, 24, 5, darker(BLACK, shade) if shade < 1 else BLACK)
    pen.save()
    pen.translate(0, bob + (-6 if p['body'] == 'sit' else 0))
    body = smooth([(-44, -76), (-62, -54), (-66, -34), (-57, -17), (0, -15), (52, -17), (68, -33), (64, -56), (46, -76), (0, -84)])
    pen.fill(body, RED)
    for by in (-52, -38, -25):                               # buttons down the jacket front
        pen.ellipse(58 + (by + 52) * 0.25, by, 2.1, 2.1, BLACK)
    if p['body'] == 'sit':
        # stubby legs straight out along the seat, soles facing forward
        pen.fill(rrect(8, -28, 50, -6, 10), BROWN)
        pen.ellipse(55, -17, 7.5, 12.5, BLACK)
    # the near arm: sleeve tucked under the head, mitten on the belly (or reaching forward)
    reach = max(0.0, p['arm_r'] - 35)
    draw_arm(pen, 6, -44, p['arm_r'], 1, p['hand_r'], p['hand_rot_r'], length=10 + reach * 0.7, width=11.5)
    # head
    pen.save()
    pen.translate(p['head_dx'], p['head_dy'])
    pen.rotate(p['head_tilt'], 0, -70)
    head = ellipse(2, -100, 63, 58)
    pen.fill(head, SKIN)
    hat_clip = ellipse(2, -100.5, 64.5, 59.5)
    brim_top = [(-72, -84), (-30, -104), (20, -124), (72, -142)]
    brim_bot = [(72, -132), (20, -115.5), (-30, -95.5), (-72, -76)]
    pen.fill(intersect(hat_clip, smooth(brim_top + [(72, -178), (-72, -178)], tension=0.8)), TEAL)
    pen.fill(intersect(hat_clip, smooth(brim_top + brim_bot, tension=0.8)), YELLOW)
    pom = union(*[ellipse(x, y, r, r * 0.86) for x, y, r in
                  ((-9, -157, 6), (-1, -161, 6), (7, -159, 5.5), (-3, -156, 7.5), (-15, -154, 4.5), (13, -154, 4))])
    pen.fill(pom, YELLOW)
    pen.stroke(pom, darker(YELLOW, 0.8), 0.9)
    pen.save()
    pen.clip(ellipse(2, -100, 66.5, 61))    # the eye sits flush with the face edge
    draw_eyes(pen, 36, -101, p, profile=True)
    pen.restore()
    draw_brows(pen, 36, -123, p, profile=True)
    pen.save()
    pen.clip(head)
    draw_mouth(pen, 43, -64, p['mouth'], p['mouth_amt'], scale=0.62)
    pen.restore()
    pen.restore()
    pen.restore()


def draw_back(pen, p):
    pen.ellipse(0, 1, 88, 8, (0, 0, 0), alpha=60)
    front_legs(pen, dict(p, body='stand' if p['body'] != 'walk' else 'walk'))
    front_body(pen, p)
    pen.line([(0, -60), (0, -12)], darker(RED, 0.8), 1.2)
    draw_arm(pen, -SHOULDER[0], SHOULDER[1], p['arm_l'], -1, p['hand_l'], p['hand_rot_l'])
    draw_arm(pen, SHOULDER[0], SHOULDER[1], p['arm_r'], 1, p['hand_r'], p['hand_rot_r'])
    head = ellipse(0, -100, 72.5, 57.5)
    pen.fill(head, SKIN)
    hat_clip = ellipse(0, -100.5, 73.5, 58.5)
    brim_top = [(-80, -90), (-40, -78), (0, -74), (40, -78), (80, -90)]
    brim_bot = [(80, -82), (40, -70), (0, -66.5), (-40, -70), (-80, -82)]
    pen.fill(intersect(hat_clip, smooth(brim_top + [(80, -170), (-80, -170)], tension=0.9)), TEAL)
    pen.fill(intersect(hat_clip, smooth(brim_top + brim_bot, tension=0.9)), YELLOW)
    pom = union(*[ellipse(x, y, r, r * 0.86) for x, y, r in
                  ((-11, -157, 6), (-3.5, -161, 6), (4.5, -161, 6), (11.5, -157, 6), (0, -156, 7.5))])
    pen.fill(pom, YELLOW)


def draw(pen, p):
    v = p['view']
    if v == 'front':
        draw_front(pen, p)
    elif v in ('side', 'right'):
        draw_side(pen, p)
    elif v == 'left':
        pen.save()
        pen.scale(-1, 1)
        draw_side(pen, p)
        pen.restore()
    elif v == 'back':
        draw_back(pen, p)
