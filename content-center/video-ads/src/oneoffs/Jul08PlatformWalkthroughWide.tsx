import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { BRAND } from "../brand";
import { Jul08PlatformWalkthrough } from "./Jul08PlatformWalkthrough";

/**
 * YOUTUBE 16:9 WIDE VARIANT — the square Jul 8 hero centered in a full-width branded backdrop
 * (navy gradient + breathing side glows + feathered seams), same pattern as
 * WebOfOpportunityFilmWide. LinkedIn/IG get the native 1:1 square cut; this is the version for
 * YouTube (and anywhere else that expects 16:9) so it fills the player instead of pillarboxing.
 */
export const Jul08PlatformWalkthroughWide: React.FC<{ audioSrc?: string | null }> = ({ audioSrc }) => {
  const frame = useCurrentFrame();
  const breathe = 0.8 + 0.2 * Math.sin(frame / 46);
  return (
    <AbsoluteFill style={{ background: `radial-gradient(120% 120% at 50% 20%, ${BRAND.navy2} 0%, ${BRAND.navy} 55%, ${BRAND.charcoal} 100%)` }}>
      <AbsoluteFill
        style={{
          opacity: breathe,
          background:
            "radial-gradient(circle at 3% 22%, rgba(212,160,23,0.22) 0%, rgba(212,160,23,0) 30%), radial-gradient(circle at 97% 80%, rgba(58,108,200,0.24) 0%, rgba(58,108,200,0) 32%)",
        }}
      />
      {/* the square hero, centered */}
      <div style={{ position: "absolute", left: (1920 - 1080) / 2, top: 0, width: 1080, height: 1080, overflow: "hidden" }}>
        <Jul08PlatformWalkthrough audioSrc={audioSrc} />
      </div>
      {/* feather the seams into the backdrop */}
      <div style={{ position: "absolute", left: (1920 - 1080) / 2 - 2, top: 0, width: 240, height: 1080, background: `linear-gradient(90deg, ${BRAND.navy} 0%, rgba(13,27,61,0) 100%)` }} />
      <div style={{ position: "absolute", right: (1920 - 1080) / 2 - 2, top: 0, width: 240, height: 1080, background: `linear-gradient(270deg, ${BRAND.navy} 0%, rgba(13,27,61,0) 100%)` }} />
    </AbsoluteFill>
  );
};
