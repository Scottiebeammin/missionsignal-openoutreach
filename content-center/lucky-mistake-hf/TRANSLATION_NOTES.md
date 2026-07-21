# Translation Notes — Remotion → HyperFrames

Source: `content-center/video-ads/src/oneoffs/LuckyMistake.tsx` (Remotion, 30fps, 904 frames)
Target: `content-center/lucky-mistake-hf/index.html` (HyperFrames, one paused GSAP timeline)

Lint: 0 blockers, 0 warnings (3 `staticFile` info notes — converted to `assets/` relative paths).

## Clean mappings

- `<Sequence>` shot clips → `<video class="clip" data-start/data-duration/data-track-index>` (framework-owned playback). `OffthreadVideo` → plain `<video muted playsinline>`.
- `useCurrentFrame()` + `interpolate()` derivations → tweens on one `gsap.timeline({paused:true})` registered at `window.__timelines["main"]`. Frame offsets converted to seconds (`frame/30`).
- `spring({damping,stiffness,mass})` → GSAP `back.out(N)`:
  - hook word slam (damping 13 / stiffness 110 / mass 0.7) → `back.out(1.3)` over 0.62s
  - end-title reveal (damping 14 / stiffness 100 / mass 0.8) → `back.out(1.2)` over 0.9s
- Per-word stagger (frame index → timeline offset): hook 0.23s/word, tagline 0.09s/word.
- "breathing" drift (`interpolate` scale 1→1.035) → `fromTo` scale tween, `ease:"none"`.
- Fonts: `Georgia` → EB Garamond, `Helvetica`/`Arial` → Inter (HyperFrames injects deterministic `@font-face`; near-identical serif/sans).

## Gaps (intentional divergences from the Remotion source)

1. **Blur-clear dropped from the slams.** The Remotion hook and end-title animated `filter: blur(16px→0)` alongside the scale punch. HyperFrames' deterministic-render allowlist (`opacity, x, y, scale, rotation, color, backgroundColor, borderRadius, transforms`) excludes `filter`, which is not seek-safe. The slam is reproduced with **scale + opacity** only. Visually very close; the entrance reads the same, minus the soft-focus-to-sharp on the first ~6 frames of each word.

2. **Music volume envelope baked into the audio file.** Remotion drove volume with `volume={(f)=>interpolate(...)}` (fade-in 0→0.6 over 0.4s, hold, fade-out over 1.5s). HyperFrames supports only static `data-volume`, so the envelope was rendered into `assets/music.mp3` at translation time with ffmpeg `volume=0.6, afade in/out`, and `data-volume="1"`. Result is identical; the ramp just lives in the file instead of the timeline.

## Not verified against a Remotion SSIM baseline

The formal eval harness (render Remotion baseline + SSIM diff) was not run — the two outputs are not expected to be frame-identical because of gap (1) (blur removed) and a bundled-font substitution. Verified instead by `hyperframes check` (0 errors, contrast 13/13 AA) + eyeballed snapshots at all three text beats.
