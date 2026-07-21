import React from "react";
import {
  AbsoluteFill,
  Audio,
  OffthreadVideo,
  Sequence,
  staticFile,
  useCurrentFrame,
  interpolate,
} from "remotion";
import { FPS } from "../brand";

// ─────────────────────────────────────────────────────────────────────────────
// LUCKY MISTAKE — 30-second vertical promo (TikTok), NOT an Anansi Atlas ad.
// Standalone creative test: two Seedance 2.0 clips (1080x1920, ~15.07s each,
// generated in Artlist Studio) cut back-to-back into one 30s piece.
//   Shot 1 (0:00–0:15) — the meeting, one open stool
//   Shot 2 (0:15–0:30) — the casino-tag spark
// End title card "LUCKY MISTAKE" fades up over the final beats.
//
// AUDIO: `musicSrc` = background music bed, `voSrc` = optional cloned-voice tagline.
// Drop files into public/lucky-mistake/ and pass their paths (or set defaults in Root).
// Both default to null so the comp renders (silent) until the tracks exist.
// ─────────────────────────────────────────────────────────────────────────────

const SHOT_SECONDS = 15.069; // measured length of each Seedance clip
export const SHOT_FRAMES = Math.round(SHOT_SECONDS * FPS); // 452 @ 30fps
export const LUCKY_MISTAKE_TOTAL = SHOT_FRAMES * 2; // 904 ≈ 30.1s

const SHOTS = ["lucky-mistake/shot-1.mp4", "lucky-mistake/shot-2.mp4"];

// End-title timing: fade in over the last ~2.5s, hold to the end.
const TITLE_IN_START = LUCKY_MISTAKE_TOTAL - 90; // ~3s before end
const TITLE_IN_END = LUCKY_MISTAKE_TOTAL - 60;

const EndTitle: React.FC = () => {
  const frame = useCurrentFrame();
  const titleOpacity = interpolate(frame, [TITLE_IN_START, TITLE_IN_END], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  // Darken the footage behind the title as it rises.
  const scrim = interpolate(frame, [TITLE_IN_START, TITLE_IN_END], [0, 0.55], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const subOpacity = interpolate(frame, [TITLE_IN_END, TITLE_IN_END + 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const soonOpacity = interpolate(frame, [TITLE_IN_END + 20, TITLE_IN_END + 38], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const rise = interpolate(frame, [TITLE_IN_START, TITLE_IN_END], [18, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ backgroundColor: `rgba(8,6,10,${scrim})` }} />
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          flexDirection: "column",
          gap: 22,
          transform: `translateY(${rise}px)`,
        }}
      >
        <div
          style={{
            opacity: titleOpacity,
            color: "#f7efe2",
            fontFamily: "Georgia, 'Times New Roman', serif",
            fontSize: 116,
            fontWeight: 700,
            letterSpacing: 6,
            textTransform: "uppercase",
            textAlign: "center",
            lineHeight: 1.02,
            textShadow: "0 4px 40px rgba(0,0,0,0.6)",
          }}
        >
          Lucky
          <br />
          Mistake
        </div>
        <div
          style={{
            opacity: subOpacity,
            color: "#e0b64d",
            fontFamily: "Helvetica, Arial, sans-serif",
            fontSize: 30,
            fontWeight: 600,
            letterSpacing: 8,
            textTransform: "uppercase",
          }}
        >
          A New Series
        </div>
        <div
          style={{
            opacity: soonOpacity,
            marginTop: 10,
            color: "#f7efe2",
            fontFamily: "Helvetica, Arial, sans-serif",
            fontSize: 22,
            fontWeight: 500,
            letterSpacing: 12,
            textTransform: "uppercase",
          }}
        >
          Coming Soon
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// Kinetic caption: fade+rise in, hold, fade out — timed to global frames.
const Caption: React.FC<{
  children: React.ReactNode;
  inStart: number;
  inEnd: number;
  outStart: number;
  outEnd: number;
  place?: "center" | "lower";
  style?: React.CSSProperties;
}> = ({ children, inStart, inEnd, outStart, outEnd, place = "center", style }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [inStart, inEnd, outStart, outEnd], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  if (opacity <= 0) return null;
  const rise = interpolate(frame, [inStart, inEnd], [16, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill
      style={{
        justifyContent: place === "lower" ? "flex-end" : "center",
        alignItems: "center",
        padding: place === "lower" ? "0 70px 300px" : "0 60px",
      }}
    >
      {/* legibility scrim tied to the caption's own fade */}
      <AbsoluteFill
        style={{
          opacity: opacity * 0.55,
          background:
            place === "lower"
              ? "linear-gradient(to top, rgba(6,4,8,0.9) 0%, rgba(6,4,8,0) 42%)"
              : "radial-gradient(60% 32% at 50% 50%, rgba(6,4,8,0.72) 0%, rgba(6,4,8,0) 100%)",
        }}
      />
      <div style={{ opacity, transform: `translateY(${rise}px)`, textAlign: "center", ...style }}>
        {children}
      </div>
    </AbsoluteFill>
  );
};

export const LuckyMistake: React.FC<{
  musicSrc?: string | null;
  voSrc?: string | null;
}> = ({ musicSrc = null, voSrc = null }) => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {SHOTS.map((src, i) => (
        <Sequence key={src} from={i * SHOT_FRAMES} durationInFrames={SHOT_FRAMES}>
          <AbsoluteFill style={{ backgroundColor: "#000" }}>
            <OffthreadVideo src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          </AbsoluteFill>
        </Sequence>
      ))}

      {/* Hook over Shot 1 */}
      <Caption
        inStart={250}
        inEnd={270}
        outStart={410}
        outEnd={440}
        style={{
          color: "#f7efe2",
          fontFamily: "Georgia, 'Times New Roman', serif",
          fontSize: 88,
          fontWeight: 700,
          letterSpacing: 5,
          textTransform: "uppercase",
          lineHeight: 1.05,
          textShadow: "0 4px 40px rgba(0,0,0,0.85)",
        }}
      >
        One Bad Night
      </Caption>

      {/* Tagline over Shot 2 */}
      <Caption
        inStart={598}
        inEnd={622}
        outStart={774}
        outEnd={798}
        place="lower"
        style={{
          color: "#f7efe2",
          fontFamily: "Georgia, 'Times New Roman', serif",
          fontStyle: "italic",
          fontSize: 42,
          fontWeight: 500,
          lineHeight: 1.28,
          letterSpacing: 1,
          maxWidth: 860,
          textShadow: "0 3px 30px rgba(0,0,0,0.9)",
        }}
      >
        Sometimes the worst decision
        <br />
        leads to the right person
      </Caption>

      <EndTitle />

      {musicSrc ? (
        <Audio
          src={staticFile(musicSrc)}
          volume={(f) =>
            interpolate(
              f,
              [0, 12, LUCKY_MISTAKE_TOTAL - 45, LUCKY_MISTAKE_TOTAL],
              [0, 0.6, 0.6, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            )
          }
        />
      ) : null}
      {voSrc ? <Audio src={staticFile(voSrc)} /> : null}
    </AbsoluteFill>
  );
};
