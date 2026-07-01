import React from "react";
import { AbsoluteFill, Audio, interpolate, Sequence, staticFile, useCurrentFrame } from "remotion";
import { BRAND, SIGNUP_URL } from "../brand";
import {
  AnimatedLogoReveal,
  BubbleCard,
  Caption,
  CheckLine,
  CTAButton,
  Eyebrow,
  FeatureCard,
  Headline,
  LogoLockup,
  NavyBG,
  OrbWeb,
  ProgressRail,
  Rise,
  SANS,
  SceneDissolve,
  ScreenshotPanel,
  SectionMarker,
  Subtitles,
} from "../components";

export type Props = { audioSrc?: string | null };

// ONE-OFF — not part of the automated ads pipeline (see ads.config.mjs). The 5-minute deep
// walkthrough: what it is, how it works end-to-end, why it's transformative, "Register Now."
// Voice: Christopher. Total: 9150 frames @ 30fps = 305s (~5:05).
const TOTAL_FRAMES = 9150;

// Section start frames (see README for the matching VO script + word-budget per section).
const S = {
  HOOK: 0, // 0-10s
  PROBLEM: 300, // 10-40s
  INTRO: 1200, // 40-65s
  DASHBOARD: 1950, // 65-105s
  WEB: 3150, // 105-145s
  SNAPSHOT: 4350, // 145-205s
  PIPELINE: 6150, // 205-245s
  VISION: 7350, // 245-275s
  CTA: 8250, // 275-305s
};

const CAPTIONS: Caption[] = [
  { text: "What if the funders, partners, and public dollars already aligned with your mission weren't hiding —", from: S.HOOK, duration: 150 },
  { text: "they were just never mapped?", from: S.HOOK + 150, duration: 150 },
  { text: "Most nonprofit teams do this work in forty browser tabs.", from: S.PROBLEM, duration: 180 },
  { text: "A funder database here. An email thread there. A spreadsheet only one person understands.", from: S.PROBLEM + 180, duration: 240 },
  { text: "It's not a lack of effort. It's a lack of a system.", from: S.PROBLEM + 420, duration: 240 },
  { text: "This is Anansi Atlas — a nonprofit opportunity intelligence platform.", from: S.INTRO, duration: 240 },
  { text: "We call it the Web of Opportunity — every mission sits at the center of one.", from: S.INTRO + 240, duration: 300 },
  { text: "Your Dashboard is home base.", from: S.DASHBOARD, duration: 150 },
  { text: "It opens with a single card: What To Do Next.", from: S.DASHBOARD + 150, duration: 210 },
  { text: "Health scores, upcoming deadlines, and your active pipeline — all at a glance.", from: S.DASHBOARD + 360, duration: 300 },
  { text: "A busy ED opens this for 60 seconds and knows exactly where to spend the day.", from: S.DASHBOARD + 660, duration: 300 },
  { text: "The Opportunity Web puts your mission at the center — literally.", from: S.WEB, duration: 240 },
  { text: "Six nodes orbit it: Funders, Partners, Government, Resources, Readiness, Pathways.", from: S.WEB + 240, duration: 300 },
  { text: "This is the actual shape of your opportunity landscape — mapped, not scattered.", from: S.WEB + 540, duration: 300 },
  { text: "Nothing here is guesswork. It's built from real research on your mission.", from: S.WEB + 840, duration: 300 },
  { text: "Your Opportunity Web Snapshot is the executive brief.", from: S.SNAPSHOT, duration: 210 },
  { text: "It opens with a plain-language summary and a 30-day action plan, ranked for your mission.", from: S.SNAPSHOT + 210, duration: 330 },
  { text: "Below that: top funder pathways, partner pathways, ranked by fit.", from: S.SNAPSHOT + 540, duration: 270 },
  { text: "Readiness — scored honestly. Teal where you're strong, gold where there's a gap.", from: S.SNAPSHOT + 810, duration: 300 },
  { text: "Risks & Gaps, so you see what could slow you down before it costs you a quarter.", from: S.SNAPSHOT + 1110, duration: 330 },
  { text: "A list tells you what exists. A Snapshot tells you what to do next — in order.", from: S.SNAPSHOT + 1440, duration: 360 },
  { text: "When it's worth pursuing, it moves into your Pipeline — spotted to submitted to won.", from: S.PIPELINE, duration: 300 },
  { text: "Partners & Sponsorship maps every aligned funder and partner, with a fit rationale.", from: S.PIPELINE + 300, duration: 300 },
  { text: "Resources surfaces capacity-building, technology, and volunteer support.", from: S.PIPELINE + 600, duration: 240 },
  { text: "Every piece points at the same goal: focused action, not more research.", from: S.PIPELINE + 840, duration: 360 },
  { text: "Mission-driven work shouldn't lose to logistics.", from: S.VISION, duration: 210 },
  { text: "The opportunity was never the problem. Seeing it clearly was.", from: S.VISION + 210, duration: 270 },
  { text: "That's what this platform gives you back — time, clarity, and a system that keeps working.", from: S.VISION + 480, duration: 360 },
  { text: "We're opening the Founding Atlas Partners Pilot to 20 organizations.", from: S.CTA, duration: 240 },
  { text: "A rate locked in for life. A Snapshot built around your mission. A personal walkthrough.", from: S.CTA + 240, duration: 330 },
  { text: "Register now at anansiatlas.com/anansi-atlas", from: S.CTA + 570, duration: 330 },
];

const Center: React.FC<{ children: React.ReactNode; gap?: number }> = ({ children, gap = 26 }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap }}>
    {children}
  </AbsoluteFill>
);

const Web: React.FC = () => {
  // useCurrentFrame() is already local to the enclosing <Sequence> — no extra offset needed.
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [0, 150], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return <OrbWeb progress={progress} />;
};

export const FullExplainer: React.FC<Props> = ({ audioSrc }) => {
  return (
    <NavyBG>
      {audioSrc ? <Audio src={staticFile(audioSrc)} /> : null}
      <ProgressRail totalFrames={TOTAL_FRAMES} />

      {/* 00 — HOOK */}
      <Sequence from={S.HOOK} durationInFrames={S.PROBLEM - S.HOOK}>
        <Center>
          <Eyebrow>The Web of Opportunity</Eyebrow>
          <Headline delay={8} size={70}>
            The funders, partners, and public dollars aligned with your mission aren't hiding.
          </Headline>
          <Rise delay={80}>
            <div style={{ fontFamily: SANS, fontSize: 32, fontWeight: 700, color: BRAND.goldLight }}>
              They were just never mapped.
            </div>
          </Rise>
        </Center>
      </Sequence>

      {/* 01 — PROBLEM */}
      <Sequence from={S.PROBLEM} durationInFrames={S.INTRO - S.PROBLEM}>
        <Center gap={20}>
          <SectionMarker index="01" total="08" title="The Problem" />
          <Headline delay={10} size={58}>Most teams do this in 40 browser tabs.</Headline>
          <Rise delay={40}>
            <div style={{ fontFamily: SANS, fontSize: 28, fontWeight: 600, color: BRAND.muted, textAlign: "center", maxWidth: 800 }}>
              A funder database here. An email thread there. A spreadsheet only one person understands.
            </div>
          </Rise>
          <Rise delay={70}>
            <div style={{ fontFamily: SANS, fontSize: 30, fontWeight: 800, color: BRAND.goldLight, textAlign: "center" }}>
              It's not a lack of effort — it's a lack of a system.
            </div>
          </Rise>
        </Center>
      </Sequence>

      {/* 02 — INTRO */}
      <Sequence from={S.INTRO} durationInFrames={S.DASHBOARD - S.INTRO}>
        <AnimatedLogoReveal delay={6} />
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: 90 }}>
          <Rise delay={60}>
            <div style={{ fontFamily: SANS, fontSize: 30, fontWeight: 700, color: BRAND.white, textAlign: "center", maxWidth: 820 }}>
              A nonprofit opportunity intelligence platform. Every mission sits at the center of a web.
            </div>
          </Rise>
        </AbsoluteFill>
      </Sequence>

      {/* 03 — DASHBOARD (real product screenshot) */}
      <Sequence from={S.DASHBOARD} durationInFrames={S.WEB - S.DASHBOARD}>
        <Center gap={20}>
          <SectionMarker index="02" total="08" title="Dashboard" />
          <Eyebrow>anansiatlas.com/dashboard</Eyebrow>
          <ScreenshotPanel
            src={staticFile("screenshots/dashboard.png")}
            label="anansiatlas.com/dashboard"
            durationInFrames={S.WEB - S.DASHBOARD}
            width={860}
            panY={[0, -20]}
          />
        </Center>
      </Sequence>

      {/* 04 — OPPORTUNITY WEB (real product screenshot + the live orb-web motif) */}
      <Sequence from={S.WEB} durationInFrames={600}>
        <Center gap={20}>
          <SectionMarker index="03" total="08" title="Opportunity Web" />
          <Eyebrow>anansiatlas.com/web</Eyebrow>
          <ScreenshotPanel
            src={staticFile("screenshots/web.png")}
            label="anansiatlas.com/web"
            durationInFrames={600}
            width={860}
            panX={[0, -20]}
          />
        </Center>
      </Sequence>
      <Sequence from={S.WEB + 600} durationInFrames={S.SNAPSHOT - S.WEB - 600}>
        <SectionMarker index="03" total="08" title="Opportunity Web" />
        <Web />
      </Sequence>

      {/* 05 — SNAPSHOT (longest section; real product screenshot first) */}
      <Sequence from={S.SNAPSHOT} durationInFrames={540}>
        <Center gap={18}>
          <SectionMarker index="04" total="08" title="The Snapshot" />
          <Eyebrow>anansiatlas.com/snapshot</Eyebrow>
          <ScreenshotPanel
            src={staticFile("screenshots/snapshot.png")}
            label="anansiatlas.com/snapshot"
            durationInFrames={540}
            width={820}
            panY={[0, -18]}
          />
        </Center>
      </Sequence>
      <Sequence from={S.SNAPSHOT + 540} durationInFrames={630}>
        <Center gap={18}>
          <SectionMarker index="04" total="08" title="The Snapshot" />
          <FeatureCard delay={4} glyph="🏛️" title="Funder & Partner Pathways" benefit="Top matches, ranked by fit — not alphabetical." />
          <FeatureCard delay={20} glyph="📈" title="Readiness, Scored Honestly" benefit="Teal where you're strong. Gold where there's a gap." />
        </Center>
      </Sequence>
      <Sequence from={S.SNAPSHOT + 1170} durationInFrames={630}>
        <Center gap={20}>
          <SectionMarker index="04" total="08" title="The Snapshot" />
          <BubbleCard delay={6} tone="gold" label="Risks & Gaps" value="What could slow you down — before it costs you a quarter." />
          <Rise delay={40}>
            <div style={{ fontFamily: SANS, fontSize: 32, fontWeight: 700, color: BRAND.goldLight, textAlign: "center", marginTop: 10 }}>
              Information vs. direction.
            </div>
          </Rise>
        </Center>
      </Sequence>

      {/* 06 — PIPELINE + PARTNERS + RESOURCES */}
      <Sequence from={S.PIPELINE} durationInFrames={S.VISION - S.PIPELINE}>
        <Center gap={18}>
          <SectionMarker index="05" total="08" title="Pipeline & Beyond" />
          <FeatureCard delay={6} glyph="📌" title="Pipeline" benefit="Every opportunity — spotted to submitted to won." />
          <FeatureCard delay={22} glyph="🤝" title="Partners & Sponsorship" benefit="Aligned funders and partners, with a fit rationale." />
          <FeatureCard delay={38} glyph="🧰" title="Resources" benefit="Capacity-building, technology, and volunteer support." />
        </Center>
      </Sequence>

      {/* 07 — VISION */}
      <Sequence from={S.VISION} durationInFrames={S.CTA - S.VISION}>
        <Center gap={24}>
          <SectionMarker index="06" total="08" title="Why It Matters" />
          <Headline delay={10} size={58}>Mission-driven work shouldn't lose to logistics.</Headline>
          <Rise delay={70}>
            <div style={{ fontFamily: SANS, fontSize: 30, fontWeight: 600, color: BRAND.white, textAlign: "center", maxWidth: 780 }}>
              The opportunity was never the problem. Seeing it clearly was.
            </div>
          </Rise>
        </Center>
      </Sequence>

      {/* 08 — CTA: REGISTER NOW */}
      <Sequence from={S.CTA} durationInFrames={TOTAL_FRAMES - S.CTA}>
        <Center gap={26}>
          <SectionMarker index="07" total="08" title="Founding Atlas Partners" />
          <Eyebrow>20 Seats · $150/mo Locked for Life</Eyebrow>
          <CheckLine delay={16} text="A Snapshot built around your actual mission" />
          <CheckLine delay={30} text="A personal 45-minute walkthrough with our team" />
          <CheckLine delay={44} text="Full platform access from day one" />
          <div style={{ height: 10 }} />
          <LogoLockup delay={60} />
          <CTAButton delay={76}>Register Now</CTAButton>
          <Rise delay={90}>
            <div style={{ fontFamily: SANS, fontSize: 30, fontWeight: 700, color: BRAND.goldLight, letterSpacing: "0.04em" }}>
              {SIGNUP_URL}
            </div>
          </Rise>
        </Center>
      </Sequence>

      <SceneDissolve boundaries={[300, 1200, 1950, 3150, 3750, 4350, 4890, 5520, 6150, 7350, 8250]} />
      <Subtitles captions={CAPTIONS} />
    </NavyBG>
  );
};
