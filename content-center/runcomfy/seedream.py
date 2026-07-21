#!/usr/bin/env python3
"""RunComfy Seedream image-EDIT: reference image URL + prompt -> keyframe.

Generates consistent keyframes (e.g. Scottie placed in a new scene) via the
RunComfy Model API — a hosted model, NO deployment needed.

IMPORTANT: Seedream's Model API takes the reference image as a PUBLIC HTTPS URL
(base64 is NOT supported). Upload the reference once to RunComfy > My Assets
(or any public host) and pass its URL.

Setup:
  export RUNCOMFY_API_KEY=...          # same key as the Wan tools; env only

Run:
  python3 seedream.py \
    --image-url https://.../scottie-ref.png \
    --prompt "Same man, same face and beard, tired expression, holding a dark duffel bag with a casino luggage tag, stepping into a dim neon-lit after-hours pool hall at night. Cinematic, warm neon, shallow depth of field." \
    --out out/kf-01-arrival.png

Then animate the keyframe with i2v.py.
Stdlib only. Result URLs expire, so it downloads immediately.
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

# swap for another Seedream variant if desired (e.g. bytedance/seedream-4-5/edit)
MODEL = "bytedance/seedream-5.0-pro/image-to-image"
BASE = "https://model-api.runcomfy.net/v1"
DONE_OK = {"completed", "succeeded"}
DONE_BAD = {"failed", "error", "cancelled", "canceled"}


def api(url, token, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    attempts = 6 if method == "GET" else 1  # never retry a POST (avoid dup jobs)
    last = None
    for _ in range(attempts):
        try:
            req = urllib.request.Request(url, data=data, method=method)
            req.add_header("Authorization", f"Bearer {token}")
            if data is not None:
                req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            last = e
            if method == "GET" and e.code in (500, 502, 503, 504):
                time.sleep(6)
                continue
            raise
        except urllib.error.URLError as e:
            last = e
            if method == "GET":
                time.sleep(6)
                continue
            raise
    raise last


def main():
    ap = argparse.ArgumentParser(description="Seedream image-edit keyframe")
    ap.add_argument("--image-url", required=True, help="public HTTPS url of the reference image")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True, help="output .png / .jpg")
    ap.add_argument("--resolution", default="2K", choices=["1K", "2K"])
    args = ap.parse_args()

    token = os.environ.get("RUNCOMFY_API_KEY")
    if not token:
        sys.exit("Set RUNCOMFY_API_KEY (export in ~/.zshenv). Env only.")
    if not args.image_url.startswith("https://"):
        sys.exit("--image-url must be a public HTTPS URL (Seedream doesn't take base64).")

    body = {"prompt": args.prompt, "image": [args.image_url], "resolution": args.resolution}
    print(f"-> submit {MODEL}")
    sub = api(f"{BASE}/models/{MODEL}", token, "POST", body)
    rid = sub["request_id"]
    print(f"   request_id={rid}")

    deadline = time.time() + 600
    while True:
        st = api(f"{BASE}/requests/{rid}/status", token)
        s = (st.get("status") or "").lower()
        print(f"   status={s}")
        if s in DONE_OK:
            break
        if s in DONE_BAD:
            sys.exit(f"job {s}: {json.dumps(st)}")
        if time.time() > deadline:
            sys.exit("timed out")
        time.sleep(4)

    res = api(f"{BASE}/requests/{rid}/result", token)
    out_url = res.get("image") or (res.get("images") or [None])[0]
    if isinstance(out_url, dict):
        out_url = out_url.get("url")
    if not out_url:
        sys.exit("no image url in result: " + json.dumps(res)[:600])

    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    dl = urllib.request.Request(out_url)
    dl.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(dl) as r, open(out, "wb") as f:
        f.write(r.read())
    print(f"OK  saved {out}")


if __name__ == "__main__":
    main()
