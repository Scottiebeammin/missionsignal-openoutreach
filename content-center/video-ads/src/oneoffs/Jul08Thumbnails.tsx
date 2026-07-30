import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { BRAND } from "../brand";
import { LaptopScreenshotPanel, NavyBG, SANS, SERIF } from "../components";

export type ThumbProps = {
  variant: "hook" | "product" | "cta";
};

/** Three static thumbnail options for the Jul 8 hero "Platform Walkthrough" — big bold
 *  thumbnail-scale text (not mid-video caption sizing), for Scott to pick from. Rendered as
 *  stills, no animation needed (frame 0 of each variant is the final deliverable). */
export const Jul08Thumbnails: React.FC<ThumbProps> = ({ variant }) => {
  if (variant === "hook") {
    return (
      <NavyBG>
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: 40 }}>
          <div style={{ transform: "scale(0.86)", opacity: 0.9 }}>
            <LaptopScreenshotPanel src={staticFile("screenshots/shot-dashboard3.png")} durationInFrames={1} width={820} />
          </div>
        </AbsoluteFill>
        <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(13,27,61,0.05) 0%, rgba(13,27,61,0.25) 32%, rgba(13,27,61,0.55) 48%, rgba(13,27,61,0.94) 62%, rgba(13,27,61,0.98) 100%)" }} />
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: 70, flexDirection: "column", gap: 20 }}>
          <div
            style={{
              fontFamily: SANS,
              fontWeight: 900,
              fontSize: 28,
              letterSpacing: "0.16em",
              textTransform: "uppercase",
              color: BRAND.goldLight,
              background: "rgba(9,18,38,0.7)",
              padding: "10px 24px",
              borderRadius: 999,
              border: `1px solid ${BRAND.gold}`,
            }}
          >
            The Real Platform
          </div>
          <div style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 100, color: BRAND.white, textAlign: "center", lineHeight: 1.02, textShadow: "0 8px 40px rgba(0,0,0,0.6)" }}>
            Not a<br />mockup.
          </div>
        </AbsoluteFill>
        {/* play button */}
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: 70 }}>
          <div
            style={{
              width: 92,
              height: 92,
              borderRadius: 999,
              background: BRAND.gold,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 20px 60px rgba(212,160,23,0.5)",
            }}
          >
            <div style={{ width: 0, height: 0, borderTop: "21px solid transparent", borderBottom: "21px solid transparent", borderLeft: "32px solid #171007", marginLeft: 8 }} />
          </div>
        </AbsoluteFill>
      </NavyBG>
    );
  }

  if (variant === "product") {
    return (
      <NavyBG>
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: 60 }}>
          <div style={{ transform: "scale(0.92)" }}>
            <LaptopScreenshotPanel src={staticFile("screenshots/shot-web-clean.png")} durationInFrames={1} width={880} />
          </div>
        </AbsoluteFill>
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: 70, gap: 14, flexDirection: "column" }}>
          <Img src={staticFile("logo-mark.png")} style={{ width: 60, height: 60 }} />
          <div style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 72, color: BRAND.white, textAlign: "center", lineHeight: 1.05, textShadow: "0 8px 40px rgba(0,0,0,0.55)" }}>
            See Inside
            <br />
            Anansi Atlas
          </div>
        </AbsoluteFill>
      </NavyBG>
    );
  }

  // variant === "cta"
  return (
    <NavyBG>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ transform: "scale(1.1)", opacity: 0.5 }}>
          <LaptopScreenshotPanel src={staticFile("screenshots/shot-snapshot3.png")} durationInFrames={1} width={840} />
        </div>
      </AbsoluteFill>
      <AbsoluteFill style={{ background: "radial-gradient(120% 90% at 50% 40%, rgba(13,27,61,0.2) 0%, rgba(13,27,61,0.88) 70%)" }} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 18 }}>
        <div style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 84, color: BRAND.white, textAlign: "center", lineHeight: 1.05, textShadow: "0 8px 40px rgba(0,0,0,0.6)" }}>
          The Platform.
          <br />
          <span style={{ color: BRAND.goldLight }}>No Pitch Deck.</span>
        </div>
      </AbsoluteFill>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: 64 }}>
        <div
          style={{
            fontFamily: SANS,
            fontWeight: 900,
            fontSize: 26,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            color: "#171007",
            background: BRAND.gold,
            padding: "16px 38px",
            borderRadius: 999,
          }}
        >
          Founding Partners Pilot Open
        </div>
      </AbsoluteFill>
    </NavyBG>
  );
};
