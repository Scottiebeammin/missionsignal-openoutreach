# Animation Systems — Research, Analysis & Integration Plan

*Created: 2026-07-01 · Anansi Atlas Content Center*

Scott gathered research (YouTube tutorials + 3 GitHub repos + a PDF prompt guide) on tools that could level up our Remotion video production. This is the analysis, what was installed, and how each slots into what we've already built. **Operational reminders** (the workflow, the GSAP gotcha, the library map) live in `BRAND-TEMPLATE.md §0b–0d` — this doc is the research record / "why."

## Sources reviewed
1. **Rangy AI "Motion-Graphics Starter Kit"** (PDF, Pouya Eti) — a 2-part Claude Code + Remotion prompt guide
2. [github.com/remotion-dev/skills](https://github.com/remotion-dev/skills) — official Remotion best-practices skill
3. [github.com/greensock/gsap-skills](https://github.com/greensock/gsap-skills) — official GSAP skill (8 modules)
4. [github.com/chrisvoncsefalvay/claude-d3js-skill](https://github.com/chrisvoncsefalvay/claude-d3js-skill) — community D3.js skill
5. [github.com/mrdoob/three.js](https://github.com/mrdoob/three.js) — 3D/WebGL engine
6. [lottiefiles.com](https://lottiefiles.com/free-animations/repository) — free Lottie animation library (Scott's account connected to GitHub)
7. `gsap-public.zip` (Downloads) — a raw Club-GSAP plugin export, superseded by installing the real `gsap` npm package (all former Club plugins are free since the Webflow acquisition)

## What each one actually is, and the call made

| Tool | What it is | Fits our workflow? | Decision |
|---|---|---|---|
| **Rangy AI PDF** | Prompt guide for building *standalone overlay graphics* (title cards, lower thirds) that export with alpha and get handed to an external editor (Premiere/CapCut). Different model from ours — we render complete self-contained final videos, no external editor. | Partially — the workflow discipline and motion rules transfer even though the "hand off to an editor" model doesn't. | **Adopted the rules, not the workflow.** Folded into `BRAND-TEMPLATE.md §0b–0c` (skeleton→timing→motion→polish; full enter+exit; stagger; anticipation+overshoot+settle; title-safe margins; sound design). The alpha/ProRes export commands are worth keeping in mind if we ever need a standalone overlay (e.g. a "New" badge) for a different tool — not needed today. |
| **remotion-dev/skills** | Official Remotion best-practices — confirms conventions we already follow (render a still before a full clip; `interpolate()`/individual transform props over composed strings; CSS transitions/animations are forbidden in Remotion). | Yes — validates our existing approach, no changes needed. | **Installed** (`.agents/skills/remotion-best-practices`). |
| **GSAP (gsap-skills + npm)** | Animation library. 8 skill modules: gsap-core, timeline, plugins, utils, react, performance, frameworks, scrolltrigger. Most of it (ScrollTrigger, Draggable, Observer, ScrollSmoother) is for scroll-driven *interactive web pages* — dead weight for a headless video render. The real value: richer easing (`back`, `elastic`) and cleaner multi-step sequencing than our hand-rolled frame-offset `delay` props, plus `SplitText`/`DrawSVGPlugin` for kinetic typography and line-draw effects. | Yes, selectively. | **Installed** (npm `gsap` + all 8 skill modules). Built `GsapRise` in `components.tsx` as the reference integration — see the mode warning below. |
| **D3.js skill** | Data-driven chart/visualization library (bar, line, network, geo). | Not yet — we don't have chart-style content in any current video; our custom visuals (`OrbWeb`, `BubbleCard`) are hand-built SVG, not data-bound charts. | **Installed** (skill + npm `d3`), **parked**. Reach for it the day we want an animated stat/chart (e.g. "89% of pilot seats filled" as a live bar). |
| **Three.js** | Full 3D/WebGL engine. | No — our brand is flat, premium 2D (navy/gold, Fraunces). 3D doesn't fit the visual identity and adds real bundle/complexity cost for marginal benefit. | **Installed** (npm `three` + `@types/three`) per instruction, **parked** — don't reach for this without a specific, deliberate 3D idea. |
| **Lottie (`@remotion/lottie`)** | Pre-made JSON micro-animations (shine sweeps, particle bursts, checkmarks) from LottieFiles. We already had the npm package installed but unused. | Yes — the fastest, lowest-risk win of everything reviewed. | **Wrapper built** (`LottieAsset` in `components.tsx`) and `public/lottie/` folder created (same drop-in pattern as `public/broll/`). **Waiting on Scott** to export 1–3 JSONs from his connected LottieFiles account (shine sweep for CTA buttons, a checkmark pop for `CheckLine`, maybe a particle burst for a payoff moment) — drop into `public/lottie/`, wire in as `<LottieAsset src={staticFile("lottie/shine-sweep.json")} />`. |
| **gsap-public.zip** | Raw pre-Webflow-acquisition GSAP plugin export (esm/umd files, no `package.json`). | No longer needed — GSAP is fully free via npm now (all former Club plugins included). | **Not used.** Installed the real `gsap` npm package instead — cleaner, versioned, updatable. Zip kept only as an offline reference if ever needed. |

## The "two ways to use it" — resolved and confirmed from the real installed skill files
This is genuinely important and easy to get wrong, so it's called out prominently in `BRAND-TEMPLATE.md §0d`:

- **GSAP's default is a live ticker** (`requestAnimationFrame`, real wall-clock time) — correct for a normal website, **wrong for Remotion** (which renders frames out of real-time order; a ticker-driven animation is non-deterministic).
- **The required mode inside Remotion:** build the timeline `paused: true`, then manually call `tl.time(frame / fps)` or `tl.progress(p)` every render, driven by `useCurrentFrame()`. Confirmed straight from the installed `gsap-timeline/SKILL.md`: *"paused: true — create paused; call `.play()` to start"* and *"`tl.time(2)` — seek to 2 seconds"* / *"`tl.progress(0.5)` — seek to 50%."*

`GsapRise` (in `components.tsx`) is the reference implementation of the correct (seek) pattern — copy it for any new GSAP-powered component.

## What's installed right now (2026-07-01)
- **npm** (in `content-center/video-ads/`): `gsap`, `d3`, `three`, `@types/d3`, `@types/three` (added to `@remotion/lottie`, already present).
- **Claude Code skills** (`.agents/skills/`, symlinked for this project): `gsap-core`, `gsap-timeline`, `gsap-plugins`, `gsap-utils`, `gsap-react`, `gsap-performance`, `gsap-frameworks`, `gsap-scrolltrigger`, `d3-viz`, `remotion-best-practices`.
- **New components** (`src/components.tsx`): `GsapRise` (GSAP seek-mode rise/entrance), `LottieAsset` (drop-in Lottie JSON wrapper, graceful if the file isn't there yet).
- **New folder**: `public/lottie/` (gitignored contents, same pattern as `public/broll/`).
- Everything verified compiling clean via `remotion still` — none of this has shipped in a rendered video yet; it's capability, ready for the next post.

## Next steps (not yet done)
1. Scott exports 1–3 Lottie JSONs from his connected LottieFiles account → drop in `public/lottie/` → wire into a CTA/payoff moment.
2. First real use of `GsapRise` on the next new post (try its `back.out(1.7)` ease vs. our default `spring()` — compare feel).
3. If/when we want kinetic character-by-character text, reach for GSAP `SplitText` (`gsap-plugins` skill) — not yet wrapped as a component.
4. D3/Three.js stay parked until a specific need (a stat/chart video, or a deliberate 3D idea) comes up.
