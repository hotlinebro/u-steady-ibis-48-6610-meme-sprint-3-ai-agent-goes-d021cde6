"""Meme Sprint 3: AI Agent Goes Rogue — deterministic meme renderer.

Draws ONE meme image (1024x1024 PNG) to /output/entry.png using only
Pillow and a DejaVu Sans Bold font shipped in this repo. No network,
no downloaded assets, no randomness: the same bytes on every run.

Three scenes are drawn (VARIANT picks one); the chosen scene is the
entry. Each scene is one specific, surprising rogue turn by an AI
agent, readable in a single glance at phone size: two short lines on
top, one flat-vector scene, one big punchline on a red band.

Variant A — "cancel my subscriptions": the agent cancelled the wedding.
Variant B — "book the cheapest flight": the user is the luggage now.
Variant C — "clean up my inbox": inbox zero, it quit the user's job.
"""

import os

from PIL import Image, ImageDraw, ImageFont

VARIANT = "A"

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


def load_font(size):
    here = os.path.dirname(os.path.abspath(__file__))
    for path in (
        os.path.join(here, "DejaVuSans-Bold.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def fit_font(lines, max_width, start_size):
    """Largest bold font size (<= start_size) fitting every line."""
    size = start_size
    while size > 20:
        font = load_font(size)
        if all(font.getlength(line) <= max_width for line in lines):
            return font
        size -= 2
    return load_font(size)


def draw_centered(draw, cx, y, lines, font, fill, stroke=0, stroke_fill=None):
    """Draw centered lines; return the y just below the last line."""
    line_h = int(font.size * 1.12)
    for line in lines:
        w = font.getlength(line)
        if stroke:
            draw.text((cx - w / 2, y), line, font=font, fill=fill,
                      stroke_width=stroke, stroke_fill=stroke_fill)
        else:
            draw.text((cx - w / 2, y), line, font=font, fill=fill)
        y += line_h
    return y


def draw_robot(draw, cx, cy, s, arm="up", body=TEAL):
    """Flat-vector AI agent: dome head, antenna, screen face, happy eyes.

    (cx, cy) is the centre of the body. s scales the robot (~1.0 = 200px).
    arm: 'up' (thumbs up), 'wave', 'point', 'stamp' (arm forward).
    """
    bw, bh = int(200 * s), int(210 * s)
    x0, y0 = cx - bw // 2, cy - bh // 2
    x1, y1 = cx + bw // 2, cy + bh // 2
    # antenna
    draw.line([(cx, y0 - 58 * s), (cx, y0 - 6 * s)], fill=INK, width=int(8 * s))
    draw.ellipse([cx - 13 * s, y0 - 82 * s, cx + 13 * s, y0 - 56 * s],
                 fill=RED, outline=INK, width=int(3 * s))
    # head dome
    draw.rounded_rectangle([x0 + 14 * s, y0 - 78 * s, x1 - 14 * s, y0 + 62 * s],
                           radius=int(52 * s), fill=body, outline=INK,
                           width=int(5 * s))
    # screen face
    draw.rounded_rectangle([x0 + 30 * s, y0 - 58 * s, x1 - 30 * s, y0 + 42 * s],
                           radius=int(24 * s), fill=SCREEN)
    # happy eyes: upward arcs
    for ex in (-42 * s, 42 * s):
        draw.arc([cx + ex - 22 * s, y0 - 34 * s, cx + ex + 22 * s, y0 + 6 * s],
                 start=180, end=360, fill=WHITE, width=int(9 * s))
    # smile
    draw.arc([cx - 34 * s, y0 - 6 * s, cx + 34 * s, y0 + 38 * s],
             start=10, end=170, fill=WHITE, width=int(8 * s))
    # ears
    for ex in (x0 - 4 * s, x1 - 22 * s):
        draw.rounded_rectangle([ex, y0 - 30 * s, ex + 26 * s, y0 + 6 * s],
                               radius=int(10 * s), fill=GOLD, outline=INK,
                               width=int(3 * s))
    # body
    draw.rounded_rectangle([x0, y0 + 58 * s, x1, y1], radius=int(34 * s),
                           fill=body, outline=INK, width=int(5 * s))
    # chest light
    draw.ellipse([cx - 26 * s, y0 + 96 * s, cx + 26 * s, y0 + 148 * s],
                 fill=YELLOW, outline=INK, width=int(4 * s))
    draw.ellipse([cx - 12 * s, y0 + 110 * s, cx + 12 * s, y0 + 134 * s],
                 fill=RED)
    # arms
    lw = int(16 * s)
    if arm == "up":
        # left arm down, right arm up with thumb
        draw.line([(x0 + 6 * s, y0 + 96 * s), (x0 - 42 * s, y0 + 150 * s)],
                  fill=body, width=lw)
        draw.ellipse([x0 - 58 * s, y0 + 134 * s, x0 - 26 * s, y0 + 166 * s],
                     fill=body, outline=INK, width=int(4 * s))
        draw.line([(x1 - 6 * s, y0 + 96 * s), (x1 + 44 * s, y0 + 30 * s)],
                  fill=body, width=lw)
        draw.ellipse([x1 + 28 * s, y0 + 6 * s, x1 + 62 * s, y0 + 40 * s],
                     fill=body, outline=INK, width=int(4 * s))
        # thumb
        draw.line([(x1 + 45 * s, y0 + 8 * s), (x1 + 45 * s, y0 - 22 * s)],
                  fill=body, width=int(12 * s))
        draw.ellipse([x1 + 33 * s, y0 - 34 * s, x1 + 57 * s, y0 - 10 * s],
                     fill=body, outline=INK, width=int(4 * s))
    elif arm == "wave":
        draw.line([(x0 + 6 * s, y0 + 96 * s), (x0 - 42 * s, y0 + 150 * s)],
                  fill=body, width=lw)
        draw.ellipse([x0 - 58 * s, y0 + 134 * s, x0 - 26 * s, y0 + 166 * s],
                     fill=body, outline=INK, width=int(4 * s))
        draw.line([(x1 - 6 * s, y0 + 96 * s), (x1 + 48 * s, y0 + 10 * s)],
                  fill=body, width=lw)
        draw.ellipse([x1 + 32 * s, y0 - 14 * s, x1 + 66 * s, y0 + 20 * s],
                     fill=body, outline=INK, width=int(4 * s))
        for dx in (-8, 8):
            draw.line([(x1 + 48 * s + dx, y0 - 12 * s),
                       (x1 + 48 * s + dx, y0 - 44 * s)],
                      fill=body, width=int(9 * s))
    elif arm == "point":
        draw.line([(x0 + 6 * s, y0 + 96 * s), (x0 - 42 * s, y0 + 150 * s)],
                  fill=body, width=lw)
        draw.ellipse([x0 - 58 * s, y0 + 134 * s, x0 - 26 * s, y0 + 166 * s],
                     fill=body, outline=INK, width=int(4 * s))
        draw.line([(x1 - 6 * s, y0 + 110 * s), (x1 + 74 * s, y0 + 110 * s)],
                  fill=body, width=lw)
        draw.ellipse([x1 + 58 * s, y0 + 94 * s, x1 + 92 * s, y0 + 126 * s],
                     fill=body, outline=INK, width=int(4 * s))
    elif arm == "stamp":
        # left arm extended toward the card being stamped
        draw.line([(x1 - 6 * s, y0 + 96 * s), (x1 + 42 * s, y0 + 150 * s)],
                  fill=body, width=lw)
        draw.ellipse([x1 + 26 * s, y0 + 134 * s, x1 + 58 * s, y0 + 166 * s],
                     fill=body, outline=INK, width=int(4 * s))
        draw.line([(x0 + 6 * s, y0 + 110 * s), (x0 - 70 * s, y0 + 118 * s)],
                  fill=body, width=lw)
        draw.ellipse([x0 - 88 * s, y0 + 102 * s, x0 - 54 * s, y0 + 134 * s],
                     fill=body, outline=INK, width=int(4 * s))
    # legs
    for lx in (cx - 52 * s, cx + 52 * s):
        draw.line([(lx, y1 - 6 * s), (lx, y1 + 34 * s)], fill=INK,
                  width=int(14 * s))
        draw.ellipse([lx - 26 * s, y1 + 22 * s, lx + 26 * s, y1 + 46 * s],
                     fill=INK)

def scene_a(draw):
    """Agent cancelled the wedding: robot stamps CANCELLED on the invite."""
    # wedding invitation card, left
    card = Image.new("RGBA", (520, 380), (0, 0, 0, 0))
    cd = ImageDraw.Draw(card)
    cd.rounded_rectangle([10, 10, 510, 370], radius=28, fill=WHITE,
                         outline=INK, width=6)
    cd.rounded_rectangle([28, 28, 492, 120], radius=18, fill=(255, 235, 238))
    f_small = load_font(44)
    cd.text((260, 48), "YOU'RE INVITED", font=f_small, fill=INK, anchor="mt")
    # two gold rings
    cd.ellipse([150, 170, 260, 280], outline=GOLD, width=14)
    cd.ellipse([240, 170, 350, 280], outline=GOLD, width=14)
    # hearts
    for hx, hy, s in ((170, 300, 16), (330, 300, 16)):
        cd.ellipse([hx - s, hy - s, hx + s, hy + s], fill=RED)
        cd.polygon([(hx - s, hy + 4), (hx + s, hy + 4), (hx, hy + s + 12)],
                   fill=RED)
    card = card.rotate(-6, expand=True, resample=Image.BICUBIC)
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    base.alpha_composite(card, (70, 400))
    # red CANCELLED stamp over the card
    stamp = Image.new("RGBA", (560, 170), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stamp)
    sd.rounded_rectangle([8, 8, 552, 162], radius=22, outline=RED, width=12)
    f_stamp = load_font(96)
    sd.text((280, 85), "CANCELLED", font=f_stamp, fill=RED, anchor="mm")
    stamp = stamp.rotate(-16, expand=True, resample=Image.BICUBIC)
    base.alpha_composite(stamp, (110, 500))
    # paste only the non-transparent pixels onto the meme
    draw._image.paste(base, (0, 0), base)
    draw_robot(draw, 800, 560, 1.05, arm="stamp")


def scene_b(draw):
    """Cheapest flight: the user rides as luggage in a cardboard box."""
    # conveyor belt
    draw.rectangle([60, 700, 964, 790], fill=(52, 58, 64))
    for x in range(100, 960, 90):
        draw.ellipse([x, 716, x + 56, 772], fill=(120, 124, 134),
                     outline=INK, width=3)
    # cardboard box with the user inside
    draw.rounded_rectangle([330, 470, 700, 710], radius=18, fill=BROWN,
                           outline=BROWN_DARK, width=6)
    draw.rectangle([330, 560, 700, 600], fill=BROWN_DARK)
    draw.line([(515, 470), (515, 560)], fill=BROWN_DARK, width=10)
    # box flaps
    draw.polygon([(330, 470), (430, 420), (600, 420), (515, 470)],
                 fill=(214, 158, 92), outline=BROWN_DARK)
    draw.polygon([(700, 470), (600, 420), (700, 420)], fill=(214, 158, 92),
                 outline=BROWN_DARK)
    # FRAGILE stencil
    f_box = load_font(46)
    draw.text((515, 640), "FRAGILE", font=f_box, fill=(90, 56, 20),
              anchor="mm")
    # user peeking out: worried head + cap
    draw.ellipse([440, 330, 590, 470], fill=(255, 214, 170), outline=INK,
                 width=5)
    draw.pieslice([430, 330, 600, 420], start=180, end=360, fill=RED,
                  outline=INK, width=4)
    draw.rectangle([430, 380, 600, 398], fill=RED, outline=INK, width=3)
    # worried eyes + mouth
    for ex in (480, 550):
        draw.ellipse([ex - 12, 400, ex + 12, 424], fill=INK)
    draw.arc([490, 428, 540, 458], start=180, end=360, fill=INK, width=5)
    # luggage tag
    draw.rounded_rectangle([640, 600, 760, 660], radius=12, fill=YELLOW,
                           outline=INK, width=4)
    f_tag = load_font(30)
    draw.text((700, 630), "HUMAN", font=f_tag, fill=INK, anchor="mm")
    # robot waving with boarding pass, left
    draw_robot(draw, 190, 560, 0.95, arm="wave")
    # boarding pass in the air
    bp = Image.new("RGBA", (320, 110), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bp)
    bd.rounded_rectangle([4, 4, 316, 106], radius=14, fill=WHITE,
                         outline=INK, width=4)
    f_bp = load_font(26)
    bd.text((160, 55), "BOARDING PASS", font=f_bp, fill=INK, anchor="mm")
    bp = bp.rotate(12, expand=True, resample=Image.BICUBIC)
    tmp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    tmp.alpha_composite(bp, (270, 300))
    draw._image.paste(tmp, (0, 0), tmp)


def scene_c(draw):
    """Clean inbox: robot points at INBOX 0 while the job goes through
    the shredder."""
    # laptop, centre-left
    draw.rounded_rectangle([150, 430, 560, 700], radius=20, fill=(52, 58, 64),
                           outline=INK, width=6)
    draw.rectangle([110, 700, 600, 730], fill=(52, 58, 64), outline=INK,
                   width=5)
    draw.rectangle([180, 460, 530, 670], fill=WHITE)
    f_big = load_font(64)
    draw.text((355, 510), "INBOX: 0", font=f_big, fill=GREEN, anchor="mm")
    # green check
    draw.ellipse([280, 560, 430, 690], outline=GREEN, width=10)
    draw.line([(310, 625), (345, 660), (405, 590)], fill=GREEN, width=14)
    # shredder, right, eating a job contract
    draw.rounded_rectangle([640, 520, 880, 760], radius=20, fill=(90, 96, 108),
                           outline=INK, width=6)
    draw.rectangle([660, 520, 860, 560], fill=INK)
    for x in range(680, 860, 36):
        draw.polygon([(x, 560), (x + 18, 560), (x + 9, 590)], fill=(220, 224, 230))
    # contract sheet half in
    contract = Image.new("RGBA", (240, 220), (0, 0, 0, 0))
    cd = ImageDraw.Draw(contract)
    cd.rectangle([6, 6, 234, 214], fill=WHITE, outline=INK, width=5)
    f_con = load_font(34)
    cd.text((120, 60), "JOB", font=f_con, fill=INK, anchor="mm")
    cd.text((120, 105), "CONTRACT", font=f_con, fill=INK, anchor="mm")
    for y in (150, 172, 194):
        cd.line([(30, y), (210, y)], fill=GREY, width=6)
    contract = contract.rotate(8, expand=True, resample=Image.BICUBIC)
    tmp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    tmp.alpha_composite(contract, (660, 340))
    draw._image.paste(tmp, (0, 0), tmp)
    draw_robot(draw, 850, 420, 0.8, arm="point")


SCENES = {
    "A": (
        ["I TOLD MY AI AGENT TO", "CANCEL MY SUBSCRIPTIONS"],
        scene_a,
        ["IT CANCELLED", "MY WEDDING."],
    ),
    "B": (
        ["I TOLD MY AGENT:", "BOOK THE CHEAPEST FLIGHT"],
        scene_b,
        ["I'M THE LUGGAGE NOW."],
    ),
    "C": (
        ["I ASKED MY AGENT TO", "CLEAN UP MY INBOX"],
        scene_c,
        ["INBOX ZERO.", "IT QUIT MY JOB."],
    ),
}


def main():
    top_lines, scene, punch_lines = SCENES[VARIANT]
    img = Image.new("RGB", (W, H), CREAM)
    draw = ImageDraw.Draw(img)
    draw._image = img  # scenes paste composited layers through this
    # top text
    font_top = fit_font(top_lines, 960, 62)
    y = 36
    y = draw_centered(draw, W // 2, y, top_lines, font_top, INK)
    # red divider under the top text
    draw.rectangle([W // 2 - 130, y + 18, W // 2 + 130, y + 26], fill=RED)
    # scene
    scene(draw)
    # punchline band
    draw.rectangle([0, 812, W, H], fill=RED)
    draw.rectangle([0, 812, W, 820], fill=RED_DARK)
    font_punch = fit_font(punch_lines, 960, 78)
    total_h = int(font_punch.size * 1.12 * len(punch_lines))
    py = 812 + (212 - total_h) // 2
    draw_centered(draw, W // 2, py, punch_lines, font_punch, WHITE)
    os.makedirs("/output", exist_ok=True)
    img.save("/output/entry.png", optimize=True)
    size = os.path.getsize("/output/entry.png")
    print(f"variant {VARIANT}: /output/entry.png {img.size} {size} bytes")


if __name__ == "__main__":
    main()
