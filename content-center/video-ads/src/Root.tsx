import React from "react";
import { Composition } from "remotion";
import { FPS, SIZE, VERT_H, VERT_W } from "./brand";
import { PlatformShowcase } from "./ads/PlatformShowcase";
import { PilotSignup } from "./ads/PilotSignup";
import { PilotSeatsReveal, PILOT_SEATS_REVEAL_TOTAL } from "./ads/PilotSeatsReveal";
import { Jul10SnapshotClip } from "./ads/Jul10SnapshotClip";
import { Jul17EndorsementOutro } from "./ads/Jul17EndorsementOutro";
import { Jul24ListVsMap, WALK_TOTAL as JUL24_TOTAL } from "./ads/Jul24ListVsMap";
import { Jul25SnapshotScroll, WALK_TOTAL as JUL25_TOTAL } from "./ads/Jul25SnapshotScroll";
import { Jul31ClosingOutro } from "./ads/Jul31ClosingOutro";
import { PremiumShowcase } from "./oneoffs/PremiumShowcase";
import { FullExplainer } from "./oneoffs/FullExplainer";
import { ProductWalkthrough, WALK_TOTAL } from "./oneoffs/ProductWalkthrough";
import { DashboardWalkthrough, WALK_TOTAL as DASHBOARD_WALK_TOTAL } from "./oneoffs/DashboardWalkthrough";
import { Jul08PlatformWalkthrough, WALK_TOTAL as JUL08_WALK_TOTAL } from "./oneoffs/Jul08PlatformWalkthrough";
import { Jul08PlatformWalkthroughWide } from "./oneoffs/Jul08PlatformWalkthroughWide";
import { WhoWeAreWalkthrough, WALK_TOTAL as WHOWEARE_TOTAL } from "./oneoffs/WhoWeAreWalkthrough";
import { WhoWeAreWalkthroughWide } from "./oneoffs/WhoWeAreWalkthroughWide";
import { Jul08Thumbnails } from "./oneoffs/Jul08Thumbnails";
import { Jul02Carousel } from "./oneoffs/Jul02Carousel";
import { CapabilityTest } from "./oneoffs/CapabilityTest";
import { CapabilityTest2 } from "./oneoffs/CapabilityTest2";
import { CapabilityTest3, CAPABILITY_TEST_3_TOTAL } from "./oneoffs/CapabilityTest3";
import { EarthWebTest, EARTH_WEB_TEST_TOTAL } from "./oneoffs/EarthWebTest";
import { WebOfOpportunityFilm, WebOfOpportunityFilmWide, FILM_TOTAL } from "./oneoffs/WebOfOpportunityFilm";
import { AnansiVisionFilm, VISION_TOTAL } from "./oneoffs/AnansiVisionFilm";
import { BamOrlandoPresentation, BamOrlandoPresentationWide, BAM_TOTAL } from "./oneoffs/BamOrlandoPresentation";
import { BamOrlandoFilm, BAM_FILM_TOTAL } from "./oneoffs/BamOrlandoFilm";
import { LuckyMistake, LUCKY_MISTAKE_TOTAL } from "./oneoffs/LuckyMistake";

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

      {/* July calendar's remaining voice-needed clips — restyled (laptop mockup / logo-mark),
          timing corrected to match the now-generated VO (see each file's header comment). */}
      <Composition
        id="Jul10-SnapshotClip"
        component={Jul10SnapshotClip}
        durationInFrames={269}
        fps={FPS}
        width={SIZE}
        height={SIZE}
        defaultProps={{ audioSrc: "jul10-siren.mp3" as string | null }}
      />
      <Composition
        id="Jul17-EndorsementOutro"
        component={Jul17EndorsementOutro}
        durationInFrames={304}
        fps={FPS}
        width={SIZE}
        height={SIZE}
        defaultProps={{ audioSrc: "jul17-jackson.mp3" as string | null }}
      />
      <Composition
        id="Jul24-ListVsMap"
        component={Jul24ListVsMap}
        durationInFrames={JUL24_TOTAL}
        fps={FPS}
        width={SIZE}
        height={SIZE}
        defaultProps={{ audioSrc: "jul24-siren.mp3" as string | null }}
      />
      <Composition
        id="Jul25-SnapshotScroll"
        component={Jul25SnapshotScroll}
        durationInFrames={JUL25_TOTAL}
        fps={FPS}
        width={VERT_W}
        height={VERT_H}
        defaultProps={{ audioSrc: "jul25-giselle.mp3" as string | null }}
      />
      <Composition
        id="Jul31-ClosingOutro"
        component={Jul31ClosingOutro}
        durationInFrames={290}
        fps={FPS}
        width={SIZE}
        height={SIZE}
        defaultProps={{ audioSrc: "jul31-jackson.mp3" as string | null }}
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

      {/* 📅 JULY CALENDAR — Wed Jul 8 hero "Platform Walkthrough". Dashboard -> Opportunity Web
          -> Snapshot, closes on the founding-seat CTA. Voice: Giselle. */}
      <Composition
        id="Jul08-PlatformWalkthrough"
        component={Jul08PlatformWalkthrough}
        durationInFrames={JUL08_WALK_TOTAL}
        fps={FPS}
        width={SIZE}
        height={SIZE}
        defaultProps={{ audioSrc: "jul08-platform-walkthrough-vo.mp3" as string | null }}
      />

      {/* 📅 JULY CALENDAR — Thu Jul 2 six-node Opportunity Web carousel (7 slides: cover + 1 per
          node). Highest-reach format per the calendar — "seeds the whole month". Stills. */}
      {Array.from({ length: 7 }, (_, i) => (
        <Composition
          key={`jul02-slide-${i}`}
          id={`Jul02Carousel-Slide${i}`}
          component={Jul02Carousel}
          durationInFrames={30}
          fps={FPS}
          width={SIZE}
          height={SIZE}
          defaultProps={{ slideIndex: i }}
        />
      ))}

      {/* 🌐 STANDALONE FLAGSHIP — "Who We Are" + product walkthrough combined. Square (LinkedIn)
          + wide (YouTube) cuts. Voice: Giselle. */}
      <Composition
        id="WhoWeAreWalkthrough"
        component={WhoWeAreWalkthrough}
        durationInFrames={WHOWEARE_TOTAL}
        fps={FPS}
        width={SIZE}
        height={SIZE}
        defaultProps={{ audioSrc: "who-we-are-walkthrough-vo.mp3" as string | null }}
      />
      <Composition
        id="WhoWeAreWalkthroughWide"
        component={WhoWeAreWalkthroughWide}
        durationInFrames={WHOWEARE_TOTAL}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{ audioSrc: "who-we-are-walkthrough-vo.mp3" as string | null }}
      />

      {/*
        🎬 THE BOARD FILM — "The Ceiling Isn't This Room" (18 scenes, five acts).
        BAM Orlando, at Vision Film scale: native 16:9, Christopher VO sliced off
        the alignment JSON, and Act IV walks THEIR OWN workspace (project 18).

        ⚠️ NOT A PUBLIC ASSET — it shows a real prospect's data on screen. Board
        room only; do not post it. See the header of oneoffs/BamOrlandoFilm.tsx.

        Render the master with --image-format=png: remotion.config.ts sets jpeg
        globally, which bands the navy gradient over six minutes at 1080p.
      */}
      <Composition
        id="BamOrlandoFilm"
        component={BamOrlandoFilm}
        durationInFrames={BAM_FILM_TOTAL}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{ audioSrc: "bam-orlando-film-vo.mp3" as string | null, captions: false, music: true }}
      />
      {/* Same film, baked captions — for a board member watching it back on mute. */}
      <Composition
        id="BamOrlandoFilmCaptioned"
        component={BamOrlandoFilm}
        durationInFrames={BAM_FILM_TOTAL}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{ audioSrc: "bam-orlando-film-vo.mp3" as string | null, captions: true, music: true }}
      />

      {/* 🎯 SUPERSEDED by BamOrlandoFilm above — the 2026-07-16 square/pillarboxed
          cut, timed by word-count estimate and rendered silent (audioSrc null).
          Kept registered so out/BamOrlandoPresentation-Wide.mp4 stays reproducible. */}
      <Composition
        id="BamOrlandoPresentation"
        component={BamOrlandoPresentation}
        durationInFrames={BAM_TOTAL}
        fps={FPS}
        width={SIZE}
        height={SIZE}
        defaultProps={{ audioSrc: null as string | null }}
      />
      <Composition
        id="BamOrlandoPresentationWide"
        component={BamOrlandoPresentationWide}
        durationInFrames={BAM_TOTAL}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{ audioSrc: null as string | null }}
      />

      {/* 📺 YOUTUBE 16:9 — wide cut of the Jul 8 hero, square content centered in a full-width
          backdrop so it doesn't pillarbox in a YouTube player. */}
      <Composition
        id="Jul08-PlatformWalkthroughWide"
        component={Jul08PlatformWalkthroughWide}
        durationInFrames={JUL08_WALK_TOTAL}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{ audioSrc: "jul08-platform-walkthrough-vo.mp3" as string | null }}
      />

      {/* 🖼️ Jul 8 hero — 3 thumbnail options (stills) to pick from. */}
      <Composition
        id="Jul08Thumb-Hook"
        component={Jul08Thumbnails}
        durationInFrames={30}
        fps={FPS}
        width={SIZE}
        height={SIZE}
        defaultProps={{ variant: "hook" as const }}
      />
      <Composition
        id="Jul08Thumb-Product"
        component={Jul08Thumbnails}
        durationInFrames={30}
        fps={FPS}
        width={SIZE}
        height={SIZE}
        defaultProps={{ variant: "product" as const }}
      />
      <Composition
        id="Jul08Thumb-CTA"
        component={Jul08Thumbnails}
        durationInFrames={30}
        fps={FPS}
        width={SIZE}
        height={SIZE}
        defaultProps={{ variant: "cta" as const }}
      />

      {/* 🎓 ONBOARDING TUTORIAL — "Getting Started with Anansi Atlas" (profile creation -> full
          dashboard tour). Instructional, no pilot CTA. Voice: Giselle. */}
      <Composition
        id="DashboardWalkthrough"
        component={DashboardWalkthrough}
        durationInFrames={DASHBOARD_WALK_TOTAL}
        fps={FPS}
        width={SIZE}
        height={SIZE}
        defaultProps={{ audioSrc: "dashboard-walkthrough-vo.mp3" as string | null }}
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
      {/* 16:9 YouTube variant — same film, full-width brand atmosphere. */}
      <Composition
        id="WebOfOpportunityFilmWide"
        component={WebOfOpportunityFilmWide}
        durationInFrames={FILM_TOTAL}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{ audioSrc: "web-of-opportunity-film-vo.mp3" as string | null }}
      />

      {/*
        🎞️ THE EXECUTIVE VISION FILM — "The Whole Field" (18 scenes, five acts).
        Orange County FL government + Central Florida grantmakers. Native 16:9 —
        NOT pillarboxed like the Wide comps above; wide cinematic type needs the
        full frame. Act IV is a CONCEPT register (wireframes of unbuilt ideas).
        Render the master with --image-format=png: remotion.config.ts sets jpeg
        globally, which bands the navy gradient over six minutes at 1080p.
      */}
      <Composition
        id="AnansiVisionFilm"
        component={AnansiVisionFilm}
        durationInFrames={VISION_TOTAL}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{ audioSrc: "anansi-vision-film-vo.mp3" as string | null, captions: false, music: true }}
      />
      {/* Same film, baked captions — for autoplay-muted feeds. */}
      <Composition
        id="AnansiVisionFilmCaptioned"
        component={AnansiVisionFilm}
        durationInFrames={VISION_TOTAL}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{ audioSrc: null as string | null, captions: true, music: true }}
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

      {/* LUCKY MISTAKE — standalone 30s vertical romcom promo (TikTok). Two Seedance
          clips cut back-to-back + end title card. musicSrc/voSrc default null until
          the tracks are dropped into public/lucky-mistake/. */}
      <Composition
        id="LuckyMistake"
        component={LuckyMistake}
        durationInFrames={LUCKY_MISTAKE_TOTAL}
        fps={FPS}
        width={VERT_W}
        height={VERT_H}
        defaultProps={{ musicSrc: "lucky-mistake/music.mp3" as string | null, voSrc: null as string | null }}
      />
    </>
  );
};
