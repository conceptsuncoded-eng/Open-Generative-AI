# THE LAST 10 MINUTES — production package

A 10-minute AI-generated spy thriller, planned against the model catalogue that
**this repo** actually exposes (127 text-to-video, 211 image-to-video, 92 video-to-video,
17 lip-sync, 28 audio models — read straight from `packages/studio/src/models.js`).

```
shots.csv                  31 shot groups, 600s, 82 planned clips, model assigned per shot
01_CHARACTER_REFERENCES/   four-view casting sheets for Ethan, Victor, Maya, Daniel
```

## 1. The production stack (this is the decision that matters)

| Role | Model | Why this one |
| --- | --- | --- |
| **Character engine** (goes on 18 of 31 shots) | `minimax-h3-reference-to-video` | Takes **9 reference images + 3 reference videos + 3 reference audios**, 16:9, **2K**, 5–12s. The reference-audio slot is what ties a *voice* to a face — continuity across the whole film, not just per shot. |
| **Action / long coverage** (9 shots) | `seedance-2.5-omni-reference-1080p` | **30 images, 10 videos, 10 audio refs**, 1080p, **4–30s** clips, and `omni_reference_task_type` = `reference` / `edit` / **`extend`** — extend is how you make a chase shot outlast one generation. |
| **Establishing + dawn exteriors** (2 shots) | `veo-4-text-to-video` | Strongest at place and weather; 5–30s, 16:9. No cast in frame, so no identity risk. |
| **Set-piece transitions** (2 shots) | `wan3.0-image-to-video` | Takes a **first frame and a last frame** — the door-closing and elevator-opening shots land on an exact composition. |
| **Dialogue voices** | `elevenlabs-text-to-dialogue-v3` | Built for multi-speaker scenes: generate Ethan + Victor exchanges as one take so the timing overlaps like real film. Single lines → `minimax-speech-2.6-hd`. |
| **Voice identity lock** | `minimax-voice-clone` | One cloned voice per character, reused on every line. Same voice across 600 seconds. |
| **Mouth sync** | `sync-lipsync` | Only on face-on dialogue close-ups. Everything else stays off-screen dialogue, which reads better than a bad sync. |
| **Score + SFX** | `minimax-music-3.0`, `suno-generate-sounds` | A ticking-clock motif that accelerates as the countdown runs down. |

**Do not use a single model for everything.** The 3–8s clip assumption in the original
plan is right for *editing*, but not for *generation*: use MiniMax H3 at 5–12s for
performance, Seedance at up to 30s where you need continuous motion, and cut the
result into 3–8s pieces in CapCut.

## 2. Clip budget (from `shots.csv`)

| | |
| --- | --- |
| Shot groups | 31 |
| Planned clips | **82** |
| Average clip | 7.3s |
| Runtime | 600s = 10:00 exactly |

Per sequence: Seq 1 = 4 shots, Seq 2 = 3, Seq 3 = 3, Seq 4 = 3, Seq 5 = 3,
Seq 6 = 3, Seq 7 = 3, Seq 8 = 3, Seq 9 = 3, Seq 10 = 3.

The film needs **roughly 2.6 clips per shot group**. That gap is the whole craft:
every dialogue shot is built as master (wide) + over-the-shoulder + close-up, so a
bad AI movement can be cut around instead of re-rendered.

## 3. Continuity protocol

1. The four sheets in `01_CHARACTER_REFERENCES/` are four-view (front / three-quarter /
   profile / full-body) on a neutral backdrop — exactly what a reference slot wants.
2. Upload **all four views** of a character into `reference_images` on every shot they
   appear in. More consistent than one hero portrait.
3. Record or clone each voice once, then attach it to `reference_audios`.
4. Wardrobe never changes inside a sequence. Daniel's jacket is the same jacket in
   Seq 3 and Seq 8; that sameness is what sells the illusion.
5. Match cuts are planned in the screenplay (badge → elevator door, map → reflection).
   Render both sides with the **same lighting direction**, or the cut will jar.

## 4. Master prompt, adapted for the reference engine

The original template is good. This version replaces `[Insert character reference]`
with instructions the reference-capable models actually obey:

```
PROJECT: THE LAST 10 MINUTES

Photorealistic live-action shot from an original American espionage thriller.

CAST: the person in the attached reference images is <CHARACTER>. Preserve their exact
face, hair, age, build and clothing from those references. Do not restyle them.

SCENE: <one clear action in one sentence — what changes between first and last frame>
LOCATION: Manhattan, rainy night, wet reflective surfaces, practical city lighting.
CAMERA: <shot size> · <lens impression> · <movement> · <subject position in frame>
PERFORMANCE: natural body mechanics, realistic eye line, restrained facial expression,
believable breathing. Controlled, not theatrical.
LIGHT: cool blue night key, restrained amber practicals, deep but readable shadows.
CONTINUITY: keep the geography of the location and the number of people in frame.
MOTION: one defined action per clip. Readable start pose, clean end pose for an edit.
NO: subtitles, captions, watermarks, logos, invented text, face morphing, extra people,
duplicated limbs, changing wardrobe, teleporting objects, graphic injury.
FORMAT: 16:9, 1080p or 2K, 24 fps target feel, <duration> seconds.
```

## 5. Rendering the shots

Two ways, both need a machine that can reach `api.muapi.ai` (this sandbox cannot —
its egress is allowlisted, so renders must run on your own machine or the studio).

**CLI (recommended for 82 clips):**

```bash
export MUAPI_API_KEY=...          # never committed; read from env only
cd the-last-10-minutes
python3 generate.py --shot S02 --dry-run    # inspect payload, sends nothing
python3 generate.py --shot S02              # render the 5s face test
python3 generate.py --sequence 1            # four shots of the opening minute
```

Clips land in `clips/S02_minimax-h3-reference-to-video_01.mp4` with a
`manifest.json`. Reference sheets are uploaded once and cached by content hash.
Prompts for all 31 shots are in `prompts/` (readable version: `prompts/ALL_PROMPTS.md`).

**Studio UI:** start the app, paste the key in Settings, Video tab → image-to-video →
model from §1 → reference slot → paste the prompt from `prompts/S<nn>.txt`.

## 6. How to run the studio

```bash
npm install          # first time
npm run dev          # studio on :3000 (or `npm run vite:dev` for the desktop build)
export MUAPI_API_KEY=...   # required — see .env.example
```

Video tab → **image-to-video** → pick the model from §1 → upload the character sheet
into the reference slot → paste the prompt → generate.

Then, per sequence: generate all its clips, download with the naming scheme below,
and assemble in CapCut.

```
S01_SH03_ETHAN_REACTION_01.mp4
             ^ shot   ^ clip number
```

## 7. What is done, and what is not

**Done, in this workspace:** the four casting sheets, the 31-shot plan with a model and
clip count for every shot, and the stack decision above.

**Not done:** the video itself. This sandbox's outbound network blocks `api.muapi.ai`
(DNS resolves, TCP is refused), so no key can render here — verified against a working
control host. Run `generate.py` on your own machine. The casting sheets were produced
with a separate image model, not by the app, so they are drop-in references rather than
proof that the pipeline renders.

## 8. Cost control

- Render **one 5s shot** of Ethan (S02) before anything else. If his face drifts, the
  whole film does, and you want to learn that for the price of one clip.
- Render the opening 60 seconds end-to-end next. Four shots, ~10 clips.
- Only then commit to the remaining 72.

## 9. QC before export

- [ ] Four characters hold identity and wardrobe across all 82 clips
- [ ] Countdown reads 09:42 → 03:00 → 00:00 in the right order, screen-visible
- [ ] Every action beat has readable geography (who is where, relative to what)
- [ ] Dialogue intelligible; no voice changes mid-scene
- [ ] Score ducks under speech; no clipping; true peak below -1 dB
- [ ] No watermarks, gibberish signage or duplicate people
- [ ] Runtime lands on exactly 10:00
