# Anansi Atlas — Premium One-Off Commercials

*Created: 2026-07-01 · Anansi Atlas Content Center (Scott Foundry Group LLC)*

Two flagship videos, built as code with Remotion. **These are separate from the automated ads pipeline** (`ads.config.mjs` / `scripts/build-scheduled.mjs`) — they don't have a scheduled date and aren't part of the July calendar's day-by-day cadence. Render and post them whenever you're ready; treat them as evergreen flagship assets (website hero, pinned LinkedIn post, outreach follow-up, YouTube).

Style direction: premium SaaS demo/explainer/brand-promo genre (the reference style you provided — Supahub-style promotional brand videos, fintech SaaS demos) — clean motion graphics, confident narration, fast benefit-driven cuts, strong CTA. Built for **our** brand, mission, and product: navy/charcoal/gold, Fraunces + Inter, the real Opportunity Web / Snapshot / Dashboard UI, Founding Atlas Partners Pilot.

## The two videos

| Composition | Length | Purpose | Voice |
|---|---|---|---|
| **PremiumShowcase** | ~85s | "This is our product, here's why you need it, join the family, click the link" — the premium brand commercial | **Christopher** |
| **FullExplainer** | ~5:05 | Deep platform walkthrough that convinces a viewer this would revolutionize their work → **Register Now** | **Christopher** |

### Later additions

| Composition | Length | Purpose | Voice |
|---|---|---|---|
| **AnansiVisionFilm** | 6:19 | "The Whole Field" — executive vision film for Orange County FL government + Central Florida grantmakers. 18 scenes, five acts. Soft CTA, no price. | **Christopher** |
| **BamOrlandoFilm** | 6:11 | "The Ceiling Isn't This Room" — board film for a single prospect (BAM Orlando). Same 18-scene / five-act spine as the vision film, but it closes on the offer. **⚠️ Board room only — see below.** | **Christopher** |

#### ⚠️ BamOrlandoFilm is not a public asset

Every other film here draws its screenshots from the Creative Display demo profile, which makes them ad-safe by construction. `BamOrlandoFilm` does not: Act IV walks **BAM Orlando's own workspace** (project 18), because the whole pitch is "this already exists and it's yours." Do not post it to LinkedIn, YouTube, or the site. It supersedes the older `BamOrlandoPresentation` (1080×1080 pillarboxed, timed by word-count estimate, and rendered **silent** — its `audioSrc` default was `null`), which stays registered only so the July 16 render remains reproducible.

Its shots come from the same capture script, with a prefix:

```bash
python scripts/capture-hd-shots.py --session <sessionid> --project 18 --prefix bam-
```

#### `--hide` — dressing a prospect's screen without touching the product

Some of what the app renders is true for a signed partner and not for a prospect. The dashboard's shot is therefore captured with four elements suppressed:

```bash
python scripts/capture-hd-shots.py --session <sid> --project 18 --prefix bam- \
  --only dashboard --hide ".fw-badge,.fw-sub,.fw-stat-verified,.fw-title"
```

| Selector | What it is | Why it's hidden here |
|---|---|---|
| `.fw-badge` | "🕸️ Founding Atlas Partner" | Honest on project 14 (EGI really is partner #1); a presumption on a prospect who hasn't signed |
| `.fw-sub` | "You're one of our first 20 founding partners…" | Same claim, in prose |
| `.fw-stat-verified` | "**0** ✓ verified grants matched to you" | Accurate but useless on a workspace whose analysis has never run — and it fights a slide whose job is to show *potential* |
| `.fw-title` | "Welcome, **there** — …" | Missing-contact-first-name fallback; reads as a bug on a projector. Set a contact first name on the org and this can come back for real |

This is capture-time cosmetics, **not** a product change — the decision belongs to the shot, since the same markup is truthful on a different project. Two guardrails: `--hide` **fails the run** if a selector matches zero elements (a stale selector otherwise fails silently into a screenshot that still shows what you meant to drop), and hiding elements **shifts the layout**, so any `UISpotlight` / `Scrim` box over that page must be re-measured against the new capture.

`--only <name,name>` re-captures a subset (names without the prefix), so fixing one shot doesn't redo all six.

Both reuse the shared brand components (`../components.tsx`) and render at 1080×1080 (square) — swap `width`/`height` in `src/Root.tsx` if you want a 16:9 cut for YouTube.

## What's actually in these (real motion graphics, not static cards)
- **`AnimatedLogoReveal`** — genuine motion: 8 gold threads converge from off-screen toward the center, a light burst, then the "Anansi Atlas" wordmark rises in with a shimmer sweep across it. Used for the brand-reveal beat in both videos.
- **`ScreenshotPanel`** — real product screenshots (not recreated mockups) inside a browser-chrome frame (traffic-light dots + URL pill), with cinematic Ken-Burns zoom/pan over the duration of the shot. This is what makes the "showcase our website" ask land — viewers see the actual Dashboard, Opportunity Web, and Snapshot pages in motion, not stylized re-creations.
- The screenshots live in `public/screenshots/*.png`, captured live off the running app (see below) — **from the Creative Display demo profile (pk=1)**, the anonymized "Riverside Girls Collective" org, so nothing in these videos exposes a real client's data.

### Re-capturing the screenshots (if the UI changes, or you want fresher data)
```bash
# 1. start the Django dev server (from the repo root)
cd /Users/scottiebeammin/Documents/GitHub/missionsignal-openoutreach
make run    # or the Preview tool

# 2. run the capture script (Playwright — already in requirements/base.txt, no new install)
.venv/bin/python - <<'PY'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_context(viewport={"width": 1600, "height": 1000}).new_page()
    page.goto("http://localhost:8001/accounts/login/")
    page.fill('input[name="username"]', "preview")
    page.fill('input[name="password"]', "<set one first via Django shell>")
    page.click('button[type="submit"]')
    for name, url in [("dashboard","dashboard"),("web","web"),("snapshot","snapshot")]:
        page.goto(f"http://localhost:8001/projects/1/{url}/")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=f"content-center/video-ads/public/screenshots/{name}.png")
    browser.close()
PY
```
Always capture from **project pk=1 (Creative Display)**, never a real client's project — that keeps every rendered ad ad-safe by construction.

#### ⚠️ Capture at 2× DPR for anything 1920×1080 (added 2026-07-29)

The existing `public/screenshots/*.png` are all **1600×1000**. That was fine for 1080×1080 comps, but it is not enough for a 16:9 cinematic film that pushes in and *holds* on the UI:

> `LaptopScreenshotPanel` at `width={1180}` with Ken Burns to `zoomTo` samples ~1,322 CSS px from a 1600 px source — **1.21× headroom**, and the panel is `objectFit: cover` on a 16:10 box, so it is effectively 1:1 at the end of the push. Visible softening on a projector, exactly when the room is staring at it.

Fix — one argument, and **keep the viewport at 1600×1000**. `ScreenshotPanel` and `LaptopScreenshotPanel` both hardcode `aspectRatio: "16 / 10"`, so staying 16:10 makes this a zero-code-change sharpness win (3200×2000 output = 2.4× oversampling):

```python
ctx = browser.new_context(
    viewport={"width": 1600, "height": 1000},
    device_scale_factor=2,          # ← 3200×2000 PNG output
)
page = ctx.new_page()
# … login as above …
page.goto(url); page.wait_for_load_state("networkidle")
# freeze animations + caret so the capture is deterministic frame-to-frame
page.add_style_tag(content="*{animation:none!important;transition:none!important;caret-color:transparent!important}")
page.wait_for_timeout(1200)         # let counters/charts settle
page.screenshot(path=f"content-center/video-ads/public/screenshots/hd-{name}.png")
```

Shots the executive vision film wants as `hd-*` (see the `SHOT` map in `AnansiVisionFilm.tsx` — swapping them is a single edit there):

| File | Scene | Note |
|---|---|---|
| `hd-dashboard.png` | 10 | mission-at-centre dashboard, held on screen for 27s |
| `hd-web.png` | 11 | Opportunity Web with all six nodes visible |
| `hd-opps-default.png` | 12 | opportunity list, **default** sort |
| `hd-opps-peersize.png` | 12 | **same viewport, same scroll** — peer-size sort the ONLY difference |
| `hd-card-verified.png` | 8 | tight crop of one card showing the ✓ Verified badge |
| `hd-readiness.png` | 10 | optional b-shot |

The two Sc12 captures are the hardest requirement in that film: if they differ by anything other than the sort control, the beat doesn't land and the audience reads it as a cut, not a re-sort.

## Render
```bash
cd content-center/video-ads
npm install                                        # first time only
npx remotion render PremiumShowcase out/PremiumShowcase.mp4
npx remotion render FullExplainer out/FullExplainer.mp4   # ~5 min video, longer render time
```
## Voiceover — now fully wired (one command)
Both flagships are now entries in `ads.config.mjs` (flagged `oneOff: true` so the date scheduler ignores them, but `npm run vo` still generates their narration). Both use **Christopher**. To produce the finished videos with sound:
```bash
export ELEVENLABS_API_KEY=sk_...          # your key — never commit it
npm run vo                                 # auto-pulls every voice by name & generates all MP3s
                                           #   (Christopher, Jackson, Siren, Giselle across all ads)
npm run build PremiumShowcase FullExplainer  # re-renders these two with VO + transitions + subtitles
```
`npm run vo PremiumShowcase` does just one. Scripts live in `ads.config.mjs`; the copy below is for reference / manual ElevenLabs paste.

**Manual fallback:** paste a script below into ElevenLabs (Christopher), export MP3, save as `public/premium-showcase-vo.mp3` / `public/full-explainer-vo.mp3`, then `npm run build <id>`.
3. Render with the file wired in:
```bash
npx remotion render PremiumShowcase out/PremiumShowcase.mp4 --props='{"audioSrc":"premium-showcase-vo.mp3"}'
npx remotion render FullExplainer out/FullExplainer.mp4 --props='{"audioSrc":"full-explainer-vo.mp3"}'
```

**Timing:** if your VO runs long/short, adjust the `S.*` frame offsets at the top of `FullExplainer.tsx` (for PremiumShowcase, the `<Sequence>` `from`/`durationInFrames` values) and the matching `CAPTIONS` timings.

### Timestamped VO — for films with silent passages

`npm run vo` joins a script into ONE continuous MP3 and lays it flat across the timeline, which bulldozes any silent passage the film is built around (`AnansiVisionFilm` Sc01 is 20s of music alone; `BamOrlandoFilm` the same). Those two films instead generate **once with alignment** and slice the master per line with `<Audio startFrom endAt>`:

```bash
node scripts/gen-vo-timestamped.mjs BamOrlandoFilm   # -> public/*.mp3 + *.alignment.json
node scripts/vo-line-slices.mjs     BamOrlandoFilm   # -> prints the LINE table to paste in
```

`vo-line-slices.mjs` reads the alignment JSON and prints the exact `LINE: [number, number][]` array, plus the inter-line gaps (useful for choosing each scene's `LEAD`). It refuses to run if the alignment is stale relative to the script in `ads.config.mjs`, so a rewritten line can't silently desync the film.

For sub-line sync — landing a count-up or a wipe on a specific *phrase* — query the alignment for the phrase's character offset. Both films' scene docstrings record the measured offsets they were built against, so a re-generated VO can be re-measured against the same beats.

**A script edit is never local.** Rewording one line changes its length, which moves every scene boundary after it. `AnansiVisionFilm` hardcodes its beat map `B`, so an edit there means re-deriving eighteen numbers by hand. `BamOrlandoFilm` instead **computes** `B` from `LEAD + line + TAIL`:

```ts
const B = LINE.reduce<number[]>(
  (acc, [from, to], i) => [...acc, acc[acc.length - 1] + LEAD[i] + (to - from) + TAIL[i]],
  [0, SILENT_LEAD],
);
```

So a VO regen is: paste the new `LINE` table → re-measure the per-scene phrase offsets → done. When three lines were reworded to drop the word "money" (2026-07-30), speech went 262.0s → 271.5s and every one of the seventeen boundaries moved; only the phrase offsets needed touching by hand. Prefer this shape for any new timestamped film.

---

## VO SCRIPT — PremiumShowcase (~85s, voice: Christopher)

> Every mission is surrounded by opportunity.
> The problem was never opportunity. It was visibility.
> This is Anansi Atlas — the platform that maps the web of opportunity around your mission.
> Your Dashboard opens with one clear answer: what to do next.
> Your Opportunity Web puts your mission at the center — funders, partners, government pathways, and resources, all mapped around it.
> Your Snapshot opens with a 30-day action plan — not a spreadsheet of maybes.
> Your Pipeline carries every opportunity from spotted to won.
> And your Readiness score tells you exactly what to fix before a funder ever sees it.
> This isn't a search tool. It's a system built to move your mission forward.
> Founding Atlas Partners aren't just customers — they're the first twenty organizations helping shape this platform, with a rate locked in for life.
> If you're ready to stop guessing and start moving — join the family.
> Click the link to learn more, and apply for a founding seat today.

---

## VO SCRIPT — FullExplainer (~5:05, voice: Christopher)

**00 — Hook**
> What if the funders, partners, and public dollars already aligned with your mission weren't hiding — they were just never mapped?

**01 — The Problem**
> Most nonprofit teams do this work in forty browser tabs. A funder database here. An email thread there. A spreadsheet somebody built two years ago that only one person still understands. Deadlines get missed. Warm partners go uncontacted. Government pathways sit undiscovered because nobody had the hours to go looking. It's not a lack of effort. It's a lack of a system built to hold all of it in one place.

**02 — Introducing Anansi Atlas**
> This is Anansi Atlas — a nonprofit opportunity intelligence platform. We call it the Web of Opportunity, because every mission sits at the center of one: aligned funders, potential partners, government pathways, and community resources, all already there, waiting to be seen clearly enough to act on.

**03 — Dashboard**
> Here's what that looks like in practice. Your Dashboard is home base. It opens with a single card: What To Do Next — one highest-leverage action, not a to-do list. Around it, health scores for Readiness, Partners, Pathways, and Opportunities, so you know at a glance where you stand. Upcoming deadlines are flagged before they're urgent. Your active pipeline sits right there, opportunity by opportunity. A busy executive director can open this for sixty seconds each morning and know exactly where to spend the day.

**04 — Opportunity Web**
> Click into the Opportunity Web, and you'll see your mission at the center — literally. Six nodes orbit it: Funders, Partners, Government, Resources, Readiness, and Pathways. This is the actual shape of your opportunity landscape, mapped instead of scattered. An Ecosystem Summary below surfaces your strongest asset in teal, and your biggest constraint in gold, plus a Top Move Right Now card that tells you the single highest-leverage relationship or opportunity to pursue first. Nothing here is guesswork. It's built from real research on your mission.

**05 — The Snapshot**
> Your Opportunity Web Snapshot is the executive brief. It opens with a plain-language summary and a 30-day action plan, ranked specifically for your mission — not a wall of grants with no context. Below that: your top funder pathways and partner pathways, ranked by fit. Your Readiness section, scored honestly — teal where you're strong, gold where there's a gap, and the specific moves that close it. And your Risks and Gaps section, so you see what could slow you down before it costs you a quarter. Rose "Due" pills flag every deadline so nothing slips through a busy week. This is the difference between information and direction — a list tells you what exists, a Snapshot tells you what to do next, in order, starting today.

**06 — Pipeline, Partners & Sponsorship, Resources**
> When an opportunity is worth pursuing, it moves into your Pipeline — a living board that carries it from spotted to submitted to won, with a next action and a deadline attached the whole way. Partners and Sponsorship maps the funders and organizations already aligned with your mission, with a fit rationale for each one. And Resources surfaces the capacity-building, technology, and volunteer support that strengthens your readiness before you ever apply. Every piece of the platform points at the same goal: focused action, not more research.

**07 — Why It Matters**
> We built Anansi Atlas because we believe mission-driven work shouldn't lose to logistics. The opportunity around your mission was never the problem. Seeing it clearly, and knowing what to do about it first, was. That's what this platform gives you back — time, clarity, and a system that keeps working even on the weeks you don't have time to look.

**08 — Register Now**
> We're opening the Founding Atlas Partners Pilot to twenty mission-driven organizations — a rate locked in for life, a Snapshot built around your actual mission, and a personal walkthrough with our team. If this is the system your organization has been missing, don't wait for the standard rate. Register now at anansi atlas dot com, slash anansi atlas, and let's map your web of opportunity today.
