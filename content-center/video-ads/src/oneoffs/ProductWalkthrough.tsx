import React from "react";
import { AbsoluteFill, Audio, interpolate, Sequence, staticFile, useCurrentFrame } from "remotion";
import { BRAND, SIGNUP_URL } from "../brand";
import {
  BRoll,
  Caption,
  CTAButton,
  Eyebrow,
  Headline,
  LogoLockup,
  NavyBG,
  OrbWeb,
  ProgressRail,
  Rise,
  SANS,
  SceneDissolve,
  ScreenshotPanel,
  Subtitles,
} from "../components";
import { WALK_SECTIONS } from "../data/walkthroughSections";

export type Props = {
  audioSrc?: string | null;
  // Optional B-roll cold-open (public/broll/*.mp4). Falls back to a plain brand moment
  // if not provided — see ELEVENLABS-ASSETS.md for what to generate + exact filenames.
  broll1Src?: string | null;
  broll2Src?: string | null;
};

const bySectionId = (id: string) => WALK_SECTIONS.find((s) => s.id === id)!;

/**
 * "From Scattered Opportunity to Focused Action" — the premium product walkthrough (~93s).
 * ONE-OFF flagship (see ads.config.mjs entry). Timing is derived from the actual VO word
 * count so narration and visuals stay in sync (re-run this math if the script changes —
 * see the comment block below). Real product screenshots, dip-to-navy dissolves, subtitles.
 * Voice: Christopher.
 */
const FPS = 30;
const BROLL_LEAD = 90; // 3s silent cold-open before narration starts

// ── Timing, derived from the ~90s VO's 10 sentences (proportional to word count) ──
// L1  0.0–9.8s   "Every nonprofit is surrounded by opportunity…"
// L2  9.8–21.1s  "The hard part was never that opportunity didn't exist…"
// L3  21.1–33.1s "Anansi Atlas changes that…"
// L4  33.1–39.5s "Your Opportunity Web Snapshot opens with a…30-day action plan…"
// L5  39.5–52.3s "Scroll deeper… funders… partners… government pathways…"
// L6  52.3–63.2s "We surface the community resources… readiness…"
// L7  63.2–74.5s "Every risk… flagged early… living pipeline… spotted… won."
// L8  74.5–81.3s "The result is simple. Instead of chasing scattered leads…"
// L9  81.3–86.2s "We're opening the Founding Atlas Partners Pilot…"
// L10 86.2–90.0s "Apply today at anansiatlas.com…"
const A = BROLL_LEAD;
const L = [0, 294, 633, 993, 1185, 1569, 1896, 2235, 2439, 2586, 2700].map((f) => f + A);
export const WALK_TOTAL = L[10];

const Center: React.FC<{ children: React.ReactNode; gap?: number }> = ({ children, gap = 22 }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap }}>
    {children}
  </AbsoluteFill>
);

const CAPTIONS: Caption[] = [
  { text: "Every nonprofit is surrounded by opportunity.", from: L[0], duration: L[1] - L[0] },
  { text: "But it was scattered — tabs, spreadsheets, inboxes.", from: L[1], duration: L[2] - L[1] },
  { text: "Anansi Atlas maps the web of opportunity around your mission.", from: L[2], duration: L[3] - L[2] },
  { text: "Your Snapshot opens with a 30-day action plan, ranked for your mission.", from: L[3], duration: L[4] - L[3] },
  { text: "Aligned funders, stronger partners, and the government pathways you never had time to find.", from: L[4], duration: L[5] - L[4] },
  { text: "Community resources, and readiness scored honestly — strong vs. a gap to close.", from: L[5], duration: L[6] - L[5] },
  { text: "Risks flagged early. Every opportunity carried from spotted, to won.", from: L[6], duration: L[7] - L[6] },
  { text: "Instead of chasing scattered leads, your team always knows where to focus next.", from: L[7], duration: L[8] - L[7] },
  { text: "We're opening the pilot to 19–20 mission-driven organizations.", from: L[8], duration: L[9] - L[8] },
  { text: "Apply today at anansiatlas.com/anansi-atlas", from: L[9], duration: L[10] - L[9] },
];

// Scattered-signal field for Act 1.
const SCATTER = ["funder portals", "spreadsheets", "grant deadlines", "partner lists", "emails", "program needs", "notes", "RFPs"];
const ScatterField: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill>
      {SCATTER.map((w, i) => {
        const x = [130, 640, 300, 780, 200, 690, 120, 560][i];
        const y = [210, 170, 760, 700, 470, 450, 640, 850][i];
        const drift = Math.sin((frame + i * 40) / 42) * 9;
        const op = interpolate(frame, [10 + i * 6, 34 + i * 6], [0, 0.8], { extrapolateRight: "clamp" });
        return (
          <div key={w} style={{ position: "absolute", left: x, top: y + drift, fontFamily: SANS, fontSize: 32, fontWeight: 700, color: BRAND.muted, opacity: op }}>
            {w}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

const Transform: React.FC = () => {
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [0, 140], [0, 1], { extrapolateRight: "clamp" });
  return <OrbWeb progress={progress} />;
};

const Section: React.FC<{ id: string; from: number; dur: number }> = ({ id, from, dur }) => {
  const s = bySectionId(id);
  return (
    <Sequence from={from} durationInFrames={dur}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 16 }}>
        <Rise>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div style={{ width: 10, height: 10, borderRadius: 999, background: s.tone === "teal" ? BRAND.teal : BRAND.gold }} />
            <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 28, letterSpacing: "0.14em", textTransform: "uppercase", color: BRAND.goldLight }}>
              {s.label}
            </div>
          </div>
        </Rise>
        <ScreenshotPanel src={staticFile(`screenshots/${s.shot}`)} label="anansiatlas.com" durationInFrames={dur} width={760} panY={[0, -14]} />
      </AbsoluteFill>
    </Sequence>
  );
};

export const ProductWalkthrough: React.FC<Props> = ({ audioSrc, broll1Src, broll2Src }) => {
  return (
    <NavyBG>
      {audioSrc ? (
        <Sequence from={BROLL_LEAD}>
          <Audio src={staticFile(audioSrc)} />
        </Sequence>
      ) : null}
      <ProgressRail totalFrames={WALK_TOTAL} />

      {/* ACT 0 — COLD OPEN (B-roll if provided, else a plain brand moment) */}
      <Sequence from={0} durationInFrames={BROLL_LEAD}>
        {broll1Src ? (
          <BRoll src={staticFile(broll1Src)} durationInFrames={BROLL_LEAD}>
            <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
              <Eyebrow>The Web of Opportunity</Eyebrow>
            </AbsoluteFill>
          </BRoll>
        ) : (
          <Center>
            <Eyebrow>The Web of Opportunity</Eyebrow>
          </Center>
        )}
      </Sequence>
      {broll2Src ? (
        <Sequence from={Math.floor(BROLL_LEAD / 2)} durationInFrames={Math.ceil(BROLL_LEAD / 2)}>
          <BRoll src={staticFile(broll2Src)} durationInFrames={Math.ceil(BROLL_LEAD / 2)} />
        </Sequence>
      ) : null}

      {/* ACT 1 — THE PROBLEM (L1–L2) */}
      <Sequence from={L[0]} durationInFrames={L[1] - L[0]}>
        <ScatterField />
        <Center>
          <Headline delay={10} size={62}>Every nonprofit is surrounded by opportunity.</Headline>
        </Center>
      </Sequence>
      <Sequence from={L[1]} durationInFrames={L[2] - L[1]}>
        <ScatterField />
        <Center>
          <Headline delay={6} size={68} color={BRAND.goldLight}>But it was scattered.</Headline>
        </Center>
      </Sequence>

      {/* ACT 2 — THE REVEAL: mission intake (L3) */}
      <Sequence from={L[2]} durationInFrames={(L[3] - L[2]) / 2}>
        <Center gap={20}>
          <Eyebrow>anansiatlas.com</Eyebrow>
          <ScreenshotPanel src={staticFile("screenshots/landing.png")} label="anansiatlas.com/anansi-atlas" durationInFrames={(L[3] - L[2]) / 2} width={860} panY={[0, -22]} />
        </Center>
      </Sequence>
      <Sequence from={L[2] + (L[3] - L[2]) / 2} durationInFrames={(L[3] - L[2]) / 2}>
        <Center gap={20}>
          <Eyebrow>Start with your mission</Eyebrow>
          <ScreenshotPanel src={staticFile("screenshots/organization.png")} label="anansiatlas.com/organization" durationInFrames={(L[3] - L[2]) / 2} width={860} panY={[0, -18]} />
        </Center>
      </Sequence>

      {/* ACT 3 — THE WALKTHROUGH (L4–L7), each beat sized to its VO clause */}
      <Section id="snapshot" from={L[3]} dur={L[4] - L[3]} />
      <Section id="funders" from={L[4]} dur={(L[5] - L[4]) / 3} />
      <Section id="partners" from={L[4] + (L[5] - L[4]) / 3} dur={(L[5] - L[4]) / 3} />
      <Section id="government" from={L[4] + (2 * (L[5] - L[4])) / 3} dur={(L[5] - L[4]) / 3} />
      <Section id="resources" from={L[5]} dur={(L[6] - L[5]) / 2} />
      <Section id="readiness" from={L[5] + (L[6] - L[5]) / 2} dur={(L[6] - L[5]) / 2} />
      <Section id="risks" from={L[6]} dur={(L[7] - L[6]) / 2} />
      <Section id="capital" from={L[6] + (L[7] - L[6]) / 2} dur={(L[7] - L[6]) / 2} />

      {/* ACT 4 — TRANSFORMATION (L8) */}
      <Sequence from={L[7]} durationInFrames={L[8] - L[7]}>
        <Transform />
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: 60 }}>
          <Rise delay={90}>
            <div style={{ fontFamily: SANS, fontSize: 30, fontWeight: 700, color: BRAND.goldLight }}>
              Scattered opportunity → focused action.
            </div>
          </Rise>
        </AbsoluteFill>
      </Sequence>

      {/* ACT 5 — PILOT CTA (L9–L10) */}
      <Sequence from={L[8]} durationInFrames={WALK_TOTAL - L[8]}>
        <Center gap={24}>
          <Eyebrow>Founding Atlas Partners Pilot</Eyebrow>
          <Headline delay={8} size={54}>We're selecting 19–20 organizations.</Headline>
          <div style={{ height: 4 }} />
          <LogoLockup delay={20} />
          <CTAButton delay={30}>Apply for the Pilot</CTAButton>
          <Rise delay={38}>
            <div style={{ fontFamily: SANS, fontSize: 28, fontWeight: 700, color: BRAND.goldLight, letterSpacing: "0.04em" }}>
              {SIGNUP_URL}
            </div>
          </Rise>
        </Center>
      </Sequence>

      <SceneDissolve
        boundaries={[
          BROLL_LEAD,
          L[1], L[2],
          L[2] + (L[3] - L[2]) / 2, L[3],
          L[4] + (L[5] - L[4]) / 3, L[4] + (2 * (L[5] - L[4])) / 3, L[5],
          L[5] + (L[6] - L[5]) / 2, L[6],
          L[6] + (L[7] - L[6]) / 2, L[7],
          L[8],
        ]}
      />
      <Subtitles captions={CAPTIONS} />
    </NavyBG>
  );
};
