# Anansi Atlas — Ad Creation Brand & Motion System

*Created: 2026-07-01 · Anansi Atlas Content Center (Scott Foundry Group LLC)*

**This is the established template for every Anansi Atlas video ad.** When we build any new ad from the content calendar, it uses this system — so the brand looks and sounds like one company across every post. Nothing here is decided per-ad; it's decided once, here.

> Source of truth for *messaging* = `../00-brand-brief.md`. This doc is the *video/motion* system that sits on top of it.

---

## 1. Brand essence (the one thing every ad must land)
- **Name / tagline:** Anansi Atlas — *The Web of Opportunity.*
- **Category:** nonprofit opportunity intelligence platform.
- **The single idea:** *The opportunity around your mission was never missing — it was scattered. We map it so you move from scattered opportunity to focused action.*
- **The offer, always:** Founding Atlas Partners Pilot · 20 seats · $150/mo locked for life · Snapshot + 45-min walkthrough included. **Never "free."**
- **Signup, always:** anansiatlas.com/anansi-atlas

## 2. Voice & tone (how every ad talks)
Clear · practical · strategic · warm · credible · direct · conversion-focused. Confident, not hype-y. We sound like a serious platform run by people who've been in the nonprofit seat — never a charity, never a startup shouting.

**Do:** short declarative sentences · "you/your" · concrete product nouns (Dashboard, Snapshot, Opportunity Web) · one idea per line.
**Don't:** guaranteed-funding claims · exaggerated AI hype · generic SaaS filler ("revolutionary synergy") · desperation · charity-pity framing · cartoon-spider / heavy folklore (tasteful weaver/web metaphor only).

## 3. Visual identity (locked — in `src/brand.ts`)
- **Colors:** navy `#0d1b3d` + charcoal `#101826` base · **gold `#d4a017`** accent · goldLight `#f3dd8c` · teal `#0f766e` = strength · gold = gap · rose `#c46a3d` = deadline/urgency.
- **Type:** **Fraunces** (serif) for headlines/wordmark · **Inter** for everything else. Eyebrows = Inter 800, uppercase, wide tracking, goldLight.
- **Formats:** 1:1 square (1080×1080) for LinkedIn feed · 9:16 vertical (1080×1920) for Reels/TikTok · 16:9 for YouTube (swap in `Root.tsx`).

## 4. Motion language (what makes it premium, not static)
Reusable components in `src/components.tsx` — **use these, don't reinvent:**
- **`AnimatedLogoReveal`** — gold threads converge → wordmark rises → shimmer sweep. The brand beat. Every hero/flagship ad opens or pivots on this.
- **`ScreenshotPanel`** — real product UI (`public/screenshots/*.png`) in a browser-chrome frame with cinematic Ken-Burns pan/zoom. **This is our signature move** — we always show the *real* website, never a fake mockup. Re-capture per `src/oneoffs/README.md`, always from the anonymized Creative Display profile (pk=1).
- **`OrbWeb`** — the six-node mission map assembling thread-by-thread. Our core visual metaphor.
- **`BubbleCard` / `FeatureCard` / `CheckLine`** — the card vocabulary (teal=strength, gold=gap).
- **`Subtitles`** — baked-in bottom captions on EVERY ad (LinkedIn/IG/TikTok autoplay muted).
- **`Rise` / `SectionMarker` / `ProgressRail`** — entrance motion + long-form orientation.

**Pacing:** hero cuts ~4–7s per beat; feature reels ~12s per screen; nothing sits static — always a slow zoom, a rise, or a reveal in motion.

## 5. The standard ad structure (the 6-beat spine)
Every ad is some subset of these beats, in this order:
1. **Hook** (0–5s) — a sharp truth or question. Serif headline.
2. **Problem** (5–12s) — "scattered / lack of a system." Amber emphasis line.
3. **Brand reveal** — `AnimatedLogoReveal`. "This is Anansi Atlas."
4. **Product** — `ScreenshotPanel` of Dashboard → Opportunity Web → Snapshot (real UI in motion). The proof.
5. **Offer / belonging** — 20 seats, $150 locked for life, "join the family / founding partner."
6. **CTA** — logo lockup + gold pill button + signup URL. Verb: *Apply · Register Now · Join the Family.*

Short ads (8–30s) pick 2–3 beats; flagships (85s–5min) use all six with the product beat expanded.

## 6. Voice roster (ElevenLabs — auto-pulled by name)
Christopher (brand/walkthrough anchor) · Jackson (assertive CTA/offer) · Siren + Giselle (feature/variety). Warm, awake, credible read — never sleepy. Settings in `ads.config.mjs`.

---

## How to make a NEW ad (the repeatable workflow)
1. **Copy the starter:** duplicate `src/_TEMPLATE.tsx` → `src/ads/<YourAd>.tsx`, rename the component.
2. **Fill the 6 beats** — swap copy, pick which beats you need, point `ScreenshotPanel` at the right screenshot.
3. **Register it** in `src/Root.tsx` (id, duration, dimensions) and, if it's a dated calendar post, add it to `ads.config.mjs` (voice, script, scheduledDate).
4. **Preview live** in Remotion Studio (`npm start` → localhost:3000) — scrub, tweak timing.
5. **Add VO** — script goes in `ads.config.mjs` (or the oneoffs README); `npm run vo` auto-pulls the voice; re-render.
6. **Render:** `node scripts/build.mjs <id>` (or the scheduler for dated posts).

**Every ad checklist:** ✅ opens on-brand · ✅ shows real product (not a mockup) · ✅ subtitles on · ✅ one clear CTA to the signup link · ✅ "$150 locked for life," Snapshot never "free" · ✅ no guaranteed-funding / no cartoon spider · ✅ ends on the logo lockup.
