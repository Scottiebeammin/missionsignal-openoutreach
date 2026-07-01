# Campaign Brief → Existing Build (alignment map)

*Created: 2026-07-01 · Anansi Atlas Content Center*

A detailed campaign brief came in (the "From Scattered Opportunity to Focused Action" ChatGPT prompt). Per the brief's own rule — *"inspect the existing repo… follow current project patterns instead of inventing a new structure"* — most of what it asks for **already exists** in this content center. This maps the brief's 12 output sections + video deliverables onto our files, so we build the *new* piece and don't duplicate the rest.

## The one genuinely new deliverable → BUILT
**Main product walkthrough video** — "From Scattered Opportunity to Focused Action" (~110s), the full journey (landing → apply → mission intake → dashboard → Snapshot → Funders → Partners → Government → Resources → Readiness → Risks → Routes to Capital → Next Steps → pilot CTA).
- Composition: `video-ads/src/oneoffs/ProductWalkthrough.tsx`
- **Data schema** (the brief's ask): `video-ads/src/data/walkthroughSections.ts` — edit section copy without touching the video.
- Uses **real product screenshots** (`video-ads/public/screenshots/*.png`, 11 pages captured live off the anonymized Creative Display profile), our `ScreenshotPanel` motion frame, and dip-to-navy dissolves.
- VO wired (Christopher) in `ads.config.mjs` → `npm run vo` generates it.

## Brief structure → our conventions (don't rebuild ChatGPT's tree)
The brief suggests `App.tsx / SceneProblem.tsx / components/AnimatedCard.tsx / data/videoScript.ts / styles/theme.ts`. We already have equivalents — use ours:
| Brief suggested | Our existing equivalent |
|---|---|
| App.tsx / Root composition | `src/Root.tsx` |
| SceneX.tsx (per scene) | `<Sequence>` acts inside one composition (our pattern) |
| components/AnimatedCard, DashboardFrame, ConnectionMap, MetricBadge, SectionLabel, CTAButton, LogoLockup | `src/components.tsx` (BubbleCard, ScreenshotPanel, OrbWeb, FeatureCard, CTAButton, LogoLockup, SectionMarker, Eyebrow…) |
| data/videoScript.ts, data/platformSections.ts | `src/data/walkthroughSections.ts` + `ads.config.mjs` |
| styles/theme.ts | `src/brand.ts` |

## Brief's 12 output sections → where each lives
1. **Strategic creative direction** → `video-ads/BRAND-TEMPLATE.md`
2. **Main walkthrough video package** → `ProductWalkthrough.tsx` + this doc (script/scenes below in the composition & data file)
3. **Remotion implementation plan** → `BRAND-TEMPLATE.md` ("make a new ad" workflow) + `_TEMPLATE.tsx`
4. **Reusable JSON/data schema** → `src/data/walkthroughSections.ts` (typed schema: id, label, value, shot, tone, vo)
5. **Cutdown plan (60/30/15s)** → see "Cutdowns" below (to build from the same data)
6. **30-day LinkedIn calendar** → `07-content-calendar-july-2026.md` (dated, with Voice Needed column) + `02-content-calendar-and-launch.md`
7. **IG/TikTok repurposing** → in the calendars (repurpose column) + `03-pillars-and-repurposing.md`
8. **Lead conversion workflow** → `04-linkedin-and-lead-conversion.md`
9. **Automation content center** → `05-automation-and-measurement.md` + `video-ads/automation/` (n8n)
10. **Asset checklist** → `public/screenshots/` (captured) + this doc
11. **Claude Code implementation prompts** → not needed as prose — the build IS the implementation (Claude Code built it)
12. **Final recommendations / production order** → below

Content pillars, 10× hooks / CTAs / carousels / graphics / DM templates / comment replies → already delivered in `06-templates.md`, `03-pillars-and-repurposing.md`, `08-creative-ad-concepts.md`. **No regeneration needed** — reuse those.

## Cutdowns (build next, from the same data)
- **60s** — Acts 2+3-abridged (5 hero sections: Snapshot, Funders, Partners, Readiness, Next Steps) + CTA.
- **30s** — Reveal → 3 sections (Snapshot, Funders, Readiness) → CTA.
- **15s teaser** — Problem line → Snapshot shot → "Apply for the pilot." (vertical 9:16 for Reels/TikTok).
All three = new compositions reading the SAME `walkthroughSections.ts` with a `sections.filter()` — fast to build.

## Export specs (per placement)
- LinkedIn feed / website: 1:1 1080×1080 (current) · YouTube: 16:9 1920×1080 (swap dims in Root) · Reels/TikTok: 9:16 1080×1920 (like `Jul25SnapshotScroll`). H.264 MP4 throughout.

## Production order (recommended)
1. ✅ Main walkthrough built + rendered (silent).
2. **Add VO** (set `ELEVENLABS_API_KEY` → `npm run vo` → `npm run build ProductWalkthrough`) — the only step blocked on the key.
3. Build the 3 cutdowns from the shared data.
4. Slot them into the existing July calendar as the anchor content (they already reference a hero video on Jul 8 / repurposes weekly).
5. Optional: B-roll open (nonprofit-leader-at-laptop via ElevenLabs Veo) for a human cold-open.

## Music / sound (brief's ask)
Not auto-generated (no licensed track in-repo). Direction locked in `BRAND-TEMPLATE.md`: soft cinematic pulse + minimal percussion + subtle UI ticks + a warm rising tone under the CTA. Source from a licensed library (Artlist/Musicbed/Epidemic) or ElevenLabs' music tool; drop into `public/` and add a second `<Audio volume={0.15}>` track under the VO.
