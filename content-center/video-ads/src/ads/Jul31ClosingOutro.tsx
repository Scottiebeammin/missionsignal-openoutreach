import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile } from "remotion";
import { BRAND } from "../brand";
import { Caption, CTAButton, Eyebrow, Headline, LogoLockup, NavyBG, Rise, SANS, Subtitles } from "../components";

export type Props = { audioSrc?: string | null };

// Voice: Jackson — optional outro card on the Fri Jul 31 founder-closing video.
const CAPTIONS: Caption[] = [
  { text: "The Founding Atlas Partners pilot is nearly full.", from: 0, duration: 120 },
  { text: "$150 / month, locked for life. Apply or message me today.", from: 120, duration: 120 },
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

      <Sequence from={0} durationInFrames={110}>
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

      <Sequence from={110} durationInFrames={130}>
        <Center gap={34}>
          <LogoLockup />
          <CTAButton delay={10}>Apply or Message Me</CTAButton>
        </Center>
      </Sequence>

      <Subtitles captions={CAPTIONS} />
    </NavyBG>
  );
};
