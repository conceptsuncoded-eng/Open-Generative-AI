# Open Generative AI — YouTube Short

A 27-second vertical (9:16) promo Short for this repo, built entirely in the
workspace with ffmpeg and Python. No cloud rendering was used.

| File | What it is |
| --- | --- |
| `open-generative-ai-short.mp4` | The finished Short — 1080×1920, 30 fps, 27.0 s, H.264 + AAC |
| `cover.png` | 1080×1920 cover / poster frame |
| `description.md` | Ready-to-paste YouTube title, description, tags |
| `assets/art1-3.webp` | The three AI artworks used in the showcase |
| `make_graphics.py` | Renders the hook card, step pills, caption plates, end card |
| `make_music.py` | Synthesizes the soundtrack from scratch (no samples) |
| `make_cover.py` | Composes the cover image |
| `build.sh` | Cuts, layers, concatenates and muxes everything |

## Structure

| Time | Section | Content |
| --- | --- | --- |
| 0.0 – 3.2 | Hook | `200+ AI MODELS / ONE FREE STUDIO` over a blurred lime sculpture |
| 3.2 – 12.0 | Live demo | Three clean cuts of the real studio UI: pick a model → write a prompt → hit generate → result |
| 12.0 – 21.0 | Showcase | Cinematic portrait, anime illustration, 3D product design with Ken Burns moves |
| 21.0 – 27.0 | End card | Repo URL, "free · open source", link-in-description cue |

## How it was made

1. **Footage** — `docs/assets/demo.mp4` (18.6 s screen recording already in the repo).
   The raw clip zooms the browser in and out between 2–14 s, so only three clean
   spans are used: `0.70–2.10`, `10.30–13.05`, `15.25–18.55`. The window chrome is
   cropped to its exact bounds (`x 116, y 128, 1570×866`), scaled to a 1000 px card
   and masked with rounded corners.
2. **Artwork** — three 9:16 images generated with an image model (not by the app
   itself), standing in for the studio's output.
3. **Typography** — Poppins ExtraBold / Bold / SemiBold, rendered to transparent PNGs
   with Pillow (letter-spaced manually) and animated in ffmpeg with `fade` + `enable`.
4. **Motion** — `zoompan` push-ins on stills, `xfade` dissolves across the showcase.
5. **Music** — `make_music.py` synthesizes a 100 BPM track: kick, hat, clap, bass,
   detuned pads, plucks, risers, impacts, sidechain ducking. Mixed and mastered to
   −14 LUFS / −2 dBTP via ffmpeg `loudnorm`.

## Rebuilding

Requires Python 3 with `pillow` and `numpy`, a static `ffmpeg` binary and the
Poppins fonts. Paths used by the scripts:

```
.tools/bin/ffmpeg          # static ffmpeg
.tools/fonts/Poppins_*.ttf # Bold / SemiBold / ExtraBold
```

Install once:

```bash
python3 -m pip install --break-system-packages imageio-ffmpeg pillow numpy
mkdir -p .tools/bin .tools/fonts
cp "$(python3 -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')" .tools/bin/ffmpeg
npm install --prefix .tools/fonts @expo-google-fonts/poppins
for w in 600SemiBold 700Bold 800ExtraBold; do
  cp ".tools/fonts/node_modules/@expo-google-fonts/poppins/$w/Poppins_$w.ttf" .tools/fonts/
done
```

Then:

```bash
python3 youtube-short/make_graphics.py   # cards, pills, masks
python3 youtube-short/make_music.py      # soundtrack
python3 youtube-short/make_cover.py      # cover
bash    youtube-short/build.sh           # final mp4
```

`.tools/` and `youtube-short/build/` are git-ignored: the toolchain is ~170 MB and
the intermediates ~70 MB.

## Note on the app's own generation

The repo is a studio UI over the MuAPI cloud. Generating *new* video through it
needs a `MUAPI_API_KEY` (`x-api-key` header, submit → poll `predictions/{id}/result`);
no key was configured in this environment, so this Short uses repo footage plus
locally assembled graphics and audio instead.
