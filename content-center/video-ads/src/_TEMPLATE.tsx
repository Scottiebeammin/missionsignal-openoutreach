import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile } from "remotion";
import { BRAND, SIGNUP_URL } from "./brand";
import {
  AnimatedLogoReveal,
  Caption,
  CTAButton,
  Eyebrow,
  Headline,
  LogoLockup,
  NavyBG,
  Rise,
  SANS,
  ScreenshotPanel,
  Subtitles,
} from "./components";

/**
 * ── AD STARTER TEMPLATE (see BRAND-TEMPLATE.md) ────────────────────────────────
 * The standard 6-beat Anansi Atlas ad. To make a new ad:
 *   1. Copy this file → src/ads/<YourAd>.tsx and rename the component.
 *   2. Keep the beats you want, delete the rest, adjust `from`/`durationInFrames`.
 *   3. Register it in src/Root.tsx (id, duration, width/height).
 *   4. If it's a dated calendar post, add it to ads.config.mjs (voice, script, date).
 * Beats: Hook → Problem → Brand reveal → Product → Offer → CTA.
 * Rules: real product (ScreenshotPanel, not mockups) · subtitles on · one CTA to the
 * signup link · "$150 locked for life" (Snapshot never "free") · end on the logo.
 * ──────────────────────────────────────────────────────────────────────────────
 */

export type Props = { audioSrc?: string | null };

// Keep captions in sync with the VO script. LinkedIn/IG/TikTok autoplay muted.
const CAPTIONS: Caption[] = [
  { text: "Your hook line here.", from: 0, duration: 120 },
  { text: "The problem — scattered, no system.", from: 120, duration: 120 },
  { text: "This is Anansi Atlas.", from: 240, duration: 120 },
  { text: "Show the real product.", from: 360, duration: 240 },
  { text: "20 seats · $150/mo locked for life.", from: 600, duration: 150 },
  { text: "Apply at anansiatlas.com/anansi-atlas", from: 750, duration: 150 },
];

const Center: React.FC<{ children: React.ReactNode; gap?: number }> = ({ children, gap = 26 }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap }}>
    {children}
  </AbsoluteFill>
);

export const AdTemplate: React.FC<Props> = ({ audioSrc }) => {
  return (
    <NavyBG>
      {audioSrc ? <Audio src={staticFile(audioSrc)} /> : null}

      {/* 1 — HOOK */}
      <Sequence from={0} durationInFrames={120}>
        <Center>
          <Headline delay={6}>Your sharp hook goes here.</Headline>
        </Center>
      </Sequence>

      {/* 2 — PROBLEM */}
      <Sequence from={120} durationInFrames={120}>
        <Center gap={16}>
          <Rise>
            <div style={{ fontFamily: SANS, fontSize: 26, fontWeight: 800, color: BRAND.muted, letterSpacing: "0.1em", textTransform: "uppercase" }}>
              Name the problem.
            </div>
          </Rise>
          <Headline delay={12} color={BRAND.goldLight} size={68}>It's not a lack of effort — it's a lack of a system.</Headline>
        </Center>
      </Sequence>

      {/* 3 — BRAND REVEAL */}
      <Sequence from={240} durationInFrames={120}>
        <AnimatedLogoReveal delay={4} />
      </Sequence>

      {/* 4 — PRODUCT (real UI — swap the screenshot: dashboard.png / web.png / snapshot.png) */}
      <Sequence from={360} durationInFrames={240}>
        <Center gap={22}>
          <Eyebrow>anansiatlas.com/dashboard</Eyebrow>
          <ScreenshotPanel src={staticFile("screenshots/dashboard.png")} label="anansiatlas.com/dashboard" durationInFrames={240} />
        </Center>
      </Sequence>

      {/* 5 — OFFER */}
      <Sequence from={600} durationInFrames={150}>
        <Center gap={14}>
          <Eyebrow>Founding Atlas Partners</Eyebrow>
          <Headline delay={8} size={84}>$150 / month</Headline>
          <Rise delay={20}>
            <div style={{ fontFamily: SANS, fontSize: 32, fontWeight: 700, color: BRAND.goldLight }}>Locked for life · 20 seats</div>
          </Rise>
        </Center>
      </Sequence>

      {/* 6 — CTA */}
      <Sequence from={750} durationInFrames={150}>
        <Center gap={34}>
          <LogoLockup />
          <CTAButton delay={14}>Apply Now</CTAButton>
          <Rise delay={24}>
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
