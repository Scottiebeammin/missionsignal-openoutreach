import React from "react";
import { AbsoluteFill, Audio, Img, Sequence, staticFile } from "remotion";
import { BRAND } from "../brand";
import { Caption, CTAButton, Eyebrow, Headline, LogoLockup, NavyBG, Rise, SANS, Subtitles } from "../components";

export type Props = { audioSrc?: string | null };

// Voice: Siren — screen segment for the Fri Jul 24 "list vs. map" split-screen short.
// Timing derived from the measured VO (10.774059s @ 30fps = 323.2f -> 323f), split across the 2
// script lines proportional to word count (25 words total: 5 + 20). A 130f hold is added after
// the VO ends so the CTA card lingers (matches the original ~15s total run time).
const CTA_HOLD = 130;
const L = [0, 65, 323];
export const WALK_TOTAL = L[2] + CTA_HOLD;

const CAPTIONS: Caption[] = [
  { text: "One page. One clear move.", from: L[0], duration: L[1] - L[0] },
  { text: "Funders, partners, and government pathways — mapped around your mission…", from: L[1], duration: (L[2] - L[1]) / 2 },
  { text: "…with readiness scored and a single top move to make next.", from: L[1] + (L[2] - L[1]) / 2, duration: (L[2] - L[1]) / 2 },
];

const Center: React.FC<{ children: React.ReactNode; gap?: number }> = ({ children, gap = 24 }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap }}>
    {children}
  </AbsoluteFill>
);

const ListSide: React.FC = () => (
  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
    {["Funder A", "Funder B", "Funder C", "Funder D", "Funder E"].map((f) => (
      <div
        key={f}
        style={{
          width: 260,
          padding: "10px 16px",
          borderRadius: 8,
          border: `1px solid ${BRAND.muted}`,
          color: BRAND.muted,
          fontFamily: SANS,
          fontSize: 22,
          fontWeight: 600,
        }}
      >
        {f}
      </div>
    ))}
  </div>
);

const MapSide: React.FC = () => (
  <div
    style={{
      width: 260,
      height: 260,
      borderRadius: "50%",
      border: `2px solid ${BRAND.gold}`,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      position: "relative",
    }}
  >
    {["Funders", "Partners", "Government"].map((n, i) => {
      const a = (i / 3) * Math.PI * 2 - Math.PI / 2;
      const x = 130 + Math.cos(a) * 130;
      const y = 130 + Math.sin(a) * 130;
      return (
        <div
          key={n}
          style={{
            position: "absolute",
            left: x - 45,
            top: y - 16,
            background: BRAND.navy2,
            border: `1px solid ${BRAND.gold}`,
            borderRadius: 999,
            padding: "6px 10px",
            fontFamily: SANS,
            fontSize: 14,
            fontWeight: 800,
            color: BRAND.goldLight,
            width: 90,
            textAlign: "center",
          }}
        >
          {n}
        </div>
      );
    })}
    <div style={{ fontFamily: SANS, fontSize: 16, fontWeight: 800, color: BRAND.white, textAlign: "center" }}>
      YOUR
      <br />
      MISSION
    </div>
  </div>
);

export const Jul24ListVsMap: React.FC<Props> = ({ audioSrc }) => {
  return (
    <NavyBG>
      {audioSrc ? <Audio src={staticFile(audioSrc)} /> : null}

      {/* the payoff line lands first in the VO — headline opens, then the list-vs-map visual
          carries the longer explanatory line */}
      <Sequence from={L[0]} durationInFrames={L[1] - L[0]}>
        <Center>
          <Eyebrow>The Opportunity Web</Eyebrow>
          <Headline delay={4} size={58}>One page. One clear move.</Headline>
        </Center>
      </Sequence>

      <Sequence from={L[1]} durationInFrames={L[2] - L[1]}>
        <AbsoluteFill style={{ flexDirection: "row" }}>
          <AbsoluteFill style={{ left: 0, width: "50%", alignItems: "center", justifyContent: "center" }}>
            <Rise>
              <div style={{ display: "flex", flexDirection: "column", gap: 16, alignItems: "center" }}>
                <div style={{ fontFamily: SANS, fontSize: 22, fontWeight: 800, color: BRAND.muted, letterSpacing: "0.1em" }}>
                  A LIST
                </div>
                <ListSide />
              </div>
            </Rise>
          </AbsoluteFill>
          <AbsoluteFill style={{ left: "50%", width: "50%", alignItems: "center", justifyContent: "center" }}>
            <Rise delay={10}>
              <div style={{ display: "flex", flexDirection: "column", gap: 16, alignItems: "center" }}>
                <div style={{ fontFamily: SANS, fontSize: 22, fontWeight: 800, color: BRAND.goldLight, letterSpacing: "0.1em" }}>
                  A MAP
                </div>
                <MapSide />
              </div>
            </Rise>
          </AbsoluteFill>
        </AbsoluteFill>
      </Sequence>

      <Sequence from={L[2]} durationInFrames={WALK_TOTAL - L[2]}>
        <Center gap={26}>
          <Rise delay={0}>
            <Img src={staticFile("logo-mark.png")} style={{ width: 68, height: 68 }} />
          </Rise>
          <LogoLockup delay={6} />
          <CTAButton delay={16}>Apply · $150/mo for life</CTAButton>
        </Center>
      </Sequence>

      <Subtitles captions={CAPTIONS} />
    </NavyBG>
  );
};
