import React from "react";
import { Composition } from "remotion";
import { FPS, SIZE, VERT_H, VERT_W } from "./brand";
import { PlatformShowcase } from "./ads/PlatformShowcase";
import { PilotSignup } from "./ads/PilotSignup";
import { Jul10SnapshotClip } from "./ads/Jul10SnapshotClip";
import { Jul17EndorsementOutro } from "./ads/Jul17EndorsementOutro";
import { Jul24ListVsMap } from "./ads/Jul24ListVsMap";
import { Jul25SnapshotScroll } from "./ads/Jul25SnapshotScroll";
import { Jul31ClosingOutro } from "./ads/Jul31ClosingOutro";

// To add narration: drop the ElevenLabs export into public/ (e.g. public/showcase-vo.mp3)
// then set the audioSrc prop below (or in Remotion Studio's props panel, or via
// scripts/build.mjs which wires it in automatically once the file exists).
export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* Two hero ads — 30s, square, LinkedIn feed */}
      <Composition
        id="PlatformShowcase"
        component={PlatformShowcase}
        durationInFrames={900}
        fps={FPS}
        width={SIZE}
        height={SIZE}
        defaultProps={{ audioSrc: null as string | null }}
      />
      <Composition
        id="PilotSignup"
        component={PilotSignup}
        durationInFrames={900}
        fps={FPS}
        width={SIZE}
        height={SIZE}
        defaultProps={{ audioSrc: null as string | null }}
      />

      {/* July calendar's remaining voice-needed clips */}
      <Composition
        id="Jul10-SnapshotClip"
        component={Jul10SnapshotClip}
        durationInFrames={360}
        fps={FPS}
        width={SIZE}
        height={SIZE}
        defaultProps={{ audioSrc: null as string | null }}
      />
      <Composition
        id="Jul17-EndorsementOutro"
        component={Jul17EndorsementOutro}
        durationInFrames={240}
        fps={FPS}
        width={SIZE}
        height={SIZE}
        defaultProps={{ audioSrc: null as string | null }}
      />
      <Composition
        id="Jul24-ListVsMap"
        component={Jul24ListVsMap}
        durationInFrames={450}
        fps={FPS}
        width={SIZE}
        height={SIZE}
        defaultProps={{ audioSrc: null as string | null }}
      />
      <Composition
        id="Jul25-SnapshotScroll"
        component={Jul25SnapshotScroll}
        durationInFrames={450}
        fps={FPS}
        width={VERT_W}
        height={VERT_H}
        defaultProps={{ audioSrc: null as string | null }}
      />
      <Composition
        id="Jul31-ClosingOutro"
        component={Jul31ClosingOutro}
        durationInFrames={240}
        fps={FPS}
        width={SIZE}
        height={SIZE}
        defaultProps={{ audioSrc: null as string | null }}
      />
    </>
  );
};
