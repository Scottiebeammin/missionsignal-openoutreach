# RunComfy image-to-video

Cheap clip generation for the content pipeline. Replaces the Artlist/Seedance
step (~3–9k credits/clip) with a ComfyUI image-to-video run on RunComfy's
serverless API (cents/clip). Output drops straight into a Remotion/HyperFrames
comp — nothing downstream changes.

## One-time setup

1. **Deploy an I2V workflow** on RunComfy → *Deployments* → *Deploy workflow as
   API* → Instant Deploy. Recommended model: **Wan 2.2 I2V** (quality) or
   **LTX-Video** (fast/cheap drafts). Copy the `deployment_id`.
2. **Note the node IDs** for the positive-prompt text node and the load-image
   node (open the workflow, or send me the `workflow_api.json` and I'll read them).
3. `cp runcomfy.config.example.json runcomfy.config.json` and fill it in.
4. Get your API token (RunComfy → avatar → Profile) and set it as an env var —
   **never commit it, never paste it in a tracked file:**
   ```bash
   export RUNCOMFY_API_KEY=rc_...
   ```

## Generate a clip

```bash
python3 i2v.py \
  --image path/to/keyframe.png \
  --prompt "slow cinematic push-in, subtle natural movement, warm neon, filmic" \
  --out ../video-ads/public/lucky-mistake/shot-3.mp4
```

Keyframe can be a local file (encoded as base64 automatically) or a public URL.
The script submits the job, polls until done, and downloads the result
(RunComfy deletes results after 7 days, so it grabs them immediately).

## How it fits

keyframe (cheap/free) ─▶ i2v.py ─▶ shot-N.mp4 ─▶ HyperFrames/Remotion comp ─▶ MP4

Same keyframe-first flow we used in Artlist, just swapping the paid motion step
for ComfyUI. Character consistency comes from feeding a locked keyframe as the
first frame.
