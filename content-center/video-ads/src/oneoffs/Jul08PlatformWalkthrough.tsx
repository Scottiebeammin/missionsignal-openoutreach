import React from "react";
import { AbsoluteFill, Audio, Img, Sequence, staticFile, useCurrentFrame, interpolate } from "remotion";
import { BRAND, SIGNUP_URL } from "../brand";
import {
  Caption,
  CTAButton,
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

export type Props = {
  audioSrc?: string | null;
};

/**
 * JULY CONTENT CALENDAR — Wed Jul 8 hero "Platform Walkthrough" (content-center/07-content-
 * calendar-july-2026.md). "Let me show you the actual product — not a mockup." Dashboard ->
 * Opportunity Web -> Snapshot, real screenshots on the new laptop-mockup treatment, closes on
 * the founding-seat CTA. Voice: Giselle.
 *
 * Timing derived from the measured VO duration (48.204626s @ 30fps = 1446.14f -> 1446f), split
 * across the 6 script lines proportional to word count (119 words total). A 300f (10s) hold is
 * added after the VO ends so the CTA card lingers — total run time ~60.2s, inside the calendar's
 * "~60-90s" target. Re-derive this math if the script changes.
 */
const FPS = 30;
const LEAD = 60; // 2s silent cold-open before narration begins
const CTA_HOLD = 300; // extra 10s hold on the closing CTA after the VO ends
const L = [0, 194, 523, 838, 1057, 1239, 1446].map((f) => f + LEAD);
export const WALK_TOTAL = L[6] + CTA_HOLD;

const CAPTIONS: Caption[] = [
  { text: "Let me show you the actual product. Not a mockup — the thing you'd use every day.", from: L[0], duration: L[1] - L[0] },
  { text: "This is Anansi Atlas. Your Dashboard opens with one card: What To Do Next, plus your health scores at a glance.", from: L[1], duration: L[2] - L[1] },
  { text: "The Opportunity Web puts your mission at the center — funders, partners, government, resources, readiness, and pathways orbiting it.", from: L[2], duration: L[3] - L[2] },
  { text: "And your Snapshot leads with a 30-day action plan, ranked for your mission — not a wall of grants.", from: L[3], duration: L[4] - L[3] },
  { text: "No pitch deck. This is the working software founding partners log into on day one.", from: L[4], duration: L[5] - L[4] },
  { text: "Want the full walkthrough with your own data? It comes with your founding seat.", from: L[5], duration: L[6] - L[5] },
];

const Center: React.FC<{ children: React.ReactNode; gap?: number }> = ({ children, gap = 22 }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap }}>
    {children}
  </AbsoluteFill>
);

const ScreenSection: React.FC<{ shot: string; label: string; from: number; dur: number }> = ({ shot, label, from, dur }) => (
  <Sequence from={from} durationInFrames={dur}>
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 18 }}>
      <Rise>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{ width: 10, height: 10, borderRadius: 999, background: BRAND.gold }} />
          <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 28, letterSpacing: "0.14em", textTransform: "uppercase", color: BRAND.goldLight }}>
            {label}
          </div>
        </div>
      </Rise>
      <LaptopScreenshotPanel src={staticFile(`screenshots/${shot}`)} label="anansiatlas.com" durationInFrames={dur} width={760} panY={[0, -16]} />
    </AbsoluteFill>
  </Sequence>
);

// NOTE: was OffthreadVideo(staticFile("broll/globe-loop.mp4")) — that asset turned out to be a
// captured clip from a different composition with its captions burned into the pixels (visible
// as a faint ghost line during the cold open). Replaced with a clean pulsing glow; no video
// dependency, no contamination risk.
const GlobeOpen: React.FC<{ durationInFrames: number }> = ({ durationInFrames }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, durationInFrames], [0.5, 0.15], { extrapolateRight: "clamp" });
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

export const Jul08PlatformWalkthrough: React.FC<Props> = ({ audioSrc }) => {
  return (
    <NavyBG>
      {audioSrc ? (
        <Sequence from={LEAD}>
          <Audio src={staticFile(audioSrc)} />
        </Sequence>
      ) : null}
      <ProgressRail totalFrames={WALK_TOTAL} />

      {/* HOOK — "Not a mockup." over the globe loop, logo-mark leads the open. */}
      <Sequence from={0} durationInFrames={L[1]}>
        <GlobeOpen durationInFrames={L[1]} />
      </Sequence>
      <Sequence from={L[0]} durationInFrames={L[1] - L[0]}>
        <Center gap={16}>
          <Rise delay={0}>
            <Img src={staticFile("logo-mark.png")} style={{ width: 76, height: 76 }} />
          </Rise>
          <Eyebrow delay={4}>The Real Platform</Eyebrow>
          <Headline delay={10} size={54}>Not a mockup.</Headline>
        </Center>
      </Sequence>

      {/* DASHBOARD */}
      <ScreenSection shot="shot-dashboard3.png" label="Dashboard — What To Do Next" from={L[1]} dur={L[2] - L[1]} />

      {/* OPPORTUNITY WEB */}
      <ScreenSection shot="shot-web-clean.png" label="Opportunity Web" from={L[2]} dur={L[3] - L[2]} />

      {/* SNAPSHOT */}
      <ScreenSection shot="shot-snapshot3.png" label="Snapshot — 30-Day Action Plan" from={L[3]} dur={L[4] - L[3]} />

      {/* "No pitch deck" beat — text only */}
      <Sequence from={L[4]} durationInFrames={L[5] - L[4]}>
        <Center gap={18}>
          <Headline delay={6} size={50}>No pitch deck.</Headline>
          <Rise delay={26}>
            <div style={{ fontFamily: SANS, fontSize: 28, fontWeight: 700, color: BRAND.goldLight, textAlign: "center", maxWidth: 700 }}>
              This is what founding partners log into on day one.
            </div>
          </Rise>
        </Center>
      </Sequence>

      {/* CTA CLOSE */}
      <Sequence from={L[5]} durationInFrames={WALK_TOTAL - L[5]}>
        <Center gap={20}>
          <Rise delay={4}>
            <Img src={staticFile("logo-mark.png")} style={{ width: 92, height: 92 }} />
          </Rise>
          <LogoLockup delay={10} />
          <Rise delay={24}>
            <div style={{ fontFamily: SANS, fontSize: 26, fontWeight: 700, color: BRAND.white, textAlign: "center", maxWidth: 720 }}>
              Want the full walkthrough with your own data?
            </div>
          </Rise>
          <CTAButton delay={34}>Apply for the Founding Pilot</CTAButton>
          <Rise delay={44}>
            <div style={{ fontFamily: SANS, fontSize: 26, fontWeight: 700, color: BRAND.goldLight, letterSpacing: "0.04em" }}>
              {SIGNUP_URL}
            </div>
          </Rise>
        </Center>
      </Sequence>

      <SceneDissolve boundaries={[L[1], L[2], L[3], L[4], L[5]]} />
      <Subtitles captions={CAPTIONS} />
    </NavyBG>
  );
};
