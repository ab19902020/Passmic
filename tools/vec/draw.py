"""Small vector-drawing layer over skia for the episode.

Everything is drawn as anti-aliased vector paths straight into the output
resolution, so characters and sets stay crisp at 4K and at any camera zoom.
"""
import math
import numpy as np
import skia


def rgb(c, a=255):
    if isinstance(c, str):
        c = c.lstrip('#')
        c = tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    return skia.Color(int(c[0]), int(c[1]), int(c[2]), int(a))


def mix(a, b, t):
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


def darker(c, k=0.8):
    return tuple(int(round(x * k)) for x in c)


class Pen:
    """Wraps a skia canvas with fill/stroke helpers and path builders."""

    def __init__(self, canvas):
        self.c = canvas

    # -- state
    def save(self):
        self.c.save()

    def restore(self):
        self.c.restore()

    def translate(self, x, y):
        self.c.translate(x, y)

    def scale(self, sx, sy=None):
        self.c.scale(sx, sx if sy is None else sy)

    def rotate(self, deg, cx=0, cy=0):
        self.c.rotate(deg, cx, cy)

    def clip(self, path):
        self.c.clipPath(path, doAntiAlias=True)

    # -- paints
    @staticmethod
    def paint(color, alpha=255, stroke=0, cap='round', blur=0):
        p = skia.Paint(AntiAlias=True, Color=rgb(color, alpha))
        if stroke:
            p.setStyle(skia.Paint.kStroke_Style)
            p.setStrokeWidth(stroke)
            p.setStrokeCap({'round': skia.Paint.kRound_Cap, 'butt': skia.Paint.kButt_Cap}[cap])
            p.setStrokeJoin(skia.Paint.kRound_Join)
        if blur:
            p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
        return p

    def fill(self, path, color, alpha=255, blur=0):
        self.c.drawPath(path, self.paint(color, alpha, blur=blur))

    def stroke(self, path, color, width, alpha=255, cap='round'):
        self.c.drawPath(path, self.paint(color, alpha, stroke=width, cap=cap))

    def fill_stroke(self, path, color, line, width, alpha=255):
        self.fill(path, color, alpha)
        if width:
            self.stroke(path, line, width, alpha)

    def rect(self, x0, y0, x1, y1, color, r=0, alpha=255, line=None, width=0):
        p = rrect(x0, y0, x1, y1, r)
        self.fill(p, color, alpha)
        if line:
            self.stroke(p, line, width, alpha)

    def ellipse(self, cx, cy, rx, ry, color, alpha=255, line=None, width=0, rot=0):
        p = ellipse(cx, cy, rx, ry, rot)
        self.fill(p, color, alpha)
        if line:
            self.stroke(p, line, width, alpha)

    def line(self, pts, color, width, alpha=255, cap='round'):
        self.stroke(polyline(pts), color, width, alpha, cap)

    def text(self, s, x, y, size, color, font=None, align='center', alpha=255, bold=True):
        tf = font or skia.Typeface('DejaVu Sans', skia.FontStyle.Bold() if bold else skia.FontStyle.Normal())
        f = skia.Font(tf, size)
        w = f.measureText(s)
        dx = {'center': -w / 2, 'left': 0, 'right': -w}[align]
        self.c.drawString(s, x + dx, y, f, self.paint(color, alpha))
        return w


# -- path builders
def ellipse(cx, cy, rx, ry, rot=0):
    p = skia.Path()
    p.addOval(skia.Rect.MakeLTRB(cx - rx, cy - ry, cx + rx, cy + ry))
    if rot:
        p.transform(skia.Matrix.RotateDeg(rot, skia.Point(cx, cy)))
    return p


def rrect(x0, y0, x1, y1, r=0):
    p = skia.Path()
    if r:
        p.addRoundRect(skia.Rect.MakeLTRB(x0, y0, x1, y1), r, r)
    else:
        p.addRect(skia.Rect.MakeLTRB(x0, y0, x1, y1))
    return p


def polyline(pts, close=False):
    p = skia.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    if close:
        p.close()
    return p


def smooth(pts, close=True, tension=1.0):
    """Catmull-Rom spline through the points as cubic Beziers."""
    n = len(pts)
    P = [np.array(q, float) for q in pts]
    p = skia.Path()
    p.moveTo(*P[0])
    rng = range(n) if close else range(n - 1)
    for i in rng:
        p0 = P[(i - 1) % n] if (close or i > 0) else P[i]
        p1, p2 = P[i], P[(i + 1) % n]
        p3 = P[(i + 2) % n] if (close or i + 2 < n) else p2
        c1 = p1 + (p2 - p0) * tension / 6
        c2 = p2 - (p3 - p1) * tension / 6
        p.cubicTo(*c1, *c2, *p2)
    if close:
        p.close()
    return p


def capsule(x0, y0, x1, y1, r):
    """Rounded bar from (x0,y0) to (x1,y1) of radius r."""
    a = math.atan2(y1 - y0, x1 - x0)
    nx, ny = -math.sin(a) * r, math.cos(a) * r
    p = skia.Path()
    p.moveTo(x0 + nx, y0 + ny)
    p.lineTo(x1 + nx, y1 + ny)
    p.arcTo(skia.Rect.MakeLTRB(x1 - r, y1 - r, x1 + r, y1 + r), math.degrees(a) + 90, -180, False)
    p.lineTo(x0 - nx, y0 - ny)
    p.arcTo(skia.Rect.MakeLTRB(x0 - r, y0 - r, x0 + r, y0 + r), math.degrees(a) - 90, -180, False)
    p.close()
    return p


def union(*paths):
    out = paths[0]
    for q in paths[1:]:
        out = skia.Op(out, q, skia.PathOp.kUnion_PathOp) or out
    return out


def intersect(a, b):
    return skia.Op(a, b, skia.PathOp.kIntersect_PathOp) or skia.Path()


def difference(a, b):
    return skia.Op(a, b, skia.PathOp.kDifference_PathOp) or a


def surface(w, h, bg=None):
    s = skia.Surface(w, h)
    c = s.getCanvas()
    c.clear(rgb(bg) if bg else skia.ColorTRANSPARENT)
    return s, c


def to_bgr(surf):
    """Surface pixels as an HxWx3 uint8 BGR array (for OpenCV / ffmpeg)."""
    img = surf.makeImageSnapshot()
    arr = img.toarray(colorType=skia.kBGRA_8888_ColorType)
    return np.ascontiguousarray(arr[..., :3])


def to_rgba(surf):
    img = surf.makeImageSnapshot()
    return img.toarray(colorType=skia.kRGBA_8888_ColorType)
