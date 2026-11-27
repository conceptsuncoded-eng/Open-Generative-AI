#!/usr/bin/env bash
# Assemble the Open Generative AI YouTube Short (1080x1920, 30fps, 27s).
set -euo pipefail
cd "$(dirname "$0")/.."

FF=.tools/bin/ffmpeg
B=youtube-short/build
A=youtube-short/assets
OUT=youtube-short/open-generative-ai-short.mp4
L="-loop 1 -framerate 30"
mkdir -p "$B/seg"

# ---------- neutral dark backdrop for the demo section --------------------
cp "$B/bg_hook.png" "$B/demo_bg.png"

# ---------- A. HOOK (0 - 3.2s) -------------------------------------------
"$FF" -y -loglevel error -i "$B/bg_hook.png" -i "$B/hook_text.png" -filter_complex "
 [0:v]scale=1080:1920,setsar=1[b];
 [1:v]format=rgba[t];
 [b][t]overlay=0:0[o];
 [o]zoompan=z='min(1.0+0.00022*on,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=97:s=1080x1920:fps=30,
    trim=duration=3.2,setpts=PTS-STARTPTS,fade=t=in:st=0:d=0.3,format=yuv420p[v]" \
 -map "[v]" -r 30 -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p "$B/seg/a.mp4"

# ---------- B. LIVE DEMO (3.2 - 12.0s) -----------------------------------
# the raw recording zooms in and out, so use three clean shots only
"$FF" -y -loglevel error -i docs/assets/demo.mp4 -filter_complex "
 [0:v]trim=0.70:2.10,setpts=PTS-STARTPTS[s1];
 [0:v]trim=10.30:13.05,setpts=PTS-STARTPTS[s2];
 [0:v]trim=15.25:18.55,setpts=PTS-STARTPTS[s3];
 [s1][s2][s3]concat=n=3:v=1:a=0,tpad=stop_mode=clone:stop_duration=1.35,fps=30,setsar=1[v]" \
 -map "[v]" -c:v libx264 -preset veryfast -crf 16 -pix_fmt yuv420p "$B/demo_cut.mp4"

"$FF" -y -loglevel error \
 -i "$B/demo_bg.png" \
 $L -t 8.8 -i "$B/card_shadow.png" \
 -i "$B/demo_cut.mp4" \
 $L -t 8.8 -i "$B/card_mask.png" \
 $L -t 8.8 -i "$B/brand.png" \
 $L -t 8.8 -i "$B/pill_1.png" $L -t 8.8 -i "$B/pill_2.png" $L -t 8.8 -i "$B/pill_3.png" \
 -filter_complex "
 [0:v]scale=1080:1920,setsar=1[bg];
 [2:v]crop=1570:866:116:128,scale=1000:555,setsar=1[card0];
 [3:v]format=gray[mask];
 [card0][mask]alphamerge[card];
 [bg][1:v]overlay=10:670[bg2];
 [bg2][card]overlay=40:700[o0];
 [o0][4:v]overlay=(W-w)/2:176[o1];
 [5:v]format=rgba,fade=t=in:st=0.10:d=0.22:alpha=1,fade=t=out:st=1.10:d=0.18:alpha=1[p1];
 [6:v]format=rgba,fade=t=in:st=1.40:d=0.20:alpha=1,fade=t=out:st=3.98:d=0.20:alpha=1[p2];
 [7:v]format=rgba,fade=t=in:st=4.18:d=0.20:alpha=1[p3];
 [o1][p1]overlay=(W-w)/2:576:enable='between(t,0.10,1.30)'[o2];
 [o2][p2]overlay=(W-w)/2:576:enable='between(t,1.40,4.18)'[o3];
 [o3][p3]overlay=(W-w)/2:576:enable='gte(t,4.18)',format=yuv420p[v]" \
 -map "[v]" -t 8.8 -r 30 -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p "$B/seg/b.mp4"

# ---------- C. AI ART SHOWCASE (12.0 - 21.0s) ----------------------------
"$FF" -y -loglevel error -i "$A/art1.webp" -filter_complex "
 [0:v]scale=1620:2903,setsar=1,
   zoompan=z='min(1.04+0.00046*on,1.17)':x='iw/2-(iw/zoom/2)':y='ih*0.55-(ih/zoom/2)':d=98:s=1080x1920:fps=30,
   trim=duration=3.25,setpts=PTS-STARTPTS,unsharp=5:5:0.5,format=yuv420p[v]" \
 -map "[v]" -r 30 -c:v libx264 -preset veryfast -crf 16 -pix_fmt yuv420p "$B/seg/c1.mp4"

"$FF" -y -loglevel error -i "$A/art2.webp" -filter_complex "
 [0:v]scale=1620:2903,setsar=1,
   zoompan=z='max(1.17-0.00052*on,1.04)':x='iw/2-(iw/zoom/2)':y='ih*0.45-(ih/zoom/2)':d=98:s=1080x1920:fps=30,
   trim=duration=3.25,setpts=PTS-STARTPTS,unsharp=5:5:0.5,format=yuv420p[v]" \
 -map "[v]" -r 30 -c:v libx264 -preset veryfast -crf 16 -pix_fmt yuv420p "$B/seg/c2.mp4"

"$FF" -y -loglevel error -i "$A/art3.webp" -filter_complex "
 [0:v]scale=1620:2903,setsar=1,
   zoompan=z='min(1.05+0.00044*on,1.17)':x='iw/2-(iw/zoom/2)':y='ih*0.48-(ih/zoom/2)':d=98:s=1080x1920:fps=30,
   trim=duration=3.25,setpts=PTS-STARTPTS,unsharp=5:5:0.5,format=yuv420p[v]" \
 -map "[v]" -r 30 -c:v libx264 -preset veryfast -crf 16 -pix_fmt yuv420p "$B/seg/c3.mp4"

"$FF" -y -loglevel error -i "$B/seg/c1.mp4" -i "$B/seg/c2.mp4" -i "$B/seg/c3.mp4" \
 $L -t 9.0 -i "$B/scrim.png" $L -t 9.0 -i "$B/brand.png" \
 $L -t 9.0 -i "$B/chip_cinematic.png" $L -t 9.0 -i "$B/chip_anime.png" $L -t 9.0 -i "$B/chip_3d.png" \
 -filter_complex "
 [0:v][1:v]xfade=transition=fade:duration=0.375:offset=2.875[x1];
 [x1][2:v]xfade=transition=fade:duration=0.375:offset=5.75[x2];
 [x2][3:v]overlay=0:1020[o0];
 [o0][4:v]overlay=(W-w)/2:176[o1];
 [5:v]format=rgba,fade=t=in:st=0.30:d=0.28:alpha=1,fade=t=out:st=2.30:d=0.28:alpha=1[q1];
 [6:v]format=rgba,fade=t=in:st=3.35:d=0.28:alpha=1,fade=t=out:st=5.20:d=0.28:alpha=1[q2];
 [7:v]format=rgba,fade=t=in:st=6.20:d=0.28:alpha=1[q3];
 [o1][q1]overlay=(W-w)/2:1210:enable='between(t,0.30,2.58)'[o2];
 [o2][q2]overlay=(W-w)/2:1210:enable='between(t,3.35,5.48)'[o3];
 [o3][q3]overlay=(W-w)/2:1210:enable='gte(t,6.20)',format=yuv420p[v]" \
 -map "[v]" -t 9.0 -r 30 -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p "$B/seg/c.mp4"

# ---------- D. END CARD (21.0 - 27.0s) -----------------------------------
"$FF" -y -loglevel error -i "$B/endcard.png" -filter_complex "
 [0:v]scale=1080:1920,setsar=1,
   zoompan=z='min(1.0+0.00025*on,1.05)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=181:s=1080x1920:fps=30,
   trim=duration=6.0,setpts=PTS-STARTPTS,fade=t=in:st=0:d=0.45,format=yuv420p[v]" \
 -map "[v]" -r 30 -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p "$B/seg/d.mp4"

# ---------- concat + soundtrack ------------------------------------------
cat > "$B/seg/list.txt" <<EOF
file 'a.mp4'
file 'b.mp4'
file 'c.mp4'
file 'd.mp4'
EOF
"$FF" -y -loglevel error -f concat -safe 0 -i "$B/seg/list.txt" -c copy "$B/seg/picture.mp4"

"$FF" -y -loglevel error -i "$B/seg/picture.mp4" -i "$B/music.wav" -filter_complex "
 [0:v]fps=30,format=yuv420p[v];
 [1:a]loudnorm=I=-14:TP=-1.2:LRA=9,aformat=sample_rates=48000:channel_layouts=stereo[a]" \
 -map "[v]" -map "[a]" -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p \
 -c:a aac -b:a 192k -ar 48000 -movflags +faststart -shortest \
 -metadata title="Open Generative AI — 200+ models, one studio" "$OUT"

echo "built: $OUT"
"$FF" -i "$OUT" 2>&1 | grep -E "Duration|Stream"
