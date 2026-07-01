import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile } from "remotion";
import { BRAND, SIGNUP_URL } from "../brand";
import {
  AnimatedLogoReveal,
  Caption,
  CheckLine,
  CTAButton,
  Eyebrow,
  Headline,
  LogoLockup,
  NavyBG,
  Rise,
  SANS,
  SceneDissolve,
  ScreenshotPanel,
  Subtitles,
} from "../components";

export type Props = { audioSrc?: string | null };

// ONE-OFF — not part of the automated ads pipeline (see ads.config.mjs). Premium brand
// commercial built from REAL product screenshots (public/screenshots/*.png, captured live
// off the Creative Display demo profile — anonymized, ad-safe). Voice: Christopher.
// Timing below is derived from the actual VO's word count per line (~34.4s total) —
// re-run the proportional-split math in scripts if the script in ads.config.mjs changes.
const L = [0, 76, 176, 227, 327, 440, 541, 805, 919, 1032];

const CAPTIONS: Caption[] = [
  { text: "Every mission is surrounded by opportunity.", from: L[0], duration: L[1] - L[0] },
  { text: "The problem was never opportunity. It was visibility.", from: L[1], duration: L[2] - L[1] },
  { text: "This is Anansi Atlas.", from: L[2], duration: L[3] - L[2] },
  { text: "Your Dashboard opens with one clear next move.", from: L[3], duration: L[4] - L[3] },
  { text: "Your Opportunity Web maps your mission at the center.", from: L[4], duration: L[5] - L[4] },
  { text: "Your Snapshot opens with a 30-day action plan.", from: L[5], duration: L[6] - L[5] },
  { text: "Founding Atlas Partners aren't just customers — they're the first 20 shaping this platform, locked in for life.", from: L[6], duration: L[7] - L[6] },
  { text: "If you're ready to stop guessing, join the family.", from: L[7], duration: L[8] - L[7] },
  { text: "Apply at anansiatlas.com/anansi-atlas", from: L[8], duration: L[9] - L[8] },
];

const Center: React.FC<{ children: React.ReactNode; gap?: number }> = ({ children, gap = 26 }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap }}>
    {children}
  </AbsoluteFill>
);

const SCREENS = [
  { from: L[3], src: "screenshots/dashboard.png", label: "anansiatlas.com/dashboard", title: "One Clear Next Move", panX: [0, 20] as [number, number] },
  { from: L[4], src: "screenshots/web.png", label: "anansiatlas.com/web", title: "Your Mission at the Center", panX: [0, -20] as [number, number] },
  { from: L[5], src: "screenshots/snapshot.png", label: "anansiatlas.com/snapshot", title: "A 30-Day Action Plan", panX: [0, 20] as [number, number] },
];

export const PremiumShowcase: React.FC<Props> = ({ audioSrc }) => {
  return (
    <NavyBG>
      {audioSrc ? <Audio src={staticFile(audioSrc)} /> : null}

      {/* S1 — hook */}
      <Sequence from={L[0]} durationInFrames={L[1] - L[0]}>
        <Center>
          <Headline delay={6} size={56}>Every mission is surrounded by opportunity.</Headline>
        </Center>
      </Sequence>

      {/* S2 — problem */}
      <Sequence from={L[1]} durationInFrames={L[2] - L[1]}>
        <Center gap={14}>
          <Rise>
            <div style={{ fontFamily: SANS, fontSize: 22, fontWeight: 800, color: BRAND.muted, letterSpacing: "0.1em", textTransform: "uppercase" }}>
              The problem was never opportunity.
            </div>
          </Rise>
          <Headline delay={10} color={BRAND.goldLight} size={60}>It was visibility.</Headline>
        </Center>
      </Sequence>

      {/* S3 — motion-graphics brand reveal (converging threads + shimmer, not a static fade) */}
      <Sequence from={L[2]} durationInFrames={L[3] - L[2]}>
        <AnimatedLogoReveal delay={2} />
      </Sequence>

      {/* S4 — real product reel: Dashboard, Opportunity Web, Snapshot */}
      {SCREENS.map((s, i) => (
        <Sequence key={s.src} from={s.from} durationInFrames={L[4 + i] - s.from}>
          <Center gap={16}>
            <Eyebrow>{s.title}</Eyebrow>
            <ScreenshotPanel src={staticFile(s.src)} label={s.label} durationInFrames={L[4 + i] - s.from} panX={s.panX} width={640} />
          </Center>
        </Sequence>
      ))}

      {/* S5 — join the family */}
      <Sequence from={L[6]} durationInFrames={L[7] - L[6]}>
        <Center gap={16}>
          <Eyebrow>Founding Atlas Partners</Eyebrow>
          <Headline delay={8} size={46}>You're not just a customer.</Headline>
          <Headline delay={18} size={46} color={BRAND.goldLight}>You're a founding partner.</Headline>
          <div style={{ height: 6 }} />
          <CheckLine delay={30} text="$150 / month, locked for life" />
          <CheckLine delay={40} text="Your Snapshot + a 45-minute walkthrough" />
        </Center>
      </Sequence>

      {/* S6 — CTA */}
      <Sequence from={L[8]} durationInFrames={L[9] - L[8]}>
        <Center gap={26}>
          <LogoLockup />
          <CTAButton delay={12}>Join the Family — Apply Now</CTAButton>
          <Rise delay={20}>
            <div style={{ fontFamily: SANS, fontSize: 24, fontWeight: 700, color: BRAND.goldLight, letterSpacing: "0.04em" }}>
              {SIGNUP_URL}
            </div>
          </Rise>
        </Center>
      </Sequence>

      <SceneDissolve boundaries={L.slice(1, -1)} />
      <Subtitles captions={CAPTIONS} />
    </NavyBG>
  );
};
