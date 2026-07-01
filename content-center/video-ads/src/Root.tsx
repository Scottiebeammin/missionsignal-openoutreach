import React from "react";
import { Composition } from "remotion";
import { FPS, SIZE } from "./brand";
import { PlatformShowcase } from "./ads/PlatformShowcase";
import { PilotSignup } from "./ads/PilotSignup";

// Both ads are 30s @ 30fps, square 1:1 (best for the LinkedIn feed).
// To add narration: drop the ElevenLabs export into public/ (e.g. public/showcase-vo.mp3)
// then set the audioSrc prop below (or in Remotion Studio's props panel) to "showcase-vo.mp3".
export const RemotionRoot: React.FC = () => {
  return (
    <>
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
    </>
  );
};
