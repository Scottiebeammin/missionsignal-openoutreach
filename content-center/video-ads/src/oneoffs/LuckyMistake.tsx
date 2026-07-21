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
      </AbsoluteFill>
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
