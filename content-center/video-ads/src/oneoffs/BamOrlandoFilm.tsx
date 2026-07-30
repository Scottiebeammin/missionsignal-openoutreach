import React from "react";
import { AbsoluteFill, Audio, Img, interpolate, Sequence, staticFile, useCurrentFrame } from "remotion";
import { BRAND, NODES } from "../brand";
import {
  ActBridge,
  Caption,
  CountUpFigure,
  Eyebrow,
  GradientMesh,
  Headline,
  HyperFrames,
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
} from "../components";
import { CHAPTERS, FUNNEL, OFFER, ORG, PEERS } from "../data/bamOrlandoFacts";

/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * "THE CEILING ISN'T THIS ROOM" — the BAM Orlando board film.
 * ═══════════════════════════════════════════════════════════════════════════════
 *
 * Audience: the board of Black Architects in the Making (BAM) Orlando.
 * Purpose:  a prospect-specific pitch, not a product ad. It opens on THEIR org,
 *           walks the three-number funnel (pool -> your lane -> your first check),
 *           shows real 990-PF grants to real peers their size, shows their OWN
 *           workspace, states plainly what Atlas will not claim, then asks.
 *
 * Register: the Vision Film's ("The Whole Field") — Apple keynote / Stripe
 *           Sessions. Slow, spacious, confident. Same 18-scene / five-act spine,
 *           same native 1920x1080, same VO-slicing method. Unlike that film, this
 *           one DOES close on the offer: it is a pitch, and the room knows it.
 *
 * Supersedes oneoffs/BamOrlandoPresentation.tsx — the 2026-07-16 cut, which was
 * 1080x1080 pillarboxed into a 16:9 backdrop, timed by word-count estimate, and
 * shipped SILENT (its `audioSrc` default was null; the narration existed only as
 * burned subtitles). That comp is left registered so the old render stays
 * reproducible. New work goes here.
 *
 * ── ⚠️ NOT A PUBLIC ASSET ────────────────────────────────────────────────────
 * Act IV shows BAM's own workspace (project 18), captured by
 * `scripts/capture-hd-shots.py --project 18 --prefix bam-`. Every other film in
 * this repo deliberately uses the Creative Display demo profile so it is ad-safe
 * by construction. This one does not, because the entire pitch is "this already
 * exists and it is yours." Consequence: board room only. Do not post it.
 *
 * ── FACTUAL SPINE (every figure traces to src/data/bamOrlandoFacts.ts) ───────
 *   300+ students / 135+ this year / 14 workshops / 87 volunteers / $29,480
 *                                       ......... bamorlando.org + their LinkedIn
 *   $56.0M · 653 foundations · 2,622 grants ..... IRS 990-PF, Orange County
 *   $20.6M · 229 foundations · 994 grants ....... same, filtered to their size band
 *   $5,000 typical grant ........................ same
 *   Peer names + amounts ........................ same; all six appear on the
 *                                                 peer-size sort in Sc14's capture
 *   61 / Developing readiness ................... their own Readiness page
 *
 * The $20.6M / 229 / 994 trio is corroborated ON SCREEN by their own dashboard in
 * Sc12, which is the point of putting that shot in the film at all.
 *
 * ── WHAT IS DELIBERATELY NOT NARRATED ───────────────────────────────────────
 * Their dashboard also reads "418 opportunities mapped" and "317 strong matches".
 * Those are computed against reference tables, not stored matched records — BAM's
 * workspace has zero Opportunity rows — so they stay on screen as context and out
 * of the VO, which claims only the sourced $20.6M / 229 / 994 trio.
 *
 * ── WHAT IS HIDDEN IN THE Sc12 CAPTURE, AND WHY (Scott, 2026-07-30) ─────────
 * The dashboard shot is taken with four elements suppressed at capture time:
 *   .fw-badge          "🕸️ Founding Atlas Partner" — true of project 14, and a
 *                      presumption on a prospect who has not signed
 *   .fw-sub            "You're one of our first 20 founding partners…" — same claim
 *   .fw-stat-verified  "0 verified grants matched to you" — accurate but useless on
 *                      a workspace whose analysis has never run, and it fights a
 *                      slide whose job is to show potential
 *   .fw-title          "Welcome, there — …" — a missing-contact-first-name fallback
 *                      that reads as a bug on a projector. Give the BAM record a
 *                      contact first name and this line can come back for real;
 *                      inventing one for a screenshot was not on the table.
 * This is a capture-time cosmetic decision, NOT a product change — see the --hide
 * docstring in scripts/capture-hd-shots.py. Re-capture with:
 *   python scripts/capture-hd-shots.py --session <sid> --project 18 --prefix bam- \
 *     --only dashboard --hide ".fw-badge,.fw-sub,.fw-stat-verified,.fw-title"
 * Hiding those shifts the layout UP, so Sc12's spotlight/scrim box was re-measured
 * against the new capture. Re-measure again if the hide list changes.
 */

const W = 1920;
const H = 1080;

// ─────────────────────────────────────────────────────────────────────────────
// BEAT MAP. Scene N occupies [B[N-1], B[N]). Scene 01 IS the silent lead; VO
// starts at B[1].
//
// Unlike AnansiVisionFilm.tsx:87, B is NOT a hand-written array — it is COMPUTED
// from the measured audio as LEAD + line + TAIL per scene. That matters because a
// script edit changes every line length downstream: rewording three lines to drop
// the word "money" (2026-07-30) moved the film from 262.0s to 271.5s of speech and
// shifted all seventeen scene boundaries. With a literal B, that edit means
// re-deriving eighteen numbers by hand and silently desyncing the film if you get
// one wrong. Computed, a VO regen is: paste the new LINE table, re-measure the
// per-scene phrase offsets, done.
//
// LEAD  = silence before the line starts — the room breathes first.
// TAIL  = silence after it ends — how long the beat is allowed to hang.
// ─────────────────────────────────────────────────────────────────────────────
const SILENT_LEAD = 600; // Sc01, music only

/** Frames of silence before each scene's narration begins. */
const LEAD = [60, 60, 70, 60, 70, 60, 45, 45, 45, 50, 70, 60, 60, 60, 60, 70, 60];
/** Frames of silence after it ends. Sc06 (the hero line) and Sc18 (the card) get the long ones. */
const TAIL = [60, 60, 70, 60, 130, 60, 60, 60, 75, 70, 80, 80, 90, 80, 80, 80, 190];

const ACT_LABELS = ["II · THE PROBLEM", "III · THE COUNT", "IV · YOUR WORKSPACE", "V · THE ASK"];

// BAM's own workspace, captured at 2x DPR off project 18. See the header warning.
const SHOT = {
  dashboard: "screenshots/bam-dashboard.png",
  web: "screenshots/bam-web.png",
  // Sc14's TRUE A/B pair — one locked scrollY, the sort control the only difference.
  // `oppsDefault` is ?sort=largest (University of Florida research grants on top);
  // `oppsPeer` is the default ?sort=fit ($5,000 grants to Orange County orgs BAM's size).
  oppsDefault: "screenshots/bam-opps-default.png",
  oppsPeer: "screenshots/bam-opps-peersize.png",
  readiness: "screenshots/bam-readiness.png",
};

/**
 * ── VO SLICING ───────────────────────────────────────────────────────────────
 * One continuous MP3 cannot hold this film's silent passages (Sc01 is 20s of
 * music alone). So we generate once with gen-vo-timestamped.mjs and slice the
 * master per line with <Audio startFrom endAt>.
 *
 * [srcFrom, srcTo] are frames INTO public/bam-orlando-film-vo.mp3 (266.9s total).
 * Produced by `node scripts/vo-line-slices.mjs BamOrlandoFilm` — measured off the
 * alignment JSON, not estimated. Line i belongs to Scene i+2; Scene 01 is silent.
 *
 * Regenerate: node scripts/gen-vo-timestamped.mjs BamOrlandoFilm
 *             node scripts/vo-line-slices.mjs   BamOrlandoFilm
 */
const LINE: [number, number][] = [
  [0, 569],     // S02 19.0s  This is Black Architects in the Making
  [578, 1002],  // S03 14.1s  Three hundred students since you started
  [1011, 1345], // S04 11.1s  None of that came from a form
  [1346, 1871], // S05 17.5s  So you already know the problem
  [1885, 2182], // S06  9.9s  Not missing. Invisible.
  [2193, 2770], // S07 19.2s  So we built the count
  [2790, 3117], // S08 10.9s  Fifty-six million — the pool
  [3132, 3567], // S09 14.5s  Twenty point six million — your lane
  [3581, 3952], // S10 12.4s  Five thousand dollars — your first check
  [3961, 4659], // S11 23.3s  The names left in
  [4660, 5141], // S12 16.0s  This is your workspace
  [5148, 5596], // S13 14.9s  Your mission sits in the middle
  [5600, 6162], // S14 18.7s  Watch one control
  [6166, 6701], // S15 17.8s  The truth about where you stand
  [6733, 7313], // S16 19.3s  Three things this will not do
  [7314, 7785], // S17 15.7s  A hundred and fifty a month
  [7794, 8304], // S18 17.0s  The ceiling is not this room
];

const MASTER_FRAMES = 8304;

/** Scene N's span = LEAD + spoken line + TAIL. Sc01 is the silent lead. */
const B = LINE.reduce<number[]>(
  (acc, [from, to], i) => [...acc, acc[acc.length - 1] + LEAD[i] + (to - from) + TAIL[i]],
  [0, SILENT_LEAD],
);

export const BAM_FILM_TOTAL = B[18]; // 11,134f = 6:11 @ 30fps

/** Act boundaries — the connection web draws THROUGH these cuts. */
const ACT_CUTS = [B[4], B[6], B[11], B[16]];
/** Everything else gets the quieter dip. DISJOINT from ACT_CUTS — never both. */
const SCENE_CUTS = [B[1], B[2], B[3], B[5], B[7], B[8], B[9], B[10], B[12], B[13], B[14], B[15], B[17]];

/**
 * Padding + ramps, for the same reason AnansiVisionFilm.tsx:162 documents: cutting
 * exactly on alignment character boundaries clicks (step discontinuity on a
 * non-zero sample) and clips the first phoneme's onset and the last consonant's
 * decay. Padding is clamped to HALF the gap to the neighbouring line so a slice
 * can never bleed the next sentence — two gaps here are 0.00s.
 */
const VO_PAD = 5;
const VO_FADE = 4;

const SLICE = LINE.map(([from, to], i) => {
  const prevEnd = i > 0 ? LINE[i - 1][1] : -Infinity;
  const nextStart = i < LINE.length - 1 ? LINE[i + 1][0] : Infinity;
  const padIn = Math.max(0, Math.min(VO_PAD, Math.floor((from - prevEnd) / 2), from));
  const padOut = Math.max(0, Math.min(VO_PAD, Math.floor((nextStart - to) / 2), MASTER_FRAMES - to));
  return { from: from - padIn, to: to + padOut, padIn };
});

/** Where line i lands in the composition. Scene components use these for visual sync. */
const VO_AT = LINE.map((_, i) => B[i + 1] + LEAD[i]);

const Center: React.FC<{ children: React.ReactNode; gap?: number }> = ({ children, gap = 26 }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap }}>
    {children}
  </AbsoluteFill>
);

/**
 * OrbWeb in a correctly-sized box. Do not replace with a bare `transform` div —
 * OrbWeb renders an AbsoluteFill, and a transform div with no intrinsic size
 * becomes its containing block and collapses to 0x0. See AnansiVisionFilm.tsx:164.
 */
const ORB = 1080;
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

/**
 * SCRIM — darkens everything OUTSIDE a rectangle, in frame percentages.
 *
 * `UISpotlight`'s own `vignette` cannot do this job here. It draws a radial
 * gradient whose radii are `w * 2.4%` and `h * 3.2%` of the frame, which is tuned
 * for a small control (the Vision Film's sort toggle is w=11 -> a 26% ellipse).
 * Sc12's band is w=50.5, giving a 121% ellipse — the dark stop lands off-screen
 * and nothing dims at all. Four hard rects are exact at any box size, and being
 * pure arithmetic they are seek-safe.
 *
 * This matters beyond aesthetics in Sc12: their dashboard carries "0 verified
 * grants matched to you" immediately above the band we are pointing at.
 */
const Scrim: React.FC<{
  x: number;
  y: number;
  w: number;
  h: number;
  at: number;
  draw?: number;
  hold: number;
  out?: number;
  opacity?: number;
}> = ({ x, y, w, h, at, draw = 26, hold, out = 20, opacity = 0.72 }) => {
  const frame = useCurrentFrame();
  const l = frame - at;
  if (l < 0 || l > draw + hold + out) return null;
  const on =
    interpolate(l, [0, draw], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) *
    (1 - interpolate(l, [draw + hold, draw + hold + out], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  const ink = `rgba(4,9,20,${opacity})`;
  const band = (style: React.CSSProperties) => (
    <div style={{ position: "absolute", background: ink, ...style }} />
  );
  return (
    <AbsoluteFill style={{ opacity: on, pointerEvents: "none" }}>
      {band({ left: 0, top: 0, width: "100%", height: `${y}%` })}
      {band({ left: 0, top: `${y + h}%`, width: "100%", bottom: 0 })}
      {band({ left: 0, top: `${y}%`, width: `${x}%`, height: `${h}%` })}
      {band({ left: `${x + w}%`, top: `${y}%`, right: 0, height: `${h}%` })}
    </AbsoluteFill>
  );
};

/** A denial row in Sc16 — the honesty beat. */
const DenyRow: React.FC<{ text: string; at: number }> = ({ text, at }) => (
  <Rise delay={at}>
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 24,
        padding: "22px 34px",
        width: 1180,
        borderRadius: 14,
        background: "rgba(255,255,255,0.04)",
        border: "1px solid rgba(255,255,255,0.10)",
        fontFamily: SANS,
        fontSize: 34,
        color: BRAND.ink,
      }}
    >
      <span style={{ color: BRAND.rose, fontSize: 36, fontWeight: 800 }}>&#10005;</span>
      {text}
    </div>
  </Rise>
);

/** A pill — used for the chapters in Sc18 and the "no ___" terms in Sc17. */
const Pill: React.FC<{ children: React.ReactNode; at: number; active?: boolean }> = ({
  children,
  at,
  active = false,
}) => (
  <Rise delay={at}>
    <div
      style={{
        padding: "12px 30px",
        borderRadius: 999,
        background: active ? "rgba(212,160,23,0.18)" : "rgba(255,255,255,0.04)",
        border: `1px solid ${active ? BRAND.gold : "rgba(255,255,255,0.14)"}`,
        fontFamily: SANS,
        fontWeight: 700,
        fontSize: 26,
        color: active ? BRAND.goldLight : BRAND.muted,
      }}
    >
      {children}
    </div>
  </Rise>
);

// ═════════════════════════════════════════════════════════════════════════════
// ACT I — RECOGNITION
// ═════════════════════════════════════════════════════════════════════════════

/** 01 · First Light — 600f, silent. Black, one hairline, nine faint nodes, three words. */
const S01: React.FC = () => {
  const frame = useCurrentFrame();
  // Hold true black for 40f before anything at all. The room settles.
  const wake = interpolate(frame, [40, 190], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: BRAND.charcoal }}>
      <AbsoluteFill style={{ opacity: wake }}>
        <NavyBG w={W} h={H} threads={0.45} />
        <GradientMesh opacity={0.28 * wake} />
      </AbsoluteFill>
      <ThreadRule from={[14, 66]} to={[86, 66]} at={70} draw={110} hold={420} out={0} opacity={0.5} />
      <NodeField w={W} h={H} count={9} opacity={0.18} at={150} fadeIn={90} />
      <HyperFrames words={["STUDENTS", "ARCHITECTURE", "ORLANDO"]} at={250} hold={54} enter={18} exit={16} gap={10} size={186} />
    </AbsoluteFill>
  );
};

/** 02 · Their Name — 689f. Lead 60. "Founded in twenty eighteen" lands at 212. */
const S02: React.FC = () => (
  <AbsoluteFill>
    <NavyBG w={W} h={H} threads={0.5} />
    <GradientMesh opacity={0.26} />
    <NodeField w={W} h={H} count={11} opacity={0.14} at={0} fadeIn={70} />
    <Center gap={30}>
      <Eyebrow delay={40}>{`${ORG.city} · Chapter since ${ORG.founded}`}</Eyebrow>
      <Headline delay={72} size={82}>
        {ORG.name}
      </Headline>
      <Rise delay={212}>
        <div
          style={{
            fontFamily: SANS,
            fontSize: 30,
            color: BRAND.muted,
            textAlign: "center",
            padding: "0 300px",
            lineHeight: 1.5,
          }}
        >
          {ORG.mission}
        </div>
      </Rise>
    </Center>
  </AbsoluteFill>
);

/**
 * 03 · Their Numbers — 544f. Lead 60. Each figure counts up as it is SPOKEN:
 * measured offsets +0 / +67 / +127 / +161 / +212 into the line.
 */
const S03: React.FC = () => (
  <AbsoluteFill>
    <NavyBG w={W} h={H} threads={0.45} />
    <GradientMesh opacity={0.2} />
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: 210 }}>
      <Eyebrow delay={20}>What you have already done</Eyebrow>
    </AbsoluteFill>
    <Center gap={0}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 74, marginTop: 40 }}>
        <CountUpFigure value={300} format={(n) => `${Math.round(n)}+`} label="students since 2018" at={60} count={54} size={94} />
        <CountUpFigure value={135} format={(n) => `${Math.round(n)}+`} label="students this year" at={127} count={48} size={94} />
        <CountUpFigure value={14} label="workshops in 2025" at={187} count={34} size={94} />
        <CountUpFigure value={87} label="volunteers" at={221} count={38} size={94} />
        <CountUpFigure
          value={29480}
          format={(n) => `$${Math.round(n).toLocaleString("en-US")}`}
          label="raised last year"
          at={272}
          count={64}
          size={94}
        />
      </div>
      <Rise delay={406}>
        <div style={{ fontFamily: SERIF, fontSize: 40, color: BRAND.ink, marginTop: 64 }}>
          Every dollar of it from your own community.
        </div>
      </Rise>
    </Center>
  </AbsoluteFill>
);

/**
 * 04 · Sourced, Not Guessed — 474f. Lead 70. "I built this from your website" at
 * 157; "Nothing you are about to see is a guess" at 343 — the sources dim as the
 * claim lands, so the line owns the frame it is spoken in.
 */
const S04: React.FC = () => {
  const frame = useCurrentFrame();
  const dim = interpolate(frame, [333, 378], [1, 0.3], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill>
      <NavyBG w={W} h={H} threads={0.4} />
      <GradientMesh opacity={0.18} />
      <Center gap={34}>
        <div style={{ opacity: dim, display: "flex", flexDirection: "column", alignItems: "center", gap: 22 }}>
          <Eyebrow delay={20}>Where this came from</Eyebrow>
          <div style={{ display: "flex", gap: 18, marginTop: 8 }}>
            <Pill at={157}>bamorlando.org</Pill>
            <Pill at={178}>your LinkedIn</Pill>
            <Pill at={199}>IRS 990-PF filings</Pill>
          </div>
        </div>
        <Rise delay={343}>
          <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 74, color: BRAND.goldLight, textAlign: "center", padding: "0 200px", lineHeight: 1.15 }}>
            Nothing you&rsquo;re about to see is a guess.
          </div>
        </Rise>
      </Center>
    </AbsoluteFill>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
// ACT II — THE PROBLEM
// ═════════════════════════════════════════════════════════════════════════════

/**
 * 05 · The Nights — 645f. Lead 60. "The opportunity exists" at 161, "nights of
 * searching" at 394, "you do not have a grant writer" at 534.
 */
const S05: React.FC = () => (
  <AbsoluteFill>
    <NavyBG w={W} h={H} threads={0.45} />
    <GradientMesh opacity={0.22} />
    <Center gap={40}>
      <Eyebrow delay={20}>The problem you already live</Eyebrow>
      <Headline delay={60} size={68} color={BRAND.ink}>
        You&rsquo;re doing the work. The opportunity exists.
      </Headline>
      <Rise delay={394}>
        <div style={{ fontFamily: SANS, fontSize: 34, color: BRAND.muted, textAlign: "center", padding: "0 280px", lineHeight: 1.5 }}>
          Finding out who actually funds architecture pathways for students of color in Orange County means nights of searching &mdash; after the workshops, after the day job.
        </div>
      </Rise>
      <Rise delay={534}>
        <Label size={28} color={BRAND.rose}>And you don&rsquo;t have a grant writer</Label>
      </Rise>
    </Center>
  </AbsoluteFill>
);

/**
 * 06 · Not Missing. Invisible. — 497f. Lead 70. The hero line lands at 192 and
 * then holds in silence for ~4s. This is the film's pivot; do not shorten the tail.
 */
const S06: React.FC = () => {
  const frame = useCurrentFrame();
  const fade = interpolate(frame, [185, 230], [1, 0.26], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill>
      <NavyBG w={W} h={H} threads={0.5} />
      <GradientMesh opacity={0.3} />
      <Center gap={26}>
        <div style={{ opacity: fade }}>
          <Headline delay={30} size={72} color={BRAND.ink}>
            The opportunity isn&rsquo;t missing.
          </Headline>
        </div>
        <Rise delay={192}>
          <div style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 168, color: BRAND.gold, letterSpacing: "-0.02em", lineHeight: 1 }}>
            It&rsquo;s invisible.
          </div>
        </Rise>
      </Center>
    </AbsoluteFill>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
// ACT III — THE COUNT
// ═════════════════════════════════════════════════════════════════════════════

/**
 * 07 · We Built the Count — 697f. Lead 60. Figures count up on their spoken
 * offsets (+44 / +182 / +293); the closing question arrives at 525.
 */
const S07: React.FC = () => (
  <AbsoluteFill>
    <NavyBG w={W} h={H} threads={0.45} />
    <GradientMesh opacity={0.22} />
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: 190 }}>
      <Eyebrow delay={20}>So we built the count</Eyebrow>
    </AbsoluteFill>
    <Center gap={0}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 108, marginTop: 30 }}>
        <CountUpFigure value={310000} label="I.R.S. returns read" at={104} count={78} size={104} />
        <CountUpFigure value={326332} label="Florida grant records" at={242} count={78} size={104} />
        <CountUpFigure value={13554} label="verified funders" at={353} count={70} size={104} />
      </div>
      <Rise delay={525}>
        <div style={{ fontFamily: SERIF, fontSize: 46, color: BRAND.ink, marginTop: 76, textAlign: "center", padding: "0 260px", lineHeight: 1.3 }}>
          Who actually gives to an organization like yours, in your county?
        </div>
      </Rise>
    </Center>
  </AbsoluteFill>
);

/**
 * The funnel rung — Sc08/09/10 share one component so the three beats are
 * visually identical and only the number changes. `countAt` and `captionAt` are
 * measured spoken offsets, passed per scene.
 */
const FunnelScene: React.FC<{ index: number; countAt: number; captionAt: number }> = ({
  index,
  countAt,
  captionAt,
}) => {
  const step = FUNNEL[index];
  const color = step.tone === "teal" ? "#5eead4" : BRAND.goldLight;
  const frame = useCurrentFrame();
  const grow = interpolate(frame, [countAt, countAt + 80], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill>
      <NavyBG w={W} h={H} threads={0.4} />
      <GradientMesh opacity={0.2} />
      <Center gap={20}>
        <Eyebrow delay={Math.max(0, countAt - 30)}>{`${index + 1} of 3`}</Eyebrow>
        <Rise delay={countAt}>
          <div style={{ fontFamily: SERIF, fontSize: 200, fontWeight: 700, color, lineHeight: 1, letterSpacing: "-0.02em" }}>
            {step.amount}
          </div>
        </Rise>
        {/* A rule that grows with the figure — the funnel narrowing, drawn not stated. */}
        <div style={{ width: 760 * (index === 2 ? 0.28 : index === 1 ? 0.62 : 1), height: 2, background: color, opacity: 0.5 * grow, transform: `scaleX(${grow})` }} />
        <Rise delay={countAt + 22}>
          <div style={{ fontFamily: SANS, fontSize: 38, color: BRAND.ink, textAlign: "center", padding: "0 220px", lineHeight: 1.3 }}>
            {step.label}
          </div>
        </Rise>
        <Rise delay={countAt + 40}>
          <Label size={24}>{step.sub}</Label>
        </Rise>
        <Rise delay={captionAt}>
          <div
            style={{
              marginTop: 22,
              padding: "14px 36px",
              borderRadius: 999,
              background: step.tone === "teal" ? "rgba(94,234,212,0.12)" : "rgba(212,160,23,0.14)",
              border: `1px solid ${color}55`,
              fontFamily: SANS,
              fontWeight: 800,
              fontSize: 32,
              color,
            }}
          >
            {step.caption}
          </div>
        </Rise>
      </Center>
    </AbsoluteFill>
  );
};

/** 08 · The Pool — 432f. Lead 45; "That is the pool" at 337. */
const S08: React.FC = () => <FunnelScene index={0} countAt={45} captionAt={337} />;
/** 09 · Your Lane — 540f. Lead 45; "That is your lane" at 444. */
const S09: React.FC = () => <FunnelScene index={1} countAt={45} captionAt={444} />;
/** 10 · Your First Check — 491f. "five thousand dollars" at 121; caption at 364. */
const S10: React.FC = () => <FunnelScene index={2} countAt={121} captionAt={364} />;

/**
 * 11 · The Names Left In — 818f. Lead 50. Each peer row lands on its own spoken
 * name: measured offsets +108 / +197 / +286 / +408 / +474 / +541. The closing
 * "Not projections. Tax filings." arrives on "Real organizations" at 625.
 */
const S11: React.FC = () => {
  const AT = [158, 247, 336, 458, 524, 591];
  return (
    <AbsoluteFill>
      <NavyBG w={W} h={H} threads={0.4} />
      <GradientMesh opacity={0.18} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: 118 }}>
        <Eyebrow delay={20}>Orgs your size · Orange County · from the filings</Eyebrow>
      </AbsoluteFill>
      <Center gap={12}>
        <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 40 }}>
          {PEERS.map((p, i) => (
            <Rise key={p.org} delay={AT[i]}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 30,
                  width: 1000,
                  padding: "18px 34px",
                  borderRadius: 14,
                  background: "rgba(255,255,255,0.04)",
                  border: "1px solid rgba(212,160,23,0.18)",
                }}
              >
                <div style={{ fontFamily: SANS, fontSize: 32, color: BRAND.ink }}>{p.org}</div>
                <div style={{ fontFamily: SERIF, fontSize: 42, fontWeight: 700, color: BRAND.goldLight }}>{p.amount}</div>
              </div>
            </Rise>
          ))}
        </div>
        <Rise delay={625}>
          <div style={{ marginTop: 34 }}>
            <Label size={26} color={BRAND.goldLight}>Not projections. Tax filings.</Label>
          </div>
        </Rise>
      </Center>
    </AbsoluteFill>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
// ACT IV — YOUR WORKSPACE  (BAM's own screens — see the header warning)
// ═════════════════════════════════════════════════════════════════════════════

/**
 * 12 · Not a Mockup — 631f. Lead 70. "This is your workspace" at 120, the $20.6M
 * figure at 234, "not marketing copy" at 413.
 *
 * The spotlight is framed on the $20,606,324 band ONLY — the one figure on this
 * screen that is sourced, corroborated, and narrated. The scrim holds the rest of
 * the card back so the room reads one number, not a dashboard.
 */
const S12: React.FC = () => (
  <AbsoluteFill>
    <NavyBG w={W} h={H} threads={0.45} />
    <GradientMesh opacity={0.2} />
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <ScreenshotPanel
        src={staticFile(SHOT.dashboard)}
        label="anansiatlas.com/dashboard"
        width={1240}
        zoomFrom={1.0}
        zoomTo={1.02}
        panY={[0, -3]}
        durationInFrames={631}
      />
    </AbsoluteFill>
    <Scrim x={30} y={29.1} w={50.5} h={5.3} at={234} draw={26} hold={195} out={20} opacity={0.74} />
    <UISpotlight x={30} y={29.1} w={50.5} h={5.3} at={234} draw={26} hold={195} out={20} vignette={0} />
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: 40 }}>
      <Eyebrow delay={120}>Your workspace &mdash; already built</Eyebrow>
    </AbsoluteFill>
    {/* The read-out sits in the bottom safe band, not against the box: their
        dashboard's CTA buttons are directly beneath that band. */}
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: 62 }}>
      <Rise delay={261}>
        <Label size={30} color={BRAND.goldLight}>$20.6M &middot; 229 orgs your size &middot; 994 grants</Label>
      </Rise>
    </AbsoluteFill>
  </AbsoluteFill>
);

/**
 * 13 · Your Mission in the Middle — 588f. Lead 60. The OrbWeb metaphor assembles,
 * then cross-dissolves into their real Opportunity Web page: the metaphor becoming
 * the product. "six things" at 131; "that is what we mean by a web" at 344 — the
 * handoff completes at 400, so the real UI is already up when that line lands.
 */
const S13: React.FC = () => {
  const frame = useCurrentFrame();
  const build = interpolate(frame, [40, 300], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const handoff = interpolate(frame, [330, 400], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill>
      <NavyBG w={W} h={H} threads={0.45} />
      <GradientMesh opacity={0.24} />
      <AbsoluteFill style={{ opacity: 1 - handoff, alignItems: "center", justifyContent: "center" }}>
        <OrbWebBox scale={0.92} progress={build} />
      </AbsoluteFill>
      <AbsoluteFill style={{ opacity: handoff, alignItems: "center", justifyContent: "center" }}>
        <ScreenshotPanel src={staticFile(SHOT.web)} label="anansiatlas.com/web" width={1240} zoomFrom={1.0} zoomTo={1.03} panY={[0, -3]} durationInFrames={258} />
      </AbsoluteFill>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: 40 }}>
        <Eyebrow delay={131}>{NODES.join("  ·  ")}</Eyebrow>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/**
 * 14 · One Control — 712f. THE HERO DEMO. Lead 60. Same viewport, same scroll,
 * one sort toggle. Measured beats: "sorted the ordinary way" 112 · "University of
 * Florida" 244 · "sort by organizations your size" 291 · "five-thousand-dollar
 * checks" 411 · "the lens changed" 588.
 *
 * The wipe runs 305 -> 375, i.e. it STARTS just after the voice says "sort by
 * organizations your size" and FINISHES before it says the new figure. Each label
 * is pinned to the screen it actually describes: the UF label clears at 300,
 * before the wipe; the peer label arrives at 375, after it.
 */
const S14: React.FC = () => {
  const frame = useCurrentFrame();
  const wipe = interpolate(frame, [305, 375], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill>
      <NavyBG w={W} h={H} threads={0.45} />
      <GradientMesh opacity={0.2} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ position: "relative" }}>
          <ScreenshotPanel src={staticFile(SHOT.oppsDefault)} label="anansiatlas.com/foundations" width={1240} zoomFrom={1.0} zoomTo={1.03} durationInFrames={712} />
          <AbsoluteFill style={{ clipPath: `inset(0 ${100 - wipe}% 0 0)` }}>
            <ScreenshotPanel src={staticFile(SHOT.oppsPeer)} label="anansiatlas.com/foundations" width={1240} zoomFrom={1.0} zoomTo={1.03} durationInFrames={712} />
          </AbsoluteFill>
          {wipe > 0 && wipe < 100 ? (
            <div style={{ position: "absolute", left: `${wipe}%`, top: 0, bottom: 0, width: 2, background: BRAND.gold, opacity: 0.9 }} />
          ) : null}
        </div>
      </AbsoluteFill>
      {/* Framed on the real toggle ("Grants your size · Largest grants"), measured
          off the 2x capture: panel left edge 17.71%, span 64.58% of the frame. */}
      {/* Right-anchored and ABOVE the box — the control sits at the panel's right
          edge, so a left-anchored label below it runs off-frame and lands on the
          panel's description copy. Short text for the same reason. */}
      <UISpotlight
        x={70.5}
        y={22.6}
        w={11}
        h={4}
        at={250}
        draw={26}
        hold={140}
        out={16}
        label="One control"
        labelPos="above"
        labelAlign="right"
      />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: 78 }}>
        <div style={{ position: "relative", height: 44, width: 1100 }}>
          <AbsoluteFill style={{ opacity: interpolate(frame, [205, 244, 300], [0, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>
            <Label size={28} color={BRAND.muted}>$1,199,692 &middot; University of Florida</Label>
          </AbsoluteFill>
          <AbsoluteFill style={{ opacity: interpolate(frame, [375, 415], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>
            <Label size={28} color={BRAND.goldLight}>$5,000 &middot; Orange County orgs your size</Label>
          </AbsoluteFill>
        </div>
      </AbsoluteFill>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: 40 }}>
        <div style={{ opacity: interpolate(frame, [588, 638], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>
          <Label size={30} color={BRAND.ink}>Nothing added. Nothing removed. The lens changed.</Label>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/**
 * 15 · The Honest Read — 675f. Lead 60. Their readiness page, spotlit twice:
 * the score at 150 ("sixty-one out of a hundred"), then the two gap cards at 387
 * ("missing documents"). Closing line on "only flatters you" at 525.
 *
 * Their score is 61 / Developing and the page names real gaps. That is the point
 * of the beat — a pitch that shows the prospect their own weak number is a pitch
 * they believe. Do not swap this for a flattering screen.
 */
const S15: React.FC = () => {
  const frame = useCurrentFrame();
  const dim = interpolate(frame, [518, 560], [1, 0.34], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill>
      <NavyBG w={W} h={H} threads={0.45} />
      <GradientMesh opacity={0.2} />
      <AbsoluteFill style={{ opacity: dim }}>
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
          <ScreenshotPanel src={staticFile(SHOT.readiness)} label="anansiatlas.com/readiness" width={1240} zoomFrom={1.0} zoomTo={1.02} panY={[0, -3]} durationInFrames={675} />
        </AbsoluteFill>
        {/* Both boxes sit on light UI panels, so the labels go above with the halo
            and the scrims do the dimming — see the Scrim docstring. */}
        <Scrim x={64} y={28} w={16} h={14} at={150} draw={22} hold={165} out={16} opacity={0.68} />
        <UISpotlight x={64} y={28} w={16} h={14} at={150} draw={22} hold={165} out={16} vignette={0} label="Your score" labelPos="above" labelAlign="right" />
        <Scrim x={30} y={49.5} w={25.5} h={13.5} at={387} draw={22} hold={110} out={16} opacity={0.68} />
        {/* No label on this one — the page's own "WHAT TO FIX NEXT" heading is
            directly above the box, and a second copy of it just reads as a glitch. */}
        <UISpotlight x={30} y={49.5} w={25.5} h={13.5} at={387} draw={22} hold={110} out={16} vignette={0} />
      </AbsoluteFill>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <Rise delay={525}>
          <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 66, color: BRAND.goldLight, textAlign: "center", padding: "0 240px", lineHeight: 1.2 }}>
            A tool that only flatters you isn&rsquo;t worth having.
          </div>
        </Rise>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/**
 * 16 · What This Won't Do — 720f. Lead 60. Each denial lands on its own clause:
 * measured +99 / +243 / +410, and "Verified means verified" at 577.
 */
const S16: React.FC = () => (
  <AbsoluteFill>
    <NavyBG w={W} h={H} threads={0.4} />
    <GradientMesh opacity={0.18} />
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: 140 }}>
      <Eyebrow delay={20}>What this won&rsquo;t do</Eyebrow>
    </AbsoluteFill>
    <Center gap={18}>
      <div style={{ display: "flex", flexDirection: "column", gap: 18, marginTop: 40 }}>
        <DenyRow at={159} text="Call a $350M university “an org like you.”" />
        <DenyRow at={303} text="Show a grant you can’t click through and verify." />
        <DenyRow at={470} text="Promise to get you funded. You still write the ask." />
      </div>
      <Rise delay={577}>
        <div
          style={{
            marginTop: 40,
            padding: "16px 42px",
            borderRadius: 999,
            background: "rgba(15,118,110,0.16)",
            border: `1px solid ${BRAND.teal}`,
            fontFamily: SANS,
            fontWeight: 800,
            fontSize: 34,
            color: "#5eead4",
          }}
        >
          &#10003; Verified means verified.
        </div>
      </Rise>
    </Center>
  </AbsoluteFill>
);

// ═════════════════════════════════════════════════════════════════════════════
// ACT V — THE ASK
// ═════════════════════════════════════════════════════════════════════════════

/**
 * 17 · The Offer — 621f. Lead 70. The price lands with the first words of the
 * line (offset +0 -> frame 70); the three "no ___" terms arrive on "No setup fee"
 * at 322, and the closing line on "If the map is wrong" at 467. Unlike the Vision
 * Film, this close DOES carry the price: the room is a board being asked for a
 * decision, not a funder being asked a question.
 */
const S17: React.FC = () => (
  <AbsoluteFill>
    <NavyBG w={W} h={H} threads={0.45} />
    <GradientMesh opacity={0.26} />
    <NodeField w={W} h={H} count={11} opacity={0.12} at={0} fadeIn={60} />
    <Center gap={20}>
      <Rise delay={70}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
          <span style={{ fontFamily: SERIF, fontSize: 190, fontWeight: 700, color: BRAND.goldLight, lineHeight: 1 }}>{OFFER.price}</span>
          <span style={{ fontFamily: SANS, fontSize: 46, color: BRAND.muted }}>{OFFER.cadence}</span>
        </div>
      </Rise>
      <Rise delay={110}>
        <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 34, color: BRAND.gold, letterSpacing: "0.04em" }}>{OFFER.terms}</div>
      </Rise>
      <Rise delay={140}>
        <Label size={24}>{OFFER.cohort}</Label>
      </Rise>
      <div style={{ display: "flex", gap: 16, marginTop: 46 }}>
        <Pill at={322}>No setup fee</Pill>
        <Pill at={346}>No annual contract</Pill>
        <Pill at={370}>No percentage of what you raise</Pill>
      </div>
      <Rise delay={467}>
        <div style={{ fontFamily: SERIF, fontSize: 40, color: BRAND.ink, marginTop: 34 }}>
          If the map is wrong, you&rsquo;ll know inside a month.
        </div>
      </Rise>
    </Center>
  </AbsoluteFill>
);

/**
 * 18 · The Ceiling — 760f. Lead 60. Measured: "the same map exists for Broward"
 * 154 · "the ceiling is not this room" 391 · "Anansi Atlas" 447 · "see the whole
 * web" 487 · "let's start with Orlando" 524. The card then holds ~4.5s in silence
 * before the fade — the room needs somewhere to land before the lights come up.
 */
const S18: React.FC = () => {
  const frame = useCurrentFrame();
  const chaptersOut = interpolate(frame, [352, 392], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const ceilingOut = interpolate(frame, [423, 463], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const logoIn = interpolate(frame, [447, 503], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const fadeOut = interpolate(frame, [710, 760], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ opacity: fadeOut }}>
      <NavyBG w={W} h={H} threads={0.45} />
      <GradientMesh opacity={0.32 * (1 - logoIn * 0.5)} />
      <NodeField w={W} h={H} count={13} opacity={0.16 * (1 - logoIn)} at={0} fadeIn={50} />

      {/* the three chapters — Orlando lit, the other two waiting */}
      <AbsoluteFill style={{ opacity: chaptersOut }}>
        <Center gap={30}>
          <Eyebrow delay={108}>The same map exists for</Eyebrow>
          <div style={{ display: "flex", gap: 18 }}>
            {CHAPTERS.map((c, i) => (
              <Pill key={c} at={154 + i * 26} active={c === "Orlando"}>
                {c}
              </Pill>
            ))}
          </div>
        </Center>
      </AbsoluteFill>

      {/* the line the film is named after */}
      <AbsoluteFill style={{ opacity: ceilingOut * (1 - chaptersOut) }}>
        <Center gap={0}>
          <Headline delay={391} size={96}>
            The ceiling isn&rsquo;t this room.
          </Headline>
        </Center>
      </AbsoluteFill>

      {/* the close */}
      <AbsoluteFill style={{ opacity: logoIn, alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 32 }}>
        {/* The emblem, not logo-mark.png — that PNG has no alpha and renders as a
            navy box against the film's navy. See AnansiVisionFilm.tsx:836. */}
        <Img src={staticFile("anansi-emblem-785.png")} style={{ width: 148, height: 148, objectFit: "contain" }} />
        <LogoLockup delay={447} />
        <Rise delay={487}>
          <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 46, color: BRAND.goldLight, textAlign: "center" }}>
            See the whole web.
          </div>
        </Rise>
        <div style={{ marginTop: 26, display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
          <Rise delay={524}>
            <Label size={20} color={BRAND.goldLight}>Let&rsquo;s start with Orlando</Label>
          </Rise>
          <Rise delay={554}>
            <div style={{ fontFamily: SERIF, fontWeight: 500, fontSize: 34, color: BRAND.white, letterSpacing: "0.02em", display: "flex", alignItems: "center", gap: 22 }}>
              <span>(321) 780&#8209;6335</span>
              <span style={{ color: BRAND.gold, opacity: 0.7, fontSize: 24 }}>&middot;</span>
              <span>anansiatlas.com</span>
            </div>
          </Rise>
          <div
            style={{
              width: 430,
              height: 1,
              background: BRAND.gold,
              opacity: 0.5,
              transformOrigin: "center",
              transform: `scaleX(${interpolate(frame, [578, 624], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })})`,
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
// ═════════════════════════════════════════════════════════════════════════════
const CAPTION_TEXT = [
  "This is Black Architects in the Making. The Orlando chapter. Founded in 2018, and run on volunteers every day since.",
  "300 students since you started. 135 this year alone. 14 workshops. 87 volunteers. $29,480 raised last year — every dollar from your own community.",
  "I built this from your website, your public tax filings, and the record you have already made in this county. Nothing you're about to see is a guess.",
  "You're doing the work. The opportunity exists. But finding who actually funds architecture pathways for students of color in Orange County means nights of searching — and you don't have a grant writer.",
  "So the opportunity stays exactly where it has always been. Not missing. Invisible.",
  "So we built the count. 310,000 IRS returns. 326,332 Florida grant records. 13,554 verified funders. Then we asked one question: who actually gives to an organization like yours, in your county?",
  "$56.0M flowed into Orange County nonprofits. 653 foundations. 2,622 grants, every one off a filing. That is the pool.",
  "$20.6M of that went to organizations your size. 229 foundations. 994 grants. That is your lane.",
  "And the typical grant to an organization your size is $5,000. It is the number that shows up, over and over, on the filings. That is your first check.",
  "Black History Project — $5,000. Love Our Youth — $5,000. Page 15 — $5,000. Lakemont Elementary PTO. Orlando Athletic Training Academy. Pop Warner. Real organizations. Your size. Your county.",
  "This is not a mockup. This is your workspace, already built. $20.6M in verified foundation grants, to 229 organizations like yours. That line is a query, and you can run it yourself.",
  "Your mission sits in the middle. Around it: funders, partners, government pathways, resources, readiness, and the pathways that connect them. Not a list you scroll — a landscape you see at once.",
  "Sorted the ordinary way, the top of the list is a million-dollar research grant to the University of Florida. Sort by organizations your size, and the same data returns $5,000 checks to Orlando nonprofits doing your kind of work.",
  "61 out of 100. Developing. Programs need clearer definition — your top gap. Missing documents in the vault — your highest-leverage fix. A tool that only flatters you isn't worth having.",
  "Three things this will not do. It won't call a $350M university an organization like you. It won't show a grant you can't verify against the filing. And it won't promise to get you funded.",
  "$150 a month. Founding rate, locked for life, as one of the first 20 partners. No setup fee. No annual contract. No percentage of anything you raise.",
  "What I built for Orlando isn't Orlando-specific. The same map exists for Broward. The same map exists for Miami. The ceiling isn't this room.",
];

const CAPTIONS: Caption[] = CAPTION_TEXT.map((text, i) => ({
  text,
  from: VO_AT[i],
  duration: LINE[i][1] - LINE[i][0],
}));

export const BamOrlandoFilm: React.FC<{
  audioSrc?: string | null;
  captions?: boolean;
  music?: boolean;
}> = ({ audioSrc = null, captions = false, music = true }) => {
  const scenes = [S01, S02, S03, S04, S05, S06, S07, S08, S09, S10, S11, S12, S13, S14, S15, S16, S17, S18];

  return (
    <AbsoluteFill style={{ background: BRAND.charcoal }}>
      {scenes.map((Scene, i) => (
        <Sequence key={i} from={B[i]} durationInFrames={B[i + 1] - B[i]}>
          <Scene />
        </Sequence>
      ))}

      {/*
       * INTERIM MUSIC — film-bed.mp3 is 80s and the film is 362s, so it is looped
       * with alternating start offsets so the seam is not identical each pass.
       * Same interim bed as the Vision Film; replace both together.
       */}
      {music
        ? [0, 1, 2, 3, 4].map((i) => (
            <Sequence key={`m${i}`} from={i * 2340} durationInFrames={2400}>
              <Audio
                src={staticFile("music/film-bed.mp3")}
                startFrom={i % 2 === 0 ? 0 : 12}
                volume={(f) =>
                  interpolate(f, [0, 60, 2340, 2400], [0, 0.34, 0.34, 0], {
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                  })
                }
              />
            </Sequence>
          ))
        : null}

      {/*
        VO — the master MP3 sliced per line. A single <Audio> across the whole
        composition would run the narration continuously and bulldoze every silent
        passage the film is built around.
      */}
      {audioSrc
        ? SLICE.map(({ from, to, padIn }, i) => {
            const dur = to - from;
            return (
              <Sequence key={`vo${i}`} from={VO_AT[i] - padIn} durationInFrames={dur}>
                <Audio
                  src={staticFile(audioSrc)}
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
  );
};
