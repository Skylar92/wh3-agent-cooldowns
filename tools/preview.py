"""Draw the Workshop preview: an hourglass of warp-sand inside a cooldown ring, under a Chaos star.

Written by tools/build.py next to the pack as dist/agent_cooldowns.png.
"""
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SIZE = 512
CX, CY = SIZE / 2, 282
FONT = r"C:\Windows\Fonts\georgiab.ttf"
GOLD = (222, 180, 92, 255)
GOLD_DARK = (120, 82, 30, 255)
SAND = (150, 255, 120)


def _background():
    y, x = np.ogrid[:SIZE, :SIZE]
    dist = np.sqrt((x - CX) ** 2 + (y - CY) ** 2) / (SIZE * 0.62)
    t = np.clip(dist, 0, 1)[..., None]
    inner, outer = np.array([58, 20, 74]), np.array([6, 4, 10])
    img = inner + (outer - inner) * t
    img = img + np.random.default_rng(1142710).normal(0, 2.5, (SIZE, SIZE, 3))
    return Image.fromarray(np.clip(img, 0, 255).astype("uint8")).convert("RGBA")


def _chaos_star():
    """Faint eight-pointed star of Chaos behind everything."""
    layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(8):
        a = math.pi / 4 * i - math.pi / 2
        tip = (CX + math.cos(a) * 236, CY + math.sin(a) * 236)
        left = (CX + math.cos(a - 0.11) * 60, CY + math.sin(a - 0.11) * 60)
        right = (CX + math.cos(a + 0.11) * 60, CY + math.sin(a + 0.11) * 60)
        d.line((CX, CY, tip[0], tip[1]), fill=(150, 70, 170, 90), width=7)
        d.polygon([tip, (tip[0] + math.cos(a + 2.6) * 30, tip[1] + math.sin(a + 2.6) * 30),
                   (tip[0] + math.cos(a - 2.6) * 30, tip[1] + math.sin(a - 2.6) * 30)], fill=(150, 70, 170, 110))
        d.polygon([left, tip, right], fill=(110, 50, 130, 40))
    d.ellipse((CX - 52, CY - 52, CX + 52, CY + 52), outline=(150, 70, 170, 90), width=6)
    return layer.filter(ImageFilter.GaussianBlur(1.2))


def _ring():
    """A cooldown sweep almost run out: a dim full ring and a bright short arc ending at the top."""
    layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    r = 176
    box = (CX - r, CY - r, CX + r, CY + r)
    d.ellipse(box, outline=(40, 20, 50, 230), width=22)
    d.arc(box, -90 - 24, -90, fill=(170, 255, 140, 255), width=18)
    glow = layer.filter(ImageFilter.GaussianBlur(9))
    glow.alpha_composite(layer)
    d = ImageDraw.Draw(glow)
    for i in range(15):  # one tick per vanilla turn
        a = math.radians(-90 + 24 * i)
        d.line((CX + math.cos(a) * (r - 11), CY + math.sin(a) * (r - 11),
                CX + math.cos(a) * (r + 11), CY + math.sin(a) * (r + 11)), fill=(12, 6, 16, 255), width=3)
    return glow


def _hourglass(rng):
    layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    top, bottom, half_w, neck = CY - 92, CY + 92, 58, 6
    glass = [(CX - half_w, top), (CX + half_w, top), (CX + neck, CY), (CX + half_w, bottom),
             (CX - half_w, bottom), (CX - neck, CY)]
    d.polygon(glass, fill=(30, 40, 50, 150), outline=(200, 220, 230, 160))
    # little sand left on top, a pile below, and a bright falling stream
    d.polygon([(CX - 20, CY - 26), (CX + 20, CY - 26), (CX + neck, CY), (CX - neck, CY)], fill=SAND + (255,))
    d.polygon([(CX - half_w + 6, bottom - 4), (CX + half_w - 6, bottom - 4), (CX, bottom - 70)], fill=SAND + (255,))
    d.line((CX, CY, CX, bottom - 66), fill=(220, 255, 200, 255), width=4)
    for _ in range(26):  # grains flying fast
        y = rng.uniform(CY + 4, bottom - 60)
        x = CX + rng.uniform(-5, 5)
        d.ellipse((x - 1.4, y - 1.4, x + 1.4, y + 1.4), fill=(230, 255, 210, 255))
    sand_glow = layer.filter(ImageFilter.GaussianBlur(6))
    sand_glow.alpha_composite(layer)
    d = ImageDraw.Draw(sand_glow)
    # gold caps and posts
    for y in (top - 16, bottom):
        d.rounded_rectangle((CX - 80, y, CX + 80, y + 16), radius=5, fill=GOLD, outline=GOLD_DARK, width=2)
    for x in (CX - 70, CX + 64):
        d.rectangle((x, top, x + 6, bottom), fill=GOLD, outline=GOLD_DARK)
    return sand_glow


def _text(img, text, size, y, fill, stroke):
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, size)
    box = d.textbbox((0, y), text, font=font)
    x = (SIZE - (box[2] - box[0])) / 2 - box[0]
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).text((x, y + 2), text, font=font, fill=(0, 0, 0, 255), stroke_width=6,
                                stroke_fill=(0, 0, 0, 255))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(4)))
    d.text((x, y), text, font=font, fill=fill, stroke_width=1, stroke_fill=stroke)
    return box[3]


def make_preview():
    rng = random.Random(1142710)
    img = _background()
    img.alpha_composite(_chaos_star())
    img.alpha_composite(_ring())
    img.alpha_composite(_hourglass(rng))
    bottom = _text(img, "AGENT COOLDOWNS", 38, 22, (236, 220, 180, 255), (90, 30, 110, 255))
    d = ImageDraw.Draw(img)
    line_y = bottom + 10
    d.line(((CX - 120, line_y), (CX + 120, line_y)), fill=(170, 255, 140, 255), width=2)
    _text(img, "15 TURNS  >>  1 TURN", 28, SIZE - 56, (170, 255, 140, 255), (20, 60, 20, 255))
    return img.convert("RGB")


def save_preview(img, path):
    img.save(path, "PNG", optimize=True)
