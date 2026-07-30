import React from "react";
import { AbsoluteFill, Audio, Img, Sequence, staticFile } from "remotion";
import { BRAND } from "../brand";
import { Caption, CTAButton, Eyebrow, Headline, LogoLockup, NavyBG, Rise, SANS, Subtitles } from "../components";

export type Props = { audioSrc?: string | null };

// Voice: Jackson — optional outro card on the Fri Jul 17 founder-endorsement video.
// Timing derived from the measured VO (10.1239s @ 30fps = 303.7f -> 304f), split across the 2
// script lines proportional to word count (22 words total: 13 + 9). The original hardcoded
// 240f (8s) ran shorter than the VO — narration would have been cut off; fixed here.
const L = [0, 180, 304];

const CAPTIONS: Caption[] = [
  { text: "Founding Partners lock in $150 / month, for life.", from: L[0], duration: L[1] - L[0] },
  { text: "Apply at anansiatlas.com/anansi-atlas", from: L[1], duration: L[2] - L[1] },
];

const Center: React.FC<{ children: React.ReactNode; gap?: number }> = ({ children, gap = 26 }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap }}>
    {children}
  </AbsoluteFill>
);

export const Jul17EndorsementOutro: React.FC<Props> = ({ audioSrc }) => {
  return (
    <NavyBG>
      {audioSrc ? <Audio src={staticFile(audioSrc)} /> : null}

      <Sequence from={L[0]} durationInFrames={L[1] - L[0]}>
        <Center>
          <Eyebrow>Founding Atlas Partners</Eyebrow>
          <Headline delay={8} size={90}>$150 / month</Headline>
          <Rise delay={20}>
            <div style={{ fontFamily: SANS, fontSize: 32, fontWeight: 700, color: BRAND.goldLight }}>
              Locked for life · 20 seats only
            </div>
          </Rise>
        </Center>
      </Sequence>

      <Sequence from={L[1]} durationInFrames={L[2] - L[1]}>
        <Center gap={26}>
          <Rise delay={0}>
            <Img src={staticFile("logo-mark.png")} style={{ width: 68, height: 68 }} />
          </Rise>
          <LogoLockup delay={6} />
          <CTAButton delay={16}>Apply Now</CTAButton>
        </Center>
      </Sequence>

      <Subtitles captions={CAPTIONS} />
    </NavyBG>
  );
};
