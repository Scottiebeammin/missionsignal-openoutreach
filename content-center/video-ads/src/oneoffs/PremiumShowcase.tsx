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
  ScreenshotPanel,
  Subtitles,
} from "../components";

export type Props = { audioSrc?: string | null };

// ONE-OFF — not part of the automated ads pipeline (see ads.config.mjs). Premium brand
// commercial built from REAL product screenshots (public/screenshots/*.png, captured live
// off the Creative Display demo profile — anonymized, ad-safe). Voice: Christopher.
const CAPTIONS: Caption[] = [
  { text: "Every mission is surrounded by opportunity.", from: 0, duration: 150 },
  { text: "The problem was never opportunity. It was visibility.", from: 150, duration: 180 },
  { text: "This is Anansi Atlas.", from: 330, duration: 180 },
  { text: "Your Dashboard opens with one clear next move.", from: 510, duration: 360 },
  { text: "Your Opportunity Web maps your mission at the center.", from: 870, duration: 360 },
  { text: "Your Snapshot opens with a 30-day action plan.", from: 1230, duration: 360 },
  { text: "Founding Atlas Partners aren't just customers.", from: 1590, duration: 180 },
  { text: "They're the first twenty organizations shaping this platform.", from: 1770, duration: 210 },
  { text: "A rate locked in for life.", from: 1980, duration: 210 },
  { text: "If you're ready to stop guessing — join the family.", from: 2190, duration: 180 },
  { text: "Apply at anansiatlas.com/anansi-atlas", from: 2370, duration: 180 },
];

const Center: React.FC<{ children: React.ReactNode; gap?: number }> = ({ children, gap = 26 }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap }}>
    {children}
  </AbsoluteFill>
);

const SCREENS = [
  { at: 510, src: "screenshots/dashboard.png", label: "anansiatlas.com/dashboard", title: "One Clear Next Move", panX: [0, 30] as [number, number] },
  { at: 870, src: "screenshots/web.png", label: "anansiatlas.com/web", title: "Your Mission at the Center", panX: [0, -30] as [number, number] },
  { at: 1230, src: "screenshots/snapshot.png", label: "anansiatlas.com/snapshot", title: "A 30-Day Action Plan", panX: [0, 30] as [number, number] },
];
const SCREEN_DUR = 360;

export const PremiumShowcase: React.FC<Props> = ({ audioSrc }) => {
  return (
    <NavyBG>
      {audioSrc ? <Audio src={staticFile(audioSrc)} /> : null}

      {/* S1 — hook */}
      <Sequence from={0} durationInFrames={150}>
        <Center>
          <Headline delay={6}>Every mission is surrounded by opportunity.</Headline>
        </Center>
      </Sequence>

      {/* S2 — problem */}
      <Sequence from={150} durationInFrames={180}>
        <Center gap={16}>
          <Rise>
            <div style={{ fontFamily: SANS, fontSize: 26, fontWeight: 800, color: BRAND.muted, letterSpacing: "0.1em", textTransform: "uppercase" }}>
              The problem was never opportunity.
            </div>
          </Rise>
          <Headline delay={12} color={BRAND.goldLight} size={72}>It was visibility.</Headline>
        </Center>
      </Sequence>

      {/* S3 — motion-graphics brand reveal (converging threads + shimmer, not a static fade) */}
      <Sequence from={330} durationInFrames={180}>
        <AnimatedLogoReveal delay={4} />
      </Sequence>

      {/* S4 — real product reel: Dashboard, Opportunity Web, Snapshot */}
      {SCREENS.map((s) => (
        <Sequence key={s.src} from={s.at} durationInFrames={SCREEN_DUR}>
          <Center gap={22}>
            <Eyebrow>{s.title}</Eyebrow>
            <ScreenshotPanel src={staticFile(s.src)} label={s.label} durationInFrames={SCREEN_DUR} panX={s.panX} />
          </Center>
        </Sequence>
      ))}

      {/* S5 — join the family */}
      <Sequence from={1590} durationInFrames={600}>
        <Center gap={22}>
          <Eyebrow>Founding Atlas Partners</Eyebrow>
          <Headline delay={10} size={62}>You're not just a customer.</Headline>
          <Headline delay={22} size={62} color={BRAND.goldLight}>You're a founding partner.</Headline>
          <div style={{ height: 12 }} />
          <CheckLine delay={40} text="$150 / month, locked for life" />
          <CheckLine delay={54} text="Your Snapshot + a 45-minute walkthrough" />
          <CheckLine delay={68} text="Direct input shaping the platform" />
        </Center>
      </Sequence>

      {/* S6 — CTA */}
      <Sequence from={2190} durationInFrames={360}>
        <Center gap={34}>
          <LogoLockup />
          <CTAButton delay={16}>Join the Family — Apply Now</CTAButton>
          <Rise delay={26}>
            <div style={{ fontFamily: SANS, fontSize: 30, fontWeight: 700, color: BRAND.goldLight, letterSpacing: "0.04em" }}>
              {SIGNUP_URL}
            </div>
          </Rise>
        </Center>
      </Sequence>

      <Subtitles captions={CAPTIONS} />
    </NavyBG>
  );
};
