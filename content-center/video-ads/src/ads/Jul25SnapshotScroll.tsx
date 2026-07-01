import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile } from "remotion";
import { BRAND } from "../brand";
import { BubbleCard, Caption, CTAButton, Eyebrow, Headline, LogoLockup, NavyBG, Rise, SANS, Subtitles } from "../components";

export type Props = { audioSrc?: string | null };

// Voice: Giselle — full VO, vertical 9:16 for the Instagram/TikTok Snapshot scroll-through repurpose.
const CAPTIONS: Caption[] = [
  { text: "Your Snapshot doesn't bury the point.", from: 0, duration: 100 },
  { text: "It opens with a 30-day action plan, ranked for your mission.", from: 100, duration: 140 },
  { text: "Teal marks strength. Gold marks a gap.", from: 240, duration: 120 },
  { text: "One page. One clear move. Included in the founding pilot.", from: 360, duration: 90 },
];

const Center: React.FC<{ children: React.ReactNode; gap?: number }> = ({ children, gap = 26 }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap }}>
    {children}
  </AbsoluteFill>
);

export const Jul25SnapshotScroll: React.FC<Props> = ({ audioSrc }) => {
  return (
    <NavyBG w={1080} h={1920}>
      {audioSrc ? <Audio src={staticFile(audioSrc)} /> : null}

      <Sequence from={0} durationInFrames={100}>
        <Center>
          <Eyebrow>The Opportunity Web Snapshot</Eyebrow>
          <Headline delay={8} size={70}>Doesn't bury the point.</Headline>
        </Center>
      </Sequence>

      <Sequence from={100} durationInFrames={140}>
        <Center gap={22}>
          <Rise>
            <div style={{ fontFamily: SANS, fontSize: 30, fontWeight: 700, color: BRAND.white, textAlign: "center", padding: "0 70px" }}>
              A 30-day action plan, ranked for your mission —
            </div>
          </Rise>
        </Center>
      </Sequence>

      <Sequence from={240} durationInFrames={120}>
        <Center gap={20}>
          <BubbleCard delay={4} tone="teal" label="Strongest Asset" value="Deep community trust and a clear, fundable mission." />
          <BubbleCard delay={16} tone="gold" label="Biggest Constraint" value="No named government funding relationships yet." />
        </Center>
      </Sequence>

      <Sequence from={360} durationInFrames={90}>
        <Center gap={30}>
          <LogoLockup />
          <CTAButton delay={8}>Join the Founding Pilot</CTAButton>
        </Center>
      </Sequence>

      <Subtitles captions={CAPTIONS} />
    </NavyBG>
  );
};
