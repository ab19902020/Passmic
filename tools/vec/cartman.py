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
CHIN = (150, 108, 84)

DEFAULT = dict(
    view='front', body='stand', walk=0.0, squash=0.0,
    head_dx=0.0, head_dy=0.0, head_tilt=0.0,
    # arm angle in degrees: 0 = hanging straight down, + = out to the side, 90 = horizontal, 160 = up
    arm_l=68.0, arm_r=68.0, hand_l='mitten', hand_r='mitten', hand_rot_l=0.0, hand_rot_r=0.0,
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
    palm = ellipse(0, 12, 15, 13.5)
    if shape == 'mitten':
        return union(palm, ellipse(-12.5, 6.5, 6, 8, -25))
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


REST = 68.0              # arm angle of the model sheet's "arms down": mittens against his sides
SHOULDER = (58.0, -55.0)  # where the sleeve leaves the side of his jacket, below the head


def draw_arm(pen, sx, sy, angle, side, hand, hand_rot, length=20, width=12.0, bend=0.0, hand_abs=None,
             explicit_length=False):
    """Stubby sleeve from the side of his body at (sx, sy); side -1 = his right
    (screen left). angle: 0 hangs down, 90 sticks straight out, 150 is up.
    Raised arms reach a little further so the mitten clears his head. bend > 0
    folds the forearm back in front of his belly (degrees)."""
    if not explicit_length:
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
def bean(w, h):
    """The show's open mouth: a dark bean, flat-ish on top, round underneath."""
    return smooth([(-w, -h * 0.28), (-w * 0.35, -h * 0.42), (w * 0.35, -h * 0.42), (w, -h * 0.28),
                   (w * 0.8, h * 0.5), (0, h), (-w * 0.8, h * 0.5)])


def mouth_path(kind, amt=1.0):
    """Returns (outer dark shape or None, teeth, tongue, line) paths, centred at 0,0.
    Open mouths are the sheet's wide dark beans with a pink tongue; closed
    ones are a short dark line."""
    k = amt
    if kind in ('rest', 'closed', 'm'):
        return None, None, None, smooth([(-8, 1), (0, -0.5), (8, 1)], close=False)
    if kind == 'frown':
        return None, None, None, smooth([(-9, 3), (0, -1.5), (9, 3)], close=False)
    if kind == 'smile':
        return None, None, None, smooth([(-11, -2.5), (0, 2.5), (11, -2.5)], close=False)
    if kind == 'smirk':
        return None, None, None, smooth([(-9, 1.5), (1, 1.5), (11, -3.5)], close=False)
    if kind == 'grin':      # big closed smile with teeth
        o = smooth([(-14, -3.5), (0, -2), (14, -3.5), (8, 6), (0, 8.5), (-8, 6)])
        return o, intersect(o, rrect(-15, -5, 15, 1.5)), None, None
    if kind in ('a', 'shout', 'laugh'):
        w, h = {'a': (11, 11), 'shout': (15.5, 17), 'laugh': (14, 12)}[kind]
        o = bean(w, h * k)
        tongue = intersect(o, ellipse(0, h * k, w * 0.62, h * k * 0.45))
        teeth = intersect(o, rrect(-w, -h, w, -h * 0.12)) if kind != 'a' else None
        return o, teeth, tongue, None
    if kind == 'e':
        o = bean(11.5, 7.5 * k)
        return o, intersect(o, rrect(-12, -5, 12, -0.6)), intersect(o, ellipse(0, 7.5 * k, 6, 3)), None
    if kind == 'i':
        o = bean(11, 4.5)
        return o, intersect(o, rrect(-12, -3, 12, 0.4)), None, None
    if kind == 'o':
        o = bean(7.5, 9.5 * k)
        return o, None, intersect(o, ellipse(0, 9.5 * k, 4.8, 3.6)), None
    if kind in ('u', 'w'):
        w = 5.0 if kind == 'u' else 5.8
        return bean(w, 6.5 * k), None, None, None
    if kind == 'l':
        o = bean(9.5, 7.5)
        return o, None, intersect(o, ellipse(0, -1.5, 4.2, 3.2)), None
    if kind in ('f', 'th'):
        o = bean(9.5, 4.5)
        teeth = intersect(o, rrect(-10, -3, 10, 0.8))
        tongue = intersect(o, ellipse(0, 3.5, 4, 2)) if kind == 'th' else None
        return o, teeth, tongue, None
    return None, None, None, smooth([(-8, 1), (0, -0.5), (8, 1)], close=False)


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
        # the little lower-lip line under an open mouth, as on the sheet
        b = o.getBounds()
        yl = b.bottom() + 3.2
        hw = min(6.5, b.width() * 0.32)
        pen.stroke(smooth([(-hw, yl), (0, yl + 0.8), (hw, yl)], close=False), CHIN, 1.0)
    if line is not None:
        pen.stroke(line, LINE, 1.7)
    pen.restore()


BROWS = {   # (inner dy, outer dy) relative to the resting brow line; + = lower
    'none': None,
    'angry': (6, -5),
    'determined': (6, -3),
    'sad': (-5, 4),
    'worried': (-4, 2),
    'raised': (-6, -6),
    'flat': (0, 0),
}


def draw_eyes(pen, cx, cy, p, profile=False):
    """Two touching eye whites (one in profile), lids, pupils. Fully closed
    eyes are drawn the show's way: no white at all, just a curved lid line."""
    top = max(p['lid_top'], p['blink'])
    eyes = [(cx + 15, cy, 1)] if profile else [(cx - 17.5, cy, -1), (cx + 18.5, cy, 1)]
    rx, ry = (13.5, 20.5) if profile else (19.5, 21)
    for ex, ey, s in eyes:
        if top >= 0.95:
            yl = ey + ry * 0.15
            pen.stroke(smooth([(ex - rx * 0.8, yl - 2), (ex, yl + 3.5), (ex + rx * 0.8, yl - 2)], close=False), LINE, 2.3)
            continue
        eye = ellipse(ex, ey, rx, ry, 0 if profile else s * 9)
        pen.fill(eye, WHITE)
        lx, ly = p['look']
        if profile:
            px, py = ex + 8 + lx * 2.5, ey + 1 + ly * 5
        else:
            px, py = ex - s * 5 + lx * 7, ey + 1 + ly * 7
        pen.save()
        pen.clip(eye)
        pen.ellipse(px, py, 2.9 * p['pupil'], 3.1 * p['pupil'], BLACK)
        # eyelids: skin coming down from the top / up from the bottom
        if top > 0.01:
            ycut = ey - ry + 2 * ry * top
            pen.fill(rrect(ex - rx - 2, ey - ry - 2, ex + rx + 2, ycut), SKIN)
            pen.line([(ex - rx, ycut), (ex + rx, ycut)], LINE, 1.7)
        if p['lid_bot'] > 0.01:
            ycut = ey + ry - 2 * ry * p['lid_bot']
            pen.fill(smooth([(ex - rx - 2, ycut + 3), (ex, ycut - 3), (ex + rx + 2, ycut + 3), (ex + rx + 2, ey + ry + 2), (ex - rx - 2, ey + ry + 2)]), SKIN)
            pen.stroke(smooth([(ex - rx, ycut + 3), (ex, ycut - 3), (ex + rx, ycut + 3)], close=False), LINE, 1.4)
        pen.restore()


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
    # jacket, as on the sheet: broad round shoulders right under the head, a
    # full belly, and a wide, nearly straight hem
    body = smooth([(-64, -86), (-80, -77), (-88, -62), (-90, -44), (-88, -28), (-80, -16), (0, -12),
                   (80, -16), (88, -28), (90, -44), (88, -62), (80, -77), (64, -86), (0, -90)])
    pen.fill(body, RED)
    # the jacket's front seam curves slightly, the buttons sit just off it
    pen.stroke(smooth([(1.5, -46), (2.5, -30), (1.0, -13)], close=False), darker(RED, 0.72), 1.3)
    for by in (-36, -23):
        pen.ellipse(-2.5, by, 2.1, 2.1, BLACK)
    pen.restore()


SIT_DROP = 14.0     # sitting, his body is this much lower than standing; the origin is the seat top
SIDE_SHOULDER = (6.0, -44.0)   # where the near arm leaves the jacket in profile


def front_sit_legs(pen):
    """Sitting, as on the sheet's SITTING (FRONT): trousers between two big
    soles that face the camera at the bottom corners of his jacket."""
    pen.fill(smooth([(-50, -6), (0, -9), (50, -6), (46, 8), (0, 10), (-46, 8)]), BROWN)
    for s in (-1, 1):
        pen.ellipse(s * 45, 3, 23, 26, BLACK)


def front_legs(pen, p):
    if p['body'] == 'sit':
        return
    lift = [0.0, 0.0]
    if p['body'] == 'walk':
        ph = p['walk'] * 2 * math.pi
        lift = [max(0.0, math.sin(ph)) * 7, max(0.0, -math.sin(ph)) * 7]
    # trousers: a brown band under the jacket hem, tapering a little to the shoes
    pen.fill(smooth([(-80, -22), (0, -23), (80, -22), (78, -8), (72, -3), (0, -2.5), (-72, -3), (-78, -8)], tension=0.6), BROWN)
    pen.line([(0, -13), (0, -3)], darker(BROWN, 0.7), 1.2)
    # shoes, as on the sheet: a thin flat black shape with pointed ends
    # standing; walking, the two feet come apart and lift in turn
    if lift[0] or lift[1]:
        for s_, l in zip((-1, 1), lift):
            pen.fill(smooth([(s_ * 2, -2 - l), (s_ * 42, -6 - l), (s_ * 86, -2 - l), (s_ * 42, 2 - l)], tension=0.8), BLACK)
    else:
        pen.fill(smooth([(-87, -1.5), (-55, -5.5), (0, -6), (55, -5.5), (87, -1.5), (55, 2.2), (0, 2.6), (-55, 2.2)], tension=0.8), BLACK)


def front_head(pen, p):
    hx, hy = p['head_dx'], p['head_dy']
    pen.save()
    pen.translate(hx, hy)
    pen.rotate(p['head_tilt'], 0, -70)
    head = ellipse(0, -100, 72.5, 57.5)
    pen.fill(head, SKIN)
    # double chin
    pen.stroke(smooth([(-56, -62), (-30, -50.5), (0, -47.5), (30, -50.5), (56, -62)], close=False), CHIN, 1.1)
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
        pen.translate(0, SIT_DROP)
    front_body(pen, p)
    if p['body'] == 'sit':
        front_sit_legs(pen)
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
    pen.translate(0, bob + (SIT_DROP if p['body'] == 'sit' else 0))
    body = smooth([(-44, -76), (-62, -54), (-66, -34), (-57, -17), (0, -15), (52, -17), (68, -33), (64, -56), (46, -76), (0, -84)])
    pen.fill(body, RED)
    for by in (-52, -38, -25):                               # buttons down the jacket front
        pen.ellipse(58 + (by + 52) * 0.25, by, 2.1, 2.1, BLACK)
    if p['body'] == 'sit':
        # as on the sheet's SITTING (SIDE): legs straight out along the seat, the sole standing up
        pen.fill(rrect(4, -31, 60, -12, 8), BROWN)
        pen.ellipse(64, -30, 11, 22, BLACK)
    # the near arm: sleeve tucked under the head, mitten on the belly (or reaching forward)
    sx, sy = SIDE_SHOULDER
    length = p.get('arm_len_r') or (10 + max(0.0, p['arm_r'] - 35) * 0.7)
    draw_arm(pen, sx, sy, p['arm_r'], 1, p['hand_r'], p['hand_rot_r'], length=length, width=11.5,
             hand_abs=p['hand_abs_r'], explicit_length=bool(p.get('arm_len_r')))
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
