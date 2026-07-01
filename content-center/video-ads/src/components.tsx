import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { BRAND, NODES, SIZE } from "./brand";
import { fontFamily as serif } from "@remotion/google-fonts/Fraunces";
import { fontFamily as sans } from "@remotion/google-fonts/Inter";

export const SERIF = serif;
export const SANS = sans;

/** Deep navy background with a subtle radial glow + faint web threads (tasteful, not spidery). */
export const NavyBG: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(120% 120% at 50% 20%, ${BRAND.navy2} 0%, ${BRAND.navy} 55%, ${BRAND.charcoal} 100%)`,
        fontFamily: SANS,
      }}
    >
      <WebThreads />
      {children}
    </AbsoluteFill>
  );
};

/** Faint gold radial threads — abstract network motif, NEVER a literal spider. */
const WebThreads: React.FC = () => {
  const cx = SIZE / 2;
  const cy = SIZE / 2;
  return (
    <AbsoluteFill style={{ opacity: 0.1 }}>
      <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`}>
        {Array.from({ length: 16 }).map((_, i) => {
          const a = (i / 16) * Math.PI * 2;
          return (
            <line
              key={i}
              x1={cx}
              y1={cy}
              x2={cx + Math.cos(a) * 900}
              y2={cy + Math.sin(a) * 900}
              stroke={BRAND.gold}
              strokeWidth={1}
            />
          );
        })}
        {[220, 380, 520].map((r) => (
          <circle key={r} cx={cx} cy={cy} r={r} fill="none" stroke={BRAND.gold} strokeWidth={1} />
        ))}
      </svg>
    </AbsoluteFill>
  );
};

/** A word/line that springs up and fades in at a given local frame offset. */
export const Rise: React.FC<{
  children: React.ReactNode;
  delay?: number;
  style?: React.CSSProperties;
}> = ({ children, delay = 0, style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 200 } });
  const y = interpolate(s, [0, 1], [40, 0]);
  const opacity = interpolate(frame - delay, [0, 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <div style={{ transform: `translateY(${y}px)`, opacity, ...style }}>{children}</div>
  );
};

/** Big serif headline. */
export const Headline: React.FC<{
  children: React.ReactNode;
  color?: string;
  size?: number;
  delay?: number;
}> = ({ children, color = BRAND.white, size = 96, delay = 0 }) => (
  <Rise delay={delay}>
    <div
      style={{
        fontFamily: SERIF,
        fontWeight: 600,
        fontSize: size,
        lineHeight: 1.04,
        color,
        textAlign: "center",
        letterSpacing: "-0.01em",
        padding: "0 90px",
      }}
    >
      {children}
    </div>
  </Rise>
);

export const Eyebrow: React.FC<{ children: React.ReactNode; delay?: number }> = ({
  children,
  delay = 0,
}) => (
  <Rise delay={delay}>
    <div
      style={{
        fontFamily: SANS,
        fontWeight: 800,
        fontSize: 28,
        letterSpacing: "0.22em",
        color: BRAND.goldLight,
        textTransform: "uppercase",
        textAlign: "center",
      }}
    >
      {children}
    </div>
  </Rise>
);

/** The Opportunity Web — YOUR MISSION hub with 6 nodes connecting via gold threads. */
export const OrbWeb: React.FC<{ progress: number }> = ({ progress }) => {
  const cx = SIZE / 2;
  const cy = SIZE / 2;
  const R = 320;
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`}>
        {NODES.map((_, i) => {
          const a = (i / NODES.length) * Math.PI * 2 - Math.PI / 2;
          const nx = cx + Math.cos(a) * R;
          const ny = cy + Math.sin(a) * R;
          const drawn = interpolate(progress, [i / 8, i / 8 + 0.25], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return (
            <line
              key={`l${i}`}
              x1={cx}
              y1={cy}
              x2={cx + (nx - cx) * drawn}
              y2={cy + (ny - cy) * drawn}
              stroke={BRAND.gold}
              strokeWidth={3}
              strokeOpacity={0.7}
            />
          );
        })}
        {NODES.map((label, i) => {
          const a = (i / NODES.length) * Math.PI * 2 - Math.PI / 2;
          const nx = cx + Math.cos(a) * R;
          const ny = cy + Math.sin(a) * R;
          const pop = interpolate(progress, [i / 8 + 0.15, i / 8 + 0.4], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          const w = 12 + label.length * 15.5;
          return (
            <g key={`n${i}`} opacity={pop} transform={`translate(${nx} ${ny}) scale(${pop})`}>
              <rect x={-w / 2} y={-26} width={w} height={52} rx={26} fill={BRAND.navy2} stroke={BRAND.gold} strokeOpacity={0.6} strokeWidth={2} />
              <text x={0} y={7} fill={BRAND.goldLight} fontSize={24} fontWeight={800} fontFamily={SANS} textAnchor="middle" letterSpacing="1.5">
                {label}
              </text>
            </g>
          );
        })}
        <circle cx={cx} cy={cy} r={92} fill={BRAND.navy} stroke={BRAND.gold} strokeWidth={3} />
        <text x={cx} y={cy - 6} fill={BRAND.white} fontSize={26} fontWeight={800} fontFamily={SANS} textAnchor="middle">
          YOUR
        </text>
        <text x={cx} y={cy + 26} fill={BRAND.white} fontSize={26} fontWeight={800} fontFamily={SANS} textAnchor="middle">
          MISSION
        </text>
      </svg>
    </AbsoluteFill>
  );
};

/** A tinted "bubble" card matching the product UI (teal = strength, gold = gap). */
export const BubbleCard: React.FC<{
  label: string;
  value: string;
  tone: "teal" | "gold";
  delay?: number;
}> = ({ label, value, tone, delay = 0 }) => {
  const bg = tone === "teal" ? BRAND.tealSoft : BRAND.goldSoft;
  const border = tone === "teal" ? BRAND.teal : BRAND.gold;
  const labelColor = tone === "teal" ? BRAND.teal : "#8a5b00";
  return (
    <Rise delay={delay}>
      <div
        style={{
          background: BRAND.white,
          borderRadius: 22,
          padding: "26px 30px",
          width: 720,
          boxShadow: "0 20px 60px rgba(0,0,0,0.35)",
        }}
      >
        <div
          style={{
            fontFamily: SANS,
            fontWeight: 800,
            fontSize: 22,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            color: labelColor,
            marginBottom: 12,
          }}
        >
          {label}
        </div>
        <div
          style={{
            background: bg,
            border: `2px solid ${border}`,
            borderRadius: 16,
            padding: "16px 20px",
            fontFamily: SANS,
            fontSize: 30,
            fontWeight: 500,
            color: BRAND.navy,
          }}
        >
          {value}
        </div>
      </div>
    </Rise>
  );
};

/** Logo lockup + tagline. */
export const LogoLockup: React.FC<{ delay?: number }> = ({ delay = 0 }) => (
  <Rise delay={delay} style={{ textAlign: "center" }}>
    <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 74, color: BRAND.white }}>
      Anansi Atlas
    </div>
    <div
      style={{
        fontFamily: SANS,
        fontWeight: 800,
        fontSize: 28,
        letterSpacing: "0.16em",
        textTransform: "uppercase",
        color: BRAND.goldLight,
        marginTop: 8,
      }}
    >
      The Web of Opportunity
    </div>
  </Rise>
);

/** Gold pill CTA button. */
export const CTAButton: React.FC<{ children: React.ReactNode; delay?: number }> = ({
  children,
  delay = 0,
}) => (
  <Rise delay={delay}>
    <div
      style={{
        display: "inline-block",
        background: BRAND.gold,
        color: "#171007",
        fontFamily: SANS,
        fontWeight: 900,
        fontSize: 34,
        padding: "22px 46px",
        borderRadius: 999,
      }}
    >
      {children}
    </div>
  </Rise>
);
