#!/usr/bin/env python3
"""Poll an EXISTING RunComfy request and download its video when done.
Usage: python3 fetch_result.py <deployment_id> <request_id> <out.mp4>
Reuses RUNCOMFY_API_KEY from env. Lets us grab a job already in flight
instead of re-submitting (and paying again)."""
import json, os, sys, time, urllib.request, urllib.error

API = "https://api.runcomfy.net/prod/v2"
DONE_OK = {"completed", "succeeded"}
DONE_BAD = {"failed", "error", "cancelled", "canceled"}
dep, rid, out = sys.argv[1], sys.argv[2], sys.argv[3]
tok = os.environ["RUNCOMFY_API_KEY"]


def api(path):
    # resilient to transient 5xx / network blips during long polls
    last = None
    for attempt in range(6):
        try:
            r = urllib.request.Request(f"{API}/deployments/{dep}/requests/{rid}/{path}")
            r.add_header("Authorization", f"Bearer {tok}")
            with urllib.request.urlopen(r) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (500, 502, 503, 504):
                print(f"  (transient {e.code}, retrying)", flush=True)
                time.sleep(6)
                continue
            raise
        except urllib.error.URLError as e:
            last = e
            print(f"  (network blip, retrying)", flush=True)
            time.sleep(6)
            continue
    raise last


deadline = time.time() + 3000
while True:
    s = (api("status").get("status") or "").lower()
    print(f"status={s}", flush=True)
    if s in DONE_OK:
        break
    if s in DONE_BAD:
        sys.exit(f"job {s}")
    if time.time() > deadline:
        sys.exit("timed out")
    time.sleep(10)

res = api("result")
url = None
for node in res.get("outputs", {}).values():
    for key in ("videos", "gifs", "images"):
        for item in node.get(key, []) or []:
            u = item.get("url", "")
            if u.split("?")[0].lower().endswith((".mp4", ".webm", ".mov", ".gif")):
                url = u
                break
if not url:
    sys.exit("no video url: " + json.dumps(res)[:800])
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
dl = urllib.request.Request(url)
dl.add_header("Authorization", f"Bearer {tok}")  # storage URL needs auth
with urllib.request.urlopen(dl) as resp, open(out, "wb") as fh:
    fh.write(resp.read())
print(f"OK saved {out}", flush=True)
print("timing: " + json.dumps({k: res.get(k) for k in ("created_at", "finished_at")}), flush=True)
