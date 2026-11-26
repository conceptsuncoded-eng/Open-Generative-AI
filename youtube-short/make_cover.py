#!/usr/bin/env python3
"""Build the 1080x1920 cover frame for the Short."""
from PIL import Image, ImageDraw, ImageFilter

W, H = 1080, 1920
BG = "youtube-short/build/bg_hook.png"
TEXT = "youtube-short/build/hook_text.png"
ARTS = ["youtube-short/assets/art1.webp", "youtube-short/assets/art2.webp",
        "youtube-short/assets/art3.webp"]
LIME = (207, 255, 61)

canvas = Image.open(BG).convert("RGB")
canvas = canvas.filter(ImageFilter.GaussianBlur(6))       # soften the grid for a poster look
canvas = canvas.convert("RGBA")
canvas.alpha_composite(Image.open(TEXT).convert("RGBA"), (0, -78))

TW, TH, GAP, RAD = 300, 400, 22, 26
total = TW * 3 + GAP * 2
x0 = (W - total) // 2
y0 = 1236

for i, path in enumerate(ARTS):
    im = Image.open(path).convert("RGB")
    # cover-crop to 300x400 then round the corners
    scale = max(TW / im.width, TH / im.height)
    im = im.resize((int(im.width * scale + 0.5), int(im.height * scale + 0.5)), Image.LANCZOS)
    left = (im.width - TW) // 2
    top = int((im.height - TH) * 0.42)
    im = im.crop((left, top, left + TW, top + TH))

    mask = Image.new("L", (TW, TH), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, TW - 1, TH - 1], radius=RAD, fill=255)
    x = x0 + i * (TW + GAP)

    # lime halo + border
    glow = Image.new("RGBA", (TW + 40, TH + 40), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle([10, 10, TW + 29, TH + 29], radius=RAD + 8,
                                           fill=(207, 255, 61, 70))
    glow = glow.filter(ImageFilter.GaussianBlur(12))
    canvas.alpha_composite(glow, (x - 20, y0 - 20))
    canvas.paste(im, (x, y0), mask)
    ImageDraw.Draw(canvas).rounded_rectangle([x, y0, x + TW - 1, y0 + TH - 1],
                                             radius=RAD, outline=(207, 255, 61, 210), width=3)

canvas.convert("RGB").save("youtube-short/cover.png", quality=95)
print("cover written")
