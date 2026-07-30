import React from "react";
import {
  AbsoluteFill,
  continueRender,
  delayRender,
  Img,
  interpolate,
  OffthreadVideo,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Lottie, LottieAnimationData } from "@remotion/lottie";
import { gsap } from "gsap";
import { BRAND, NODES, SIZE } from "./brand";
import { fontFamily as serif } from "@remotion/google-fonts/Fraunces";
import { fontFamily as sans } from "@remotion/google-fonts/Inter";

export const SERIF = serif;
export const SANS = sans;

/**
 * Deep navy background with a subtle radial glow + faint web threads (tasteful, not spidery).
 *
 * `threads` scales the radial thread layer (1 = the established look, 0 = off). The vision
 * film dials this down in its acentric constellation scenes, where a centred radial hub
 * fights the drifting NodeField and reads closer to a literal web than we want.
 */
export const NavyBG: React.FC<{
  children?: React.ReactNode;
  w?: number;
  h?: number;
  threads?: number;
}> = ({ children, w = SIZE, h = SIZE, threads = 1 }) => {
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(120% 120% at 50% 20%, ${BRAND.navy2} 0%, ${BRAND.navy} 55%, ${BRAND.charcoal} 100%)`,
        fontFamily: SANS,
      }}
    >
      {threads > 0 ? <WebThreads w={w} h={h} strength={threads} /> : null}
      {children}
    </AbsoluteFill>
  );
};

/** Faint gold radial threads — abstract network motif, NEVER a literal spider. */
const WebThreads: React.FC<{ w: number; h: number; strength?: number }> = ({ w, h, strength = 1 }) => {
  const cx = w / 2;
  const cy = h / 2;
  return (
    <AbsoluteFill style={{ opacity: 0.1 * strength }}>
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

/** The same browser-chrome screenshot as ScreenshotPanel, set into a CSS laptop mockup (screen
 *  bezel + hinge + keyboard deck) instead of floating flat. Self-contained — no environment
 *  photo required (unlike LaptopFrame, which needs an envSrc office shot). */
export const LaptopScreenshotPanel: React.FC<{
  src: string;
  label?: string;
  zoomFrom?: number;
  zoomTo?: number;
  panX?: [number, number];
  panY?: [number, number];
  durationInFrames: number;
  width?: number;
  delay?: number;
  glow?: string;
}> = ({ src, label, zoomFrom = 1, zoomTo = 1.12, panX = [0, 0], panY = [0, -4], durationInFrames, width = 900, delay = 0, glow }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = interpolate(frame, [0, durationInFrames], [zoomFrom, zoomTo], { extrapolateRight: "clamp" });
  const tx = interpolate(frame, [0, durationInFrames], panX, { extrapolateRight: "clamp" });
  const ty = interpolate(frame, [0, durationInFrames], panY, { extrapolateRight: "clamp" });
  const s = spring({ frame: frame - delay, fps, config: { damping: 16, mass: 0.9 } });
  const entranceScale = interpolate(s, [0, 1], [0.88, 1]);
  const opacity = interpolate(frame - delay, [0, 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const screenH = (width * 10) / 16 + 44; // 16:10 content + browser chrome bar

  return (
    <div style={{ position: "relative", opacity, transform: `scale(${entranceScale})`, display: "flex", flexDirection: "column", alignItems: "center" }}>
      {/* colorful under-glow */}
      <div
        style={{
          position: "absolute",
          inset: -70,
          borderRadius: 60,
          background: glow ?? "radial-gradient(ellipse at 30% 15%, rgba(212,160,23,0.32) 0%, rgba(58,108,200,0.24) 45%, transparent 75%)",
          filter: "blur(50px)",
        }}
      />
      {/* laptop screen bezel */}
      <div
        style={{
          position: "relative",
          width,
          height: screenH,
          borderRadius: "16px 16px 5px 5px",
          background: "linear-gradient(160deg, #232d44 0%, #0a0f1c 100%)",
          border: "1px solid rgba(255,255,255,0.2)",
          boxShadow: "0 40px 100px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.18)",
          padding: 14,
        }}
      >
        {/* front camera dot */}
        <div style={{ position: "absolute", top: 5, left: "50%", width: 5, height: 5, borderRadius: 999, background: "#2a3550", transform: "translateX(-50%)" }} />
        <div style={{ width: "100%", height: "100%", borderRadius: 8, overflow: "hidden", background: "#1b2a4a" }}>
          {/* browser chrome bar */}
          <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 14px", background: "#16233f" }}>
            <div style={{ display: "flex", gap: 6 }}>
              <div style={{ width: 9, height: 9, borderRadius: 999, background: "#e5695b" }} />
              <div style={{ width: 9, height: 9, borderRadius: 999, background: "#e5b93f" }} />
              <div style={{ width: 9, height: 9, borderRadius: 999, background: "#57b76b" }} />
            </div>
            <div
              style={{
                marginLeft: 8,
                padding: "3px 12px",
                borderRadius: 999,
                background: "rgba(255,255,255,0.06)",
                color: BRAND.muted,
                fontFamily: SANS,
                fontSize: 11,
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
      </div>
      {/* hinge */}
      <div style={{ width: width * 0.97, height: 6, background: "linear-gradient(180deg, #0a0f1c 0%, #1b2333 100%)" }} />
      {/* keyboard deck */}
      <div
        style={{
          position: "relative",
          width: width * 1.1,
          height: 18,
          borderRadius: "2px 2px 12px 12px",
          background: "linear-gradient(180deg, #2a3348 0%, #141a2b 55%, #0d1120 100%)",
          boxShadow: "0 16px 34px rgba(0,0,0,0.5)",
        }}
      >
        <div
          style={{
            position: "absolute",
            left: "50%",
            bottom: -1,
            transform: "translateX(-50%)",
            width: width * 0.16,
            height: 6,
            borderRadius: "0 0 8px 8px",
            background: "rgba(0,0,0,0.35)",
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

/**
 * B-roll — a generated video clip (ElevenLabs Veo / any MP4 in public/broll/) played full-frame
 * with a navy→gold brand overlay so it matches the look and any text on top stays readable.
 * Muted by default (our VO is the audio). Use for cinematic cold-opens / cutaways that
 * screen-recordings can't provide (e.g. a nonprofit leader at a laptop).
 */
export const BRoll: React.FC<{
  src: string;
  overlay?: number;
  children?: React.ReactNode;
  fade?: number;
  durationInFrames?: number;
}> = ({ src, overlay = 0.45, children, fade = 12, durationInFrames }) => {
  const frame = useCurrentFrame();
  const opIn = interpolate(frame, [0, fade], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const opOut = durationInFrames
    ? interpolate(frame, [durationInFrames - fade, durationInFrames], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    : 1;
  return (
    <AbsoluteFill style={{ opacity: Math.min(opIn, opOut) }}>
      <OffthreadVideo src={src} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      <AbsoluteFill
        style={{
          background: `linear-gradient(180deg, rgba(13,27,61,${overlay * 0.55}) 0%, rgba(13,27,61,${overlay}) 60%, rgba(13,27,61,${Math.min(1, overlay + 0.3)}) 100%)`,
        }}
      />
      {children}
    </AbsoluteFill>
  );
};

/**
 * LaptopFrame — a real product screenshot composited onto a laptop screen sitting in a
 * real environment (office B-roll), instead of a "floating" browser-chrome card. If no
 * environment clip/photo is provided yet, falls back to ScreenshotPanel so nothing breaks
 * while you're still generating B-roll.
 *
 * screenRect is in PERCENT of the frame (0-100) — the four corners of the laptop's screen
 * in your specific B-roll shot. Defaults assume a front-facing, mostly-flat laptop centered
 * in frame (matches the prompt in ELEVENLABS-ASSETS.md). Once you generate the real clip,
 * tell me and I'll nudge these numbers to match exactly.
 */
export const LaptopFrame: React.FC<{
  src: string; // the screenshot to show ON the laptop screen
  envSrc?: string | null; // public/broll/*.mp4 or .jpg — the laptop-in-office shot
  screenRect?: { top: number; left: number; width: number; height: number };
  durationInFrames: number;
  fallbackLabel?: string;
}> = ({ src, envSrc, screenRect = { top: 21, left: 30, width: 40, height: 30 }, durationInFrames, fallbackLabel }) => {
  const frame = useCurrentFrame();
  if (!envSrc) {
    return <ScreenshotPanel src={src} label={fallbackLabel} durationInFrames={durationInFrames} />;
  }
  const isVideo = /\.(mp4|mov|webm)$/i.test(envSrc);
  const scale = interpolate(frame, [0, durationInFrames], [1, 1.05], { extrapolateRight: "clamp" });
  const opacity = interpolate(frame, [0, 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ opacity }}>
      {isVideo ? (
        <OffthreadVideo src={envSrc} muted style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${scale})` }} />
      ) : (
        <Img src={envSrc} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${scale})` }} />
      )}
      {/* screenshot composited into the laptop's screen region, slight perspective tilt */}
      <div
        style={{
          position: "absolute",
          top: `${screenRect.top}%`,
          left: `${screenRect.left}%`,
          width: `${screenRect.width}%`,
          height: `${screenRect.height}%`,
          overflow: "hidden",
          borderRadius: 4,
          transform: "perspective(900px) rotateX(2deg)",
          boxShadow: "0 0 40px rgba(0,0,0,0.35) inset",
        }}
      >
        <Img src={src} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "top" }} />
      </div>
    </AbsoluteFill>
  );
};

/**
 * LottieAsset — drop-in wrapper for a Lottie JSON (public/lottie/*.json) at a fixed
 * position/size. Use for payoff-moment accents: a shine sweep, checkmark pop, or
 * particle burst on a CTA. Renders nothing if the file hasn't been generated/added
 * yet (graceful, same optional-asset pattern as BRoll/ScreenshotPanel).
 *
 *   <LottieAsset src={staticFile("lottie/shine-sweep.json")} width={400} loop={false} />
 */
export const LottieAsset: React.FC<{
  src: string;
  width?: number;
  height?: number;
  loop?: boolean;
  style?: React.CSSProperties;
}> = ({ src, width = 400, height = 400, loop = false, style }) => {
  const [animationData, setAnimationData] = React.useState<LottieAnimationData | null>(null);
  const [handle] = React.useState(() => delayRender(`loading Lottie asset ${src}`));

  React.useEffect(() => {
    fetch(src)
      .then((res) => res.json())
      .then((data) => {
        setAnimationData(data);
        continueRender(handle);
      })
      .catch((err) => {
        // Asset not present yet (not generated/dropped in) — fail gracefully, don't block render.
        // If you expect this asset to exist, check: (1) the file is really at public/<src>,
        // (2) it's valid Bodymovin/Lottie JSON — every keyframe in an animated ("a":1) property
        // needs "i"/"o" easing handles except the last one; lottie-web fails silently otherwise.
        console.warn("LottieAsset: no asset at", src, "— rendering nothing.", err);
        continueRender(handle);
      });
  }, [src, handle]);

  if (!animationData) return null;
  return (
    <div style={{ width, height, ...style }}>
      <Lottie animationData={animationData} loop={loop} style={{ width: "100%", height: "100%" }} />
    </div>
  );
};

/**
 * GsapRise — same job as `Rise`, but driven by a GSAP timeline instead of Remotion's
 * spring(). Demonstrates the REQUIRED integration pattern for GSAP inside Remotion:
 * the timeline is created `paused: true` and manually seeked via `tl.progress()` on
 * every frame — GSAP's own ticker (real wall-clock autoplay) must NEVER run here, or
 * rendering becomes non-deterministic. See BRAND-TEMPLATE.md "GSAP in Remotion" note.
 * Gives access to GSAP's richer eases (back/elastic) for the anticipation+overshoot+
 * settle feel the Pro Prompts guide recommends over plain linear/spring motion.
 */
export const GsapRise: React.FC<{
  children: React.ReactNode;
  delay?: number;
  durationInFrames?: number;
  ease?: string;
  style?: React.CSSProperties;
}> = ({ children, delay = 0, durationInFrames = 24, ease = "back.out(1.7)", style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const ref = React.useRef<HTMLDivElement>(null);
  const tlRef = React.useRef<import("gsap").core.Timeline | null>(null);

  // IMPORTANT: creation + the first seek must happen in the SAME synchronous pass
  // (useLayoutEffect, before paint). Splitting creation into useEffect (which fires
  // AFTER paint) left `.from()`'s starting state (opacity:0) captured on the very
  // first frame Remotion renders — a real bug caught via CapabilityTest, 2026-07-01.
  React.useLayoutEffect(() => {
    if (!ref.current) return;
    if (!tlRef.current) {
      // paused: true — we drive it manually below; GSAP's ticker never runs.
      tlRef.current = gsap.timeline({ paused: true }).from(ref.current, {
        y: 44,
        opacity: 0,
        duration: durationInFrames / fps,
        ease,
      });
    }
    const localFrame = Math.max(0, frame - delay);
    tlRef.current.time(localFrame / fps); // seek mode — deterministic, frame-exact
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [frame, delay, fps]);

  React.useEffect(() => {
    return () => {
      tlRef.current?.kill();
      tlRef.current = null;
    };
  }, []);

  return (
    <div ref={ref} style={style}>
      {children}
    </div>
  );
};

/**
 * DeviceFrame — a screenshot presented inside a modern tablet/iPad-style device
 * (dark rounded bezel, metallic edge light, floating drop shadow, colorful under-glow,
 * and a slow light-reflection sweep across the glass). Per the Pinterest device ref:
 * the product should look like it's ON a real device, not floating as a browser card.
 */
export const DeviceFrame: React.FC<{
  src: string;
  width?: number;
  durationInFrames: number;
  delay?: number;
  glow?: string; // CSS gradient for the colorful under-glow
}> = ({ src, width = 760, durationInFrames, delay = 0, glow }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 16, mass: 0.9 } });
  const scale = interpolate(s, [0, 1], [0.82, 1]);
  const opacity = interpolate(frame - delay, [0, 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const sweep = interpolate(frame, [delay + 20, delay + Math.min(durationInFrames - 10, 110)], [-30, 130], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const h = width * 0.68;
  return (
    <div style={{ position: "relative", opacity, transform: `scale(${scale})` }}>
      {/* colorful under-glow */}
      <div
        style={{
          position: "absolute",
          inset: -60,
          borderRadius: 60,
          background: glow ?? "radial-gradient(ellipse at 30% 20%, rgba(212,160,23,0.4) 0%, rgba(15,118,110,0.3) 45%, rgba(196,106,61,0.25) 75%, transparent 100%)",
          filter: "blur(46px)",
        }}
      />
      {/* device body */}
      <div
        style={{
          position: "relative",
          width,
          height: h,
          borderRadius: 30,
          background: "linear-gradient(145deg, #1b2333 0%, #0a0f1c 100%)",
          border: "1px solid rgba(255,255,255,0.22)",
          boxShadow: "0 40px 90px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.18)",
          padding: 16,
        }}
      >
        <div style={{ position: "relative", width: "100%", height: "100%", borderRadius: 16, overflow: "hidden", background: "#0b1428" }}>
          <Img src={src} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "top" }} />
          {/* glass reflection sweep */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              background: `linear-gradient(115deg, transparent ${sweep - 14}%, rgba(255,255,255,0.14) ${sweep}%, transparent ${sweep + 14}%)`,
            }}
          />
        </div>
        {/* front camera dot */}
        <div style={{ position: "absolute", top: 7, left: "50%", width: 6, height: 6, borderRadius: 999, background: "#2a3550", transform: "translateX(-50%)" }} />
      </div>
    </div>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
// EXECUTIVE VISION FILM SYSTEM
// Added 2026-07-29 for oneoffs/AnansiVisionFilm.tsx (Orange County FL screening).
//
// Every component below is a PURE FUNCTION of useCurrentFrame() — no GSAP ticker,
// no Three.js Clock, no DOM measurement, no Math.random. Remotion renders frames
// out of order, so anything else is non-deterministic (BRAND-TEMPLATE.md §0d).
//
// Motion register for this system: motion GUIDES attention, it never performs.
// Cubic ease-out on entrances, ease-in on exits, no spring overshoot, no bounce.
// Everything animates fully IN and fully OUT before its clip ends (§0c rule #1).
// ═════════════════════════════════════════════════════════════════════════════

/** Cubic ease-out — the entrance curve used across the whole vision-film system. */
const easeOut3 = (p: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, p)), 3);
/** Quadratic ease-in — the exit curve. Slower to leave than to arrive. */
const easeIn2 = (p: number) => Math.pow(Math.min(1, Math.max(0, p)), 2);
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

/**
 * Seeded PRNG — deterministic scatter with no Math.random in a render path.
 * Promoted out of oneoffs/WebOfOpportunityFilm.tsx so NodeField/ActBridge share
 * the exact generator the approved launch film used.
 */
export function makePrng(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

/**
 * Gradient-mesh atmosphere — four slow drifting colour blobs behind everything.
 * Promoted out of oneoffs/WebOfOpportunityFilm.tsx (was module-private there).
 * Palette is film-register only: gold / cream / blue on navy. No teal, no rose.
 */
export const GradientMesh: React.FC<{ opacity?: number }> = ({ opacity = 0.5 }) => {
  const frame = useCurrentFrame();
  const t = frame / 30;
  const blobs = [
    { color: "222,168,28", x: 22 + Math.sin(t * 0.21) * 8, y: 24 + Math.cos(t * 0.17) * 7, r: 38 },
    { color: "58,108,200", x: 76 + Math.sin(t * 0.16 + 2) * 9, y: 68 + Math.cos(t * 0.19 + 1) * 8, r: 42 },
    { color: "243,221,140", x: 55 + Math.sin(t * 0.13 + 4) * 10, y: 30 + Math.cos(t * 0.15 + 3) * 9, r: 30 },
    { color: "40,78,160", x: 34 + Math.sin(t * 0.18 + 5.5) * 9, y: 74 + Math.cos(t * 0.14 + 4.5) * 7, r: 32 },
  ];
  return (
    <AbsoluteFill style={{ opacity, filter: "blur(70px)" }}>
      {blobs.map((b, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: `${b.x - b.r / 2}%`,
            top: `${b.y - b.r / 2}%`,
            width: `${b.r}%`,
            height: `${b.r}%`,
            borderRadius: "50%",
            background: `radial-gradient(circle, rgba(${b.color},0.9) 0%, rgba(${b.color},0) 70%)`,
          }}
        />
      ))}
    </AbsoluteFill>
  );
};

export type HyperFrameWord = string | { word: string; hold?: number; color?: string };

/** Total frame length of a HyperFrames run — so the beat map never has to guess. */
export const hyperFramesLength = (n: number, hold = 42, enter = 16, exit = 14, gap = 8) =>
  n * (enter + hold + exit) + Math.max(0, n - 1) * gap;

/**
 * HYPERFRAMES — single-word cinematic typography. One word owns the frame, enters by
 * contracting its own letter-spacing (not by sliding), holds with a near-imperceptible
 * tracking drift so it is never a static freeze, and fully exits before the next word
 * begins. The film's connective typographic device; recurs once per act.
 *
 * Deliberately NOT spring-driven — `Rise`/`GsapRise` overshoot, and this register bans
 * bouncy easing. Renders nothing outside its slots, so it is free to leave mounted.
 */
export const HyperFrames: React.FC<{
  words: HyperFrameWord[];
  at?: number;
  hold?: number;
  enter?: number;
  exit?: number;
  gap?: number;
  size?: number;
  face?: "serif" | "sans";
  color?: string;
  outline?: boolean;
  trackFrom?: number;
  trackTo?: number;
  y?: number;
}> = ({
  words,
  at = 0,
  hold = 42,
  enter = 16,
  exit = 14,
  gap = 8,
  size = 168,
  face = "serif",
  color = BRAND.white,
  outline = false,
  trackFrom = 0.3,
  trackTo = 0.09,
  y = 0,
}) => {
  const frame = useCurrentFrame();
  const local = frame - at;

  // Slot layout is pure arithmetic — no state, no memo needed.
  let cursor = 0;
  const slots = words.map((w) => {
    const word = typeof w === "string" ? w : w.word;
    const h = typeof w === "string" ? hold : w.hold ?? hold;
    const c = typeof w === "string" ? undefined : w.color;
    const slot = { start: cursor, end: cursor + enter + h + exit, word, hold: h, color: c };
    cursor += enter + h + exit + gap;
    return slot;
  });

  const active = slots.find((s) => local >= s.start && local < s.end);
  if (!active) return null;

  const l = local - active.start;
  const e = easeOut3(l / enter);
  const f = easeIn2((l - enter - active.hold) / exit);
  // Tracking keeps drifting a hair through the hold — invisible per frame, alive over 1.5s.
  const holdT = Math.min(1, Math.max(0, (l - enter) / Math.max(1, active.hold)));
  const tracking = lerp(trackFrom, trackTo, e) + holdT * 0.004;

  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div
        style={{
          fontFamily: face === "serif" ? SERIF : SANS,
          fontWeight: face === "serif" ? 600 : 800,
          fontSize: size,
          lineHeight: 1.0,
          textTransform: "uppercase",
          textAlign: "center",
          color: outline ? "transparent" : active.color ?? color,
          WebkitTextStroke: outline ? `1.5px ${BRAND.goldLight}` : undefined,
          letterSpacing: `${tracking}em`,
          // Uppercase + letter-spacing adds a trailing gap; nudge back to true centre.
          textIndent: `${tracking}em`,
          opacity: e * (1 - f),
          transform: `translateY(${y - 10 * f}px) scale(${0.985 + 0.015 * e})`,
          filter: f > 0 ? `blur(${3 * f}px)` : undefined,
          padding: "0 80px",
        }}
      >
        {active.word}
      </div>
    </AbsoluteFill>
  );
};

/**
 * THREAD RULE — a single gold hairline that draws between two points and later retracts.
 * The atomic unit of the web motif. Used in-scene (Sc01 horizon, Sc03 the connection
 * between two orgs, Sc06 under each figure) so the web reads as a recurring MOTIF
 * rather than only a transition effect.
 *
 * Coordinates are percentages of the frame, so it is resolution-independent.
 */
export const ThreadRule: React.FC<{
  from: [number, number];
  to: [number, number];
  at?: number;
  draw?: number;
  hold?: number;
  out?: number;
  color?: string;
  width?: number;
  opacity?: number;
  dots?: boolean;
}> = ({
  from,
  to,
  at = 0,
  draw = 40,
  hold = 60,
  out = 20,
  color = BRAND.gold,
  width = 1.5,
  opacity = 0.75,
  dots = false,
}) => {
  const frame = useCurrentFrame();
  const l = frame - at;
  if (l < 0 || l > draw + hold + out) return null;

  const p = easeOut3(l / draw);
  const fade = easeIn2((l - draw - hold) / out);
  const x2 = lerp(from[0], to[0], p);
  const y2 = lerp(from[1], to[1], p);
  const op = opacity * (1 - fade);

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <svg width="100%" height="100%" style={{ overflow: "visible" }}>
        <line
          x1={`${from[0]}%`}
          y1={`${from[1]}%`}
          x2={`${x2}%`}
          y2={`${y2}%`}
          stroke={color}
          strokeWidth={width}
          strokeOpacity={op}
          strokeLinecap="round"
        />
        {dots ? (
          <>
            <circle cx={`${from[0]}%`} cy={`${from[1]}%`} r={4} fill={color} fillOpacity={op} />
            <circle cx={`${to[0]}%`} cy={`${to[1]}%`} r={4} fill={color} fillOpacity={op * p} />
          </>
        ) : null}
      </svg>
    </AbsoluteFill>
  );
};

/**
 * NODE FIELD — a seeded constellation that drifts very slowly, with optional
 * highlighted nodes. Generalized from ParticleLogoOpen in the launch film.
 * Carries the web motif in 2D at native resolution (we deliberately do NOT use the
 * Three.js globe here — a rotating Earth reads "global SaaS" to a county audience).
 */
export const NodeField: React.FC<{
  w?: number;
  h?: number;
  count?: number;
  seed?: number;
  opacity?: number;
  highlight?: number[];
  connect?: boolean;
  at?: number;
  fadeIn?: number;
}> = ({
  w = SIZE,
  h = SIZE,
  count = 9,
  seed = 20260729,
  opacity = 0.18,
  highlight = [],
  connect = true,
  at = 0,
  fadeIn = 40,
}) => {
  const frame = useCurrentFrame();
  const t = frame / 30;
  const appear = easeOut3((frame - at) / fadeIn);
  if (appear <= 0) return null;

  const rnd = makePrng(seed);
  const pts = Array.from({ length: count }).map(() => ({
    x: 12 + rnd() * 76,
    y: 16 + rnd() * 68,
    ph: rnd() * Math.PI * 2,
    sp: 0.05 + rnd() * 0.06,
  }));
  const at2 = pts.map((p) => ({
    x: p.x + Math.sin(t * p.sp + p.ph) * 1.1,
    y: p.y + Math.cos(t * p.sp * 0.8 + p.ph) * 0.9,
  }));

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <svg width="100%" height="100%" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
        {connect
          ? at2.map((a, i) => {
              // Each node links to its single nearest neighbour — a loose constellation,
              // never a radial hub (that grammar belongs to OrbWeb).
              let best = -1;
              let bd = Infinity;
              at2.forEach((b, j) => {
                if (j === i) return;
                const d = (a.x - b.x) ** 2 + (a.y - b.y) ** 2;
                if (d < bd) {
                  bd = d;
                  best = j;
                }
              });
              if (best < 0 || best < i) return null;
              const b = at2[best];
              return (
                <line
                  key={`e${i}`}
                  x1={(a.x / 100) * w}
                  y1={(a.y / 100) * h}
                  x2={(b.x / 100) * w}
                  y2={(b.y / 100) * h}
                  stroke={BRAND.gold}
                  strokeWidth={1}
                  strokeOpacity={opacity * appear * 0.8}
                />
              );
            })
          : null}
        {at2.map((a, i) => {
          const hot = highlight.includes(i);
          const pulse = hot ? 0.85 + Math.sin(t * 1.1) * 0.15 : 1;
          return (
            <circle
              key={`n${i}`}
              cx={(a.x / 100) * w}
              cy={(a.y / 100) * h}
              r={hot ? 7 : 3.5}
              fill={hot ? BRAND.goldLight : BRAND.gold}
              fillOpacity={(hot ? 0.95 * pulse : opacity * 1.6) * appear}
            />
          );
        })}
      </svg>
    </AbsoluteFill>
  );
};

/**
 * ACT BRIDGE — an animated connection web that draws THROUGH an act cut, peaking exactly
 * on the boundary so the audience sees the network connect, then the new act.
 *
 * Deliberately the same boundaries[] overlay API as SceneDissolve (not a TransitionSeries)
 * so it is timing-safe and cannot desync fixed-frame captions — see SceneDissolve above.
 *
 * Complements rather than duplicates:
 *   SceneDissolve — dip only, no geometry        → the 13 in-act cuts
 *   OrbWeb        — radial, hub-centred, labelled, diegetic (it IS the product)
 *   ActBridge     — acentric, unlabelled, non-diegetic (connective tissue)
 * Pass DISJOINT boundary arrays; never both at the same frame.
 */
export const ActBridge: React.FC<{
  boundaries: number[];
  w?: number;
  h?: number;
  lead?: number;
  tail?: number;
  nodes?: number;
  dip?: number;
  seed?: number;
  label?: (string | null)[];
}> = ({
  boundaries,
  w = SIZE,
  h = SIZE,
  lead = 40,
  tail = 40,
  nodes = 11,
  dip = 0.62,
  seed = 20260729,
  label,
}) => {
  const frame = useCurrentFrame();

  const idx = boundaries.findIndex((b) => frame >= b - lead && frame <= b + tail);
  if (idx < 0) return null;
  const b = boundaries[idx];

  // Geometry — pure arithmetic from the seed, identical on every frame.
  const rnd = makePrng(seed + idx * 977);
  const cx = w / 2;
  const cy = h / 2;
  const homes = Array.from({ length: nodes }).map(() => {
    const x = (12 + rnd() * 76) * (w / 100);
    const y = (12 + rnd() * 76) * (h / 100);
    return { x, y };
  });
  // Each node flies in from off-frame along the centre→home vector.
  const origins = homes.map((p) => ({
    x: cx + (p.x - cx) * 1.9,
    y: cy + (p.y - cy) * 1.9,
  }));

  const pIn = easeOut3((frame - (b - lead)) / lead);
  const pOut = easeIn2((frame - b) / tail);

  const pos = homes.map((home, i) => {
    const o = origins[i];
    // Continue drifting ~6% past home during the out-phase so nothing freezes.
    const t = pIn + pOut * 0.06;
    return { x: lerp(o.x, home.x, t), y: lerp(o.y, home.y, t) };
  });

  // Edges: 2 nearest neighbours per node, deduped — plus no hub, ever.
  const edges: [number, number][] = [];
  const seen = new Set<string>();
  homes.forEach((a, i) => {
    const near = homes
      .map((c, j) => ({ j, d: (a.x - c.x) ** 2 + (a.y - c.y) ** 2 }))
      .filter((n) => n.j !== i)
      .sort((p, q) => p.d - q.d)
      .slice(0, 2);
    near.forEach((n) => {
      const k = i < n.j ? `${i}-${n.j}` : `${n.j}-${i}`;
      if (!seen.has(k)) {
        seen.add(k);
        edges.push([i, n.j]);
      }
    });
  });

  const alpha = pIn * (1 - pOut);
  const navyDip = interpolate(frame, [b - lead * 0.7, b, b + tail * 0.7], [0, dip, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const text = label?.[idx] ?? null;
  const labelOp = text
    ? interpolate(frame, [b - 14, b, b + 14], [0, 1, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 0;

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <AbsoluteFill style={{ background: BRAND.navy, opacity: navyDip }} />
      <svg width="100%" height="100%" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
        {edges.map(([i, j], k) => {
          const a = pos[i];
          const c = pos[j];
          // Draw by interpolating the endpoint — same technique as OrbWeb, so the two
          // read as one visual family, and it stays a pure function of frame.
          const drawn = easeOut3((pIn - (k % 5) * 0.05) / 0.7);
          return (
            <line
              key={`e${k}`}
              x1={a.x}
              y1={a.y}
              x2={a.x + (c.x - a.x) * drawn}
              y2={a.y + (c.y - a.y) * drawn}
              stroke={BRAND.gold}
              strokeWidth={1.4}
              strokeOpacity={0.55 * alpha}
            />
          );
        })}
        {pos.map((p, i) => (
          <circle key={`n${i}`} cx={p.x} cy={p.y} r={4} fill={BRAND.goldLight} fillOpacity={0.9 * alpha} />
        ))}
      </svg>
      {text ? (
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
          <div
            style={{
              fontFamily: SANS,
              fontWeight: 800,
              fontSize: 22,
              letterSpacing: "0.28em",
              textTransform: "uppercase",
              color: BRAND.goldLight,
              opacity: labelOp,
            }}
          >
            {text}
          </div>
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};

/**
 * CONCEPT FRAME — the Act IV register. Everything inside it reads as UNBUILT.
 *
 * This is the film's largest credibility exposure: a room of county officials must never
 * mistake a wireframe for shipped product. Defence is layered so no single failure exposes
 * us — desaturation, a blueprint grid, and a persistent dashed "CONCEPT · NOT BUILT" chip.
 * The other three layers live in the film itself: zero screenshots in Act IV, outline
 * typography, and a reverse un-draw on the last wireframe.
 */
export const ConceptFrame: React.FC<{
  children?: React.ReactNode;
  at?: number;
  enter?: number;
  exit?: number;
  durationInFrames?: number;
  chip?: string;
  grid?: number;
}> = ({
  children,
  at = 0,
  enter = 20,
  exit = 20,
  durationInFrames,
  chip = "CONCEPT · NOT BUILT",
  grid = 48,
}) => {
  const frame = useCurrentFrame();
  const l = frame - at;
  const pIn = easeOut3(l / enter);
  const pOut = durationInFrames ? easeIn2((l - (durationInFrames - exit)) / exit) : 0;
  const on = pIn * (1 - pOut);

  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ filter: `saturate(${lerp(1, 0.55, on)})` }}>{children}</AbsoluteFill>
      {/* blueprint grid — draws on as the register changes */}
      <AbsoluteFill
        style={{
          opacity: 0.06 * on,
          backgroundImage: `linear-gradient(${BRAND.gold} 1px, transparent 1px), linear-gradient(90deg, ${BRAND.gold} 1px, transparent 1px)`,
          backgroundSize: `${grid}px ${grid}px`,
        }}
      />
      <AbsoluteFill style={{ alignItems: "flex-end", justifyContent: "flex-start", padding: 54 }}>
        <div
          style={{
            opacity: on,
            border: `1px dashed ${BRAND.goldLight}`,
            borderRadius: 6,
            padding: "9px 16px",
            fontFamily: SANS,
            fontWeight: 800,
            fontSize: 18,
            letterSpacing: "0.24em",
            color: BRAND.goldLight,
            textTransform: "uppercase",
          }}
        >
          {chip}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/**
 * WIRE BLOCK — a hairline rectangle that draws itself stroke-by-stroke and can UN-DRAW
 * in reverse. The Act IV primitive. Never fills, never colours in: an outline that
 * retracts is the strongest non-verbal statement of "this does not exist yet."
 *
 * Perimeter is computed analytically (not via getTotalLength) so it stays frame-pure.
 */
export const WireBlock: React.FC<{
  x: number;
  y: number;
  w: number;
  h: number;
  at?: number;
  draw?: number;
  undrawAt?: number;
  undraw?: number;
  label?: string;
  color?: string;
  radius?: number;
  rows?: number;
}> = ({
  x,
  y,
  w,
  h,
  at = 0,
  draw = 30,
  undrawAt,
  undraw = 24,
  label,
  color = BRAND.goldLight,
  radius = 4,
  rows = 0,
}) => {
  const frame = useCurrentFrame();
  const l = frame - at;
  if (l < 0) return null;

  const p = easeOut3(l / draw);
  const back = undrawAt !== undefined ? easeIn2((frame - undrawAt) / undraw) : 0;
  const shown = Math.max(0, p - back);
  if (shown <= 0) return null;

  const perim = 2 * (w + h);

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <svg width="100%" height="100%" style={{ overflow: "visible" }}>
        <rect
          x={`${x}%`}
          y={`${y}%`}
          width={`${w}%`}
          height={`${h}%`}
          rx={radius}
          fill="none"
          stroke={color}
          strokeWidth={1.25}
          strokeOpacity={0.85}
          pathLength={perim}
          strokeDasharray={perim}
          strokeDashoffset={perim * (1 - shown)}
        />
        {Array.from({ length: rows }).map((_, i) => {
          const ry = y + (h / (rows + 1)) * (i + 1);
          const rp = Math.max(0, Math.min(1, (shown - 0.5 - i * 0.08) / 0.4));
          return (
            <line
              key={i}
              x1={`${x + 2}%`}
              y1={`${ry}%`}
              x2={`${x + 2 + (w - 4) * rp}%`}
              y2={`${ry}%`}
              stroke={color}
              strokeWidth={1}
              strokeOpacity={0.4 * rp}
            />
          );
        })}
      </svg>
      {label ? (
        <div
          style={{
            position: "absolute",
            left: `${x}%`,
            top: `calc(${y}% - 26px)`,
            opacity: shown,
            fontFamily: SANS,
            fontWeight: 800,
            fontSize: 15,
            letterSpacing: "0.2em",
            textTransform: "uppercase",
            color,
          }}
        >
          {label}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

/**
 * UI SPOTLIGHT — a gold hairline rectangle drawn in panel-relative percentages, plus an
 * optional soft vignette. Points at one control in a screenshot WITHOUT a fake cursor
 * (a drawn cursor implies interaction we aren't performing, and reads as demo-ware).
 */
export const UISpotlight: React.FC<{
  x: number;
  y: number;
  w: number;
  h: number;
  at?: number;
  draw?: number;
  hold?: number;
  out?: number;
  vignette?: number;
  label?: string;
  /** Which side of the box the label sits on. Below (default) is fine for a box in
   *  the upper half; a box low in the frame, or one sitting on light UI, wants "above". */
  labelPos?: "below" | "above";
  /** Anchor edge. "right" keeps a long label from running off-frame when the box
   *  is already near the right edge — which is where sort/filter controls live. */
  labelAlign?: "left" | "right";
}> = ({
  x,
  y,
  w,
  h,
  at = 0,
  draw = 22,
  hold = 90,
  out = 18,
  vignette = 0.36,
  label,
  labelPos = "below",
  labelAlign = "left",
}) => {
  const frame = useCurrentFrame();
  const l = frame - at;
  if (l < 0 || l > draw + hold + out) return null;

  const p = easeOut3(l / draw);
  const fade = easeIn2((l - draw - hold) / out);
  const on = p * (1 - fade);
  const perim = 2 * (w + h);

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {vignette > 0 ? (
        <AbsoluteFill
          style={{
            opacity: on * vignette,
            background: `radial-gradient(ellipse ${w * 2.4}% ${h * 3.2}% at ${x + w / 2}% ${
              y + h / 2
            }%, transparent 0%, rgba(4,9,20,0.92) 100%)`,
          }}
        />
      ) : null}
      <svg width="100%" height="100%" style={{ overflow: "visible" }}>
        <rect
          x={`${x}%`}
          y={`${y}%`}
          width={`${w}%`}
          height={`${h}%`}
          rx={5}
          fill="none"
          stroke={BRAND.gold}
          strokeWidth={2}
          strokeOpacity={on}
          pathLength={perim}
          strokeDasharray={perim}
          strokeDashoffset={perim * (1 - p)}
        />
      </svg>
      {label ? (
        <div
          style={{
            position: "absolute",
            ...(labelAlign === "right" ? { right: `${100 - (x + w)}%` } : { left: `${x}%` }),
            ...(labelPos === "above"
              ? { bottom: `calc(${100 - y}% + 14px)` }
              : { top: `calc(${y + h}% + 14px)` }),
            opacity: on,
            fontFamily: SANS,
            fontWeight: 800,
            fontSize: 20,
            letterSpacing: "0.2em",
            textTransform: "uppercase",
            whiteSpace: "nowrap",
            color: BRAND.goldLight,
            // The label often sits over a light UI panel, where gold-on-white is
            // unreadable. A dark halo keeps it legible without a solid plate.
            textShadow: "0 2px 10px rgba(4,9,20,0.95), 0 0 22px rgba(4,9,20,0.9)",
          }}
        >
          {label}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

/**
 * COUNT-UP FIGURE — a number that counts to its value on a cubic ease and settles, with a
 * gold hairline drawing beneath it and a wide-tracked label below. Generalized from the
 * CountUpMoney pattern in oneoffs/BamOrlandoPresentation.tsx, minus the spring (no
 * overshoot in this register).
 *
 * `format` receives the eased value so callers own their own units — every figure in this
 * film traces to a real source, so nothing is formatted speculatively here.
 */
export const CountUpFigure: React.FC<{
  value: number;
  format?: (n: number) => string;
  label?: string;
  at?: number;
  count?: number;
  size?: number;
  labelSize?: number;
  color?: string;
  rule?: boolean;
  outFrom?: number;
  out?: number;
}> = ({
  value,
  format = (n) => Math.round(n).toLocaleString("en-US"),
  label,
  at = 0,
  count = 70,
  size = 104,
  labelSize = 18,
  color = BRAND.goldLight,
  rule = true,
  outFrom,
  out = 18,
}) => {
  const frame = useCurrentFrame();
  const l = frame - at;
  if (l < 0) return null;

  const p = easeOut3(l / count);
  const appear = easeOut3(l / 14);
  const fade = outFrom !== undefined ? easeIn2((frame - outFrom) / out) : 0;
  const on = appear * (1 - fade);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 10,
        opacity: on,
        transform: `translateY(${8 * (1 - appear) + 8 * fade}px)`,
      }}
    >
      <div
        style={{
          fontFamily: SERIF,
          fontWeight: 700,
          fontSize: size,
          lineHeight: 1,
          color,
          letterSpacing: "-0.02em",
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {format(value * p)}
      </div>
      {rule ? (
        <div
          style={{
            width: `${72 * easeOut3((l - 8) / 30)}px`,
            height: 1,
            background: BRAND.gold,
            opacity: 0.7,
          }}
        />
      ) : null}
      {label ? (
        <div
          style={{
            fontFamily: SANS,
            fontWeight: 800,
            fontSize: labelSize,
            letterSpacing: "0.22em",
            textTransform: "uppercase",
            color: BRAND.muted,
            textAlign: "center",
          }}
        >
          {label}
        </div>
      ) : null}
    </div>
  );
};
