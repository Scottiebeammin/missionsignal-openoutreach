#!/usr/bin/env python3
"""
RunComfy image-to-video: keyframe + motion prompt -> a video clip.

Swaps the expensive Artlist/Seedance step (~3-9k credits/clip) for a cheap
ComfyUI I2V run on RunComfy's serverless API. Output drops straight into the
Lucky Mistake comp (public/lucky-mistake/shot-N.mp4).

Setup (once):
  1. Deploy an image-to-video workflow on RunComfy ("Deploy workflow as API").
  2. Copy the deployment_id + note the node IDs for the prompt and image inputs.
  3. Fill runcomfy.config.json (copy from runcomfy.config.example.json).
  4. export RUNCOMFY_API_KEY=...        # never commit this; env only

Run:
  python3 i2v.py --image keyframe.png --prompt "slow cinematic push-in ..." \
                 --out ../video-ads/public/lucky-mistake/shot-3.mp4

Stdlib only — no pip install. Result URLs on RunComfy expire after 7 days,
so this downloads immediately.
"""
import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.request
import urllib.error

API_BASE = "https://api.runcomfy.net/prod/v2"
DONE_OK = {"completed", "succeeded"}
DONE_BAD = {"failed", "error", "cancelled", "canceled"}


def api(url, token, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    # Retry transient 5xx / network errors on GETs only. Never retry a POST
    # (submit) — retrying it could create a duplicate paid job.
    attempts = 6 if method == "GET" else 1
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, data=data, method=method)
            req.add_header("Authorization", f"Bearer {token}")
            if data is not None:
                req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            last = e
            if method == "GET" and e.code in (500, 502, 503, 504):
                print(f"   (transient {e.code}, retrying)")
                time.sleep(6)
                continue
            raise
        except urllib.error.URLError as e:
            last = e
            if method == "GET":
                print("   (network blip, retrying)")
                time.sleep(6)
                continue
            raise
    raise last


def as_image_input(path):
    """Local path -> base64 data URI; an http(s) URL is passed through as-is."""
    if path.startswith(("http://", "https://")):
        return path
    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()


def find_output_url(outputs):
    """Pull the first video-ish URL out of the ComfyUI outputs map."""
    vid_ext = (".mp4", ".webm", ".mov", ".gif")
    for node in outputs.values():
        for key in ("videos", "gifs", "images"):
            for item in node.get(key, []) or []:
                url = item.get("url", "")
                if url.split("?")[0].lower().endswith(vid_ext):
                    return url
    # fallback: any url at all (e.g. workflow only tags "images")
    for node in outputs.values():
        for items in node.values():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and item.get("url"):
                        return item["url"]
    return None


def main():
    ap = argparse.ArgumentParser(description="RunComfy image-to-video")
    ap.add_argument("--image", required=True, help="keyframe path or public URL")
    ap.add_argument("--prompt", required=True, help="motion prompt")
    ap.add_argument("--out", required=True, help="output .mp4 path")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument(
        "--config",
        default=os.path.join(os.path.dirname(__file__), "runcomfy.config.json"),
    )
    args = ap.parse_args()

    token = os.environ.get("RUNCOMFY_API_KEY")
    if not token:
        sys.exit("Set RUNCOMFY_API_KEY (export RUNCOMFY_API_KEY=...). Env only — never commit it.")
    if not os.path.exists(args.config):
        sys.exit(f"Missing {args.config} — copy runcomfy.config.example.json and fill it in.")

    cfg = json.load(open(args.config))
    dep = cfg["deployment_id"]

    overrides = {
        cfg["prompt_node"]: {"inputs": {cfg.get("prompt_input", "text"): args.prompt}},
        cfg["image_node"]: {"inputs": {cfg.get("image_input", "image"): as_image_input(args.image)}},
    }
    if args.seed is not None and cfg.get("seed_node"):
        overrides[cfg["seed_node"]] = {"inputs": {cfg.get("seed_input", "seed"): args.seed}}

    print(f"-> submit  deployment={dep}")
    sub = api(f"{API_BASE}/deployments/{dep}/inference", token, "POST", {"overrides": overrides})
    rid = sub["request_id"]
    print(f"   request_id={rid}")

    deadline = time.time() + cfg.get("timeout_seconds", 900)
    while True:
        st = api(f"{API_BASE}/deployments/{dep}/requests/{rid}/status", token)
        status = (st.get("status") or "").lower()
        print(f"   status={status} {st.get('queue_position', '')}".rstrip())
        if status in DONE_OK:
            break
        if status in DONE_BAD:
            sys.exit(f"job {status}: {json.dumps(st)}")
        if time.time() > deadline:
            sys.exit("timed out waiting for job")
        time.sleep(cfg.get("poll_seconds", 5))

    res = api(f"{API_BASE}/deployments/{dep}/requests/{rid}/result", token)
    url = find_output_url(res.get("outputs", {}))
    if not url:
        sys.exit(f"no output file in result: {json.dumps(res)[:600]}")

    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    print(f"-> download {url}")
    dl = urllib.request.Request(url)
    dl.add_header("Authorization", f"Bearer {token}")  # storage URL needs auth
    with urllib.request.urlopen(dl) as resp, open(out, "wb") as fh:
        fh.write(resp.read())
    print(f"OK  saved {out}")


if __name__ == "__main__":
    main()
