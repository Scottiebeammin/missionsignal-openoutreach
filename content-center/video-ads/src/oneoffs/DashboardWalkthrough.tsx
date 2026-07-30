import React from "react";
import { AbsoluteFill, Audio, Img, Sequence, staticFile, useCurrentFrame, interpolate } from "remotion";
import { BRAND } from "../brand";
import {
  Caption,
  Eyebrow,
  Headline,
  LaptopScreenshotPanel,
  LogoLockup,
  NavyBG,
  ProgressRail,
  Rise,
  SANS,
  SceneDissolve,
  Subtitles,
} from "../components";
import { bySectionId } from "../data/dashboardWalkthroughSections";

export type Props = {
  audioSrc?: string | null;
};

/**
 * "Getting Started with Anansi Atlas" — the onboarding tutorial: sign-in -> profile creation ->
 * full dashboard tour. Instructional, not a sales piece: no pilot CTA/pricing, ends by pointing
 * the viewer back to Home. Real screenshots off the live app (redesigned IA, captured
 * 2026-07-03) including two frames of the app's own in-product guided tour overlay ("Step 1 of
 * 7" / "Step 2 of 7") for authenticity. Voice: Giselle (~76.7s VO).
 *
 * Timing derived from the measured VO duration (78.344127s @ 30fps = 2350.32f -> 2350f), split
 * across the 10 script lines proportional to word count (188 words total) — same method as
 * ProductWalkthrough. Re-derive this math if the script changes.
 */
const FPS = 30;
const LEAD = 60; // 2s silent cold-open before narration begins
const L = [0, 250, 500, 750, 1000, 1213, 1438, 1638, 1850, 2150, 2350].map((f) => f + LEAD);
export const WALK_TOTAL = L[10];

const CAPTIONS: Caption[] = [
  { text: "Welcome to Anansi Atlas. Sign in, and let's take a tour — from profile to dashboard.", from: L[0], duration: L[1] - L[0] },
  { text: "First, tell us about your organization. Atlas builds your profile from there.", from: L[1], duration: L[2] - L[1] },
  { text: "Home is your daily base: one clear next move, health scores, and upcoming deadlines.", from: L[2], duration: L[3] - L[2] },
  { text: "Snapshot is your executive brief: summary, Opportunity Web map, and a 30-day action plan.", from: L[3], duration: L[4] - L[3] },
  { text: "Ecosystem maps everything around your mission: funding, government, resources, and relationships.", from: L[4], duration: L[5] - L[4] },
  { text: "Opportunities is where you decide — top picks first, matches and discovery behind tabs.", from: L[5], duration: L[6] - L[5] },
  { text: "Pipeline is your lifecycle board — everything from discovered to awarded, deadlines flagged.", from: L[6], duration: L[7] - L[6] },
  { text: "Readiness shows what stands between you and a competitive application.", from: L[7], duration: L[8] - L[7] },
  { text: "And Organization is home for your profile, your wins, and your membership.", from: L[8], duration: L[9] - L[8] },
  { text: "That's the tour, start to finish. Come back anytime at anansiatlas.com.", from: L[9], duration: L[10] - L[9] },
];

const Center: React.FC<{ children: React.ReactNode; gap?: number }> = ({ children, gap = 22 }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap }}>
    {children}
  </AbsoluteFill>
);

const Section: React.FC<{ id: string; from: number; dur: number; label?: string }> = ({ id, from, dur, label }) => {
  const s = bySectionId(id);
  return (
    <Sequence from={from} durationInFrames={dur}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 16 }}>
        <Rise>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div style={{ width: 10, height: 10, borderRadius: 999, background: s.tone === "teal" ? BRAND.teal : BRAND.gold }} />
            <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 28, letterSpacing: "0.14em", textTransform: "uppercase", color: BRAND.goldLight }}>
              {label ?? s.label}
            </div>
          </div>
        </Rise>
        <LaptopScreenshotPanel src={staticFile(`screenshots/${s.shot}`)} label="anansiatlas.com" durationInFrames={dur} width={680} panY={[0, -14]} />
      </AbsoluteFill>
    </Sequence>
  );
};

// NOTE: was OffthreadVideo(staticFile("broll/globe-loop.mp4")) — that asset turned out to be a
// captured clip from a different composition with its captions burned into the pixels (visible
// as a faint ghost line during the cold open). Replaced with a clean pulsing glow; no video
// dependency, no contamination risk.
const GlobeOpen: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, LEAD], [0.5, 0.22], { extrapolateRight: "clamp" });
  const breathe = 0.85 + 0.15 * Math.sin(frame / 40);
  return (
    <AbsoluteFill style={{ opacity }}>
      <AbsoluteFill
        style={{
          opacity: breathe,
          background:
            "radial-gradient(60% 55% at 50% 40%, rgba(212,160,23,0.28) 0%, rgba(212,160,23,0) 55%), radial-gradient(50% 45% at 50% 40%, rgba(58,108,200,0.2) 0%, rgba(58,108,200,0) 60%)",
        }}
      />
    </AbsoluteFill>
  );
};

export const DashboardWalkthrough: React.FC<Props> = ({ audioSrc }) => {
  return (
    <NavyBG>
      {audioSrc ? (
        <Sequence from={LEAD}>
          <Audio src={staticFile(audioSrc)} />
        </Sequence>
      ) : null}
      <ProgressRail totalFrames={WALK_TOTAL} />

      {/* COLD OPEN — brief brand moment over the globe loop, then straight into Sign In. */}
      <Sequence from={0} durationInFrames={L[1]}>
        <GlobeOpen />
      </Sequence>

      {/* L0 — SIGN IN */}
      <Sequence from={L[0]} durationInFrames={L[1] - L[0]}>
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 14 }}>
          <Rise delay={0}>
            <Img src={staticFile("logo-mark.png")} style={{ width: 84, height: 84 }} />
          </Rise>
          <Eyebrow delay={4}>Getting Started</Eyebrow>
          <Headline delay={10} size={50}>Welcome to Anansi Atlas.</Headline>
          <LaptopScreenshotPanel src={staticFile("screenshots/shot-signin.png")} label="anansiatlas.com/accounts/login" durationInFrames={L[1] - L[0]} width={520} panY={[0, -8]} delay={16} />
        </AbsoluteFill>
      </Sequence>

      {/* L1 — CREATING YOUR PROFILE */}
      <Section id="intake" from={L[1]} dur={L[2] - L[1]} label="Creating Your Profile" />

      {/* L2 — HOME (tour card, then the clean dashboard) */}
      <Section id="tour1" from={L[2]} dur={(L[3] - L[2]) * 0.4} label="Guided Tour — Step 1 of 7" />
      <Section id="dashboard" from={L[2] + (L[3] - L[2]) * 0.4} dur={(L[3] - L[2]) * 0.6} label="Home" />

      {/* L3 — SNAPSHOT (tour card, then the clean snapshot) */}
      <Section id="tour2" from={L[3]} dur={(L[4] - L[3]) * 0.4} label="Guided Tour — Step 2 of 7" />
      <Section id="snapshot" from={L[3] + (L[4] - L[3]) * 0.4} dur={(L[4] - L[3]) * 0.6} label="Snapshot" />

      {/* L4 — ECOSYSTEM */}
      <Section id="ecosystem" from={L[4]} dur={L[5] - L[4]} />

      {/* L5 — OPPORTUNITIES */}
      <Section id="opportunities" from={L[5]} dur={L[6] - L[5]} />

      {/* L6 — PIPELINE */}
      <Section id="pipeline" from={L[6]} dur={L[7] - L[6]} />

      {/* L7 — READINESS */}
      <Section id="readiness" from={L[7]} dur={L[8] - L[7]} />

      {/* L8 — ORGANIZATION */}
      <Section id="organization" from={L[8]} dur={L[9] - L[8]} />

      {/* L9 — CLOSING: logo + web address, no CTA/pricing (this is a tutorial, not a sales piece). */}
      <Sequence from={L[9]} durationInFrames={WALK_TOTAL - L[9]}>
        <Center gap={20}>
          <Rise delay={4}>
            <Img src={staticFile("logo-mark.png")} style={{ width: 100, height: 100 }} />
          </Rise>
          <LogoLockup delay={12} />
          <Rise delay={32}>
            <div style={{ fontFamily: SANS, fontSize: 30, fontWeight: 700, color: BRAND.goldLight, letterSpacing: "0.04em" }}>
              anansiatlas.com
            </div>
          </Rise>
        </Center>
      </Sequence>

      <SceneDissolve
        boundaries={[
          L[1],
          L[2] + (L[3] - L[2]) * 0.4, L[3],
          L[3] + (L[4] - L[3]) * 0.4, L[4],
          L[5], L[6], L[7], L[8], L[9],
        ]}
      />
      <Subtitles captions={CAPTIONS} />
    </NavyBG>
  );
};
