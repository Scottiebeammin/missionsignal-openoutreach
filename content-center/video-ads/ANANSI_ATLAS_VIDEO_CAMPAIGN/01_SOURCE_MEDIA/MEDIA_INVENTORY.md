# Media Inventory — Anansi Atlas Three-Video Campaign

Audited 2026-07-31. All paths relative to `content-center/video-ads/` unless noted.

## Finished films
| Asset | Path | Reusable? |
|---|---|---|
| The Whole Field (6:10 show version) | `out/AnansiVisionFilm.mp4` + Captioned | Yes — concept beats, but campaign videos are new builds |
| The Whole Field source | `src/oneoffs/AnansiVisionFilm.tsx` | Yes — scene patterns, timing idioms |
| BAM film + BAM vision variant | `out/BamOrlandoFilm*.mp4`, `out/AnansiVisionFilmBAM.mp4` | **NO — see BAM exclusion list** |
| Web of Opportunity film (75.6s) | `out/WebOfOpportunityFilm.mp4` | Reference only (older register) |

## Brand & logo
| Asset | Path | Notes |
|---|---|---|
| Official emblem (alpha) | `public/anansi-emblem-785.png` | THE logo for all animation. `logo-mark.png`/`anansi-mark.png` have no alpha — renders as navy box, do not use |
| Brand tokens | `src/brand.ts` | navy #0d1b3d, gold #d4a017, goldLight #f3dd8c, cream; six NODES |
| Brand rules | `BRAND-TEMPLATE.md`, vault Motion/Graphic Language docs | Film register: no teal/rose |
| Component library | `src/components.tsx` | OrbWeb, HyperFrames, ActBridge, ThreadRule, ConceptFrame, WireBlock, NodeField, UISpotlight, CountUpFigure, GradientMesh, Rise, Eyebrow, SceneDissolve, Subtitles, LogoLockup, ScreenshotPanel, LaptopScreenshotPanel |

## Platform screenshots (2x DPR, 1600×1000 CSS, 16:10)
| Set | Files | Whose data | Cleared for campaign? |
|---|---|---|---|
| `hd-*` (6 shots) | dashboard, web, ecosystem, opps-default, opps-peersize, readiness | **Empowered Girls Inc.** live workspace (project 14) | Yes — Scott authorized EGI workspace data on screen 2026-07-29; impact figures stay OUT |
| `bam-*`, `bamv-*` | 8 shots | BAM Orlando (project 18) | **NO — board-room only** |
| `shot-*3`, legacy singles | ~25 shots | Creative Display demo (pk=1) | Yes — anonymized demo profile |

## Audio
| Asset | Path | Notes |
|---|---|---|
| Vision film VO master + alignment | `public/anansi-vision-film-vo.mp3/.alignment.json` | 260.7s Christopher master — reusable only for the finished film |
| Score stems | `public/music/stem-minimal.mp3` (145s), `stem-build.mp3` (110s), `stem-resolve.mp3` (126s) | Generated, licensed to us; reusable; new shorter stems preferred for 30s/90s cuts |
| `film-bed.mp3` | `public/music/` | 80s legacy bed |

## Motion/other
- `public/broll/globe-loop.mp4` — banned for county register (says "global SaaS")
- `../anansi-atlas-hf/` — HyperFrames microsite (intro.mp4, outro.mp4, scene renders) — contains the cal.com booking link end card; harvest for social end-card reference
- `public/lottie/` — misc lottie assets

## VO pipeline (tooling, all working)
`ads.config.mjs` (scripts + ENGLISH-LOCKED VOICE_SETTINGS) → `scripts/gen-vo-timestamped.mjs` → `scripts/vo-line-slices.mjs` → computed beat map. Music: `scripts/gen-music-stems.mjs`. Captures: `scripts/capture-hd-shots.py`.
