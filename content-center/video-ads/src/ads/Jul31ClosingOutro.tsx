import React from "react";
import { AbsoluteFill, Audio, Img, Sequence, staticFile } from "remotion";
import { BRAND } from "../brand";
import { Caption, CTAButton, Eyebrow, Headline, LogoLockup, NavyBG, Rise, SANS, Subtitles } from "../components";

export type Props = { audioSrc?: string | null };

// Voice: Jackson — optional outro card on the Fri Jul 31 founder-closing video.
// Timing derived from the measured VO (9.659501s @ 30fps = 289.8f -> 290f), split across the 2
// script lines proportional to word count (23 words total: 8 + 15). The original hardcoded 240f
// (8s) ran shorter than the VO — narration would have been cut off; fixed here.
const L = [0, 101, 290];

const CAPTIONS: Caption[] = [
  { text: "The Founding Atlas Partners pilot is nearly full.", from: L[0], duration: L[1] - L[0] },
  { text: "$150 / month, locked for life. Apply or message me today.", from: L[1], duration: L[2] - L[1] },
];

const Center: React.FC<{ children: React.ReactNode; gap?: number }> = ({ children, gap = 26 }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap }}>
    {children}
  </AbsoluteFill>
);

export const Jul31ClosingOutro: React.FC<Props> = ({ audioSrc }) => {
  return (
    <NavyBG>
      {audioSrc ? <Audio src={staticFile(audioSrc)} /> : null}

      <Sequence from={L[0]} durationInFrames={L[1] - L[0]}>
        <Center>
          <Eyebrow>Nearly Full</Eyebrow>
          <Headline delay={8} size={62}>Last few founding seats.</Headline>
          <Rise delay={20}>
            <div style={{ fontFamily: SANS, fontSize: 30, fontWeight: 700, color: BRAND.goldLight }}>
              $150/month · locked for life
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
          <CTAButton delay={16}>Apply or Message Me</CTAButton>
        </Center>
      </Sequence>

      <Subtitles captions={CAPTIONS} />
    </NavyBG>
  );
};
