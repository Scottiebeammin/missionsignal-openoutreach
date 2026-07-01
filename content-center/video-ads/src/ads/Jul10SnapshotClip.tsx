import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile } from "remotion";
import { BubbleCard, Caption, Eyebrow, Headline, NavyBG, Rise, Subtitles } from "../components";

export type Props = { audioSrc?: string | null };

// Voice: Siren — optional screen b-roll segment for the Fri Jul 10 talking-head short.
const CAPTIONS: Caption[] = [
  { text: "The Opportunity Web Snapshot leads with a summary and a 30-day action plan…", from: 0, duration: 150 },
  { text: "…not a search result.", from: 150, duration: 90 },
  { text: "That's the difference between information and direction.", from: 240, duration: 120 },
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

      <Sequence from={0} durationInFrames={150}>
        <Center>
          <Eyebrow>The Opportunity Web Snapshot</Eyebrow>
          <Headline delay={8} size={64}>A 30-day plan. Not a search result.</Headline>
        </Center>
      </Sequence>

      <Sequence from={150} durationInFrames={210}>
        <Center gap={20}>
          <BubbleCard delay={6} tone="teal" label="Strongest Asset" value="Deep community trust and a clear, fundable mission." />
          <BubbleCard delay={20} tone="gold" label="Biggest Constraint" value="No named government funding relationships yet." />
          <Rise delay={40}>
            <div style={{ fontFamily: "inherit", fontSize: 34, fontWeight: 700, color: "#f3dd8c", textAlign: "center", marginTop: 8 }}>
              Information vs. direction.
            </div>
          </Rise>
        </Center>
      </Sequence>

      <Subtitles captions={CAPTIONS} />
    </NavyBG>
  );
};
