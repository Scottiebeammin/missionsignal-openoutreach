import React from "react";
import {
  AbsoluteFill,
  Img,
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
export const NavyBG: React.FC<{ children?: React.ReactNode; w?: number; h?: number }> = ({
  children,
  w = SIZE,
  h = SIZE,
}) => {
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(120% 120% at 50% 20%, ${BRAND.navy2} 0%, ${BRAND.navy} 55%, ${BRAND.charcoal} 100%)`,
        fontFamily: SANS,
      }}
    >
      <WebThreads w={w} h={h} />
      {children}
    </AbsoluteFill>
  );
};

/** Faint gold radial threads — abstract network motif, NEVER a literal spider. */
const WebThreads: React.FC<{ w: number; h: number }> = ({ w, h }) => {
  const cx = w / 2;
  const cy = h / 2;
  return (
    <AbsoluteFill style={{ opacity: 0.1 }}>
      <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
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

/** A timed subtitle segment (global composition frames). */
export type Caption = { text: string; from: number; duration: number };

/** Bottom caption bar — synced to the VO, readable on autoplay-muted LinkedIn. */
export const Subtitles: React.FC<{ captions: Caption[] }> = ({ captions }) => {
  const frame = useCurrentFrame();
  const active = captions.find((c) => frame >= c.from && frame < c.from + c.duration);
  if (!active) return null;
  const local = frame - active.from;
  const opacity = interpolate(local, [0, 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 54 }}>
      <div
        style={{
          maxWidth: 900,
          opacity,
          background: "rgba(6,12,26,0.74)",
          border: "1px solid rgba(212,160,23,0.35)",
          borderRadius: 14,
          padding: "16px 28px",
          fontFamily: SANS,
          fontSize: 34,
          fontWeight: 600,
          color: BRAND.white,
          textAlign: "center",
          lineHeight: 1.25,
        }}
      >
        {active.text}
      </div>
    </AbsoluteFill>
  );
};

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

/** Section eyebrow bar used to orient a long walkthrough ("02 / 07 — Opportunity Web"). */
export const SectionMarker: React.FC<{ index: string; total: string; title: string; delay?: number }> = ({
  index,
  total,
  title,
  delay = 0,
}) => (
  <Rise delay={delay} style={{ position: "absolute", top: 60, left: 0, right: 0, textAlign: "center" }}>
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 14,
        fontFamily: SANS,
        fontWeight: 800,
        fontSize: 22,
        letterSpacing: "0.12em",
        color: BRAND.goldLight,
        textTransform: "uppercase",
        border: "1px solid rgba(212,160,23,0.4)",
        borderRadius: 999,
        padding: "8px 20px",
      }}
    >
      <span style={{ opacity: 0.7 }}>
        {index} / {total}
      </span>
      <span style={{ width: 1, height: 16, background: "rgba(212,160,23,0.4)" }} />
      {title}
    </div>
  </Rise>
);

/** A single feature highlight card — icon glyph, title, one-line benefit. Used in fast-cut reels. */
export const FeatureCard: React.FC<{
  glyph: string;
  title: string;
  benefit: string;
  delay?: number;
}> = ({ glyph, title, benefit, delay = 0 }) => (
  <Rise delay={delay}>
    <div
      style={{
        width: 780,
        background: "rgba(255,255,255,0.04)",
        border: "1px solid rgba(212,160,23,0.3)",
        borderRadius: 20,
        padding: "28px 34px",
        display: "flex",
        alignItems: "center",
        gap: 26,
      }}
    >
      <div
        style={{
          width: 64,
          height: 64,
          flexShrink: 0,
          borderRadius: 16,
          background: BRAND.gold,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 32,
        }}
      >
        {glyph}
      </div>
      <div>
        <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 36, color: BRAND.white, marginBottom: 4 }}>
          {title}
        </div>
        <div style={{ fontFamily: SANS, fontSize: 24, fontWeight: 500, color: BRAND.muted }}>{benefit}</div>
      </div>
    </div>
  </Rise>
);

/** A checked benefit line — used for "join the family" / what-you-get lists. */
export const CheckLine: React.FC<{ text: string; delay?: number; big?: boolean }> = ({
  text,
  delay = 0,
  big = false,
}) => (
  <Rise delay={delay}>
    <div style={{ display: "flex", alignItems: "center", gap: 18, width: 820 }}>
      <div style={{ color: BRAND.gold, fontSize: big ? 44 : 34, fontWeight: 900 }}>✓</div>
      <div
        style={{
          fontFamily: SANS,
          fontSize: big ? 38 : 30,
          fontWeight: 600,
          color: BRAND.white,
          lineHeight: 1.3,
        }}
      >
        {text}
      </div>
    </div>
  </Rise>
);

/** Thin progress rail across the very top — orients a viewer during a long-form (5-min) walkthrough. */
export const ProgressRail: React.FC<{ totalFrames: number }> = ({ totalFrames }) => {
  const frame = useCurrentFrame();
  const pct = Math.min(100, (frame / totalFrames) * 100);
  return (
    <AbsoluteFill style={{ justifyContent: "flex-start" }}>
      <div style={{ height: 5, width: "100%", background: "rgba(255,255,255,0.08)" }}>
        <div style={{ height: "100%", width: `${pct}%`, background: BRAND.gold }} />
      </div>
    </AbsoluteFill>
  );
};

/** Browser-chrome frame around a real product screenshot, with cinematic Ken-Burns pan/zoom. */
export const ScreenshotPanel: React.FC<{
  src: string;
  label?: string;
  zoomFrom?: number;
  zoomTo?: number;
  panX?: [number, number];
  panY?: [number, number];
  durationInFrames: number;
  width?: number;
}> = ({ src, label, zoomFrom = 1, zoomTo = 1.12, panX = [0, 0], panY = [0, -4], durationInFrames, width = 940 }) => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, durationInFrames], [zoomFrom, zoomTo], { extrapolateRight: "clamp" });
  const tx = interpolate(frame, [0, durationInFrames], panX, { extrapolateRight: "clamp" });
  const ty = interpolate(frame, [0, durationInFrames], panY, { extrapolateRight: "clamp" });
  const entrance = spring({ frame, fps: 30, config: { damping: 200 } });
  const opacity = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: "clamp" });
  const riseY = interpolate(entrance, [0, 1], [30, 0]);

  return (
    <div
      style={{
        width,
        opacity,
        transform: `translateY(${riseY}px)`,
        borderRadius: 18,
        overflow: "hidden",
        background: "#1b2a4a",
        boxShadow: "0 40px 100px rgba(0,0,0,0.5), 0 0 0 1px rgba(212,160,23,0.25)",
      }}
    >
      {/* browser chrome bar */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 16px", background: "#16233f" }}>
        <div style={{ display: "flex", gap: 7 }}>
          <div style={{ width: 11, height: 11, borderRadius: 999, background: "#e5695b" }} />
          <div style={{ width: 11, height: 11, borderRadius: 999, background: "#e5b93f" }} />
          <div style={{ width: 11, height: 11, borderRadius: 999, background: "#57b76b" }} />
        </div>
        <div
          style={{
            marginLeft: 10,
            padding: "4px 14px",
            borderRadius: 999,
            background: "rgba(255,255,255,0.06)",
            color: BRAND.muted,
            fontFamily: SANS,
            fontSize: 13,
            fontWeight: 700,
          }}
        >
          {label || "anansiatlas.com"}
        </div>
      </div>
      {/* screenshot with Ken Burns motion */}
      <div style={{ position: "relative", width: "100%", aspectRatio: "16 / 10", overflow: "hidden" }}>
        <Img
          src={src}
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            objectFit: "cover",
            objectPosition: "top",
            transform: `scale(${scale}) translate(${tx}px, ${ty}px)`,
            transformOrigin: "top center",
          }}
        />
      </div>
    </div>
  );
};

/** Genuine motion-graphics logo reveal: gold threads converge from the edges into the wordmark. */
export const AnimatedLogoReveal: React.FC<{ delay?: number }> = ({ delay = 0 }) => {
  const frame = useCurrentFrame();
  const local = Math.max(0, frame - delay);
  const converge = interpolate(local, [0, 40], [0, 1], { extrapolateRight: "clamp" });
  const textIn = interpolate(local, [30, 55], [0, 1], { extrapolateRight: "clamp" });
  const textY = interpolate(textIn, [0, 1], [20, 0]);
  const shimmerX = interpolate(local, [50, 100], [-300, 900], { extrapolateRight: "clamp" });
  const cx = SIZE / 2;
  const cy = SIZE / 2;

  // 8 threads converging from off-screen points toward the center.
  const threads = Array.from({ length: 8 }, (_, i) => {
    const a = (i / 8) * Math.PI * 2;
    const startR = 620;
    const sx = cx + Math.cos(a) * startR;
    const sy = cy + Math.sin(a) * startR;
    return { sx, sy };
  });

  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} style={{ position: "absolute" }}>
        {threads.map((t, i) => {
          const x = interpolate(converge, [0, 1], [t.sx, cx]);
          const y = interpolate(converge, [0, 1], [t.sy, cy]);
          const op = interpolate(converge, [0, 0.9, 1], [0, 0.9, 0]);
          return <line key={i} x1={t.sx} y1={t.sy} x2={x} y2={y} stroke={BRAND.gold} strokeWidth={2} opacity={op} />;
        })}
        <circle cx={cx} cy={cy} r={interpolate(converge, [0.8, 1], [0, 40])} fill={BRAND.gold} opacity={interpolate(converge, [0.8, 1], [0, 0.25])} />
      </svg>
      <div style={{ position: "relative", overflow: "hidden", textAlign: "center", opacity: textIn, transform: `translateY(${textY}px)` }}>
        <div style={{ position: "relative", fontFamily: SERIF, fontWeight: 600, fontSize: 92, color: BRAND.white }}>
          Anansi Atlas
          <div
            style={{
              position: "absolute",
              top: 0,
              left: shimmerX,
              width: 120,
              height: "100%",
              background: "linear-gradient(100deg, transparent, rgba(255,255,255,0.55), transparent)",
              transform: "skewX(-20deg)",
            }}
          />
        </div>
        <div
          style={{
            fontFamily: SANS,
            fontWeight: 800,
            fontSize: 30,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            color: BRAND.goldLight,
            marginTop: 10,
          }}
        >
          The Web of Opportunity
        </div>
      </div>
    </AbsoluteFill>
  );
};

/**
 * Scene dissolve overlay — a brief dip-to-navy at each scene boundary, creating a smooth
 * cross-dissolve WITHOUT restructuring Sequences (so global-frame subtitle timing is preserved).
 * Add ONE of these per composition (below <Subtitles> so captions stay on top), passing the
 * scene start frames. Timing-safe alternative to @remotion/transitions' TransitionSeries, which
 * would shift the timeline and desync fixed-frame captions.
 */
export const SceneDissolve: React.FC<{ boundaries: number[]; fade?: number; peak?: number }> = ({
  boundaries,
  fade = 8,
  peak = 0.9,
}) => {
  const frame = useCurrentFrame();
  let op = 0;
  for (const b of boundaries) {
    op = Math.max(
      op,
      interpolate(frame, [b - fade, b, b + fade], [0, peak, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      }),
    );
  }
  if (op <= 0) return null;
  return <AbsoluteFill style={{ background: BRAND.navy, opacity: op, pointerEvents: "none" }} />;
};
