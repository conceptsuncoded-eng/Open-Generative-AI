#!/usr/bin/env python3
"""Contact sheet of the finished Short, so it can be reviewed as a still image."""
import subprocess
from PIL import Image, ImageDraw, ImageFont

MP4 = "youtube-short/open-generative-ai-short.mp4"
FF = ".tools/bin/ffmpeg"
TIMES = [1.2, 3.9, 5.4, 7.0, 8.6, 10.2, 12.6, 14.4, 16.6, 18.8, 21.8, 24.5]

TW, TH = 300, 533
COLS, ROWS = 4, 3
PAD, GAP, BAR = 26, 12, 96
W = COLS * TW + (COLS - 1) * GAP + PAD * 2
H = BAR + ROWS * (TH + 34) + (ROWS - 1) * GAP + PAD

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
sheet = Image.new("RGB", (W, H), (10, 10, 12))
d = ImageDraw.Draw(sheet)

d.text((PAD, 30), "OPEN GENERATIVE AI  ·  YOUTUBE SHORT  ·  27s  ·  1080x1920",
       font=ImageFont.truetype(FONT, 30), fill=(207, 255, 61))
d.text((PAD, 68), "storyboard — one frame every ~2.2s",
       font=ImageFont.truetype(FONT, 22), fill=(150, 157, 168))

for i, t in enumerate(TIMES):
    p = f"/tmp/sb{i}.png"
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", MP4, "-ss", str(t),
                    "-frames:v", "1", "-update", "1", "-vf", f"scale={TW}:{TH}", p], check=True)
    col, row = i % COLS, i // COLS
    x = PAD + col * (TW + GAP)
    y = BAR + row * (TH + 34 + GAP)
    sheet.paste(Image.open(p).convert("RGB"), (x, y))
    lab = f"0:{int(t):02d}"
    d.rounded_rectangle([x, y + TH + 6, x + 74, y + TH + 30], radius=6, fill=(24, 25, 28))
    d.text((x + 12, y + TH + 9), lab, font=ImageFont.truetype(FONT, 17), fill=(207, 255, 61))

sheet.save("youtube-short/storyboard.png")
print("storyboard.png", sheet.size)
