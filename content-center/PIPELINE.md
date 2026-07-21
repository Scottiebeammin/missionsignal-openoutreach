# Content Pipeline — cheap AI short-form video system

The system for producing short-form vertical video (TikTok/Reels/Shorts) — e.g.
*Lucky Mistake* — from AI generation at **per-clip cost of cents**, fully
scriptable, with the expensive step decoupled from assembly.

```
 keyframe (image)  ──►  motion (image-to-video)  ──►  assembly (comp)  ──►  MP4
   Seedream edit          Wan 2.2 I2V on RunComfy      HyperFrames/Remotion    TikTok
   (cheap, no deploy)      (open model, GPU-time)       text/music/transitions
```

The composition layer doesn't care where clips come from — swap the generator
freely (Seedance credits → RunComfy Wan) with **zero downstream rework**.

---

## Status of the system

| Layer | Tool / asset | Status |
| --- | --- | --- |
| **Motion (I2V)** | Wan 2.2 + Lightx2v on RunComfy · `runcomfy/i2v.py` | ✅ **working, quality validated** (holds character likeness) |
| **Keyframes (image edit)** | Seedream 5.0 Pro edit · `runcomfy/seedream.py` | 🟡 scaffolded — needs a hosted reference URL |
| **Assembly** | `lucky-mistake-hf/` (HyperFrames) · `video-ads/` (Remotion) | ✅ working (text, music, transitions, render) |
| **Character consistency** | free via I2V (animates the given frame); LoRA optional | ✅ (I2V) / 🔜 (LoRA for fresh poses) |

---

## The economics (this is the whole point)

RunComfy serverless bills by **GPU-second**, so cost = *time on the machine*.

- **Cold start dominates.** First run downloads/loads ~30GB of Wan weights (~12–13 min). Actual sampling is fast (~2–3 min).
- **Batch while warm.** The machine stays warm briefly after a job — fire all clips for a scene back-to-back so you pay the cold start **once**, not per clip.
- **Slim the workflow.** The stock template runs an I2V *and* a T2V branch (4 model passes). We only need I2V → `runcomfy/wan-i2v.workflow.json` mutes T2V (~half the compute).
- **Right-size the GPU.** 48GB OOM'd on the dual branch; 80GB held it and ran **4×** faster per step (models fit, no thrashing). Slim I2V-only should fit smaller/cheaper hardware.

**Measured so far:** $20.16 → $18.22 = **$1.94** for two *cold-start, dual-branch* runs (worst case). **Target steady state** (slim + warm batch): **~$0.30–0.60/clip**, so a ~60s video (6–8 clips) ≈ **$2–4** — and it scales with no credit ceiling.

---

## SOP — make a new scene

1. **Keyframes** — for each shot, generate a still with `seedream.py` (reference + scene prompt) so characters stay on-model. Establishing shots with no recurring face can be plain text-to-image.
2. **Batch the motion** — with the (warm) slim Wan deployment, run `i2v.py` for every keyframe back-to-back:
   ```bash
   python3 runcomfy/i2v.py --image kf-01.png --prompt "<motion>" --out shot-01.mp4
   ```
3. **Assemble** — drop the clips into the comp (`lucky-mistake-hf/` or `video-ads/`), which already handles hook text, tagline, end card, music, and transitions.
4. **Render & post** — `npm run render` → vertical MP4 → TikTok.

Config for the Wan step lives in `runcomfy/runcomfy.config.json` (gitignored):
`deployment_id` + node IDs (`85` LoadImage, `86` positive prompt, `79`
width/height/length). API key is env-only (`RUNCOMFY_API_KEY` in `~/.zshenv`).

---

## Workflow catalog — this system + potential others

### Deployed / built
- **Wan 2.2 I2V** — motion from a keyframe. The core generator. (`i2v.py`, `wan-i2v.workflow.json`)
- **Seedream 5.0 Pro edit** — keyframe generation/editing via Model API, no deploy. (`seedream.py`) *Needs the reference image at a public URL — upload once to RunComfy → My Assets.*

### Roadmap (add just-in-time, not all at once)
- **Character LoRA** (RunComfy Trainer) — train a "Scottie"/"Zaria" LoRA to lock likeness across *fresh* poses/scenes for a whole series. The real consistency answer at series scale. Needs ~15–30 reference images each.
- **Upscale** (e.g. video/ESRGAN) — 480p → 1080p for crisper TikTok output.
- **Frame interpolation** (RIFE/FILM) — 16fps → 24/30fps for smoother motion.
- **Lip-sync** (Wan Animate / LatentSync) — only if characters *speak on camera* with the cloned voice; skip if dialogue is voiceover over B-roll.
- **Voice** — not a ComfyUI workflow: if Artlist is dropped, replace its voice-clone with ElevenLabs (or a TTS workflow).

### Potential other systems (same skeleton, different content)
The keyframe → I2V → assemble skeleton generalizes: product promos, faceless
explainers (text → keyframes → motion), music-driven montages, ad variations.
Only the assembly comp and prompts change.

---

## Open decisions
- **Slim redeploy** — swap the 80GB dual-branch deployment for the slim I2V-only workflow to hit the target cost. (One redeploy.)
- **Reference hosting** — where the Scottie/Zaria reference URLs live (RunComfy My Assets is simplest).
- **Cancel Artlist?** — only after replacing **music** (Artlist's core product — verify license on already-used tracks) and **voice cloning**. Generation is covered by RunComfy; music/voice are the gaps. See vault note.
