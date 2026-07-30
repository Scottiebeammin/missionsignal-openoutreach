import React from "react";
import { AbsoluteFill, Audio, Img, Sequence, staticFile } from "remotion";
import { BRAND } from "../brand";
import { BubbleCard, Caption, CTAButton, Eyebrow, Headline, LogoLockup, NavyBG, Rise, SANS, Subtitles } from "../components";

export type Props = { audioSrc?: string | null };

// Voice: Giselle — full VO, vertical 9:16 for the Instagram/TikTok Snapshot scroll-through repurpose.
// Timing derived from the measured VO (13.931973s @ 30fps = 417.96f -> 418f), split across the 3
// script lines proportional to word count (34 words total: 17 + 12 + 5). A 90f hold is added
// after the VO ends so the CTA card lingers.
const CTA_HOLD = 90;
const L = [0, 209, 357, 418];
export const WALK_TOTAL = L[3] + CTA_HOLD;

const CAPTIONS: Caption[] = [
  { text: "Your Snapshot doesn't bury the point. It opens with a 30-day action plan, ranked for your mission.", from: L[0], duration: L[1] - L[0] },
  { text: "Teal marks strength. Gold marks a gap. One page. One clear move.", from: L[1], duration: L[2] - L[1] },
  { text: "Included in the founding pilot.", from: L[2], duration: L[3] - L[2] },
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

      <Sequence from={L[0]} durationInFrames={(L[1] - L[0]) * 0.45}>
        <Center>
          <Eyebrow>The Opportunity Web Snapshot</Eyebrow>
          <Headline delay={8} size={70}>Doesn't bury the point.</Headline>
        </Center>
      </Sequence>

      <Sequence from={L[0] + (L[1] - L[0]) * 0.45} durationInFrames={(L[1] - L[0]) * 0.55}>
        <Center gap={22}>
          <Rise>
            <div style={{ fontFamily: SANS, fontSize: 30, fontWeight: 700, color: BRAND.white, textAlign: "center", padding: "0 70px" }}>
              A 30-day action plan, ranked for your mission —
            </div>
          </Rise>
        </Center>
      </Sequence>

      <Sequence from={L[1]} durationInFrames={L[2] - L[1]}>
        <Center gap={20}>
          <BubbleCard delay={4} tone="teal" label="Strongest Asset" value="Deep community trust and a clear, fundable mission." />
          <BubbleCard delay={16} tone="gold" label="Biggest Constraint" value="No named government funding relationships yet." />
        </Center>
      </Sequence>

      <Sequence from={L[2]} durationInFrames={WALK_TOTAL - L[2]}>
        <Center gap={26}>
          <Rise delay={0}>
            <Img src={staticFile("logo-mark.png")} style={{ width: 68, height: 68 }} />
          </Rise>
          <LogoLockup delay={6} />
          <CTAButton delay={16}>Join the Founding Pilot</CTAButton>
        </Center>
      </Sequence>

      <Subtitles captions={CAPTIONS} />
    </NavyBG>
  );
};
