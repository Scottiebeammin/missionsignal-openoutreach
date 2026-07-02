import React from "react";
import { Composition } from "remotion";
import { FPS, SIZE, VERT_H, VERT_W } from "./brand";
import { PlatformShowcase } from "./ads/PlatformShowcase";
import { PilotSignup } from "./ads/PilotSignup";
import { PilotSeatsReveal, PILOT_SEATS_REVEAL_TOTAL } from "./ads/PilotSeatsReveal";
import { Jul10SnapshotClip } from "./ads/Jul10SnapshotClip";
import { Jul17EndorsementOutro } from "./ads/Jul17EndorsementOutro";
import { Jul24ListVsMap } from "./ads/Jul24ListVsMap";
import { Jul25SnapshotScroll } from "./ads/Jul25SnapshotScroll";
import { Jul31ClosingOutro } from "./ads/Jul31ClosingOutro";
import { PremiumShowcase } from "./oneoffs/PremiumShowcase";
import { FullExplainer } from "./oneoffs/FullExplainer";
import { ProductWalkthrough, WALK_TOTAL } from "./oneoffs/ProductWalkthrough";
import { CapabilityTest } from "./oneoffs/CapabilityTest";
import { CapabilityTest2 } from "./oneoffs/CapabilityTest2";
import { CapabilityTest3, CAPABILITY_TEST_3_TOTAL } from "./oneoffs/CapabilityTest3";
import { EarthWebTest, EARTH_WEB_TEST_TOTAL } from "./oneoffs/EarthWebTest";
import { WebOfOpportunityFilm, FILM_TOTAL } from "./oneoffs/WebOfOpportunityFilm";

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

      {/* FIRST LINKEDIN POST — "19 of 20 Seats" stat reveal (GSAP+D3+Three.js+Lottie layered) */}
      <Composition
        id="PilotSeatsReveal"
        component={PilotSeatsReveal}
        durationInFrames={PILOT_SEATS_REVEAL_TOTAL}
        fps={FPS}
        width={SIZE}
        height={SIZE}
        defaultProps={{ audioSrc: "pilot-seats-reveal-vo.mp3" as string | null }}
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

      {/* ONE-OFFS — separate from the automated ads pipeline (see oneoffs/README.md) */}
      <Composition
        id="PremiumShowcase"
        component={PremiumShowcase}
        durationInFrames={1032} // retimed to the actual ~34.4s Christopher VO
        fps={FPS}
        width={SIZE}
        height={SIZE}
        defaultProps={{ audioSrc: "premium-showcase-vo.mp3" as string | null }}
      />
      <Composition
        id="FullExplainer"
        component={FullExplainer}
        durationInFrames={9150}
        fps={FPS}
        width={SIZE}
        height={SIZE}
        defaultProps={{ audioSrc: null as string | null }}
      />
      <Composition
        id="ProductWalkthrough"
        component={ProductWalkthrough}
        durationInFrames={WALK_TOTAL}
        fps={FPS}
        width={SIZE}
        height={SIZE}
        // VO wired so Remotion Studio plays it WITH SOUND (localhost:3000).
        // (Requires public/product-walkthrough-vo.mp3 — generated via `npm run vo ProductWalkthrough`.)
        // broll1/broll2: optional cold-open clips (public/broll/*.mp4) — see ELEVENLABS-ASSETS.md.
        // Leave null until you've generated + dropped them in; falls back to a plain brand moment.
        defaultProps={{
          audioSrc: "product-walkthrough-vo.mp3" as string | null,
          broll1Src: null as string | null,
          broll2Src: null as string | null,
          problemBrollSrc: null as string | null, // e.g. "broll/hands-typing.mp4"
          officeEnvSrc: null as string | null, // e.g. "broll/laptop-office.mp4" or ".jpg"
        }}
      />

      {/* ⚠️ THROWAWAY TEST — not part of the ads pipeline. GSAP capability showcase. */}
      <Composition
        id="CapabilityTest"
        component={CapabilityTest}
        durationInFrames={720}
        fps={FPS}
        width={SIZE}
        height={SIZE}
      />

      {/* ⚠️ THROWAWAY TEST #2 — D3 / Three.js / Lottie capability showcase. */}
      <Composition
        id="CapabilityTest2"
        component={CapabilityTest2}
        durationInFrames={660}
        fps={FPS}
        width={SIZE}
        height={SIZE}
      />

      {/* ⚠️ THROWAWAY TEST #3 — all four systems LAYERED simultaneously, one scene. */}
      <Composition
        id="CapabilityTest3"
        component={CapabilityTest3}
        durationInFrames={CAPABILITY_TEST_3_TOTAL}
        fps={FPS}
        width={SIZE}
        height={SIZE}
      />

      {/* 🎬 THE LAUNCH FILM — "The Web of Opportunity" cinematic brand film (9 scenes). */}
      <Composition
        id="WebOfOpportunityFilm"
        component={WebOfOpportunityFilm}
        durationInFrames={FILM_TOTAL}
        fps={FPS}
        width={SIZE}
        height={SIZE}
        defaultProps={{ audioSrc: "web-of-opportunity-film-vo.mp3" as string | null }}
      />

      {/* ⚠️ PROTOTYPE — de-risking the rotating-globe hero visual before committing it. */}
      <Composition
        id="EarthWebTest"
        component={EarthWebTest}
        durationInFrames={EARTH_WEB_TEST_TOTAL}
        fps={FPS}
        width={SIZE}
        height={SIZE}
      />
    </>
  );
};
