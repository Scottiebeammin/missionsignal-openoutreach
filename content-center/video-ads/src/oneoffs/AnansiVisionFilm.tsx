import React from "react";
import { AbsoluteFill, Audio, Img, interpolate, Sequence, staticFile, useCurrentFrame } from "remotion";
import { BRAND, NODES } from "../brand";
import {
  ActBridge,
  Caption,
  ConceptFrame,
  CountUpFigure,
  Eyebrow,
  GradientMesh,
  Headline,
  HyperFrames,
  LaptopScreenshotPanel,
  LogoLockup,
  NavyBG,
  NodeField,
  OrbWeb,
  Rise,
  SANS,
  SERIF,
  SceneDissolve,
  ScreenshotPanel,
  Subtitles,
  ThreadRule,
  UISpotlight,
  WireBlock,
} from "../components";

/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * "THE WHOLE FIELD" — the Anansi Atlas executive vision film.
 * ═══════════════════════════════════════════════════════════════════════════════
 *
 * Audience: Orange County, FLORIDA government (OCFL) + Central Florida grantmakers.
 * Purpose:  open a conversation about the future of community investment.
 *           The room should leave thinking "what if this became part of how we
 *           support nonprofits?" — never "they're selling us software."
 *
 * Register: Apple keynote / Stripe Sessions. Slow, spacious, confident. This is
 *           NOT an ad — deliberately no price and no seat count. It closes on a
 *           soft CTA (call / visit), not a conversion card. See BRAND-DEVIATION.
 *
 * 18 scenes across five acts: Inspiration → Discovery → Realization → Vision →
 * Partnership. Native 1920×1080 (not a pillarboxed square like the earlier Wide
 * comps — wide cinematic type needs the full frame).
 *
 * ── FACTUAL SPINE (every figure traces to a real source — Brand Bible §10.4) ──
 *   $63.6M / 474 orgs / 1,912 grants — COUNTY-WIDE ..... IRS 990-PF, computed
 *     ⚠️ SCOPE MATTERS. This is Orange County in aggregate, NOT the organization
 *     shown in Act III. Act III shows Empowered Girls Inc.'s own view, whose
 *     "organizations like yours" figure is smaller ($25.3M locally). Narrating
 *     this as one org's result while EGI's dashboard is on screen would put two
 *     contradicting numbers in front of funders — hence "Orange County itself".
 *     Provenance confirmed by Scott 2026-07-29; local DB is older than the run.
 *   310,000 IRS returns → 326,332 FL grant records ...... ingest pipeline
 *   13,554 verified funders ............................. derived (≥3 grants)
 *   114,435 FL exempt organizations ..................... IRS EO file
 *   Empowered Girls Inc. = founding partner #1 .......... live in production
 *     (Orlando, Orange County — `seed_egi` + `setup_egi_seats`, 2 founding seats)
 *
 * ── BRAND-DEVIATION (partially resolved — Scott, 2026-07-29) ────────────────
 * BRAND-TEMPLATE.md §5 beat 6 requires every ad to close on a CTA with the
 * signup URL, and the every-ad checklist requires "$150 locked for life."
 *   RESOLVED: the film now closes on a soft CTA — "Call or visit to learn more"
 *   over (321) 780-6335 · anansiatlas.com.
 *   STILL DEVIATES: no price, no seat count. "We're not here to sell you
 *   software" and "$150 locked for life" cannot both be true in the same thirty
 *   seconds. This close invites a conversation; it does not convert. Flagged,
 *   not silently overridden (Brand Bible §14).
 *
 * ── ACT IV IS NOT SHIPPED PRODUCT ───────────────────────────────────────────
 * Funder-side intelligence is a PARKED roadmap idea. Act IV runs inside
 * ConceptFrame with six independent "unbuilt" signals: zero screenshots,
 * wireframe-only, a persistent CONCEPT · NOT BUILT chip, outline typography,
 * desaturation + blueprint grid, and a reverse un-draw on the final wireframe —
 * plus three explicit verbal denials in the VO. Do not weaken any of these.
 */

const W = 1920;
const H = 1080;

// ─────────────────────────────────────────────────────────────────────────────
// BEAT MAP — same idiom as WebOfOpportunityFilm.tsx:33, extended to 18 scenes.
// Scene N occupies [B[N-1], B[N]). Scene 01 IS the silent lead; VO starts at B[1].
// Phase 3: re-derive these from public/anansi-vision-film-vo.alignment.json.
// ─────────────────────────────────────────────────────────────────────────────
// B is COMPUTED, not hand-written (2026-07-30). It was a literal array, which meant
// any script edit — a reworded line changes its spoken length — required re-deriving
// all eighteen boundaries by hand, with a silent desync as the penalty for getting
// one wrong. Dropping the word "money" from Sc02 proved the point: regenerating the
// VO moved every line, and TTS pacing drift alone added ~14s across the film.
//
// TAIL was derived FROM the literal B it replaced (dur - LEAD - line) and round-trips
// to it exactly, so this refactor was a no-op at the moment it landed.
//
// Sc17/Sc18 each gained 120f when the CTA and the Orange County line went in — hence
// their long tails. Sc01 was cut 600f -> 150f (Scott, 2026-07-30): a 20s silent open
// tested as too long. NOTE that cut forced the removal of Sc01's MISSION -> COMMUNITY
// -> POSSIBILITY hyperframe, which alone ran 294f and cannot fit inside 150f. That was
// the film's opening statement — flagged, not silently dropped.
const SILENT_LEAD = 150; // Sc01, music only

/** Frames of silence before each scene's narration begins — the room breathes first. */
const LEAD = [60, 60, 70, 60, 70, 40, 60, 30, 80, 70, 40, 70, 60, 70, 90, 90, 70, 60];
/** Frames of silence after it ends — how long each beat is allowed to hang. */
const TAIL = [114, 107, 108, 94, 113, 148, 72, 214, 188, 116, 84, 120, 73, 131, 132, 128, 107, 231];

const ACT_LABELS = ["II · DISCOVERY", "III · REALIZATION", "IV · VISION", "V · PARTNERSHIP"];

// Screenshots. Phase 4 swaps these for 2× DPR `hd-*` recaptures (see oneoffs/README.md).
// Kept in one map so the swap is a single edit and never a hunt through 18 scenes.
const SHOT = {
  dashboard: "screenshots/hd-dashboard.png",
  web: "screenshots/hd-web.png",
  // Sc12's TRUE A/B pair — captured by scripts/capture-hd-shots.py at one locked
  // scrollY with the sort control as the only difference. `oppsDefault` is
  // ?sort=largest (million-dollar university research grants on top); `oppsPeer`
  // is the default ?sort=fit (peer-size $25,000 grants to Orange County orgs).
  oppsDefault: "screenshots/hd-opps-default.png",
  oppsPeer: "screenshots/hd-opps-peersize.png",
  card: "screenshots/hd-ecosystem.png",
  // State & Local Funding, grouped by issuing government (Sc13, added 2026-09-01).
  local: "screenshots/hd-local-money.png",
};

/**
 * The walkthrough's org is swappable per audience (Scott, 2026-07-30).
 *
 * Default is Empowered Girls Inc. (project 14) — the real founding partner, which is
 * what the OCFL/grantmaker cut must show, because Sc17 names them out loud.
 * `AnansiVisionFilmBAM` overrides `dashboard` + `web` with BAM Orlando's own screens
 * so the film can be shown IN a BAM pitch and feel like theirs.
 *
 * ⚠️ Sc12's A/B pair is deliberately NOT overridden. Its narration says
 * "twenty-five-thousand-dollar grants to organizations the same size" — $25,000 is
 * EGI's size band. BAM's band is $5,000. Pointing Sc12 at BAM's capture would put a
 * $5,000 screen under a $25,000 voice-over. Changing that beat honestly needs the
 * line re-voiced, not the screenshot swapped.
 */
const ShotCtx = React.createContext<typeof SHOT>(SHOT);

/**
 * ── VO SLICING ───────────────────────────────────────────────────────────────
 * scripts/generate-vo.mjs joins the script into ONE continuous MP3, which cannot
 * hold this film's silent passages (Sc01 is music alone; Sc16 un-draws in
 * silence). So we generate once with gen-vo-timestamped.mjs and slice the master
 * per line with <Audio startFrom endAt>.
 *
 * [srcFrom, srcTo] are frames INTO public/anansi-vision-film-vo.mp3 (260.7s total),
 * derived from public/anansi-vision-film-vo.alignment.json — not estimated.
 * Line i belongs to Scene i+2; Scene 01 is silent and has no line.
 *
 * Regenerate: node scripts/gen-vo-timestamped.mjs AnansiVisionFilm
 */
const LINE: [number, number][] = [
  [0, 513],      // S02 Orange County
  [521, 1011],   // S03 Two blocks apart
  [1018, 1237],  // S04 More than it can see
  [1242, 1398],  // S05 Scattered
  [1401, 2020],  // S06 We counted
  [2029, 2607],  // S07 $63.6M county-wide
  [2619, 2991],  // S08 Verified
  [3000, 3244],  // S09 Six nodes
  [3253, 3808],  // S10 The platform
  [3811, 4348],  // S11 Nothing was invented
  [4359, 4954],  // S12 Sort by peer size
  // S13 State & Local — NOT a slice of the master. See LINE_SRC: this line was
  // generated on its own (scripts/gen-vo-line.mjs) so the other sixteen takes stay
  // byte-identical. [0, 313] are frames into ITS OWN file, not the master.
  [0, 313],
  [4955, 5229],  // S14 Where to look + "That's Anansi Atlas."
  [5234, 5507],  // S15 Unbuilt from here
  [5519, 5963],  // S16 Funder-side: lifecycle, communication, data hub
  [5974, 6552],  // S17 A whole sector
  [6560, 7023],  // S18 Empowered Girls Inc.
  [7031, 7821],  // S19 The invitation + CTA
];

/**
 * Length of the master VO in frames. Only used to stop the last slice's tail
 * padding running past the end of the file. Re-print it with
 * `node scripts/vo-line-slices.mjs AnansiVisionFilm` after every VO regeneration.
 */
const MASTER_FRAMES = 7821;

/**
 * ── WHY THE SLICES ARE PADDED AND FADED ──────────────────────────────────────
 * The first cut of this film had audibly choppy narration. Cause: each line was
 * played as <Audio startFrom={from} endAt={to} /> cut EXACTLY on the alignment
 * character boundaries, with no padding and no ramp. Two problems:
 *
 *   1. A hard in/out on a non-zero waveform sample is a step discontinuity —
 *      i.e. a click. With 17 lines that is 34 clicks across the film.
 *   2. floor()/ceil() on character times shaves the onset of the first phoneme
 *      and truncates the final consonant's decay and the breath after it, so
 *      lines ended abruptly rather than settling.
 *
 * Fix: grab a few frames of air either side of the measured speech, and ramp the
 * volume over VO_FADE frames so the waveform always starts and ends at zero. The
 * padding is clamped to HALF the gap to the neighbouring line, so a slice can
 * never bleed a fragment of the next sentence into the end of a scene — some
 * gaps in the master are as small as 2 frames.
 */
const VO_PAD = 5;
const VO_FADE = 4;

/**
 * Which lines come from their OWN file instead of the master.
 *
 * Adding Sc13 to a finished film could have meant regenerating the whole VO master —
 * but ElevenLabs is nondeterministic, so every existing take would change and the
 * approved performance would be gone (the July 29 note calls this "a full VO
 * regeneration plus a re-derivation of every timing"). Generating one line on its own
 * keeps the other sixteen byte-identical; only the new scene is new audio.
 *
 * null = a slice of the master. A string = that line's own file in public/.
 */
const LINE_SRC: (string | null)[] = [
  null, null, null, null, null, null, null, null, null, null, null,
  "anansi-vision-film-local-vo.mp3", // S13 State & Local
  null, null, null, null, null, null,
];

const SLICE = LINE.map(([from, to], i) => {
  // A line with its own file needs no padding: it is not cut out of a continuous
  // take, so there is no neighbouring sentence to bleed in and nothing to clamp
  // against. The VO_FADE ramp below still guarantees it starts and ends at zero.
  // Padding here would also be wrong twice over — the neighbours in LINE are frame
  // offsets into the MASTER, and MASTER_FRAMES is not this file's length.
  if (LINE_SRC[i]) return { from, to, padIn: 0, src: LINE_SRC[i] as string };
  const prevEnd = i > 0 && !LINE_SRC[i - 1] ? LINE[i - 1][1] : -Infinity;
  const nextStart = i < LINE.length - 1 && !LINE_SRC[i + 1] ? LINE[i + 1][0] : Infinity;
  const padIn = Math.max(0, Math.min(VO_PAD, Math.floor((from - prevEnd) / 2), from));
  const padOut = Math.max(0, Math.min(VO_PAD, Math.floor((nextStart - to) / 2), MASTER_FRAMES - to));
  return { from: from - padIn, to: to + padOut, padIn, src: null as string | null };
});

/** Scene N's span = LEAD + spoken line + TAIL. Sc01 is the silent lead. */
const B = LINE.reduce<number[]>(
  (acc, [from, to], i) => [...acc, acc[acc.length - 1] + LEAD[i] + (to - from) + TAIL[i]],
  [0, SILENT_LEAD],
);

export const VISION_TOTAL = B[19]; // 19 scenes since Sc13 (State & Local) was added

/** Act boundaries — the connection web draws THROUGH these cuts. */
const ACT_CUTS = [B[4], B[8], B[14], B[17]];
/** Everything else gets the quieter dip. DISJOINT from ACT_CUTS — never both. */
const SCENE_CUTS = [B[1], B[2], B[3], B[5], B[6], B[7], B[9], B[10], B[11], B[12], B[13], B[15], B[16], B[18]];

/** Where line i lands in the composition. Scene components use these for visual sync. */
const VO_AT = LINE.map((_, i) => B[i + 1] + LEAD[i]);

const Center: React.FC<{ children: React.ReactNode; gap?: number }> = ({ children, gap = 26 }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap }}>
    {children}
  </AbsoluteFill>
);

/**
 * OrbWeb in a correctly-sized box.
 *
 * ⚠️ Do not replace this with `<div style={{transform}}><OrbWeb/></div>`. `OrbWeb`
 * renders an `AbsoluteFill` (position:absolute; inset:0), and a bare `transform`
 * div becomes the containing block for absolute descendants while having NO
 * intrinsic size of its own — so it collapses to 0×0 and OrbWeb renders nothing
 * at all. That bug shipped 18 seconds of empty navy across Sc09 and Sc11 in the
 * first render pass; the explicit width/height below is the fix.
 */
const ORB = 1080; // OrbWeb's internal viewBox is hardcoded to SIZE
const OrbWebBox: React.FC<{ scale: number; progress: number }> = ({ scale, progress }) => (
  <div style={{ position: "relative", width: ORB, height: ORB, transform: `scale(${scale})` }}>
    <OrbWeb progress={progress} />
  </div>
);

/** Wide-tracked label in the film's secondary register. */
const Label: React.FC<{ children: React.ReactNode; size?: number; color?: string }> = ({
  children,
  size = 26,
  color = BRAND.muted,
}) => (
  <div
    style={{
      fontFamily: SANS,
      fontWeight: 800,
      fontSize: size,
      letterSpacing: "0.2em",
      textTransform: "uppercase",
      color,
      textAlign: "center",
    }}
  >
    {children}
  </div>
);

// ═════════════════════════════════════════════════════════════════════════════
// ACT I — INSPIRATION
// ═════════════════════════════════════════════════════════════════════════════

/** 01 · First Light — 600f, silent. Black, one hairline, nine faint nodes. */
const S01: React.FC = () => {
  const frame = useCurrentFrame();
  // 150f open. Still true black first — just 10f of it, not 40.
  const wake = interpolate(frame, [10, 95], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: BRAND.charcoal }}>
      <AbsoluteFill style={{ opacity: wake }}>
        <NavyBG w={W} h={H} threads={0.45} />
        <GradientMesh opacity={0.28 * wake} />
      </AbsoluteFill>
      <ThreadRule from={[14, 66]} to={[86, 66]} at={18} draw={72} hold={60} out={0} opacity={0.5} />
      <NodeField w={W} h={H} count={9} opacity={0.18} at={42} fadeIn={64} />
    </AbsoluteFill>
  );
};

/** 02 · Orange County — 660f. The constellation forms; three nodes brighten. */
const S02: React.FC = () => (
  <AbsoluteFill>
    <NavyBG w={W} h={H} threads={0.45} />
    <GradientMesh opacity={0.38} />
    <NodeField w={W} h={H} count={11} opacity={0.22} highlight={[2, 5, 8]} at={0} fadeIn={70} />
    {/* The mark rises with the place-name (Scott, 2026-07-30) — the film now
        signs itself in its first spoken scene instead of withholding the brand
        until the close. Emblem, not anansi-mark.png: the mark PNG has no alpha
        channel and renders as a navy box on navy. */}
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: 96, gap: 26 }}>
      <Rise delay={22}>
        <Img
          src={staticFile("anansi-emblem-785.png")}
          style={{ width: 92, height: 92, objectFit: "contain" }}
        />
      </Rise>
      <Eyebrow delay={40}>Orange County · Florida</Eyebrow>
    </AbsoluteFill>
    {/*
      The three assets, animated on their measured spoken beats (Scott, 2026-07-30):
      "The people" 137 · "The institutions" 163 · "The opportunity" 200. Deliberately
      NO exit — they hold the frame until the Sc03 cut, so the scene ends on the
      film's whole thesis standing in one place. Opportunity lands in gold: it is
      the one of the three this film is actually about.
    */}
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 34, paddingTop: 40 }}>
      <Rise delay={139}>
        <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 84, color: BRAND.white, textAlign: "center" }}>
          The People.
        </div>
      </Rise>
      <Rise delay={166}>
        <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 84, color: BRAND.white, textAlign: "center" }}>
          The Institutions.
        </div>
      </Rise>
      <Rise delay={200}>
        <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 92, color: BRAND.goldLight, textAlign: "center" }}>
          The Opportunity.
        </div>
      </Rise>
    </AbsoluteFill>
  </AbsoluteFill>
);

/**
 * 03 · Two Blocks Apart — 630f. Two organizations, no edge between them, then one
 * gold line draws. The emotional thesis of the whole film in a single gesture.
 */
const S03: React.FC = () => (
  <AbsoluteFill>
    <NavyBG w={W} h={H} threads={0.45} />
    <GradientMesh opacity={0.3} />
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <svg width="100%" height="100%">
        <circle cx="26%" cy="44%" r={9} fill={BRAND.gold} fillOpacity={0.9} />
        <circle cx="74%" cy="58%" r={9} fill={BRAND.gold} fillOpacity={0.9} />
      </svg>
    </AbsoluteFill>
    <div style={{ position: "absolute", left: "26%", top: "44%", transform: "translate(-50%, -64px)", width: 460, marginLeft: 0 }}>
      <Rise delay={40}>
        <Label>A workforce nonprofit</Label>
      </Rise>
    </div>
    <div style={{ position: "absolute", left: "74%", top: "58%", transform: "translate(-50%, 34px)", width: 520 }}>
      <Rise delay={130}>
        <Label>A foundation that funds exactly this</Label>
      </Rise>
    </div>
    {/* The line arrives late and alone — 440f of separation earns it. */}
    <ThreadRule from={[26, 44]} to={[74, 58]} at={440} draw={90} hold={100} out={0} width={2} opacity={0.9} />
  </AbsoluteFill>
);

/** 04 · More Than It Can See — 390f. The philosophy line, alone. */
const S04: React.FC = () => (
  <AbsoluteFill>
    <NavyBG w={W} h={H} threads={0.45} />
    <GradientMesh opacity={0.3} />
    <Center>
      <Headline size={88} delay={24}>
        Every mission has more
        <br />
        opportunities than it can see.
      </Headline>
    </Center>
  </AbsoluteFill>
);

// ═════════════════════════════════════════════════════════════════════════════
// ACT II — DISCOVERY
// ═════════════════════════════════════════════════════════════════════════════

/** 05 · Hyperframe II — 300f. */
const S05: React.FC = () => (
  <AbsoluteFill>
    <NavyBG w={W} h={H} threads={0.45} />
    <GradientMesh opacity={0.32} />
    <HyperFrames
      words={["SCATTERED", "UNSEEN", "UNCOUNTED"]}
      at={20}
      hold={44}
      enter={16}
      exit={14}
      gap={8}
      size={172}
    />
  </AbsoluteFill>
);

/** 06 · We Counted — 780f. Four figures, staggered 90f apart, each with a rule. */
const S06: React.FC = () => {
  // Each count begins ~10f before its number is spoken (VO lead 70 + measured offsets
  // 29 / 173 / 318 / 431 from the alignment JSON), so the figure is already rising
  // as the narration reaches it.
  const figures = [
    { v: 310000, label: "IRS returns read", at: 89 },
    { v: 326332, label: "Florida grant records", at: 233 },
    { v: 13554, label: "Verified funders", at: 378 },
    { v: 114435, label: "Exempt organizations", at: 491 },
  ];
  return (
    <AbsoluteFill>
      <NavyBG w={W} h={H} threads={0.45} />
      <GradientMesh opacity={0.26} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ display: "flex", gap: 96, alignItems: "flex-start" }}>
          {figures.map((f) => (
            <CountUpFigure
              key={f.label}
              value={f.v}
              label={f.label}
              at={f.at}
              count={80}
              size={92}
              outFrom={720}
            />
          ))}
        </div>
      </AbsoluteFill>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: 150 }}>
        <Rise delay={560}>
          <Label size={22}>Source · IRS Form 990-PF and the IRS exempt-organization file</Label>
        </Rise>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/** 07 · $63.6 Million — 750f. The film's single loudest moment. */
const S07: React.FC = () => {
  const frame = useCurrentFrame();
  // Measured (lead 40): "sixty-three" 149 · "reaching four hundred" 270 ·
  // "One thousand nine hundred" 409 · "traceable" 533. The count runs 107→182 so the
  // figure completes mid-phrase, and the bloom lands on that completion.
  const bloom = interpolate(frame, [182, 202, 344], [0, 0.5, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill>
      <NavyBG w={W} h={H} threads={0.45} />
      <GradientMesh opacity={0.42} />
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at 50% 44%, rgba(212,160,23,${bloom}) 0%, transparent 55%)`,
          filter: "blur(40px)",
        }}
      />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 62 }}>
        <CountUpFigure
          value={63.6}
          format={(n) => `$${n.toFixed(1)}M`}
          at={107}
          count={75}
          size={260}
          rule={false}
          outFrom={690}
        />
        {/* Each label lands on its own measured phrase: 270 · 409 · 533. */}
        <div style={{ display: "flex", gap: 90 }}>
          <Rise delay={270}>
            <Label size={24} color={BRAND.ink}>474 Orange County organizations</Label>
          </Rise>
          <Rise delay={409}>
            <Label size={24} color={BRAND.ink}>1,912 grants</Label>
          </Rise>
          <Rise delay={533}>
            <Label size={24} color={BRAND.ink}>IRS Form 990-PF</Label>
          </Rise>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/** 08 · Verified, or Verify-First — 450f. The discipline behind the number. */
const S08: React.FC = () => (
  <AbsoluteFill>
    <NavyBG w={W} h={H} threads={0.45} />
    <GradientMesh opacity={0.24} />
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", paddingBottom: 90 }}>
      <ScreenshotPanel
        src={staticFile(SHOT.card)}
        width={1000}
        zoomFrom={1.02}
        zoomTo={1.06}
        panY={[0, -2]}
        durationInFrames={450}
      />
    </AbsoluteFill>
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: 92, flexDirection: "column", gap: 26 }}>
      <div style={{ display: "flex", gap: 22 }}>
        <Rise delay={90}>
          <Chip text="✓ Verified" tone="gold" />
        </Rise>
        <Rise delay={124}>
          <Chip text="⚠ Verify-first" tone="muted" />
        </Rise>
      </div>
      <Rise delay={170}>
        <Label size={22}>Every opportunity carries a source URL — or it is rejected at import</Label>
      </Rise>
    </AbsoluteFill>
  </AbsoluteFill>
);

const Chip: React.FC<{ text: string; tone: "gold" | "muted" }> = ({ text, tone }) => (
  <div
    style={{
      border: `1px solid ${tone === "gold" ? BRAND.gold : BRAND.muted}`,
      borderRadius: 999,
      padding: "10px 22px",
      fontFamily: SANS,
      fontWeight: 800,
      fontSize: 20,
      letterSpacing: "0.14em",
      textTransform: "uppercase",
      color: tone === "gold" ? BRAND.goldLight : BRAND.muted,
      background: "rgba(6,12,26,0.55)",
    }}
  >
    {text}
  </div>
);

// ═════════════════════════════════════════════════════════════════════════════
// ACT III — REALIZATION
// ═════════════════════════════════════════════════════════════════════════════

/** 09 · The Six Nodes — 450f. Product vocabulary, so Inter 800 not Fraunces. */
const S09: React.FC = () => {
  const frame = useCurrentFrame();
  // After the six words pass, all six settle into a ring together.
  const ring = interpolate(frame, [190, 270], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill>
      <NavyBG w={W} h={H} threads={0.45} />
      <GradientMesh opacity={0.3} />
      {/*
        Timed to the narration, not to a comfortable reading pace: Christopher says
        all six nouns in 131 frames (measured: 30·56·82·103·131·161), so the cycle is
        ~26f/word. Faster than
        the film's other hyperframes by necessity — a word on screen that isn't the
        word being spoken is worse than a quick cut.
      */}
      <HyperFrames words={[...NODES]} at={30} hold={15} enter={7} exit={4} gap={0} size={140} face="sans" />
      <AbsoluteFill style={{ opacity: ring, alignItems: "center", justifyContent: "center" }}>
        <OrbWebBox scale={0.86 + ring * 0.04} progress={ring} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/**
 * 10 · The Platform, Slowly — 810f. The UI holds the frame for 27 seconds with one
 * slow push and no callouts for the first 400f. "Never rush through features."
 */
const S10: React.FC = () => {
  const shot = React.useContext(ShotCtx);
  return (
  <AbsoluteFill>
    <NavyBG w={W} h={H} threads={0.45} />
    <GradientMesh opacity={0.2} />
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <LaptopScreenshotPanel
        src={staticFile(shot.dashboard)}
        label="anansiatlas.com/dashboard"
        width={1180}
        zoomFrom={1.0}
        zoomTo={1.05}
        panY={[0, -6]}
        delay={24}
        durationInFrames={810}
      />
    </AbsoluteFill>
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: 74 }}>
      <Eyebrow delay={40}>The Dashboard</Eyebrow>
    </AbsoluteFill>
  </AbsoluteFill>
  );
};

/**
 * 11 · Mission at the Center — 690f. OrbWeb assembles thread-by-thread, then
 * cross-dissolves into the real UI: the metaphor becoming the product.
 */
const S11: React.FC = () => {
  const shot = React.useContext(ShotCtx);
  const frame = useCurrentFrame();
  const build = interpolate(frame, [20, 300], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const handoff = interpolate(frame, [320, 400], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill>
      <NavyBG w={W} h={H} threads={0.45} />
      <GradientMesh opacity={0.24} />
      <AbsoluteFill style={{ opacity: 1 - handoff, alignItems: "center", justifyContent: "center" }}>
        <OrbWebBox scale={0.92} progress={build} />
      </AbsoluteFill>
      <AbsoluteFill style={{ opacity: handoff, alignItems: "center", justifyContent: "center" }}>
        <ScreenshotPanel
          src={staticFile(shot.web)}
          width={1240}
          zoomFrom={1.0}
          zoomTo={1.04}
          panY={[0, -3]}
          durationInFrames={370}
        />
      </AbsoluteFill>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: 66 }}>
        <Eyebrow delay={30}>The Opportunity Web</Eyebrow>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/**
 * 12 · Sort by Peer Size — 750f. The hero demo. Same viewport, same scroll, one
 * control. The top row stops being a $5M university gift and becomes a $25k peer grant.
 */
const S12: React.FC = () => {
  const frame = useCurrentFrame();
  // Measured (lead 40): "Sort by peer size" 82 · "million-dollar research grant" 187 ·
  // "twenty-five-thousand-dollar" 278 · "The lens changed" ~545. The wipe runs BETWEEN the
  // two dollar figures, so the re-sort happens exactly as the narration turns the corner.
  const wipe = interpolate(frame, [212, 272], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill>
      <NavyBG w={W} h={H} threads={0.45} />
      <GradientMesh opacity={0.2} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ position: "relative" }}>
          <ScreenshotPanel
            src={staticFile(SHOT.oppsDefault)}
            width={1240}
            zoomFrom={1.0}
            zoomTo={1.03}
            durationInFrames={750}
          />
          <AbsoluteFill style={{ clipPath: `inset(0 ${100 - wipe}% 0 0)` }}>
            <ScreenshotPanel
              src={staticFile(SHOT.oppsPeer)}
              width={1240}
              zoomFrom={1.0}
              zoomTo={1.03}
              durationInFrames={750}
            />
          </AbsoluteFill>
          {/* the leading edge of the wipe, as a gold hairline */}
          {wipe > 0 && wipe < 100 ? (
            <div
              style={{
                position: "absolute",
                left: `${wipe}%`,
                top: 0,
                bottom: 0,
                width: 2,
                background: BRAND.gold,
                opacity: 0.9,
              }}
            />
          ) : null}
        </div>
      </AbsoluteFill>
      {/* Point at the control without a fake cursor. */}
      {/* Framed on the actual toggle control ("Grants your size · Largest grants"),
      measured off the 2x capture at ~71-80% x, ~24% y of the 1920x1080 frame.
      The earlier box sat over the panel's description text instead. */}
  <UISpotlight x={70.5} y={22.6} w={11} h={4} at={56} draw={26} hold={170} out={16} label="Sort by peer size" />
      {/*
        Each label is pinned to its own spoken figure AND to the wipe: the "before"
        label peaks at 195 while the screen still shows million-dollar university
        grants and clears by 220 as the wipe starts (215); the "after" label arrives
        at 270-300, on "twenty-five-thousand-dollar". Keying these to the old beats
        left the before-label peaking mid-wipe, captioning the wrong screen.
      */}
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: 84 }}>
        <div style={{ position: "relative", height: 40, width: 900 }}>
          <AbsoluteFill style={{ opacity: interpolate(frame, [175, 215, 281], [0, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>
            <Label size={26} color={BRAND.muted}>$1,199,692 · University of Florida</Label>
          </AbsoluteFill>
          <AbsoluteFill style={{ opacity: interpolate(frame, [278, 318], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>
            <Label size={26} color={BRAND.goldLight}>$25,000 · Orange County peer</Label>
          </AbsoluteFill>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/**
 * 13 · State & Local — 503f. The layer under the federal one.
 *
 * Added 2026-09-01 for the OCFL cut: the film showed federal discovery and the peer-size
 * sort, but never the State & Local section shipped on 2026-08-11 — which for a room of
 * county officials is the most directly relevant thing the product does. It groups money
 * by the government that issues it, so a county programme stops competing with a federal
 * notice on keyword overlap, a contest it structurally loses.
 *
 * This is SHIPPED product, so it sits in Act III with a real screenshot — not in Act IV's
 * concept register. The capture is Empowered Girls' own board: FLORIDA · state, ORANGE
 * COUNTY · county, ORLANDO · city.
 *
 * Measured (lead 70): "State" 142 · "county" 156 · "city" 172 · "grouped" 204. The three
 * jurisdiction words illuminate on the frames the voice says them — the sync-to-voice rule
 * in Motion Language, same idiom as Sc09's six node words.
 */
const S12B: React.FC = () => {
  const frame = useCurrentFrame();
  const shot = React.useContext(ShotCtx);
  const tiers: [string, number][] = [["STATE", 142], ["COUNTY", 156], ["CITY", 172]];
  return (
    <AbsoluteFill>
      <NavyBG w={W} h={H} threads={0.45} />
      <GradientMesh opacity={0.2} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <ScreenshotPanel
          src={staticFile(shot.local)}
          width={1240}
          zoomFrom={1.0}
          zoomTo={1.04}
          durationInFrames={503}
        />
      </AbsoluteFill>
      {/* The three tiers, lit on the spoken word.
          ANCHORED TOP, not bottom. Bottom is the caption band: in the captioned cut the
          subtitle card sat directly on this row and swallowed the word COUNTY. The master
          cut looked fine, which is exactly why this only showed up on a frame check of the
          OTHER composition. Nothing else in Act III puts type in the lower third — this
          scene was the first, and the collision is invisible until it renders. */}
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: 46 }}>
        <div style={{ display: "flex", gap: 30, alignItems: "center" }}>
          {tiers.map(([word, at], i) => {
            const up = interpolate(frame, [at, at + 16], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            return (
              <React.Fragment key={word}>
                {i > 0 ? (
                  <span style={{ color: BRAND.gold, opacity: up * 0.5, fontSize: 20 }}>·</span>
                ) : null}
                <span
                  style={{
                    fontFamily: SANS,
                    fontSize: 26,
                    letterSpacing: 4,
                    fontWeight: 600,
                    color: BRAND.white,
                    opacity: up,
                    transform: `translateY(${(1 - up) * 10}px)`,
                  }}
                >
                  {word}
                </span>
              </React.Fragment>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/** 13 · Where to Look — 420f. The honesty line, at full weight. */
const S13: React.FC = () => {
  const frame = useCurrentFrame();
  // Measured (lead 60): "where to look" 261 · "That's Anansi Atlas" 288. First two dim as
  // the tagline lands; then ALL THREE dim after the line ends (419), so Act III signs
  // itself off before the concept register begins.
  const dim = interpolate(frame, [245, 295], [1, 0.3], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const dimAll = interpolate(frame, [288, 326], [1, 0.28], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill>
      <NavyBG w={W} h={H} threads={0.45} />
      <GradientMesh opacity={0.3} />
      <Center gap={30}>
        <div style={{ opacity: dim * dimAll }}>
          <Headline size={62} delay={70} color={BRAND.ink}>
            We don&rsquo;t get anyone funded.
          </Headline>
        </div>
        <div style={{ opacity: dim * dimAll }}>
          <Headline size={62} delay={150} color={BRAND.ink}>
            We map what&rsquo;s already there.
          </Headline>
        </div>
        <div style={{ opacity: dimAll }}>
          <Headline size={76} delay={261}>
            We show you where to look.
          </Headline>
        </div>
        {/* 288 = measured frame the voice says "That's Anansi Atlas." */}
        <div style={{ marginTop: 18 }}>
          <Rise delay={288}>
            <div
              style={{
                fontFamily: SERIF,
                fontWeight: 600,
                fontSize: 58,
                color: BRAND.goldLight,
                textAlign: "center",
              }}
            >
              That&rsquo;s Anansi Atlas.
            </div>
          </Rise>
        </div>
      </Center>
    </AbsoluteFill>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
// ACT IV — VISION · CONCEPT REGISTER
// Everything in this act is UNBUILT. See the header note before changing anything.
// ═════════════════════════════════════════════════════════════════════════════

/** 14 · What If — 450f. Outline type + the placard that names the register. */
const S14: React.FC = () => (
  <ConceptFrame at={0} enter={20} durationInFrames={450} exit={0}>
    <AbsoluteFill>
      <NavyBG w={W} h={H} threads={0.45} />
      <GradientMesh opacity={0.22} />
      <HyperFrames words={["WHAT", "IF"]} at={24} hold={70} enter={22} exit={20} gap={14} size={220} outline />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: 132 }}>
        <Rise delay={290}>
          <Label size={21} color={BRAND.goldLight}>
            The following is not built · not a beta · not a roadmap commitment
          </Label>
        </Rise>
      </AbsoluteFill>
    </AbsoluteFill>
  </ConceptFrame>
);

/** 15 · The Other Side of the Map — 750f. A wireframe that never fills in. */
const S15: React.FC = () => (
  <ConceptFrame at={0} enter={0} durationInFrames={750} exit={0}>
    <AbsoluteFill>
      <NavyBG w={W} h={H} threads={0.45} />
      <GradientMesh opacity={0.18} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: 84 }}>
        <Rise delay={20}>
          <Label size={24} color={BRAND.goldLight}>Funder intelligence — concept</Label>
        </Rise>
      </AbsoluteFill>
      {/* Each block draws in as its phrase is spoken (measured, lead 90):
          "lifecycle" 228 · "One place for communication" 300 · "central hub" 390. */}
      <WireBlock x={11} y={26} w={35} h={26} at={196} draw={40} label="Grant lifecycle" rows={4} />
      <WireBlock x={54} y={26} w={35} h={26} at={272} draw={40} label="Awardee communication" rows={4} />
      <WireBlock x={11} y={60} w={78} h={22} at={360} draw={50} label="Grant data hub — every grant, every awardee" rows={3} />
    </AbsoluteFill>
  </ConceptFrame>
);

/**
 * 16 · A Whole Sector — 810f. The wireframe assembles, holds, then UN-DRAWS in
 * reverse, leaving only the closing line. The strongest non-verbal statement of
 * "this does not exist" available to us.
 */
const S16: React.FC = () => {
  const frame = useCurrentFrame();
  const closing = interpolate(frame, [700, 750], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <ConceptFrame at={0} enter={0} durationInFrames={810} exit={20}>
      <AbsoluteFill>
        <NavyBG w={W} h={H} threads={0.45} />
        <GradientMesh opacity={0.18} />
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: 84, opacity: 1 - closing }}>
          <Rise delay={20}>
            <Label size={24} color={BRAND.goldLight}>County sector view — concept</Label>
          </Rise>
        </AbsoluteFill>
        <WireBlock x={9} y={26} w={24} h={44} at={40} draw={44} label="Youth development" rows={6} undrawAt={640} undraw={90} />
        <WireBlock x={38} y={26} w={24} h={44} at={80} draw={44} label="Housing" rows={6} undrawAt={660} undraw={90} />
        <WireBlock x={67} y={26} w={24} h={44} at={120} draw={44} label="Workforce" rows={6} undrawAt={680} undraw={90} />
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: closing }}>
          <Headline size={72} delay={0} color={BRAND.goldLight}>
            None of this exists today.
          </Headline>
        </AbsoluteFill>
      </AbsoluteFill>
    </ConceptFrame>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
// ACT V — PARTNERSHIP
// ═════════════════════════════════════════════════════════════════════════════

/**
 * 17 · One, So Far — 630f. A single node lights on a wide empty field.
 * Restraint is the point: one organization is not a movement.
 *
 * Partner is Empowered Girls Inc. (Scott, 2026-07-29) — seeded by `manage.py seed_egi`,
 * two founding seats via `setup_egi_seats`, and based in Orlando, ORANGE COUNTY. That
 * last fact is why the narration says "right here in Orange County": for an OCFL room,
 * a local partner lands harder than a national one.
 *
 * ⚠️ STILL NEEDS WRITTEN CONSENT before this screens to OCFL or named grantmakers.
 * Without it, drop the name and the sub-label reads "Founding partner · live in
 * production" alone — the scene works unnamed.
 */
const S17: React.FC = () => (
  <AbsoluteFill>
    <NavyBG w={W} h={H} threads={0.45} />
    <GradientMesh opacity={0.28} />
    <NodeField w={W} h={H} count={11} opacity={0.12} highlight={[4]} at={0} fadeIn={60} />
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 22 }}>
      {/* 133 = measured frame the voice says "Empowered Girls" */}
      <Rise delay={133}>
        <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 62, color: BRAND.white, textAlign: "center" }}>
          Empowered Girls Inc.
        </div>
      </Rise>
      {/* 314 = "live in production" — the sub-label lands on the words */}
      <Rise delay={319}>
        <Label size={22} color={BRAND.goldLight}>
          Founding partner · Orlando, Orange County · live in production
        </Label>
      </Rise>
    </AbsoluteFill>
  </AbsoluteFill>
);

/** 18 · The Invitation — 1050f. The ask, the pillars, the mark, the CTA, the hold. */
const S18: React.FC = () => {
  const frame = useCurrentFrame();
  // Measured (lead 60): "Reveal." 528 · "Anansi Atlas." 653 · "See the whole web." 691 ·
  // "Call us" 736 · narration ends 850. The five pillars span 125 frames (25f/word).
  // The card then holds in silence before the fade (scene is 1081f).
  const askOut = interpolate(frame, [470, 520], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const logoIn = interpolate(frame, [653, 713], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const fadeOut = interpolate(frame, [1031, 1081], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ opacity: fadeOut }}>
      <NavyBG w={W} h={H} threads={0.45} />
      <GradientMesh opacity={0.32 * (1 - logoIn * 0.5)} />
      <NodeField w={W} h={H} count={13} opacity={0.16 * (1 - logoIn)} at={0} fadeIn={50} />

      {/* the ask */}
      <AbsoluteFill style={{ opacity: askOut }}>
        <Center gap={28}>
          <Headline size={66} delay={70} color={BRAND.ink}>
            We&rsquo;re not here to sell you software.
          </Headline>
          <Headline size={78} delay={150}>
            We&rsquo;re here to ask a question.
          </Headline>
        </Center>
      </AbsoluteFill>

      {/* The five brand pillars, spoken rapidly — 22f/word to stay on the voice. */}
      <HyperFrames
        words={["REVEAL", "CONNECT", "CLARIFY", "EMPOWER", "ACT"]}
        at={528}
        hold={14}
        enter={7}
        exit={4}
        gap={0}
        size={132}
        face="sans"
      />

      {/* the close */}
      <AbsoluteFill style={{ opacity: logoIn, alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 34 }}>
        {/* The emblem, not anansi-mark.png — the mark PNG has no alpha channel and
            renders as a navy box against the film's navy. This is the site mark
            extracted onto transparency. */}
        <Img
          src={staticFile("anansi-emblem-785.png")}
          style={{ width: 152, height: 152, objectFit: "contain" }}
        />
        <LogoLockup delay={653} />
        <div style={{ marginTop: 16 }}>
          <Rise delay={691}>
            <div
              style={{
                fontFamily: SERIF,
                fontWeight: 600,
                fontSize: 46,
                color: BRAND.goldLight,
                textAlign: "center",
              }}
            >
              See the whole web.
            </div>
          </Rise>
        </div>

        {/*
          CTA (Scott, 2026-07-29) — a SOFT close, landing on "Call us" at 736.
          The voice never reads the digits: ten spoken numerals would turn a
          six-minute executive film into a late-night ad. The voice invites, the
          card carries the details. Still no price and no seat count.
        */}
        <div style={{ marginTop: 30, display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
          <Rise delay={736}>
            <Label size={19} color={BRAND.goldLight}>Call or visit to learn more</Label>
          </Rise>
          <Rise delay={763}>
            <div
              style={{
                fontFamily: SERIF,
                fontWeight: 500,
                fontSize: 34,
                color: BRAND.white,
                letterSpacing: "0.02em",
                display: "flex",
                alignItems: "center",
                gap: 22,
              }}
            >
              <span>(321) 780&#8209;6335</span>
              <span style={{ color: BRAND.gold, opacity: 0.7, fontSize: 24 }}>·</span>
              <span>anansiatlas.com</span>
            </div>
          </Rise>
          {/*
            A hairline under the CTA that DRAWS rather than fades — the film's
            connective idiom. Inline instead of <ThreadRule>, which is an
            absolutely-positioned SVG keyed to frame coordinates and would not
            sit inside this flex column.
          */}
          <div
            style={{
              width: 430,
              height: 1,
              background: BRAND.gold,
              opacity: 0.5,
              transformOrigin: "center",
              transform: `scaleX(${interpolate(frame, [787, 833], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              })})`,
            }}
          />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
// CAPTIONS — derived from VO_AT and the measured line lengths, NOT from the scene
// grid, so a caption never hangs over a silent passage (Sc01 has none by design).
// Long lines are split in two at a measured beat so no card carries a paragraph.
// ═════════════════════════════════════════════════════════════════════════════
const cap = (i: number, text: string, offset = 0, duration?: number): Caption => ({
  text,
  from: VO_AT[i] + offset,
  duration: duration ?? LINE[i][1] - LINE[i][0] - offset,
});

const CAPTIONS: Caption[] = [
  cap(0, "Every community already holds what it needs.", 0, 260),
  cap(0, "Can the organizations closest to the work actually see it?", 260),
  cap(1, "A workforce nonprofit two blocks from a foundation that funds exactly this work.", 0, 300),
  cap(1, "Not because anyone failed. Because nobody ever drew the map.", 300),
  cap(2, "Every mission has more opportunities than it can see."),
  cap(3, "The opportunity already exists. It's just scattered."),
  cap(4, "310,000 IRS returns. 326,332 Florida grant records.", 0, 310),
  cap(4, "13,554 verified funders. 114,435 exempt organizations.", 310),
  cap(5, "$63.6 million in verified foundation grants, across Orange County.", 0, 241),
  cap(5, "Reaching 474 organizations across this county. 1,912 individual grants.", 241),
  cap(6, "Every opportunity carries a real source — or it never enters the system."),
  cap(7, "Funders. Partners. Government. Resources. Readiness. Pathways."),
  cap(8, "A mission sits at the centre. Around it, the whole field.", 0, 300),
  cap(8, "And an honest read on how ready that organization is.", 300),
  cap(9, "Nothing here was invented — it's drawn from public filings and public records.", 0, 260),
  cap(9, "The platform holds it in one shape, so one person can see all of it.", 260),
  cap(10, "Sort by peer size.", 0, 252),
  cap(10, "The top stops being a $1.2M university research grant and becomes $25,000 peer grants.", 252),
  cap(11, "State, county and city funding — grouped by who issues it.", 0, 200),
  cap(11, "So smaller, more winnable opportunities don't get buried.", 200),
  cap(12, "We map what is already there — and we show you where to look.", 0, 228),
  cap(12, "That's Anansi Atlas.", 228),
  cap(13, "Everything after this line is unbuilt. Not a beta. Not a roadmap promise."),
  cap(14, "Imagine a funder could see the same map — the full lifecycle of every managed grant.", 0, 210),
  cap(14, "One place for communication. A central hub for your grant data. Seen at once.", 210),
  cap(15, "What if a county could see an entire sector at once?", 0, 300),
  cap(15, "None of that exists today. We're showing it in wireframe, on purpose.", 300),
  cap(16, "Empowered Girls works with girls ages 9–18, right here in Orange County.", 0, 249),
  cap(16, "Live in production today — our first founding partner.", 249),
  cap(17, "We're not here to sell you software. We're here to ask a question.", 0, 300),
  cap(17, "Whether the organizations doing the work deserve to see the whole field.", 300, 168),
  cap(17, "Reveal. Connect. Clarify. Empower. Act. See the whole web.", 468, 208),
  cap(17, "Call us, or visit anansiatlas.com, to learn more.", 676),
];

// ═════════════════════════════════════════════════════════════════════════════
// THE FILM
// ═════════════════════════════════════════════════════════════════════════════

export const AnansiVisionFilm: React.FC<{
  audioSrc?: string | null;
  captions?: boolean;
  music?: boolean;
  /** Per-audience screenshot overrides for the Act III walkthrough. See ShotCtx. */
  shots?: Partial<typeof SHOT>;
}> = ({ audioSrc = null, captions = false, music = true, shots }) => {
    // S12B is Sc13; the components after it keep their original names so this stayed a
  // one-line insertion rather than renaming six of them.
  const scenes = [S01, S02, S03, S04, S05, S06, S07, S08, S09, S10, S11, S12, S12B, S13, S14, S15, S16, S17, S18];
  // Memoised so the context value is referentially stable frame to frame.
  const shotValue = React.useMemo(() => ({ ...SHOT, ...shots }), [shots]);

  return (
    <ShotCtx.Provider value={shotValue}>
    <AbsoluteFill style={{ background: BRAND.charcoal }}>
      {scenes.map((Scene, i) => (
        <Sequence key={i} from={B[i]} durationInFrames={B[i + 1] - B[i]}>
          <Scene />
        </Sequence>
      ))}

      {/*
       * SCORE — three purpose-generated stems (ElevenLabs Music, 2026-07-30),
       * replacing the interim 80s looped bed whose seam was audible in a quiet
       * room. Stems crossfade 90f at the ACT boundaries, not at arbitrary loop
       * points, so the music turns over exactly when the film does:
       *
       *   minimal  0      -> B[8]   Acts I-II   opens near-silent, grows with the count
       *   build    B[8]   -> B[13]  Act III     momentum enters as the OrbWeb assembles
       *   resolve  B[13]  -> end    Acts IV-V   sits LOW (0.26) under the concept
       *            register — "unbuilt" deserves doubt, not swell — then warms for
       *            EGI and settles to a single chord under the closing card.
       *
       * Regenerate: node scripts/gen-music-stems.mjs (lengths derive from B[]).
       */}
      {music ? (
        <>
          {/*
            Crossfade centers sit INSIDE the measured speech gaps, not on the act
            cuts themselves: S08 ends at 4201 and S09 begins at 4303, so A->B
            hands off at 4207-4297. B->C hands off at 7889-7979, in the gap after
            "That's Anansi Atlas." and before Act IV's first line. On the raw
            boundaries both fades clipped the edges of speech.

            A->B is UNCHANGED by Sc13: it sits in Act II, before the insertion.
            B->C moved 7386 -> 7889 (+503f) and stem-build was regenerated 110s ->
            130s, because Act III is 503 frames longer than it was. stem-minimal and
            stem-resolve are the SAME takes as the approved cut — music generation is
            nondeterministic, so only the stem whose act changed length was replaced
            (`node scripts/gen-music-stems.mjs stem-build`).
          */}
          <Sequence key="score-a" from={0} durationInFrames={4297}>
            <Audio
              src={staticFile("music/stem-minimal.mp3")}
              endAt={4297}
              volume={(f) =>
                interpolate(f, [0, 60, 4207, 4297], [0, 0.36, 0.36, 0], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                })
              }
            />
          </Sequence>
          <Sequence key="score-b" from={4207} durationInFrames={3772}>
            <Audio
              src={staticFile("music/stem-build.mp3")}
              endAt={3772}
              volume={(f) =>
                interpolate(f, [0, 90, 3682, 3772], [0, 0.34, 0.34, 0], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                })
              }
            />
          </Sequence>
          <Sequence key="score-c" from={7889} durationInFrames={3704}>
            <Audio
              src={staticFile("music/stem-resolve.mp3")}
              endAt={3737}
              volume={(f) =>
                interpolate(
                  f,
                  // low under Act IV's concept register; warm from S17 (EGI, film
                  // frame 9369 = seq 1983); fade with the film's own closing fade.
                  [0, 90, 1983, 2103, 3644, 3704],
                  [0, 0.26, 0.26, 0.36, 0.36, 0],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                )
              }
            />
          </Sequence>
        </>
      ) : null}

      {/*
        VO — the master MP3 sliced per line. A single <Audio> across the whole
        composition would run the narration continuously and bulldoze every silent
        passage the film is built around.
      */}
      {audioSrc
        ? SLICE.map(({ from, to, padIn, src }, i) => {
            const dur = to - from;
            return (
              <Sequence key={`vo${i}`} from={VO_AT[i] - padIn} durationInFrames={dur}>
                <Audio
                  src={staticFile(src ?? audioSrc)}
                  startFrom={from}
                  endAt={to}
                  volume={(f) =>
                    interpolate(f, [0, VO_FADE, dur - VO_FADE, dur], [0, 1, 1, 0], {
                      extrapolateLeft: "clamp",
                      extrapolateRight: "clamp",
                    })
                  }
                />
              </Sequence>
            );
          })
        : null}

      {/* Overlays last, so they sit above every scene. Order matters. */}
      <SceneDissolve boundaries={SCENE_CUTS} fade={10} peak={0.85} />
      <ActBridge boundaries={ACT_CUTS} w={W} h={H} lead={40} tail={40} label={ACT_LABELS} />
      {captions ? <Subtitles captions={CAPTIONS} /> : null}
    </AbsoluteFill>
    </ShotCtx.Provider>
  );
};
