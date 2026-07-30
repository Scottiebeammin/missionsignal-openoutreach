import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile } from "remotion";
import { Caption, Eyebrow, Headline, LaptopScreenshotPanel, NavyBG, Rise, Subtitles } from "../components";

export type Props = { audioSrc?: string | null };

// Voice: Siren — optional screen b-roll segment for the Fri Jul 10 talking-head short.
// Timing derived from the measured VO (8.962902s @ 30fps = 268.9f -> 269f), split across the
// 2 script lines proportional to word count (24 words total: 17 + 7).
const L = [0, 191, 269];

const CAPTIONS: Caption[] = [
  { text: "The Opportunity Web Snapshot leads with a summary and a 30-day action plan — not a search result.", from: L[0], duration: L[1] - L[0] },
  { text: "That's the difference between information and direction.", from: L[1], duration: L[2] - L[1] },
];

const Center: React.FC<{ children: React.ReactNode; gap?: number }> = ({ children, gap = 24 }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap }}>
    {children}
  </AbsoluteFill>
);

export const Jul10SnapshotClip: React.FC<Props> = ({ audioSrc }) => {
  return (
    <NavyBG>
      {audioSrc ? <Audio src={staticFile(audioSrc)} /> : null}

      {/* real product proof — new style: laptop mockup, not an abstract card */}
      <Sequence from={L[0]} durationInFrames={L[1] - L[0]}>
        <Center gap={18}>
          <Eyebrow delay={2}>The Opportunity Web Snapshot</Eyebrow>
          <LaptopScreenshotPanel src={staticFile("screenshots/shot-snapshot3.png")} label="anansiatlas.com" durationInFrames={L[1] - L[0]} width={620} panY={[0, -10]} />
        </Center>
      </Sequence>

      <Sequence from={L[1]} durationInFrames={L[2] - L[1]}>
        <Center>
          <Rise delay={2}>
            <Headline delay={0} size={58}>Information vs. direction.</Headline>
          </Rise>
        </Center>
      </Sequence>

      <Subtitles captions={CAPTIONS} />
    </NavyBG>
  );
};
