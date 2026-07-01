import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile } from "remotion";
import { BRAND } from "../brand";
import { Caption, CTAButton, Eyebrow, Headline, LogoLockup, NavyBG, Rise, SANS, Subtitles } from "../components";

export type Props = { audioSrc?: string | null };

// Voice: Jackson — optional outro card on the Fri Jul 17 founder-endorsement video.
const CAPTIONS: Caption[] = [
  { text: "Founding Partners lock in $150 / month, for life.", from: 0, duration: 120 },
  { text: "Apply at anansiatlas.com/anansi-atlas", from: 120, duration: 120 },
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

      <Sequence from={0} durationInFrames={110}>
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

      <Sequence from={110} durationInFrames={130}>
        <Center gap={34}>
          <LogoLockup />
          <CTAButton delay={10}>Apply Now</CTAButton>
        </Center>
      </Sequence>

      <Subtitles captions={CAPTIONS} />
    </NavyBG>
  );
};
