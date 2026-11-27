#!/usr/bin/env python3
"""
THE LAST 10 MINUTES — shot renderer for the MuAPI studio backend.

Uses the same contract as src/lib/muapi.js:
    POST https://api.muapi.ai/api/v1/{endpoint}      x-api-key
    GET  https://api.muapi.ai/api/v1/predictions/{id}/result
    POST https://api.muapi.ai/api/v1/upload_file     (multipart, field "file")

The key is read from the environment only. It is never written to disk.

    export MUAPI_API_KEY=...
    python3 generate.py --shot S02 --dry-run
    python3 generate.py --shot S02
    python3 generate.py --sequence 1
    python3 generate.py --all --max 10

Output: clips/S02_<model>_<n>.mp4 plus clips/manifest.json
"""
import argparse
import csv
import hashlib
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request

BASE = "https://api.muapi.ai"
ROOT = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(ROOT, "shots.csv")
PROMPTS = os.path.join(ROOT, "prompts")
REFS = os.path.join(ROOT, "01_CHARACTER_REFERENCES")
OUT = os.path.join(ROOT, "clips")
CACHE = os.path.join(ROOT, ".upload_cache.json")

REF_FILES = {
    "ETHAN": "ETHAN_COLE_reference_sheet.png",
    "VICTOR": "VICTOR_HALE_reference_sheet.png",
    "MAYA": "MAYA_REED_reference_sheet.png",
    "DANIEL": "DANIEL_COLE_reference_sheet.png",
}

# how each model wants its inputs named (from packages/studio/src/models.js)
MODEL_SPEC = {
    "minimax-h3-reference-to-video": {
        "ref_field": "reference_images", "ref_is_list": True,
        "extra": {"resolution": "2k"}, "max_refs": 9, "max_duration": 12, "min_duration": 5,
    },
    "seedance-2.5-omni-reference-1080p": {
        "ref_field": "images_list", "ref_is_list": True,
        "extra": {"omni_reference_task_type": "reference"}, "max_refs": 30,
        "max_duration": 30, "min_duration": 4,
    },
    "veo-4-text-to-video": {
        "ref_field": None, "ref_is_list": False, "extra": {},
        "max_refs": 0, "max_duration": 30, "min_duration": 5,
    },
    "wan3.0-image-to-video": {
        "ref_field": "image_url", "ref_is_list": False,
        "extra": {"resolution": "1080p"}, "max_refs": 1, "max_duration": 30, "min_duration": 2,
    },
}


def key():
    k = os.environ.get("MUAPI_API_KEY", "").strip()
    if not k:
        sys.exit("MUAPI_API_KEY is not set.  export MUAPI_API_KEY=...")
    if not k.isascii():
        sys.exit("MUAPI_API_KEY contains non-ASCII characters.")
    return k


def api(path, method="GET", body=None, timeout=120, k=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("x-api-key", k or key())
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, data=data, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        if e.code in (401, 403):
            sys.exit(f"401/403 — key rejected. Check the key and its credit balance. {detail}")
        raise


def upload(path, k):
    """Upload a reference image, cached by content hash so we pay once."""
    h = hashlib.sha256(open(path, "rb").read()).hexdigest()
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    if h in cache:
        return cache[h]

    boundary = "----last10min" + hashlib.md5(path.encode()).hexdigest()[:12]
    ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
    name = os.path.basename(path)
    body = b"".join([
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{name}"\r\n'.encode(),
        f"Content-Type: {ctype}\r\n\r\n".encode(),
        open(path, "rb").read(),
        f"\r\n--{boundary}--\r\n".encode(),
    ])
    req = urllib.request.Request(BASE + "/api/v1/upload_file", data=body, method="POST")
    req.add_header("x-api-key", k)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.loads(r.read().decode())
    url = d.get("url") or d.get("file_url") or (d.get("data") or {}).get("url")
    if not url:
        raise RuntimeError(f"upload returned no url: {d}")
    cache[h] = url
    json.dump(cache, open(CACHE, "w"))
    return url


def build(shot, k=None, dry=True):
    sid = shot["shot"]
    model = shot["primary_model"]
    spec = MODEL_SPEC[model]

    dur = int(round(float(shot["avg_clip_seconds"])))
    dur = max(spec["min_duration"], min(spec["max_duration"], dur))

    prompt = open(os.path.join(PROMPTS, sid + ".txt")).read().replace("<duration>", str(dur))

    payload = {"prompt": prompt, "aspect_ratio": "16:9", "duration": dur, **spec["extra"]}

    names = [n.strip() for n in shot["reference_images"].split(",") if n.strip().lower() not in ("", "none")]
    if spec["ref_field"] and names:
        urls = []
        for n in names[: spec["max_refs"]]:
            f = os.path.join(REFS, REF_FILES[n])
            if not os.path.isfile(f):
                sys.exit(f"missing reference for {n}: {f}")
            urls.append("<pending-upload>" if dry else upload(f, k))
        payload[spec["ref_field"]] = urls if spec["ref_is_list"] else urls[0]

    return model, payload, dur


def render(shot, k):
    model, payload, dur = build(shot, k, dry=False)
    status, sub = api(f"/api/v1/{model}", "POST", payload, k=k)
    rid = sub.get("request_id") or sub.get("id")
    if not rid:
        print(f"  ! no request_id: {sub}")
        return None
    print(f"  submitted {rid}  ({status})")

    t0 = time.time()
    delay = 5
    while time.time() - t0 < 1800:
        time.sleep(delay)
        delay = min(delay * 1.35, 20)
        _, res = api(f"/api/v1/predictions/{rid}/result", k=k)
        st = str(res.get("status", "")).lower()
        if st in ("completed", "succeeded", "success"):
            url = (res.get("outputs") or [None])[0] or res.get("url") or (res.get("output") or {}).get("url")
            if not url:
                print(f"  ! completed without url: {res}")
                return None
            return download(url, shot, model)
        if st in ("failed", "error", "cancelled", "canceled"):
            print(f"  ! failed: {res}")
            return None
        print(f"  … {st or 'queued'}  {int(time.time()-t0)}s", end="\r")
    print("  ! timed out")
    return None


def download(url, shot, model):
    os.makedirs(OUT, exist_ok=True)
    i = 1
    while True:
        f = os.path.join(OUT, f"{shot['shot']}_{model}_{i:02d}.mp4")
        if not os.path.exists(f):
            break
        i += 1
    urllib.request.urlretrieve(url, f)
    print(f"  saved {os.path.relpath(f, ROOT)}")
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot", help="shot id, e.g. S02")
    ap.add_argument("--sequence", type=int, help="render a whole sequence")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--max", type=int, default=0, help="stop after N shots")
    ap.add_argument("--dry-run", action="store_true", help="print payloads, send nothing")
    a = ap.parse_args()

    rows = list(csv.DictReader(open(SHOTS)))
    if a.shot:
        rows = [r for r in rows if r["shot"].upper() == a.shot.upper()]
    elif a.sequence:
        rows = [r for r in rows if r["sequence"] == f"Seq {a.sequence}"]
    elif not a.all:
        sys.exit("choose --shot S02, --sequence 1, or --all (add --dry-run to preview)")
    if a.max:
        rows = rows[: a.max]
    if not rows:
        sys.exit("no matching shots")

    k = None if a.dry_run else key()
    print(f"{len(rows)} shot(s)\n")
    for shot in rows:
        model, payload, dur = build(shot, k, dry=a.dry_run)
        print(f"{shot['shot']}  {model}  {dur}s  refs={shot['reference_images']}")
        if a.dry_run:
            print(json.dumps(payload, indent=2)[:900], "\n")
        else:
            render(shot, k)
    print("\ndone")


if __name__ == "__main__":
    main()
