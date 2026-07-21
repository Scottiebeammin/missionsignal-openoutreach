#!/usr/bin/env python3
"""
Seedance 2.0 via RunComfy's Model API — reference image(s) + prompt -> video clip.

Same Seedance 2.0 we used in Artlist, called directly at API cost (~cents/clip)
instead of Artlist's credit markup. No ComfyUI workflow to deploy — the model
endpoint is fixed. Output drops straight into the Lucky Mistake comp.

Setup (once):
  export RUNCOMFY_API_KEY=rc_...        # env only; never commit

Run:
  python3 seedance.py \
    --image https://.../scottie-keyframe.png \
    --prompt "slow cinematic push-in, warm neon, subtle natural movement" \
    --duration 15 --resolution 1080p --aspect 9:16 \
    --out ../video-ads/public/lucky-mistake/shot-3.mp4

--image accepts a public URL, or a local file (encoded as a base64 data URI —
if the API rejects that, host the image and pass its URL). Repeat --image for
multiple reference images (up to 9). Stdlib only.
"""
import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.request

MODEL_URL = "https://model-api.runcomfy.net/v1/models/bytedance/seedance-2.0/pro"
REQ_BASE = "https://model-api.runcomfy.net/v1/requests"
DONE_OK = {"completed", "succeeded", "success"}
DONE_BAD = {"failed", "error", "cancelled", "canceled"}


def api(url, token, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def as_image(path):
    if path.startswith(("http://", "https://")):
        return path
    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()


def extract_video_url(result):
    out = result.get("output") or result.get("outputs") or {}
    # output.video (string) or output.videos (list of str/dict)
    v = out.get("video")
    if isinstance(v, str):
        return v
    if isinstance(v, dict) and v.get("url"):
        return v["url"]
    for vs in (out.get("videos"), result.get("videos")):
        if isinstance(vs, list) and vs:
            first = vs[0]
            return first if isinstance(first, str) else first.get("url")
    # last resort: any mp4-ish url anywhere in the blob
    blob = json.dumps(result)
    import re
    m = re.search(r'https?://[^\s"\']+\.(?:mp4|mov|webm)', blob)
    return m.group(0) if m else None


def main():
    ap = argparse.ArgumentParser(description="Seedance 2.0 via RunComfy Model API")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--image", action="append", default=[], help="reference image URL or local path (repeatable)")
    ap.add_argument("--out", required=True, help="output .mp4 path")
    ap.add_argument("--duration", type=int, default=5, help="4-15s (default 5)")
    ap.add_argument("--resolution", default="1080p", choices=["480p", "720p", "1080p", "4k"])
    ap.add_argument("--aspect", default="9:16", help="9:16, 16:9, 1:1, adaptive, ...")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--audio", action="store_true", help="let Seedance generate audio (default off; we add music in the comp)")
    args = ap.parse_args()

    token = os.environ.get("RUNCOMFY_API_KEY") or os.environ.get("YOUR_API_TOKEN")
    if not token:
        sys.exit("Set RUNCOMFY_API_KEY (export RUNCOMFY_API_KEY=...). Env only — never commit it.")

    body = {
        "prompt": args.prompt,
        "duration": args.duration,
        "resolution": args.resolution,
        "aspect_ratio": args.aspect,
        "generate_audio": bool(args.audio),
    }
    if args.image:
        body["images"] = [as_image(i) for i in args.image]
    if args.seed is not None:
        body["seed"] = args.seed

    print(f"-> submit  seedance-2.0/pro  {args.duration}s {args.resolution} {args.aspect}")
    sub = api(MODEL_URL, token, "POST", body)
    rid = sub.get("request_id") or sub.get("id")
    if not rid:
        sys.exit(f"no request_id in response: {json.dumps(sub)[:500]}")
    print(f"   request_id={rid}")

    deadline = time.time() + 1200
    while True:
        st = api(f"{REQ_BASE}/{rid}/status", token)
        status = (st.get("status") or "").lower()
        print(f"   status={status} {st.get('queue_position', '')}".rstrip())
        if status in DONE_OK:
            break
        if status in DONE_BAD:
            sys.exit(f"job {status}: {json.dumps(st)}")
        if time.time() > deadline:
            sys.exit("timed out")
        time.sleep(5)

    res = api(f"{REQ_BASE}/{rid}/result", token)
    url = extract_video_url(res)
    if not url:
        sys.exit(f"no video url in result: {json.dumps(res)[:600]}")

    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    print(f"-> download {url}")
    urllib.request.urlretrieve(url, out)
    print(f"OK  saved {out}")


if __name__ == "__main__":
    main()
