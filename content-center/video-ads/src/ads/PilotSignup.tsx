import React from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { BRAND, SIGNUP_URL } from "../brand";
import { Caption, CTAButton, Eyebrow, Headline, LogoLockup, NavyBG, Rise, SANS, SERIF, Subtitles } from "../components";

export type PilotProps = { audioSrc?: string | null };

// Bottom subtitles — kept in sync with the Jackson VO script (see README).
const CAPTIONS: Caption[] = [
  { text: "Applications are open for the Founding Atlas Partners Pilot.", from: 0, duration: 90 },
  { text: "We're selecting 19 nonprofit & mission-driven organizations.", from: 90, duration: 150 },
  { text: "Included: the Snapshot, a 45-minute walkthrough, the living platform.", from: 240, duration: 210 },
  { text: "$150 / month — locked for life — first 20 organizations.", from: 450, duration: 150 },
  { text: "19 seats remain.", from: 600, duration: 150 },
  { text: "Apply now · anansiatlas.com/anansi-atlas", from: 750, duration: 150 },
];

const Center: React.FC<{ children: React.ReactNode; gap?: number }> = ({ children, gap = 28 }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap }}>
    {children}
  </AbsoluteFill>
);

const BigNumber: React.FC<{ value: string; label: string }> = ({ value, label }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 120 } });
  const scale = interpolate(s, [0, 1], [0.6, 1]);
  return (
    <div style={{ textAlign: "center", transform: `scale(${scale})` }}>
      <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 340, lineHeight: 1, color: BRAND.goldLight }}>
        {value}
      </div>
      <div
        style={{
          fontFamily: SANS,
          fontWeight: 800,
          fontSize: 40,
          letterSpacing: "0.14em",
          textTransform: "uppercase",
          color: BRAND.white,
          marginTop: 10,
        }}
      >
        {label}
      </div>
    </div>
  );
};

const Included: React.FC<{ text: string; delay: number }> = ({ text, delay }) => (
  <Rise delay={delay}>
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 20,
        width: 760,
        background: "rgba(255,255,255,0.05)",
        border: "1px solid rgba(212,160,23,0.4)",
        borderRadius: 18,
        padding: "22px 28px",
      }}
    >
      <div style={{ color: BRAND.gold, fontSize: 40, fontWeight: 900 }}>✓</div>
      <div style={{ fontFamily: SANS, fontSize: 34, fontWeight: 600, color: BRAND.white }}>{text}</div>
    </div>
  </Rise>
);

const SeatDots: React.FC = () => {
  const frame = useCurrentFrame();
  const filled = Math.min(19, Math.floor(interpolate(frame, [10, 90], [0, 19], { extrapolateRight: "clamp" })));
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 16, width: 720, justifyContent: "center" }}>
      {Array.from({ length: 20 }).map((_, i) => (
        <div
          key={i}
          style={{
            width: 54,
            height: 54,
            borderRadius: 12,
            background: i < filled ? BRAND.gold : "transparent",
            border: `2px solid ${i < filled ? BRAND.gold : "rgba(255,255,255,0.3)"}`,
          }}
        />
      ))}
    </div>
  );
};

export const PilotSignup: React.FC<PilotProps> = ({ audioSrc }) => {
  return (
    <NavyBG>
      {audioSrc ? <Audio src={staticFile(audioSrc)} /> : null}

      {/* S1 — open */}
      <Sequence from={0} durationInFrames={90}>
        <Center>
          <Eyebrow>Founding Atlas Partners Pilot</Eyebrow>
          <Headline delay={8}>Applications are open.</Headline>
        </Center>
      </Sequence>

      {/* S2 — the number */}
      <Sequence from={90} durationInFrames={150}>
        <Center>
          <BigNumber value="19" label="nonprofits we're selecting" />
        </Center>
      </Sequence>

      {/* S3 — what's included */}
      <Sequence from={240} durationInFrames={210}>
        <Center gap={22}>
          <Eyebrow>What partners receive</Eyebrow>
          <Included delay={14} text="A guided Opportunity Web Snapshot" />
          <Included delay={30} text="A 45-minute founder walkthrough" />
          <Included delay={46} text="The living platform — alerts, matches, deadlines" />
        </Center>
      </Sequence>

      {/* S4 — price / offer */}
      <Sequence from={450} durationInFrames={150}>
        <Center gap={18}>
          <Headline size={84}>$150 / month</Headline>
          <Rise delay={16}>
            <div style={{ fontFamily: SANS, fontSize: 34, fontWeight: 700, color: BRAND.goldLight, textAlign: "center" }}>
              Locked for life · first 20 organizations
            </div>
          </Rise>
        </Center>
      </Sequence>

      {/* S5 — scarcity */}
      <Sequence from={600} durationInFrames={150}>
        <Center gap={30}>
          <SeatDots />
          <Rise delay={70}>
            <div style={{ fontFamily: SERIF, fontSize: 64, fontWeight: 600, color: BRAND.white }}>
              19 seats remain.
            </div>
          </Rise>
        </Center>
      </Sequence>

      {/* S6 — CTA */}
      <Sequence from={750} durationInFrames={150}>
        <Center gap={34}>
          <LogoLockup />
          <CTAButton delay={16}>Apply Now</CTAButton>
          <Rise delay={26}>
            <div style={{ fontFamily: SANS, fontSize: 32, fontWeight: 700, color: BRAND.goldLight, letterSpacing: "0.04em" }}>
              {SIGNUP_URL}
            </div>
          </Rise>
        </Center>
      </Sequence>

      <Subtitles captions={CAPTIONS} />
    </NavyBG>
  );
};
