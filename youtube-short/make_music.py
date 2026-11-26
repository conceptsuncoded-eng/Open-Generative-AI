#!/usr/bin/env python3
"""Synthesize an original 27s music bed for the Short (no external samples)."""
import wave
import numpy as np

SR = 44100
DUR = 27.0
N = int(SR * DUR)
rng = np.random.default_rng(11)
t_all = np.arange(N) / SR

BPM = 100.0
BEAT = 60.0 / BPM          # 0.6 s
BAR = BEAT * 4             # 2.4 s

mix = np.zeros(N, dtype=np.float64)
pad_bus = np.zeros(N, dtype=np.float64)
bass_bus = np.zeros(N, dtype=np.float64)

A4 = 440.0


def hz(midi):
    return A4 * 2 ** ((midi - 69) / 12.0)


def place(sig, at, gain=1.0, bus=None):
    i = int(at * SR)
    if i >= N:
        return
    n = min(len(sig), N - i)
    target = mix if bus is None else bus
    target[i:i + n] += sig[:n] * gain


def lowpass(x, win):
    if win < 2:
        return x
    k = np.ones(win) / win
    return np.convolve(x, k, mode="same")


def env_ad(n, attack, decay, curve=1.0):
    a = max(1, int(attack * SR))
    e = np.ones(n)
    e[:a] = np.linspace(0, 1, a)
    d = np.linspace(0, 1, n) ** curve
    return e * np.exp(-d * (n / SR) / max(decay, 1e-4))


# ------------------------------------------------------------------ drums
def kick(vel=1.0):
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    f = 46 + 120 * np.exp(-t / 0.028)
    phase = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(phase) * np.exp(-t / 0.13)
    click = rng.normal(0, 1, n) * np.exp(-t / 0.004) * 0.25
    return np.tanh((body + click) * 1.6) * vel


def hat(vel=0.5, decay=0.02):
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    x = rng.normal(0, 1, n)
    x = np.diff(np.diff(x, prepend=0), prepend=0)  # crude highpass
    return x * np.exp(-t / decay) * vel


def clap(vel=0.7):
    n = int(0.28 * SR)
    t = np.arange(n) / SR
    x = rng.normal(0, 1, n)
    x = np.diff(x, prepend=0)
    x = lowpass(x, 6)
    body = x * (np.exp(-t / 0.055) + 0.6 * np.exp(-((t - 0.018).clip(0) / 0.02)))
    return body * vel


def whoosh(vel=0.5, dur=0.55):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = rng.normal(0, 1, n)
    x = np.diff(x, prepend=0)
    env = np.exp(-((t - 0.16) ** 2) / (2 * 0.11 ** 2))
    return x * env * vel


def riser(vel=0.35, dur=1.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = rng.normal(0, 1, n)
    x = np.diff(x, prepend=0)
    env = (t / dur) ** 2.2
    sweep = 0.5 + 0.5 * np.sin(2 * np.pi * (2 + 8 * t) * t)
    return x * env * (0.6 + 0.4 * sweep) * vel


def boom(vel=0.9):
    n = int(1.2 * SR)
    t = np.arange(n) / SR
    f = 40 + 60 * np.exp(-t / 0.09)
    phase = 2 * np.pi * np.cumsum(f) / SR
    sig = np.sin(phase) * np.exp(-t / 0.35)
    sig += rng.normal(0, 1, n) * np.exp(-t / 0.02) * 0.15
    return np.tanh(sig * 1.4) * vel


# ------------------------------------------------------------------ tonal
CHORDS = [
    [57, 60, 64],  # Am
    [53, 57, 60],  # F
    [48, 55, 60],  # C
    [55, 59, 62],  # G
]


def pad_chord(midis, dur, vel=0.16):
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for m in midis:
        f0 = hz(m)
        for det in (-0.18, 0.0, 0.16):
            sig += np.sin(2 * np.pi * (f0 + det) * t)
            sig += 0.25 * np.sin(4 * np.pi * (f0 + det) * t + 0.7)
    sig /= (len(midis) * 3)
    sig = lowpass(sig, 26)
    a = min(1.0, n / SR * 0.35)
    env = np.minimum(1.0, t / max(a, 1e-3)) * np.minimum(1.0, (dur - t) / 0.35)
    trem = 0.85 + 0.15 * np.sin(2 * np.pi * 0.28 * t)
    return sig * env * trem * vel


def bass_note(midi, dur=0.42, vel=0.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = hz(midi)
    sig = np.sin(2 * np.pi * f * t) + 0.28 * np.sin(4 * np.pi * f * t)
    sig += 0.12 * np.sin(6 * np.pi * f * t)
    sig = np.tanh(sig * 1.5)
    return sig * env_ad(n, 0.006, 0.16, 1.6) * vel


def pluck(midi, dur=0.5, vel=0.2):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = hz(midi)
    sig = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2.01 * t)
    sig += 0.15 * np.sin(2 * np.pi * f * 3 * t)
    return sig * np.exp(-t / 0.11) * vel


# ------------------------------------------------------------------ arrangement
BAR_COUNT = int(np.ceil(DUR / BAR))
drum_start, drum_stop, out_start = 3.2, 21.0, 21.0
kick_times = []

for b in range(BAR_COUNT):
    t0 = b * BAR
    chord = CHORDS[b % len(CHORDS)]
    root = chord[0] - 12

    intro = t0 < drum_start
    full = drum_start <= t0 < drum_stop
    outro = t0 >= out_start

    # ---- pads always
    place(pad_chord(chord, BAR + 0.3, vel=0.30 if intro else 0.22), t0, 1.0, pad_bus)
    if outro:
        place(pad_chord([m + 12 for m in chord], BAR + 0.3, vel=0.16), t0, 1.0, pad_bus)

    if intro:
        for beat in range(4):
            tb = t0 + beat * BEAT
            if t0 + beat * BEAT >= 1.2:
                place(kick(0.62), tb, 0.8)
                kick_times.append(tb)
            place(hat(0.20 if beat % 2 else 0.12), tb, 1.0)
            place(hat(0.10, 0.014), tb + BEAT / 2, 1.0)
        place(bass_note(root, 0.5, 0.40), t0, 1.0, bass_bus)
        place(bass_note(root, 0.5, 0.34), t0 + 2 * BEAT, 1.0, bass_bus)

    if full:
        # ---- drums
        for beat in range(4):
            tb = t0 + beat * BEAT
            place(kick(1.0), tb, 0.95)
            kick_times.append(tb)
            if b % 2 == 1 and beat == 3:  # extra pickup kick
                place(kick(0.5), tb + BEAT * 0.5, 0.5)
                kick_times.append(tb + BEAT * 0.5)
            if beat in (1, 3):
                place(clap(0.42), tb, 1.0)
        for h in range(8):
            th = t0 + h * BEAT / 2
            place(hat(0.34 if h % 2 else 0.16), th, 1.0)
            place(hat(0.10, 0.012), th + BEAT / 4, 1.0)

        # ---- bass
        for pos, off in ((0, 0.0), (0, 0.9), (2, 0.0), (3, 0.6)):
            place(bass_note(root + (0 if pos != 3 else 7), 0.38, 0.46),
                  t0 + pos * BEAT + off * BEAT, 1.0, bass_bus)

        # ---- arp (16ths)
        for s in range(16):
            ts = t0 + s * BEAT / 4
            note = chord[s % len(chord)] + (12 if (s // 3) % 2 else 24)
            place(pluck(note, 0.4, 0.10), ts, 1.0)

    if outro:
        for beat in range(4):
            tb = t0 + beat * BEAT
            place(kick(0.72), tb, 0.9)
            kick_times.append(tb)
            place(hat(0.22 if beat % 2 else 0.13), tb, 1.0)
            place(hat(0.09, 0.012), tb + BEAT / 2, 1.0)
        for s in range(8):
            ts = t0 + s * BEAT / 2
            note = chord[s % len(chord)] + 24
            place(pluck(note, 0.9, 0.16), ts, 1.0)

# ------------------------------------------------------------------ transitions
for tt, v in ((0.0, 0.75), (3.2, 0.85), (12.0, 0.70), (21.0, 0.95)):
    place(boom(v), tt, 1.0)

for tt in (3.2, 12.0, 21.0):
    place(whoosh(0.30, 0.6), tt - 0.30, 1.0)

place(boom(0.95, ), 25.15, 1.0)
place(whoosh(0.22, 0.5), 24.7, 1.0)
place(riser(0.30, 1.9), 1.25, 1.0)
place(riser(0.22, 1.2), 10.7, 1.0)
place(riser(0.26, 1.0), 19.9, 1.0)

# ------------------------------------------------------------------ sidechain
sc = np.ones(N)
if kick_times:
    for kt in kick_times:
        i = int(kt * SR)
        n = min(int(0.30 * SR), N - i)
        if n <= 0:
            continue
        e = 1.0 - 0.55 * np.exp(-np.arange(n) / (0.055 * SR))
        sc[i:i + n] = np.minimum(sc[i:i + n], e)

mix += pad_bus * sc * 0.55 + bass_bus * sc * 0.9

# ------------------------------------------------------------------ master
mix = lowpass(mix, 3)
mix = np.tanh(mix * 1.15)

fade_in = np.minimum(1.0, t_all / 0.35)
fade_out = np.clip((DUR - t_all) / 2.2, 0, 1) ** 1.5
mix *= fade_in * fade_out

mix /= np.max(np.abs(mix)) + 1e-9
mix *= 0.88

# subtle stereo width via haas on a copy
delay = int(0.011 * SR)
right = np.concatenate([np.zeros(delay), mix[:-delay]]) * 0.96
stereo = np.stack([mix, right], axis=1)
pcm = (np.clip(stereo, -1, 1) * 32767).astype("<i2")

with wave.open("youtube-short/build/music.wav", "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())

print(f"music.wav: {DUR}s, kicks={len(kick_times)}")
