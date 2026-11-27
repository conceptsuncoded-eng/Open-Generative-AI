#!/usr/bin/env python3
"""Builds the 60-second cold open of THE LAST 10 MINUTES from photoreal key frames.

Stage 1: per-shot camera moves (zoompan) -> intermediate clips
Stage 2: concat, overlay HUD/title sequence, grain, vignette, fades
Stage 3: synthesize score + rain + clock, mux, encode 1080p master and 720p web copy
"""
import os
import subprocess
import sys
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
KF = os.path.join(ROOT, "02_KEYFRAMES")
OUT = os.path.join(ROOT, "03_SEQUENCE_01")
TMP = os.path.join(ROOT, ".build")
FF = os.path.join(os.path.dirname(ROOT), ".tools", "bin", "ffmpeg")
W, H, FPS = 1920, 1080, 24
DUR = 60.0

FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_M = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

# (keyframe, start, duration, zoom_start, zoom_end, x_drift, y_drift, crop)
SEGMENTS = [
    ("S01_aerial_manhattan_rain.png", 0.0,  8.0, 1.00, 1.09,  0.35, -0.20, None),
    ("S02_ethan_suv_phone.png",       8.0, 10.0, 1.04, 1.16, -0.30,  0.10, None),
    ("S03_daniel_holding_room.png",  18.0,  8.0, 1.02, 1.13,  0.00,  0.05, None),
    ("S03b_ethan_watching.png",      26.0,  8.0, 1.03, 1.15,  0.20,  0.00, None),
    ("S04a_ethan_eyes.png",          34.0,  7.0, 1.02, 1.12,  0.00,  0.00, None),
    ("S04b_ethan_garage.png",        41.0,  9.0, 1.06, 1.00, -0.25,  0.15, None),
    ("S03_daniel_holding_room.png",  50.0,  8.0, 1.18, 1.30,  0.00, -0.28, (0.18, 0.42)),
    ("__black__",                    58.0,  2.0, 1.00, 1.00,  0.00,  0.00, None),
]


def sh(cmd, label=""):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        print(f"FAILED {label}\n{' '.join(cmd)[:400]}\n{p.stderr[-1500:]}")
        sys.exit(1)
    return p


# ---------------------------------------------------------------- stage 1
def build_segments():
    os.makedirs(TMP, exist_ok=True)
    files = []
    for i, (img, start, dur, z0, z1, dx, dy, crop) in enumerate(SEGMENTS):
        dst = os.path.join(TMP, f"seg_{i:02d}.mp4")
        files.append(dst)
        if img == "__black__":
            sh([FF, "-y", "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:d={dur}:r={FPS}",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", dst], img)
            continue

        src = os.path.join(KF, img)
        # optional crop before the move, expressed as a fraction of the frame
        pre = ""
        if crop:
            x0, wf = crop
            cw = int(W * wf)
            ch = int(H * wf)
            pre = f"crop={cw}:{ch}:{int(W*x0)}:{int(H*0.30)},scale={W}:{H},"
        else:
            pre = f"scale={W}:{H},"

        frames = int(round(dur * FPS))
        z = f"{z0}+({z1}-{z0})*on/{frames}"
        x = f"iw/2-(iw/zoom/2)+{dx}*iw*on/{frames}/10"
        y = f"ih/2-(ih/zoom/2)+{dy}*ih*on/{frames}/10"
        vf = (f"{pre}scale={int(W*1.25)}:{int(H*1.25)},"
              f"zoompan=z='{z}':x='{x}':y='{y}':d=1:s={W}x{H}:fps={FPS},"
              f"format=yuv420p")
        sh([FF, "-y", "-loop", "1", "-framerate", str(FPS), "-i", src, "-t", str(dur),
            "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", dst], img)
        print(f"  seg {i:02d} {img} {dur}s")
    return files


# ---------------------------------------------------------------- hud + title
def build_overlay():
    """24fps RGBA overlay: letterspaced title 1.2-6.4s, countdown from t=8."""
    d = os.path.join(TMP, "hud")
    os.makedirs(d, exist_ok=True)
    for f in os.listdir(d):
        os.remove(os.path.join(d, f))

    title_font = ImageFont.truetype(FONT_B, 54)
    sub_font = ImageFont.truetype(FONT_B, 17)
    mono = ImageFont.truetype(FONT_M, 30)

    def spaced(draw, xy, text, font, fill, tracking):
        x, y = xy
        for ch in text:
            draw.text((x, y), ch, font=font, fill=fill)
            x += draw.textlength(ch, font=font) + tracking

    def title_layer(alpha):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        t = "THE LAST 10 MINUTES"
        # measure for centring
        widths = [dr.textlength(c, font=title_font) for c in t]
        total = sum(widths) + 17 * (len(t) - 1)
        x = (W - total) / 2
        a = int(255 * alpha)
        for c, w in zip(t, widths):
            dr.text((x, 470), c, font=title_font, fill=(232, 237, 242, a))
            x += w + 17
        dr.text((W / 2, 552), "AN ORIGINAL SPY THRILLER", font=sub_font,
                fill=(198, 242, 78, int(a * 0.85)), anchor="mm")
        return img

    title_cache = {}
    for frame in range(int(DUR * FPS)):
        t = frame / FPS
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)

        # opening title: 1.2 -> 6.4 with 0.8s in / 1.2s out
        if 1.2 <= t <= 6.4:
            if t < 2.0:
                a = (t - 1.2) / 0.8
            elif t > 5.2:
                a = max(0.0, (6.4 - t) / 1.2)
            else:
                a = 1.0
            q = round(a * 40) / 40
            if q not in title_cache:
                title_cache[q] = title_layer(q)
            img = Image.alpha_composite(img, title_cache[q])
            dr = ImageDraw.Draw(img)

        # countdown: real time from 9:52 at t=8
        if t >= 8.0:
            secs = 592 - int(t - 8.0)
            m, s = divmod(max(0, secs), 60)
            txt = f"{m:02d}:{s:02d}"
            bx, by = W - 190, H - 96
            dr.rounded_rectangle([bx - 18, by - 12, bx + 168, by + 46], radius=8,
                                 fill=(10, 12, 14, 150), outline=(60, 68, 78, 190))
            pulse = 255 if (t % 1.0) < 0.5 else 120
            dr.ellipse([bx - 6, by + 8, bx + 6, by + 20], fill=(255, 60, 48, pulse))
            dr.text((bx + 20, by - 4), txt, font=mono, fill=(232, 237, 242, 235))
            dr.text((bx + 20, by + 26), "TIME TO EXTRACTION", font=ImageFont.truetype(FONT_B, 10),
                    fill=(140, 152, 164, 200))
        img.save(os.path.join(d, f"{frame:05d}.png"))
        if frame % 240 == 0:
            print(f"  overlay {frame}/{int(DUR*FPS)}")
    return d


# ---------------------------------------------------------------- audio
def build_audio(path):
    sr = 48000
    n = int(DUR * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(7)
    L = np.zeros(n, dtype=np.float64)
    R = np.zeros(n, dtype=np.float64)

    def add(sig, at=0, pan=0.0, gain=1.0):
        nonlocal L, R
        a, b = max(0, at), min(n, at + len(sig))
        if b <= a:
            return
        seg = sig[a - at:b - at]
        L[a:b] += seg * gain * (1 - max(0.0, pan))
        R[a:b] += seg * gain * (1 + min(0.0, pan))

    # ---- rain: shaped noise
    rain = rng.normal(0, 1, n)
    k = np.ones(24) / 24
    rain = np.convolve(rain, k, mode="same")          # soften hiss
    rain -= np.convolve(rain, np.ones(600) / 600, mode="same")  # high-pass
    env = 0.55 + 0.45 * np.clip((t - 41) / 19, 0, 1)
    add(rain * env, gain=0.10)

    # ---- low drone, detuned pair
    for f, g in ((55, 0.16), (82.4, 0.07), (110, 0.05)):
        vib = 1 + 0.0015 * np.sin(2 * np.pi * 0.11 * t)
        add(np.sin(2 * np.pi * f * t * vib) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.03 * t)), gain=g)

    # ---- clock ticks, accelerating slightly toward the end
    for i in range(int(DUR)):
        tt = i * 1.0
        if tt < 1.0:
            continue
        acc = 1.0 + (0.5 if i % 4 == 0 else 0.0)
        ln = int(0.045 * sr)
        idx = int(tt * sr)
        if idx + ln >= n:
            break
        click = rng.normal(0, 1, ln) * np.exp(-np.linspace(0, 9, ln))
        accent = np.sin(2 * np.pi * 1800 * np.arange(ln) / sr) * np.exp(-np.linspace(0, 14, ln))
        add(click * 0.5 + accent * 0.5, at=idx, pan=(-1) ** i * 0.25, gain=0.09 * acc)

    # ---- reveal booms
    for bt in (18.0, 50.0):
        ln = int(2.4 * sr)
        idx = int(bt * sr)
        e = np.exp(-np.linspace(0, 4.5, ln))
        boom = np.sin(2 * np.pi * 44 * np.arange(ln) / sr) * e
        boom += np.sin(2 * np.pi * 66 * np.arange(ln) / sr) * e * 0.5
        add(boom, at=idx, gain=0.30)
        hit = rng.normal(0, 1, int(0.4 * sr)) * np.exp(-np.linspace(0, 12, int(0.4 * sr)))
        L[idx:idx + len(hit)] += hit * 0.05
        R[idx:idx + len(hit)] += hit * 0.05

    # ---- heartbeat 26-34
    pos = 26.0
    while pos < 34.0:
        for off, g in ((0.0, 0.22), (0.19, 0.15)):
            ln = int(0.22 * sr)
            idx = int((pos + off) * sr)
            if idx + ln >= n:
                break
            e = np.exp(-np.linspace(0, 11, ln))
            thump = np.sin(2 * np.pi * 52 * np.arange(ln) / sr) * e
            L[idx:idx + ln] += thump * g
            R[idx:idx + ln] += thump * g
        pos += 1.15

    # ---- riser 34-50: filtered harmonics swelling
    ln = int(16 * sr)
    idx = int(34 * sr)
    tt = np.arange(ln) / sr
    riser = np.zeros(ln)
    for h, g in ((1, .5), (2, .3), (3, .18), (5, .1), (7, .06)):
        riser += np.sin(2 * np.pi * 98 * h * tt * (1 + 0.004 * tt)) * g
    riser *= np.linspace(0, 1, ln) ** 2.2
    L[idx:idx + ln] += riser * 0.13
    R[idx:idx + ln] += riser * 0.13

    # ---- master: gentle limit, fades
    mix = np.stack([L, R], axis=1)
    fade_in = np.clip(t / 1.2, 0, 1)[:, None]
    fade_out = np.clip((DUR - t) / 2.2, 0, 1)[:, None]
    mix *= fade_in * fade_out
    peak = np.abs(mix).max()
    mix = np.tanh(mix / max(peak, 1e-9) * 1.15) * 0.82   # soft clip, then back off
    mix = (mix / max(np.abs(mix).max(), 1e-9)) * 0.89    # -1 dBFS ceiling
    pcm = (mix * 32767).astype(np.int16)

    import wave
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    print(f"  audio {path}  peak={np.abs(mix).max():.3f}")


# ---------------------------------------------------------------- stage 3
def finalize(segs, hud, wav, master, web):
    lst = os.path.join(TMP, "list.txt")
    with open(lst, "w") as f:
        for s in segs:
            f.write(f"file '{s}'\n")

    fc = (
        f"[0:v]fps={FPS},format=yuv420p[base];"
        f"[1:v]format=rgba[hud];"
        f"[base][hud]overlay=0:0:shortest=0[o1];"
        f"[o1]scale=1920:1080:flags=lanczos,setsar=1,noise=alls=7:allf=t+u,vignette=PI/5.2,"
        f"eq=contrast=1.04:saturation=0.96:brightness=-0.012,"
        f"fade=t=in:st=0:d=1.0,fade=t=out:st={DUR-2.0}:d=2.0[vout]"
    )
    cmd = [FF, "-y",
           "-f", "concat", "-safe", "0", "-i", lst,
           "-framerate", str(FPS), "-i", os.path.join(hud, "%05d.png"),
           "-i", wav,
           "-filter_complex", fc,
           "-map", "[vout]", "-map", "2:a",
           "-c:v", "libx264", "-preset", "medium", "-crf", "19",
           "-pix_fmt", "yuv420p", "-r", str(FPS), "-profile:v", "high",
           "-movflags", "+faststart",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           "-t", str(DUR), master]
    sh(cmd, "master")

    cmd2 = [FF, "-y", "-i", master, "-vf", "scale=1280:720:flags=lanczos",
            "-c:v", "libx264", "-preset", "medium", "-crf", "27",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-c:a", "aac", "-b:a", "128k", "-ac", "2", web]
    sh(cmd2, "web")


def main():
    os.makedirs(OUT, exist_ok=True)
    print("stage 1 — camera moves")
    segs = build_segments()
    print("stage 2 — title + countdown overlay")
    hud = build_overlay()
    print("stage 3 — score")
    wav = os.path.join(TMP, "score.wav")
    build_audio(wav)
    print("stage 4 — encode")
    master = os.path.join(OUT, "SEQUENCE_01_open_60s_1080p.mp4")
    web = os.path.join(OUT, "SEQUENCE_01_open_60s_720p.mp4")
    finalize(segs, hud, wav, master, web)
    for f in (master, web):
        print(f"  {f}  {os.path.getsize(f)/1e6:.1f} MB")


if __name__ == "__main__":
    main()
