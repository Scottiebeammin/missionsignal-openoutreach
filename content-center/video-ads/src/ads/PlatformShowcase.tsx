import React from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  Sequence,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { BRAND } from "../brand";
import {
  BubbleCard,
  Caption,
  CTAButton,
  Eyebrow,
  Headline,
  LogoLockup,
  NavyBG,
  OrbWeb,
  Rise,
  SANS,
  Subtitles,
} from "../components";
import { SIGNUP_URL } from "../brand";

export type ShowcaseProps = { audioSrc?: string | null };

// Bottom subtitles — kept in sync with the Christopher VO script (see README).
const CAPTIONS: Caption[] = [
  { text: "Your next opportunity is already out there.", from: 0, duration: 120 },
  { text: "It's just scattered — funder portals, emails, spreadsheets, relationships.", from: 120, duration: 150 },
  { text: "Anansi Atlas maps the web of opportunity around your mission.", from: 270, duration: 180 },
  { text: "Your Snapshot: your strongest asset, your biggest gap…", from: 450, duration: 180 },
  { text: "…and the single highest-leverage move to make next.", from: 630, duration: 150 },
  { text: "Apply for a founding seat · anansiatlas.com/anansi-atlas", from: 780, duration: 120 },
];

const Center: React.FC<{ children: React.ReactNode; gap?: number }> = ({ children, gap = 28 }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap }}>
    {children}
  </AbsoluteFill>
);

const SCATTER = ["grant portals", "funder emails", "spreadsheets", "deadlines", "partners", "RFPs", "local knowledge", "relationships"];

const ScatterField: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill>
      {SCATTER.map((w, i) => {
        const x = [140, 640, 340, 780, 210, 700, 120, 560][i];
        const y = [220, 180, 760, 700, 470, 460, 640, 840][i];
        const drift = Math.sin((frame + i * 40) / 40) * 10;
        const op = interpolate(frame, [10 + i * 6, 30 + i * 6], [0, 0.85], { extrapolateRight: "clamp" });
        return (
          <div
            key={w}
            style={{
              position: "absolute",
              left: x,
              top: y + drift,
              fontFamily: SANS,
              fontSize: 34,
              fontWeight: 700,
              color: BRAND.muted,
              opacity: op,
            }}
          >
            {w}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

export const PlatformShowcase: React.FC<ShowcaseProps> = ({ audioSrc }) => {
  return (
    <NavyBG>
      {audioSrc ? <Audio src={staticFile(audioSrc)} /> : null}

      {/* S1 — who/what */}
      <Sequence from={0} durationInFrames={120}>
        <Center>
          <Eyebrow>Nonprofit Opportunity Intelligence</Eyebrow>
          <Headline delay={8}>Your next opportunity is already out there.</Headline>
        </Center>
      </Sequence>

      {/* S2 — the problem: scattered */}
      <Sequence from={120} durationInFrames={150}>
        <ScatterField />
        <Center>
          <Headline color={BRAND.goldLight}>It's just scattered.</Headline>
        </Center>
      </Sequence>

      {/* S3 — the web assembles */}
      <Sequence from={270} durationInFrames={180}>
        <Web />
      </Sequence>

      {/* S4 — the Snapshot */}
      <Sequence from={450} durationInFrames={180}>
        <Center gap={22}>
          <Eyebrow>The Opportunity Web Snapshot</Eyebrow>
          <BubbleCard delay={14} tone="teal" label="Strongest Asset" value="Deep community trust and a clear, fundable mission." />
          <BubbleCard delay={30} tone="gold" label="Biggest Constraint" value="No named government funding relationships yet." />
        </Center>
      </Sequence>

      {/* S5 — one next move */}
      <Sequence from={630} durationInFrames={150}>
        <Center gap={20}>
          <Eyebrow>What To Do Next</Eyebrow>
          <Rise delay={12}>
            <div
              style={{
                width: 780,
                background: "linear-gradient(145deg,#0d1b3d,#17284f)",
                border: `2px solid rgba(212,160,23,.4)`,
                borderRadius: 24,
                padding: "44px 46px",
                color: BRAND.white,
                fontFamily: SANS,
                fontSize: 44,
                fontWeight: 700,
                lineHeight: 1.15,
                textAlign: "center",
              }}
            >
              One highest-leverage move — mapped, prioritized, and ready to act on.
            </div>
          </Rise>
        </Center>
      </Sequence>

      {/* S6 — brand + CTA */}
      <Sequence from={780} durationInFrames={120}>
        <Center gap={34}>
          <LogoLockup />
          <CTAButton delay={16}>Apply for a Founding Seat</CTAButton>
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

const Web: React.FC = () => {
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [0, 120], [0, 1], { extrapolateRight: "clamp" });
  const capOp = interpolate(frame, [110, 140], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill>
      <OrbWeb progress={progress} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: 70 }}>
        <div
          style={{
            opacity: capOp,
            fontFamily: SANS,
            fontSize: 34,
            fontWeight: 600,
            color: BRAND.ink,
            textAlign: "center",
            padding: "0 120px",
          }}
        >
          Anansi Atlas maps the web of opportunity around your mission.
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
