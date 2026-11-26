#!/usr/bin/env python3
"""Render all typographic / background assets for the Open Generative AI YouTube Short."""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
OUT = "youtube-short/build"
os.makedirs(OUT, exist_ok=True)

FONT_DIR = ".tools/fonts"
EXTRA = f"{FONT_DIR}/Poppins_800ExtraBold.ttf"
BOLD = f"{FONT_DIR}/Poppins_700Bold.ttf"
SEMI = f"{FONT_DIR}/Poppins_600SemiBold.ttf"

LIME = (207, 255, 61)
WHITE = (255, 255, 255)
GRAY = (150, 157, 168)
INK = (10, 10, 12)


def f(path, size):
    return ImageFont.truetype(path, size)


def tw(text, font, tracking=0.0):
    if not text:
        return 0
    return sum(font.getlength(c) for c in text) + tracking * (len(text) - 1)


def draw_tracked(draw, x, y, text, font, fill, tracking=0.0, center_x=None):
    w = tw(text, font, tracking)
    if center_x is not None:
        x = center_x - w / 2
    cx = x
    for c in text:
        draw.text((cx, y), c, font=font, fill=fill)
        cx += font.getlength(c) + tracking
    return w


def fit_size(lines, path, max_w, start, floor=40):
    """Largest common font size where every line fits inside max_w (tracking -0.02em)."""
    size = start
    while size > floor:
        font = f(path, size)
        tr = -size * 0.02
        if all(tw(t, font, tr) <= max_w for t in lines):
            return size, font, tr
        size -= 2
    return floor, f(path, floor), 0


# ---------------------------------------------------------------- backgrounds
def radial(h, w, cx, cy, rx, ry, power=2.0):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    return np.exp(-(d ** 2) * power)


def hook_bg(path):
    rng = np.random.default_rng(7)
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    base = np.zeros((H, W, 3), dtype=np.float32)
    top = np.array([6, 7, 9], dtype=np.float32)
    bot = np.array([18, 21, 24], dtype=np.float32)
    base += top * (1 - yy[..., None]) + bot * yy[..., None]

    # blurred lime sculpture as texture
    try:
        art = Image.open("youtube-short/assets/art3.webp").convert("RGB")
        art = art.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(34))
        base += np.asarray(art).astype(np.float32) * 0.26
    except FileNotFoundError:
        pass

    glow = radial(H, W, 190, 1720, 1150, 1000, 2.4)[..., None]
    base += glow * np.array([70, 96, 18], dtype=np.float32) * 0.55
    glow2 = radial(H, W, 950, 260, 900, 700, 3.0)[..., None]
    base += glow2 * np.array([20, 44, 60], dtype=np.float32) * 0.5

    # faint technical grid
    gx = (np.arange(W) % 90) < 1
    gy = (np.arange(H) % 90) < 1
    grid = np.zeros((H, W), dtype=np.float32)
    grid[:, gx] += 7.0
    grid[gy, :] += 7.0
    base += grid[..., None] * np.array([1.0, 1.0, 1.05])

    # darken the middle band so the headline stays legible
    band = np.exp(-(((np.arange(H) - 960) / 430.0) ** 2))[:, None, None]
    base *= (1.0 - 0.55 * band)

    v = 1.0 - 0.55 * radial(H, W, 540, 960, 1300, 1900, 1.3)
    base *= v[..., None]
    base += rng.normal(0, 2.6, (H, W, 1)).astype(np.float32)
    Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).save(path, "PNG")


# ---------------------------------------------------------------- rounded mask
def rounded_mask(path, w, h, r):
    img = Image.new("L", (w, h), 0)
    ImageDraw.Draw(img).rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)
    img.save(path)


# ---------------------------------------------------------------- hook text
def hook_text(path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = W / 2

    # kicker with its own rule lines
    kfont = f(SEMI, 34)
    ktxt = "OPEN GENERATIVE AI"
    kw = draw_tracked(d, 0, 0, ktxt, kfont, LIME, 9, center_x=cx)
    ky = 784
    d.text((cx - kw / 2, ky), "", font=kfont, fill=LIME)
    # redraw at proper y
    img2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img2)
    draw_tracked(d, 0, ky, ktxt, kfont, LIME, 9, center_x=cx)
    for sx in (-1, 1):
        x0 = cx + sx * (kw / 2 + 34)
        x1 = cx + sx * (kw / 2 + 108)
        d.line([(x0, ky + 26), (x1, ky + 26)], fill=(207, 255, 61, 130), width=3)

    # headline: "200+" lime + " AI MODELS" white
    l1a, l1b = "200+", " AI MODELS"
    l2 = "ONE FREE STUDIO"
    size, font, tr = fit_size([l1a + l1b, l2], EXTRA, 900, 118)
    wa = tw(l1a, font, tr)
    wb = tw(l1b, font, tr)
    y1 = 860
    draw_tracked(d, cx - (wa + wb) / 2, y1, l1a, font, LIME, tr)
    draw_tracked(d, cx - (wa + wb) / 2 + wa, y1, l1b, font, WHITE, tr)
    draw_tracked(d, 0, y1 + size * 1.18, l2, font, WHITE, tr, center_x=cx)

    subfont = f(SEMI, 40)
    draw_tracked(d, 0, y1 + size * 2.5, "images  ·  video  ·  cinema  ·  audio",
                 subfont, GRAY, 2, center_x=cx)
    img2.save(path)


# ---------------------------------------------------------------- pills / chips
def pill(path, text, bg, fg, size=46, padx=44, pady=26, tracking=2.0, dot=None):
    font = f(EXTRA, size)
    wtxt = tw(text, font, tracking)
    dotw = (size * 0.26 + 22) if dot else 0
    w = int(wtxt + dotw + padx * 2)
    h = int(size * 1.32 + pady * 2)
    img = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([4, 4, w + 3, h + 3], radius=h // 2, fill=bg)
    x = 4 + padx
    if dot:
        r = size * 0.13
        cy = 4 + h / 2
        d.ellipse([x, cy - r, x + 2 * r, cy + r], fill=dot)
        x += dotw
    asc = font.getbbox(text)[1]
    draw_tracked(d, x, 4 + pady - asc * 0.15, text, font, fg, tracking)
    img.save(path)


def label_chip(path, text):
    """Editorial caption for the showcase: lime bar + white caps on a dark plate."""
    S = 3
    font = f(EXTRA, 50 * S)
    tracking = 1.6 * S
    w = tw(text, font, tracking)
    padx, pady, bar = 44 * S, 26 * S, 9 * S
    width = int(padx * 2 + bar + 24 * S + w)
    height = int(50 * 1.35 * S + pady * 2)
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, width - 1, height - 1], radius=height // 2,
                        fill=(10, 10, 12, 232))
    draw_tracked(d, padx + bar + 24 * S, pady - 2 * S, text, font, WHITE, tracking)
    d.rounded_rectangle([padx, pady + 4 * S, padx + bar, height - pady - 4 * S],
                        radius=bar // 2, fill=LIME)
    img = img.resize((width // S, height // S), Image.LANCZOS)
    img.save(path)


def card_shadow(path, w, h, pad=30):
    img = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([pad - 2, pad - 2, pad + w + 1, pad + h + 1], radius=28,
                        fill=(207, 255, 61, 60))
    img = img.filter(ImageFilter.GaussianBlur(18))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([pad, pad, pad + w - 1, pad + h - 1], radius=26, fill=(0, 0, 0, 235))
    img.save(path)


def scrim(path):
    h = 900
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None, None] ** 2.1
    arr = np.zeros((h, W, 4), dtype=np.float32)
    arr[..., 3] = yy[..., 0] * 235
    Image.fromarray(arr.astype(np.uint8), "RGBA").save(path)


def brand_bar(path):
    """Small persistent wordmark used on the demo + showcase sections."""
    font = f(SEMI, 30)
    txt = "OPEN GENERATIVE AI"
    wtxt = tw(txt, font, 7)
    img = Image.new("RGBA", (int(wtxt + 120), 70), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, img.width - 1, 69], radius=35, fill=(10, 10, 12, 190))
    d.ellipse([26, 29, 40, 43], fill=LIME)
    draw_tracked(d, 58, 17, txt, font, WHITE, 7)
    img.save(path)


# ---------------------------------------------------------------- end card
def end_card(path):
    art = Image.open("youtube-short/assets/art1.webp").convert("RGB")
    art = art.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(46))
    arr = np.asarray(art).astype(np.float32) * 0.30

    glow = radial(H, W, 540, 1180, 900, 800, 2.2)[..., None]
    arr += glow * np.array([54, 70, 14], dtype=np.float32)
    arr *= (1.0 - 0.45 * radial(H, W, 540, 960, 1250, 1900, 1.2))[..., None]

    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(img)
    cx = W / 2

    kicker = f(SEMI, 32)
    draw_tracked(d, 0, 520, "FREE  ·  OPEN SOURCE", kicker, LIME, 10, center_x=cx)

    size, font, tr = fit_size(["OPEN", "GENERATIVE AI"], EXTRA, 940, 150)
    draw_tracked(d, 0, 590, "OPEN", font, WHITE, tr, center_x=cx)
    draw_tracked(d, 0, 590 + size * 1.12, "GENERATIVE AI", font, LIME, tr, center_x=cx)

    sub = f(SEMI, 40)
    draw_tracked(d, 0, 900, "200+ AI models · one studio", sub, (225, 230, 236), 1, center_x=cx)

    # URL pill
    ufont = f(BOLD, 38)
    utxt = "github.com/Anil-matcha"
    uw = tw(utxt, ufont, 0)
    ph, pw = 108, uw + 96
    py = 1010
    d.rounded_rectangle([cx - pw / 2, py, cx + pw / 2, py + ph], radius=ph / 2, fill=LIME)
    d.text((cx - uw / 2, py + 26), utxt, font=ufont, fill=INK)

    foot = f(SEMI, 34)
    draw_tracked(d, 0, 1190, "FULL LINK IN DESCRIPTION", foot, (190, 197, 206), 6, center_x=cx)
    # downward arrow
    ax, ay = cx, 1280
    d.line([(ax, ay), (ax, ay + 70)], fill=LIME, width=8)
    d.polygon([(ax - 26, ay + 58), (ax + 26, ay + 58), (ax, ay + 100)], fill=LIME)

    img.save(path)


if __name__ == "__main__":
    hook_bg(f"{OUT}/bg_hook.png")
    hook_text(f"{OUT}/hook_text.png")
    rounded_mask(f"{OUT}/card_mask.png", 1000, 555, 26)
    pill(f"{OUT}/pill_1.png", "1  PICK A MODEL", LIME, INK, size=44)
    pill(f"{OUT}/pill_2.png", "2  WRITE A PROMPT", LIME, INK, size=44)
    pill(f"{OUT}/pill_3.png", "3  HIT GENERATE", LIME, INK, size=44)
    card_shadow(f"{OUT}/card_shadow.png", 1000, 555, pad=30)
    label_chip(f"{OUT}/chip_cinematic.png", "CINEMATIC PORTRAIT")
    label_chip(f"{OUT}/chip_anime.png", "ANIME ILLUSTRATION")
    label_chip(f"{OUT}/chip_3d.png", "3D PRODUCT DESIGN")
    scrim(f"{OUT}/scrim.png")
    brand_bar(f"{OUT}/brand.png")
    end_card(f"{OUT}/endcard.png")
    print("graphics done")
