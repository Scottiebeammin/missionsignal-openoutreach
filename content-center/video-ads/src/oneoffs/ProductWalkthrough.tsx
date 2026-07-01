import React from "react";
import { AbsoluteFill, Audio, interpolate, Sequence, staticFile, useCurrentFrame } from "remotion";
import { BRAND, SIGNUP_URL } from "../brand";
import {
  Caption,
  CTAButton,
  Eyebrow,
  Headline,
  LogoLockup,
  NavyBG,
  OrbWeb,
  ProgressRail,
  Rise,
  SANS,
  SceneDissolve,
  ScreenshotPanel,
  Subtitles,
} from "../components";
import { WALK_SECTIONS } from "../data/walkthroughSections";

export type Props = { audioSrc?: string | null };

/**
 * "From Scattered Opportunity to Focused Action" — the premium product walkthrough
 * (~110s). ONE-OFF flagship (see ads.config.mjs entry). Real product screenshots,
 * data-driven section reel (src/data/walkthroughSections.ts), dip-to-navy dissolves,
 * baked-in subtitles. Voice: Christopher.
 */
const FPS = 30;
const SEC_DUR = 180; // 6s per Act-3 section
const ACT3_START = 1050;
const ACT4_START = ACT3_START + WALK_SECTIONS.length * SEC_DUR; // 2850
const ACT5_START = ACT4_START + 210; // 3060
export const WALK_TOTAL = ACT5_START + 240; // 3300 = 110s

const Center: React.FC<{ children: React.ReactNode; gap?: number }> = ({ children, gap = 22 }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap }}>
    {children}
  </AbsoluteFill>
);

// ── Captions (derived from the section data so VO + subtitles + visuals stay in sync) ──
const CAPTIONS: Caption[] = [
  { text: "Nonprofits are surrounded by opportunity.", from: 0, duration: 210 },
  { text: "But too often, that opportunity is scattered.", from: 210, duration: 240 },
  { text: "Anansi Atlas maps the web of opportunity around your mission.", from: 450, duration: 300 },
  { text: "Apply for the Founding Atlas Partners Pilot, tell us about your mission…", from: 750, duration: 300 },
  ...WALK_SECTIONS.map((s, i) => ({ text: s.vo, from: ACT3_START + i * SEC_DUR + 8, duration: SEC_DUR - 10 })),
  { text: "Instead of chasing scattered leads, you see exactly where to focus next.", from: ACT4_START, duration: 210 },
  { text: "We're selecting 19–20 nonprofit organizations for the pilot.", from: ACT5_START, duration: 130 },
  { text: "Apply at anansiatlas.com/anansi-atlas", from: ACT5_START + 130, duration: 110 },
];

// Scattered-signal field for Act 1.
const SCATTER = ["funder portals", "spreadsheets", "grant deadlines", "partner lists", "emails", "program needs", "notes", "RFPs"];
const ScatterField: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill>
      {SCATTER.map((w, i) => {
        const x = [130, 640, 300, 780, 200, 690, 120, 560][i];
        const y = [210, 170, 760, 700, 470, 450, 640, 850][i];
        const drift = Math.sin((frame + i * 40) / 42) * 9;
        const op = interpolate(frame, [10 + i * 6, 34 + i * 6], [0, 0.8], { extrapolateRight: "clamp" });
        return (
          <div key={w} style={{ position: "absolute", left: x, top: y + drift, fontFamily: SANS, fontSize: 32, fontWeight: 700, color: BRAND.muted, opacity: op }}>
            {w}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

const Transform: React.FC = () => {
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [0, 140], [0, 1], { extrapolateRight: "clamp" });
  return <OrbWeb progress={progress} />;
};

export const ProductWalkthrough: React.FC<Props> = ({ audioSrc }) => {
  return (
    <NavyBG>
      {audioSrc ? <Audio src={staticFile(audioSrc)} /> : null}
      <ProgressRail totalFrames={WALK_TOTAL} />

      {/* ACT 1 — THE PROBLEM */}
      <Sequence from={0} durationInFrames={210}>
        <ScatterField />
        <Center>
          <Headline delay={10} size={64}>Nonprofits are surrounded by opportunity.</Headline>
        </Center>
      </Sequence>
      <Sequence from={210} durationInFrames={240}>
        <ScatterField />
        <Center>
          <Headline delay={6} size={70} color={BRAND.goldLight}>But it's scattered.</Headline>
        </Center>
      </Sequence>

      {/* ACT 2 — THE REVEAL (landing → apply → intake) */}
      <Sequence from={450} durationInFrames={300}>
        <Center gap={20}>
          <Eyebrow>anansiatlas.com</Eyebrow>
          <ScreenshotPanel src={staticFile("screenshots/landing.png")} label="anansiatlas.com/anansi-atlas" durationInFrames={300} width={880} panY={[0, -24]} />
        </Center>
      </Sequence>
      <Sequence from={750} durationInFrames={300}>
        <Center gap={20}>
          <Eyebrow>Start with your mission</Eyebrow>
          <ScreenshotPanel src={staticFile("screenshots/organization.png")} label="anansiatlas.com/organization" durationInFrames={300} width={880} panY={[0, -18]} />
        </Center>
      </Sequence>

      {/* ACT 3 — THE DASHBOARD WALKTHROUGH (data-driven) */}
      {WALK_SECTIONS.map((s, i) => (
        <Sequence key={s.id} from={ACT3_START + i * SEC_DUR} durationInFrames={SEC_DUR}>
          <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 18 }}>
            <Rise>
              <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                <div style={{ width: 10, height: 10, borderRadius: 999, background: s.tone === "teal" ? BRAND.teal : BRAND.gold }} />
                <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 30, letterSpacing: "0.14em", textTransform: "uppercase", color: BRAND.goldLight }}>
                  {s.label}
                </div>
              </div>
            </Rise>
            <ScreenshotPanel src={staticFile(`screenshots/${s.shot}`)} label={`anansiatlas.com`} durationInFrames={SEC_DUR} width={800} panY={[0, -16]} />
            <Rise delay={10}>
              <div style={{ fontFamily: SANS, fontSize: 28, fontWeight: 600, color: BRAND.white, textAlign: "center", maxWidth: 820 }}>
                {s.value}
              </div>
            </Rise>
          </AbsoluteFill>
        </Sequence>
      ))}

      {/* ACT 4 — TRANSFORMATION */}
      <Sequence from={ACT4_START} durationInFrames={210}>
        <Transform />
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: 60 }}>
          <Rise delay={150}>
            <div style={{ fontFamily: SANS, fontSize: 30, fontWeight: 700, color: BRAND.goldLight }}>
              Scattered opportunity → focused action.
            </div>
          </Rise>
        </AbsoluteFill>
      </Sequence>

      {/* ACT 5 — PILOT CTA */}
      <Sequence from={ACT5_START} durationInFrames={WALK_TOTAL - ACT5_START}>
        <Center gap={26}>
          <Eyebrow>Founding Atlas Partners Pilot</Eyebrow>
          <Headline delay={8} size={56}>We're selecting 19–20 organizations.</Headline>
          <div style={{ height: 6 }} />
          <LogoLockup delay={22} />
          <CTAButton delay={34}>Apply for the Pilot</CTAButton>
          <Rise delay={44}>
            <div style={{ fontFamily: SANS, fontSize: 30, fontWeight: 700, color: BRAND.goldLight, letterSpacing: "0.04em" }}>
              {SIGNUP_URL}
            </div>
          </Rise>
        </Center>
      </Sequence>

      <SceneDissolve
        boundaries={[
          210, 450, 750, // acts 1–2
          ...WALK_SECTIONS.map((_, i) => ACT3_START + i * SEC_DUR), // each section
          ACT4_START, ACT5_START,
        ]}
      />
      <Subtitles captions={CAPTIONS} />
    </NavyBG>
  );
};
