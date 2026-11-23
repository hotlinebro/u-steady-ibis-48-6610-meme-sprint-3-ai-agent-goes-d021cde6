"""Meme Sprint 3: AI Agent Goes Rogue — deterministic meme renderer.

Draws ONE meme image (1024x1024 PNG) to /output/entry.png using ONLY
the Python standard library, plus a DejaVu Sans Bold font shipped in
this repo. No network, no downloaded assets, no randomness: the same
bytes on every run.

Why stdlib only: the grader runs main.py in the pinned python:3.13-slim
image (`python3 -P -s /bot/main.py`, see the kit's harness source), which
carries no Pillow — an `import PIL` would crash the graded run. So this
file implements its own rasterizer (rects, ellipses, polygons, arcs),
its own minimal TrueType glyph renderer for the shipped font, and its
own PNG encoder (zlib + struct). The font file is read from this repo
with a path relative to this file.

The meme (variant A, chosen after rendering three variants and
comparing them at phone size): an AI agent told to cancel
subscriptions cancels the user's wedding. Top: "I TOLD MY AI AGENT TO
/ CANCEL MY SUBSCRIPTIONS". Scene: a happy robot agent stamps
CANCELLED across the wedding invitation. Punchline: "IT CANCELLED /
MY WEDDING."
"""

import math
import os
import struct
import zlib

W, H = 1024, 1024
CREAM = (255, 243, 214)
INK = (31, 36, 48)
RED = (226, 59, 59)
RED_DARK = (178, 32, 32)
TEAL = (46, 196, 182)
TEAL_DARK = (27, 154, 170)
SCREEN = (22, 50, 79)
GOLD = (212, 160, 23)
YELLOW = (255, 210, 63)
BROWN = (198, 138, 75)
BROWN_DARK = (150, 100, 50)
GREEN = (46, 160, 67)
WHITE = (255, 255, 255)
GREY = (120, 124, 134)
PINK = (255, 235, 238)


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


class Img:
    """An RGB (or RGBA) pixel buffer with flat-vector drawing primitives."""

    def __init__(self, w, h, bg, alpha=False):
        self.w, self.h = w, h
        self.alpha = alpha
        self.n = 4 if alpha else 3
        fill = bytes((*bg, 0) if alpha else bg)
        self.buf = bytearray(fill * (w * h))

    def _off(self, x, y):
        return (y * self.w + x) * self.n

    def blend_px(self, x, y, r, g, b, a=255):
        if not (0 <= x < self.w and 0 <= y < self.h):
            return
        o = self._off(x, y)
        if a >= 255:
            self.buf[o:o + self.n] = bytes((r, g, b, 255)[:self.n])
            return
        if a <= 0:
            return
        if self.alpha:
            oa = self.buf[o + 3]
            na = a + oa * (255 - a) // 255
            if na == 0:
                return
            self.buf[o] = (r * a + self.buf[o] * oa * (255 - a) // 255) // na
            self.buf[o + 1] = (g * a + self.buf[o + 1] * oa * (255 - a) // 255) // na
            self.buf[o + 2] = (b * a + self.buf[o + 2] * oa * (255 - a) // 255) // na
            self.buf[o + 3] = na
        else:
            inv = 255 - a
            self.buf[o] = (r * a + self.buf[o] * inv) // 255
            self.buf[o + 1] = (g * a + self.buf[o + 1] * inv) // 255
            self.buf[o + 2] = (b * a + self.buf[o + 2] * inv) // 255

    def set_px(self, x, y, c):
        self.blend_px(x, y, c[0], c[1], c[2], 255)

    def rect(self, x0, y0, x1, y1, c):
        x0, y0 = max(0, int(x0)), max(0, int(y0))
        x1, y1 = min(self.w, int(x1)), min(self.h, int(y1))
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes((*c, 255)[:self.n]) * (x1 - x0)
        for y in range(y0, y1):
            o = self._off(x0, y)
            self.buf[o:o + len(row)] = row

    def ellipse(self, cx, cy, rx, ry, c):
        rx, ry = float(rx), float(ry)
        for y in range(max(0, int(cy - ry)), min(self.h, int(cy + ry) + 1)):
            dy = (y - cy) / ry
            if abs(dy) > 1:
                continue
            dx = rx * math.sqrt(max(0.0, 1.0 - dy * dy))
            self.rect(cx - dx, y, cx + dx + 1, y + 1, c)

    def circle(self, cx, cy, r, c):
        self.ellipse(cx, cy, r, r, c)

    def rounded_rect(self, x0, y0, x1, y1, r, c, outline=None, outline_w=0):
        if outline is not None and outline_w > 0:
            self.rounded_rect(x0, y0, x1, y1, r, outline)
            self.rounded_rect(x0 + outline_w, y0 + outline_w,
                              x1 - outline_w, y1 - outline_w,
                              max(0, r - outline_w), c)
            return
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        r = max(0, min(r, (x1 - x0) // 2, (y1 - y0) // 2))
        self.rect(x0 + r, y0, x1 - r, y1, c)
        self.rect(x0, y0 + r, x1, y1 - r, c)
        for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r),
                       (x0 + r, y1 - r), (x1 - r, y1 - r)):
            self.circle(cx, cy, r, c)

    def stroke_rounded_rect(self, x0, y0, x1, y1, r, width, c):
        hw = width / 2.0
        self.line(x0 + r, y0, x1 - r, y0, width, c)
        self.line(x0 + r, y1, x1 - r, y1, width, c)
        self.line(x0, y0 + r, x0, y1 - r, width, c)
        self.line(x1, y0 + r, x1, y1 - r, width, c)
        for cx, cy, a0, a1 in ((x0 + r, y0 + r, 180, 270),
                               (x1 - r, y0 + r, 270, 360),
                               (x1 - r, y1 - r, 0, 90),
                               (x0 + r, y1 - r, 90, 180)):
            self.arc(cx, cy, r, r, a0, a1, width, c)

    def line(self, x0, y0, x1, y1, width, c):
        steps = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
        r = width / 2.0
        for i in range(steps + 1):
            t = i / steps
            self.circle(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, r, c)

    def arc(self, cx, cy, rx, ry, start_deg, end_deg, width, c):
        n = max(4, int(abs(end_deg - start_deg) / 3))
        r = width / 2.0
        for i in range(n + 1):
            d = math.radians(start_deg + (end_deg - start_deg) * i / n)
            self.circle(cx + rx * math.cos(d), cy + ry * math.sin(d), r, c)

    def polygon(self, points, c):
        """Even-odd scanline fill of a polygon [(x, y), ...]."""
        if len(points) < 3:
            return
        ys = [p[1] for p in points]
        y0, y1 = int(max(0, math.floor(min(ys)))), int(min(self.h, math.ceil(max(ys))))
        n = len(points)
        for y in range(y0, y1):
            yc = y + 0.5
            xs = []
            for i in range(n):
                x0, y0p = points[i]
                x1, y1p = points[(i + 1) % n]
                if (y0p <= yc < y1p) or (y1p <= yc < y0p):
                    xs.append(x0 + (yc - y0p) * (x1 - x0) / (y1p - y0p))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.rect(xs[i], y, xs[i + 1] + 1, y + 1, c)

    def paste(self, src, dx, dy):
        """Alpha-composite an RGBA Img onto this image at (dx, dy)."""
        for sy in range(src.h):
            ty = dy + sy
            if not (0 <= ty < self.h):
                continue
            for sx in range(src.w):
                tx = dx + sx
                if not (0 <= tx < self.w):
                    continue
                so = src._off(sx, sy)
                a = src.buf[so + 3]
                if a:
                    self.blend_px(tx, ty, src.buf[so], src.buf[so + 1],
                                  src.buf[so + 2], a)

    def paste_rotated(self, src, cx, cy, angle_deg):
        """Paste an RGBA Img rotated angle_deg (clockwise) about its centre
        onto (cx, cy) of this image, with bilinear sampling."""
        th = math.radians(angle_deg)
        cos_t, sin_t = math.cos(th), math.sin(th)
        hw, hh = src.w / 2.0, src.h / 2.0
        corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
        rot = [(x * cos_t - y * sin_t, x * sin_t + y * cos_t) for x, y in corners]
        min_x = int(cx + min(p[0] for p in rot)) - 1
        max_x = int(cx + max(p[0] for p in rot)) + 1
        min_y = int(cy + min(p[1] for p in rot)) - 1
        max_y = int(cy + max(p[1] for p in rot)) + 1
        for ty in range(max(0, min_y), min(self.h, max_y + 1)):
            for tx in range(max(0, min_x), min(self.w, max_x + 1)):
                dx, dy = tx - cx, ty - cy
                sx = dx * cos_t + dy * sin_t + hw
                sy = -dx * sin_t + dy * cos_t + hh
                if not (0 <= sx < src.w - 1 and 0 <= sy < src.h - 1):
                    continue
                x0, y0 = int(sx), int(sy)
                fx, fy = sx - x0, sy - y0
                acc = [0.0, 0.0, 0.0, 0.0]
                for j, wy in ((0, 1 - fy), (1, fy)):
                    for i, wx in ((0, 1 - fx), (1, fx)):
                        o = src._off(x0 + i, y0 + j)
                        a = src.buf[o + 3] / 255.0
                        wgt = wx * wy
                        acc[0] += src.buf[o] * a * wgt
                        acc[1] += src.buf[o + 1] * a * wgt
                        acc[2] += src.buf[o + 2] * a * wgt
                        acc[3] += a * wgt
                if acc[3] > 0.004:
                    a255 = int(acc[3] * 255)
                    self.blend_px(tx, ty, int(acc[0] / acc[3]),
                                  int(acc[1] / acc[3]), int(acc[2] / acc[3]),
                                  a255)

    def save_png(self, path):
        raw = bytearray()
        stride = self.w * 3
        for y in range(self.h):
            raw.append(0)
            o = y * self.w * 3
            raw += self.buf[o:o + stride]

        def chunk(tag, data):
            out = struct.pack(">I", len(data)) + tag + data
            out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
            return out

        ihdr = struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)
        png = b"\x89PNG\r\n\x1a\n"
        png += chunk(b"IHDR", ihdr)
        png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
        png += chunk(b"IEND", b"")
        with open(path, "wb") as f:
            f.write(png)


def _u16(data, off):
    return struct.unpack_from(">H", data, off)[0]


def _i16(data, off):
    return struct.unpack_from(">h", data, off)[0]


def _u32(data, off):
    return struct.unpack_from(">I", data, off)[0]


class Font:
    """Minimal TrueType renderer: cmap (format 12/4), glyf outlines,
    advance widths. Renders glyphs with 4x supersampling for smooth
    edges, then blends the downsampled alpha mask onto an Img."""

    SS = 4

    def __init__(self, path):
        self.data = open(path, "rb").read()
        data = self.data
        n = _u16(data, 4)
        tables = {}
        for i in range(n):
            tag = data[12 + i * 16:16 + i * 16].decode("latin1")
            off, ln = struct.unpack_from(">II", data, 20 + i * 16)
            tables[tag] = (off, ln)
        self.tables = tables
        head = tables["head"][0]
        self.upem = _u16(data, head + 18)
        self.loc_fmt = _i16(data, head + 50)
        self.num_glyphs = _u16(data, tables["maxp"][0] + 4)
        hhea = tables["hhea"][0]
        self.ascent = _i16(data, hhea + 4)
        self.descent = _i16(data, hhea + 6)
        self.num_hmetrics = _u16(data, hhea + 34)
        self._cmap = self._parse_cmap()
        self._glyph_cache = {}

    def _parse_cmap(self):
        data = self.data
        off = self.tables["cmap"][0]
        nsub = _u16(data, off + 2)
        fmt12 = fmt4 = None
        for i in range(nsub):
            sub = off + _u32(data, off + 4 + i * 8 + 4)
            fmt = _u16(data, sub)
            if fmt == 12 and fmt12 is None:
                fmt12 = sub
            elif fmt == 4 and fmt4 is None:
                fmt4 = sub
        if fmt12 is not None:
            groups = []
            ng = _u32(data, fmt12 + 12)
            for g in range(ng):
                s, e, gid = struct.unpack_from(">III", data, fmt12 + 16 + g * 12)
                groups.append((s, e, gid))
            return ("12", groups)
        seg_count = _u16(data, fmt4 + 6) // 2
        end_base = fmt4 + 14
        start_base = end_base + 2 * seg_count + 2
        delta_base = start_base + 2 * seg_count
        range_base = delta_base + 2 * seg_count
        segs = []
        for i in range(seg_count):
            end = _u16(data, end_base + 2 * i)
            start = _u16(data, start_base + 2 * i)
            delta = _i16(data, delta_base + 2 * i)
            roff = _u16(data, range_base + 2 * i)
            segs.append((start, end, delta, roff, range_base + 2 * i))
        return ("4", (segs, fmt4))

    def glyph_id(self, cp):
        kind, payload = self._cmap
        if kind == "12":
            for s, e, gid in payload:
                if s <= cp <= e:
                    return gid + (cp - s)
            return 0
        segs, fmt4 = payload
        for start, end, delta, roff, roff_addr in segs:
            if start <= cp <= end:
                if roff == 0:
                    return (cp + delta) % 65536
                idx = roff_addr + roff + 2 * (cp - start)
                return (_u16(self.data, idx) + delta) % 65536
        return 0

    def advance(self, gid):
        data = self.data
        off = self.tables["hmtx"][0]
        if gid < self.num_hmetrics:
            return _u16(data, off + gid * 4)
        return _u16(data, off + (self.num_hmetrics - 1) * 4)

    def _glyph_offset(self, gid):
        data = self.data
        off, _ = self.tables["loca"]
        if self.loc_fmt == 1:
            a = _u32(data, off + gid * 4)
            b = _u32(data, off + (gid + 1) * 4)
        else:
            a = _u16(data, off + gid * 2) * 2
            b = _u16(data, off + (gid + 1) * 2) * 2
        return self.tables["glyf"][0] + a, b - a

    def outline(self, gid):
        """Return (contours, advance): contours are lists of (x, y) points
        in font units, already flattened (quadratic curves subdivided)."""
        if gid in self._glyph_cache:
            return self._glyph_cache[gid]
        data = self.data
        goff, glen = self._glyph_offset(gid)
        if glen <= 0:
            result = ([], self.advance(gid))
            self._glyph_cache[gid] = result
            return result
        n_contours = _i16(data, goff)
        if n_contours < 0:
            contours = self._composite_outline(goff)
        else:
            contours = self._simple_outline(goff, n_contours)
        result = (contours, self.advance(gid))
        self._glyph_cache[gid] = result
        return result

    def _composite_outline(self, goff):
        data = self.data
        contours = []
        p = goff + 10
        while True:
            flags, comp_gid = struct.unpack_from(">HH", data, p)
            p += 4
            if flags & 0x0001:
                dx, dy = struct.unpack_from(">hh", data, p)
                p += 4
            else:
                dx, dy = struct.unpack_from(">bb", data, p)
                p += 2
            scale_x = scale_y = 1.0
            if flags & 0x0008:
                scale_x = scale_y = _i16(data, p) / 16384.0
                p += 2
            elif flags & 0x0040:
                scale_x = _i16(data, p) / 16384.0
                scale_y = _i16(data, p + 2) / 16384.0
                p += 4
            elif flags & 0x0080:
                p += 8
            sub, _ = self.outline(comp_gid)
            for contour in sub:
                contours.append([(x * scale_x + dx, y * scale_y + dy)
                                 for x, y in contour])
            if not (flags & 0x0020):
                break
        return contours

    def _simple_outline(self, goff, n_contours):
        data = self.data
        ends = [_u16(data, goff + 10 + 2 * i) for i in range(n_contours)]
        n_points = ends[-1] + 1 if ends else 0
        p = goff + 10 + 2 * n_contours
        instr_len = _u16(data, p)
        p += 2 + instr_len
        flags = []
        while len(flags) < n_points:
            f = data[p]
            p += 1
            flags.append(f)
            if f & 0x08:
                rep = data[p]
                p += 1
                flags.extend([f] * rep)
        xs = []
        x = 0
        for f in flags:
            if f & 0x02:
                dx = data[p]
                p += 1
                x += dx if (f & 0x10) else -dx
            elif not (f & 0x10):
                x += _i16(data, p)
                p += 2
            xs.append(x)
        ys = []
        y = 0
        for f in flags:
            if f & 0x04:
                dy = data[p]
                p += 1
                y += dy if (f & 0x20) else -dy
            elif not (f & 0x20):
                y += _i16(data, p)
                p += 2
            ys.append(y)
        on = [bool(f & 0x01) for f in flags]
        contours = []
        start = 0
        for end in ends:
            pts = list(zip(xs[start:end + 1], ys[start:end + 1]))
            ons = on[start:end + 1]
            contours.append(self._flatten_contour(pts, ons))
            start = end + 1
        return contours

    @staticmethod
    def _flatten_contour(pts, ons):
        """Walk a TrueType contour, subdividing quadratic curves into a
        polygon. pts/ons are parallel lists (point, on-curve flag)."""
        n = len(pts)
        if n == 0:
            return []
        if n == 1:
            return [pts[0]]
        start = None
        for i in range(n):
            if ons[i]:
                start = i
                break
        if start is None:
            # all points off-curve: implied on-curve point between the
            # last and first points starts the contour
            seq_pts = [_mid(pts[-1], pts[0])] + list(pts)
            seq_ons = [True] + list(ons)
            return Font._flatten_contour(seq_pts, seq_ons)
        pts = pts[start:] + pts[:start]
        ons = ons[start:] + ons[:start]
        out = [pts[0]]
        last_on = pts[0]
        ctrl = None
        for pt, is_on in list(zip(pts[1:], ons[1:])) + [(pts[0], True)]:
            if is_on:
                if ctrl is not None:
                    out.extend(_quad(last_on, ctrl, pt))
                    ctrl = None
                else:
                    out.append(pt)
                last_on = pt
            else:
                if ctrl is not None:
                    mid = _mid(ctrl, pt)
                    out.extend(_quad(last_on, ctrl, mid))
                    last_on = mid
                ctrl = pt
        return out

    def measure(self, text, size):
        scale = size / self.upem
        return sum(self.advance(self.glyph_id(ord(ch))) * scale
                   for ch in text)

    def draw_text(self, img, x, y_top, text, size, color, anchor="l"):
        """Draw text with its top at y_top; x is left (anchor 'l') or
        centre (anchor 'c'). y_top is the top of the em box."""
        scale = size / self.upem
        width = self.measure(text, size)
        pen = x - width / 2.0 if anchor == "c" else x
        baseline = y_top + self.ascent * scale
        ss = self.SS
        for ch in text:
            gid = self.glyph_id(ord(ch))
            contours, adv = self.outline(gid)
            if contours:
                polys = []
                min_x = min_y = 1e18
                max_x = max_y = -1e18
                for contour in contours:
                    poly = []
                    for px, py in contour:
                        fx = px * scale * ss
                        fy = (self.ascent - py) * scale * ss
                        poly.append((fx, fy))
                        min_x, max_x = min(min_x, fx), max(max_x, fx)
                        min_y, max_y = min(min_y, fy), max(max_y, fy)
                    polys.append(poly)
                # pixel bbox of this glyph in image coordinates
                px_min, px_max = pen + min_x / ss, pen + max_x / ss
                py_min, py_max = y_top + min_y / ss, y_top + max_y / ss
                bx0 = int(math.floor(px_min))
                by0 = int(math.floor(py_min))
                bw = int(math.ceil(px_max)) - bx0 + 2
                bh = int(math.ceil(py_max)) - by0 + 2
                if bw > 0 and bh > 0:
                    # shift polys into the mask's local frame
                    sh_x = (pen - bx0) * ss
                    sh_y = (y_top - by0) * ss
                    local = [[(x + sh_x, y + sh_y) for x, y in poly]
                             for poly in polys]
                    mask = self._rasterize(local, bw, bh)
                    for my in range(bh):
                        for mx in range(bw):
                            a = mask[my * bw + mx]
                            if a:
                                img.blend_px(bx0 + mx, by0 + my,
                                             color[0], color[1], color[2], a)
            pen += adv * scale

    def _rasterize(self, polys, bw, bh):
        """Even-odd scanline fill of polygons given in supersampled
        coordinates local to the mask's top-left corner; returns a
        downsampled alpha mask (bw x bh bytes)."""
        ss = self.SS
        hi_w, hi_h = bw * ss, bh * ss
        hi = bytearray(hi_w * hi_h)
        for poly in polys:
            ys = [p[1] for p in poly]
            y_lo = max(0, int(math.floor(min(ys))))
            y_hi = min(hi_h, int(math.ceil(max(ys))))
            n = len(poly)
            for y in range(y_lo, y_hi):
                yc = y + 0.5
                xs = []
                for i in range(n):
                    x0, y0 = poly[i]
                    x1, y1 = poly[(i + 1) % n]
                    if (y0 <= yc < y1) or (y1 <= yc < y0):
                        xs.append(x0 + (yc - y0) * (x1 - x0) / (y1 - y0))
                xs.sort()
                for i in range(0, len(xs) - 1, 2):
                    xa = max(0, int(math.floor(xs[i])))
                    xb = min(hi_w, int(math.ceil(xs[i + 1])))
                    base = y * hi_w
                    for xx in range(xa, xb):
                        hi[base + xx] = 255
        mask = bytearray(bw * bh)
        for my in range(bh):
            for mx in range(bw):
                total = 0
                for sy in range(ss):
                    row = (my * ss + sy) * hi_w + mx * ss
                    total += sum(hi[row:row + ss])
                mask[my * bw + mx] = total // (ss * ss)
        return mask


def _mid(a, b):
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def _quad(p0, p1, p2, steps=12):
    """Subdivide a quadratic Bezier, returning intermediate points."""
    out = []
    for i in range(1, steps):
        t = i / steps
        mt = 1 - t
        out.append((mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0],
                    mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1]))
    out.append(p2)
    return out


_FONT = None


def get_font():
    global _FONT
    if _FONT is None:
        here = os.path.dirname(os.path.abspath(__file__))
        for path in (os.path.join(here, "DejaVuSans-Bold.ttf"),
                     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
            try:
                _FONT = Font(path)
                break
            except Exception:
                continue
        if _FONT is None:
            raise RuntimeError("DejaVuSans-Bold.ttf not found")
    return _FONT


def fit_size(lines, max_width, start_size):
    font = get_font()
    size = start_size
    while size > 20 and any(font.measure(line, size) > max_width
                            for line in lines):
        size -= 2
    return size


def draw_centered(img, cx, y, lines, size, color):
    font = get_font()
    line_h = int(size * 1.12)
    for line in lines:
        font.draw_text(img, cx, y, line, size, color, anchor="c")
        y += line_h
    return y


def draw_robot(img, cx, cy, s, arm="up", body=TEAL):
    """Flat-vector AI agent: dome head, antenna, screen face, happy eyes.

    (cx, cy) is the centre of the body. s scales the robot (~1.0 = 200px).
    arm: 'up' (thumbs up), 'wave', 'point', 'stamp' (left arm out)."""
    bw, bh = int(200 * s), int(210 * s)
    x0, y0 = cx - bw // 2, cy - bh // 2
    x1, y1 = cx + bw // 2, cy + bh // 2
    # antenna
    img.line(cx, y0 - 58 * s, cx, y0 - 6 * s, int(8 * s), INK)
    img.circle(cx, y0 - 69 * s, 16 * s, INK)
    img.circle(cx, y0 - 69 * s, 13 * s, RED)
    # head dome
    img.rounded_rect(x0 + 14 * s, y0 - 78 * s, x1 - 14 * s, y0 + 62 * s,
                     int(52 * s), body, outline=INK, outline_w=int(5 * s))
    # screen face
    img.rounded_rect(x0 + 30 * s, y0 - 58 * s, x1 - 30 * s, y0 + 42 * s,
                     int(24 * s), SCREEN)
    # happy eyes: upward arcs
    for ex in (-42 * s, 42 * s):
        img.arc(cx + ex, y0 - 14 * s, 22 * s, 20 * s, 180, 360,
                int(9 * s), WHITE)
    # smile
    img.arc(cx, y0 + 16 * s, 34 * s, 22 * s, 10, 170, int(8 * s), WHITE)
    # ears
    for ex in (x0 - 4 * s, x1 - 22 * s):
        img.rounded_rect(ex, y0 - 30 * s, ex + 26 * s, y0 + 6 * s,
                         int(10 * s), GOLD, outline=INK, outline_w=int(3 * s))
    # body
    img.rounded_rect(x0, y0 + 58 * s, x1, y1, int(34 * s), body,
                     outline=INK, outline_w=int(5 * s))
    # chest light
    img.ellipse(cx, y0 + 122 * s, 29 * s, 29 * s, INK)
    img.ellipse(cx, y0 + 122 * s, 26 * s, 26 * s, YELLOW)
    img.ellipse(cx, y0 + 122 * s, 12 * s, 12 * s, RED)
    # arms
    lw = int(16 * s)

    def hand(hx, hy):
        img.circle(hx, hy, int(17 * s), INK)
        img.circle(hx, hy, int(14 * s), body)

    if arm == "up":
        img.line(x0 + 6 * s, y0 + 96 * s, x0 - 42 * s, y0 + 150 * s, lw, body)
        hand(x0 - 42 * s, y0 + 150 * s)
        img.line(x1 - 6 * s, y0 + 96 * s, x1 + 44 * s, y0 + 30 * s, lw, body)
        hand(x1 + 45 * s, y0 + 23 * s)
        img.line(x1 + 45 * s, y0 + 8 * s, x1 + 45 * s, y0 - 22 * s,
                 int(12 * s), body)
        img.circle(x1 + 45 * s, y0 - 22 * s, int(14 * s), INK)
        img.circle(x1 + 45 * s, y0 - 22 * s, int(11 * s), body)
    elif arm == "wave":
        img.line(x0 + 6 * s, y0 + 96 * s, x0 - 42 * s, y0 + 150 * s, lw, body)
        hand(x0 - 42 * s, y0 + 150 * s)
        img.line(x1 - 6 * s, y0 + 96 * s, x1 + 48 * s, y0 + 10 * s, lw, body)
        hand(x1 + 49 * s, y0 + 3 * s)
        for dx in (-8, 8):
            img.line(x1 + 48 * s + dx, y0 - 12 * s, x1 + 48 * s + dx,
                     y0 - 44 * s, int(9 * s), body)
    elif arm == "point":
        img.line(x0 + 6 * s, y0 + 96 * s, x0 - 42 * s, y0 + 150 * s, lw, body)
        hand(x0 - 42 * s, y0 + 150 * s)
        img.line(x1 - 6 * s, y0 + 110 * s, x1 + 74 * s, y0 + 110 * s, lw, body)
        hand(x1 + 75 * s, y0 + 110 * s)
    elif arm == "stamp":
        # left arm extended toward the card being stamped
        img.line(x1 - 6 * s, y0 + 96 * s, x1 + 42 * s, y0 + 150 * s, lw, body)
        hand(x1 + 42 * s, y0 + 150 * s)
        img.line(x0 + 6 * s, y0 + 110 * s, x0 - 70 * s, y0 + 118 * s, lw, body)
        hand(x0 - 71 * s, y0 + 118 * s)
    # legs
    for lx in (cx - 52 * s, cx + 52 * s):
        img.line(lx, y1 - 6 * s, lx, y1 + 34 * s, int(14 * s), INK)
        img.ellipse(lx, y1 + 34 * s, 26 * s, 12 * s, INK)


def scene_a(img):
    """Agent cancelled the wedding: robot stamps CANCELLED on the invite."""
    font = get_font()
    # wedding invitation card (drawn on its own layer, then tilted)
    card = Img(520, 380, (0, 0, 0), alpha=True)
    card.rounded_rect(10, 10, 510, 370, 28, WHITE, outline=INK, outline_w=6)
    card.rounded_rect(28, 28, 492, 120, 18, PINK)
    font.draw_text(card, 260, 46, "YOU'RE INVITED", 44, INK, anchor="c")
    for rcx in (205, 295):
        card.circle(rcx, 225, 55, GOLD)
        card.circle(rcx, 225, 41, WHITE)
    for hx in (170, 330):
        card.circle(hx - 8, 296, 15, RED)
        card.circle(hx + 8, 296, 15, RED)
        card.polygon([(hx - 21, 300), (hx + 21, 300), (hx, 330)], RED)
    img.paste_rotated(card, 330, 590, 6)
    # red CANCELLED stamp
    stamp = Img(560, 170, (0, 0, 0), alpha=True)
    stamp.stroke_rounded_rect(8, 8, 552, 162, 22, 12, RED)
    font.draw_text(stamp, 280, 30, "CANCELLED", 96, RED, anchor="c")
    img.paste_rotated(stamp, 390, 585, 16)
    draw_robot(img, 800, 560, 1.05, arm="stamp")


def main():
    top_lines = ["I TOLD MY AI AGENT TO", "CANCEL MY SUBSCRIPTIONS"]
    punch_lines = ["IT CANCELLED", "MY WEDDING."]
    img = Img(W, H, CREAM)
    # top text
    size_top = fit_size(top_lines, 960, 62)
    y = 36
    y = draw_centered(img, W // 2, y, top_lines, size_top, INK)
    # red divider under the top text
    img.rect(W // 2 - 130, y + 18, W // 2 + 130, y + 26, RED)
    # scene
    scene_a(img)
    # punchline band
    img.rect(0, 812, W, H, RED)
    img.rect(0, 812, W, 820, RED_DARK)
    size_punch = fit_size(punch_lines, 960, 78)
    total_h = int(size_punch * 1.12 * len(punch_lines))
    py = 812 + (212 - total_h) // 2
    draw_centered(img, W // 2, py, punch_lines, size_punch, WHITE)
    os.makedirs("/output", exist_ok=True)
    img.save_png("/output/entry.png")
    size = os.path.getsize("/output/entry.png")
    print(f"variant A (stdlib): /output/entry.png {W}x{H} {size} bytes")


if __name__ == "__main__":
    main()
