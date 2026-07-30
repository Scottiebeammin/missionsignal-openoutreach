import React from "react";
import { AbsoluteFill, Audio, Img, Sequence, staticFile, useCurrentFrame, interpolate } from "remotion";
import { BRAND, SIGNUP_URL } from "../brand";
import {
  Caption,
  CTAButton,
  Eyebrow,
  Headline,
  LaptopScreenshotPanel,
  LogoLockup,
  NavyBG,
  OrbWeb,
  ProgressRail,
  Rise,
  SANS,
  SERIF,
  SceneDissolve,
  Subtitles,
} from "../components";

export type Props = {
  audioSrc?: string | null;
};

/**
 * "Who We Are + Platform Walkthrough" — cold-outreach video, revised per Scott's 2026-07-04
 * conversion review ("fix it" pass). Changes from the original approved script:
 *  1. Sharper cold-open hook (was the abstract "Every mission has a web of opportunity around
 *     it" — cold viewers don't grant patience to a category statement; now a concrete loss-
 *     aversion line).
 *  2. An early "real software" screenshot tease during the Product Reveal beat, so there's
 *     proof before the full brand argument finishes.
 *  3. "Picture this mapped to your own mission" folded directly into the Walkthrough Bridge VO
 *     line, so the demo org's screenshots (Horizon Youth Collective, visibly modest scores) read
 *     as "picture yours" rather than "here's someone else's data."
 *  4. Price + scarcity ("$150/month, locked for life, while founding seats remain") added to the
 *     close — the previous cut never stated the offer, the single biggest missing lever.
 *  5. The two negation lines ("Not as a generic list... / Not as another database...") tightened
 *     into one beat.
 *  6. A persistent small "anansiatlas.com" corner tag for sound-off / skimming viewers who'd
 *     otherwise only see the URL once at the very end.
 *
 * TIMING: frame-accurate, generated via scripts/gen-vo-timestamped.mjs (ElevenLabs
 * /with-timestamps -> public/who-we-are-walkthrough-vo.alignment.json). Every boundary below is
 * `round(startTimeSeconds * 30) + LEAD`. Re-run the script and recompute if the VO text changes.
 */
const LEAD = 60; // 2s silent cold-open before narration begins
const CTA_HOLD = 240; // 8s hold on the closing CTA after the VO ends
const VO_END = 3657; // round(119.908 * 30) + LEAD

const T = {
  somewhereRightNow: 60,
  cascadeFunders: 220,
  cascadePartners: 245,
  cascadeResources: 269,
  cascadeGovernment: 300,
  cascadeRelationships: 340,
  cascadeRisks: 376,
  cascadeNextSteps: 399,
  challenge: 441,
  evenStrong: 726,
  thatIsTheProblem: 863,
  anansiAtlasHelps: 971,
  notGenericList: 1146,
  notAnotherDatabase: 1190,
  clearerWay: 1259,
  walkthroughBridge: 1515,
  dashboardFocus: 1662,
  whatToDoNext: 1729,
  readinessSignals: 1775,
  relationshipOpportunities: 1810,
  pathwayHealth: 1862,
  clearerViewStands: 1897,
  webPlacesCenter: 2045,
  aroundItOrganizes: 2155,
  snapshotTurnsMap: 2499,
  itGivesYourTeam: 2632,
  soInsteadOfChasing: 2869,
  thisIsAnansiAtlas: 3054,
  webOfOpportunityMapped: 3128,
  weAreCurrentlyInviting: 3225,
  applyAt: 3569,
};

export const WALK_TOTAL = VO_END + CTA_HOLD;

const CAPTIONS: Caption[] = [
  { text: "Somewhere right now, a funder is aligned with your mission — and you don't know it exists.", from: T.somewhereRightNow, duration: T.cascadeFunders - T.somewhereRightNow },
  { text: "Funders. Partners. Resources. Government pathways. Relationships. Risks. Next steps.", from: T.cascadeFunders, duration: T.challenge - T.cascadeFunders },
  { text: "The challenge is that most of that opportunity is scattered — across websites, portals, conversations, spreadsheets, deadlines, and institutional knowledge.", from: T.challenge, duration: T.evenStrong - T.challenge },
  { text: "So even strong organizations can miss what is already connected to their mission.", from: T.evenStrong, duration: T.thatIsTheProblem - T.evenStrong },
  { text: "That is the problem Anansi Atlas is built to solve.", from: T.thatIsTheProblem, duration: T.anansiAtlasHelps - T.thatIsTheProblem },
  { text: "Anansi Atlas helps mission-driven organizations map the web of opportunity around their mission.", from: T.anansiAtlasHelps, duration: T.notGenericList - T.anansiAtlasHelps },
  { text: "Not a generic list. Not another database to search through.", from: T.notGenericList, duration: T.clearerWay - T.notGenericList },
  { text: "But a clearer way to see the funders, partners, resources, pathways, readiness gaps, risks, and next steps that may matter most.", from: T.clearerWay, duration: T.walkthroughBridge - T.clearerWay },
  { text: "Here is what that looks like inside the platform — picture this mapped to your own mission.", from: T.walkthroughBridge, duration: T.dashboardFocus - T.walkthroughBridge },
  { text: "The dashboard begins with focus.", from: T.dashboardFocus, duration: T.whatToDoNext - T.dashboardFocus },
  { text: "What to do next. Readiness signals. Relationship opportunities. Pathway health.", from: T.whatToDoNext, duration: T.clearerViewStands - T.whatToDoNext },
  { text: "A clearer view of where your organization stands — and where it can move next.", from: T.clearerViewStands, duration: T.webPlacesCenter - T.clearerViewStands },
  { text: "The Opportunity Web places your mission at the center.", from: T.webPlacesCenter, duration: T.aroundItOrganizes - T.webPlacesCenter },
  { text: "Around it, Anansi Atlas organizes the opportunities and connections surrounding your work — funders, partners, government pathways, resources, risks, and practical next steps.", from: T.aroundItOrganizes, duration: T.snapshotTurnsMap - T.aroundItOrganizes },
  { text: "The Opportunity Web Snapshot turns that map into action.", from: T.snapshotTurnsMap, duration: T.itGivesYourTeam - T.snapshotTurnsMap },
  { text: "It gives your team a mission-centered brief with aligned opportunities, readiness insights, and a practical 30-day action plan.", from: T.itGivesYourTeam, duration: T.soInsteadOfChasing - T.itGivesYourTeam },
  { text: "So instead of chasing scattered leads, your organization can move with more clarity and focus.", from: T.soInsteadOfChasing, duration: T.thisIsAnansiAtlas - T.soInsteadOfChasing },
  { text: "This is Anansi Atlas.", from: T.thisIsAnansiAtlas, duration: T.webOfOpportunityMapped - T.thisIsAnansiAtlas },
  { text: "The Web of Opportunity, mapped around your mission.", from: T.webOfOpportunityMapped, duration: T.weAreCurrentlyInviting - T.webOfOpportunityMapped },
  { text: "We're currently inviting a limited group of mission-driven organizations to the Founding Atlas Partners Pilot — $150 a month, locked for life, while founding seats remain.", from: T.weAreCurrentlyInviting, duration: T.applyAt - T.weAreCurrentlyInviting },
  { text: "Apply at anansiatlas.com.", from: T.applyAt, duration: VO_END - T.applyAt },
];

const Center: React.FC<{ children: React.ReactNode; gap?: number }> = ({ children, gap = 22 }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap }}>
    {children}
  </AbsoluteFill>
);

// NOTE: was OffthreadVideo(staticFile("broll/globe-loop.mp4")) — that asset turned out to be a
// captured clip from a different composition with its captions burned into the pixels (visible
// as a faint ghost line during the cold open). Replaced with a clean pulsing glow; no video
// dependency, no contamination risk.
const GlobeOpen: React.FC<{ durationInFrames: number }> = ({ durationInFrames }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, durationInFrames], [0.5, 0.15], { extrapolateRight: "clamp" });
  const breathe = 0.85 + 0.15 * Math.sin(frame / 40);
  return (
    <AbsoluteFill style={{ opacity }}>
      <AbsoluteFill
        style={{
          opacity: breathe,
          background:
            "radial-gradient(60% 55% at 50% 40%, rgba(212,160,23,0.28) 0%, rgba(212,160,23,0) 55%), radial-gradient(50% 45% at 50% 40%, rgba(58,108,200,0.2) 0%, rgba(58,108,200,0) 60%)",
        }}
      />
    </AbsoluteFill>
  );
};

/** One word/phrase of the cascade, mounted exactly when it's spoken (own Sequence, not a
 *  shared-timeline delay) so it can never drift out of sync with the VO. */
const CascadeWord: React.FC<{ text: string; tone: "gold" | "white" }> = ({ text, tone }) => {
  const frame = useCurrentFrame();
  const op = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: "clamp" });
  const rise = interpolate(frame, [0, 8], [18, 0], { extrapolateRight: "clamp" });
  return (
    <div style={{ opacity: op, transform: `translateY(${rise}px)`, fontFamily: SERIF, fontWeight: 700, fontSize: 46, color: tone === "gold" ? BRAND.goldLight : BRAND.white }}>
      {text}
    </div>
  );
};

const ScreenSection: React.FC<{ shot: string; label: string; from: number; dur: number; children?: React.ReactNode }> = ({
  shot,
  label,
  from,
  dur,
  children,
}) => (
  <Sequence from={from} durationInFrames={dur}>
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 18 }}>
      <Rise>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{ width: 10, height: 10, borderRadius: 999, background: BRAND.gold }} />
          <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 28, letterSpacing: "0.14em", textTransform: "uppercase", color: BRAND.goldLight }}>
            {label}
          </div>
        </div>
      </Rise>
      <LaptopScreenshotPanel src={staticFile(`screenshots/${shot}`)} label="anansiatlas.com" durationInFrames={dur} width={700} panY={[0, -16]} />
      {children}
    </AbsoluteFill>
  </Sequence>
);

/** Persistent small corner tag so sound-off/skimming viewers see the URL more than once. */
const CornerTag: React.FC = () => (
  <AbsoluteFill style={{ alignItems: "flex-end", justifyContent: "flex-start", padding: "34px 30px 0 0" }}>
    <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 17, color: BRAND.muted, opacity: 0.6, letterSpacing: "0.03em" }}>
      anansiatlas.com
    </div>
  </AbsoluteFill>
);

export const WhoWeAreWalkthrough: React.FC<Props> = ({ audioSrc }) => {
  return (
    <NavyBG>
      {audioSrc ? (
        <Sequence from={LEAD}>
          <Audio src={staticFile(audioSrc)} />
        </Sequence>
      ) : null}
      <ProgressRail totalFrames={WALK_TOTAL} />

      {/* persistent URL tag — hidden during the cold open (logo already establishes brand) and
          during the closing CTA (URL is already large and center-stage there) */}
      <Sequence from={T.challenge} durationInFrames={T.thisIsAnansiAtlas - T.challenge}>
        <CornerTag />
      </Sequence>

      {/* ══════════ SECTION 1 — OPENING / BRAND BELIEF ══════════ */}
      <Sequence from={0} durationInFrames={T.cascadeFunders}>
        <GlobeOpen durationInFrames={T.cascadeFunders} />
      </Sequence>

      <Sequence from={T.somewhereRightNow} durationInFrames={T.cascadeFunders - T.somewhereRightNow}>
        <Center gap={16}>
          <Rise delay={0}>
            <Img src={staticFile("logo-mark.png")} style={{ width: 76, height: 76 }} />
          </Rise>
          <Headline delay={8} size={46}>Somewhere right now, a funder is aligned with your mission.</Headline>
          <Rise delay={20}>
            <div style={{ fontFamily: SANS, fontSize: 26, fontWeight: 700, color: BRAND.goldLight }}>You don't know it exists.</div>
          </Rise>
        </Center>
      </Sequence>

      {/* cascade — each word is its own Sequence starting at its exact spoken timestamp */}
      <Sequence from={T.cascadeFunders} durationInFrames={T.challenge - T.cascadeFunders}>
        <Center gap={20}>
          <Sequence from={0} layout="none"><CascadeWord text="Funders." tone="gold" /></Sequence>
          <Sequence from={T.cascadePartners - T.cascadeFunders} layout="none"><CascadeWord text="Partners." tone="white" /></Sequence>
          <Sequence from={T.cascadeResources - T.cascadeFunders} layout="none"><CascadeWord text="Resources." tone="gold" /></Sequence>
          <Sequence from={T.cascadeGovernment - T.cascadeFunders} layout="none"><CascadeWord text="Government pathways." tone="white" /></Sequence>
          <Sequence from={T.cascadeRelationships - T.cascadeFunders} layout="none"><CascadeWord text="Relationships." tone="gold" /></Sequence>
          <Sequence from={T.cascadeRisks - T.cascadeFunders} layout="none"><CascadeWord text="Risks." tone="white" /></Sequence>
          <Sequence from={T.cascadeNextSteps - T.cascadeFunders} layout="none"><CascadeWord text="Next steps." tone="gold" /></Sequence>
        </Center>
      </Sequence>

      <Sequence from={T.challenge} durationInFrames={T.evenStrong - T.challenge}>
        <Center gap={16}>
          <Eyebrow delay={0}>The Challenge</Eyebrow>
          <Rise delay={8}>
            <div style={{ fontFamily: SANS, fontSize: 32, fontWeight: 700, color: BRAND.white, textAlign: "center", maxWidth: 780, lineHeight: 1.4 }}>
              Most of that opportunity is scattered — websites, portals, conversations, spreadsheets, deadlines, institutional knowledge.
            </div>
          </Rise>
        </Center>
      </Sequence>

      <Sequence from={T.evenStrong} durationInFrames={T.thatIsTheProblem - T.evenStrong}>
        <Center>
          <Headline delay={6} size={46}>Even strong organizations can miss what's already connected to their mission.</Headline>
        </Center>
      </Sequence>

      <Sequence from={T.thatIsTheProblem} durationInFrames={T.anansiAtlasHelps - T.thatIsTheProblem}>
        <Center gap={14}>
          <div style={{ fontFamily: SANS, fontSize: 24, fontWeight: 700, color: BRAND.muted, letterSpacing: "0.1em", textTransform: "uppercase" }}>
            That's the problem
          </div>
          <Headline delay={6} size={62}>Anansi Atlas is built to solve.</Headline>
        </Center>
      </Sequence>

      {/* ══════════ SECTION 2 — PRODUCT REVEAL ══════════ */}
      <Sequence from={T.anansiAtlasHelps} durationInFrames={T.notGenericList - T.anansiAtlasHelps}>
        <AbsoluteFill style={{ opacity: 0.85 }}>
          <div style={{ position: "absolute", inset: 0, transform: "scale(0.56) translateY(-220px)" }}>
            <OrbWeb progress={1} />
          </div>
        </AbsoluteFill>
        <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(13,27,61,0) 0%, rgba(13,27,61,0) 52%, rgba(13,27,61,0.9) 68%, rgba(13,27,61,0.98) 100%)" }} />
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: 170 }}>
          <div style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 48, color: BRAND.white, textAlign: "center", maxWidth: 820, textShadow: "0 8px 30px rgba(0,0,0,0.6)" }}>
            Anansi Atlas maps the <span style={{ color: BRAND.goldLight }}>web of opportunity</span> around your mission.
          </div>
        </AbsoluteFill>
        {/* early proof tease — a real screenshot glimpse before the full walkthrough, so there's
            evidence this is working software before the brand argument finishes */}
        <Sequence from={30} layout="none">
          <AbsoluteFill style={{ alignItems: "flex-end", justifyContent: "flex-end", padding: "0 40px 40px 0" }}>
            <Rise delay={0}>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
                <div
                  style={{
                    width: 230,
                    borderRadius: 10,
                    overflow: "hidden",
                    border: `1px solid ${BRAND.gold}`,
                    boxShadow: "0 16px 40px rgba(0,0,0,0.5)",
                    opacity: 0.92,
                  }}
                >
                  <Img src={staticFile("screenshots/shot-dashboard3.png")} style={{ width: "100%", display: "block" }} />
                </div>
                <div style={{ fontFamily: SANS, fontSize: 15, fontWeight: 700, color: BRAND.goldLight, letterSpacing: "0.06em" }}>
                  Real software →
                </div>
              </div>
            </Rise>
          </AbsoluteFill>
        </Sequence>
      </Sequence>

      <Sequence from={T.notGenericList} durationInFrames={T.notAnotherDatabase - T.notGenericList}>
        <Center gap={22}>
          <Rise delay={0}>
            <div style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 46, color: BRAND.muted, textDecoration: "line-through", textDecorationColor: BRAND.rose }}>
              Not a generic list.
            </div>
          </Rise>
        </Center>
      </Sequence>
      <Sequence from={T.notAnotherDatabase} durationInFrames={T.clearerWay - T.notAnotherDatabase}>
        <Center gap={22}>
          <Rise delay={0}>
            <div style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 46, color: BRAND.muted, textDecoration: "line-through", textDecorationColor: BRAND.rose }}>
              Not another database to search.
            </div>
          </Rise>
        </Center>
      </Sequence>

      <Sequence from={T.clearerWay} durationInFrames={T.walkthroughBridge - T.clearerWay}>
        <Center gap={10}>
          <Headline delay={4} size={40}>
            A clearer way to see the funders, partners, resources, pathways, readiness gaps, risks, and next steps that matter most.
          </Headline>
        </Center>
      </Sequence>

      {/* ══════════ SECTION 3 — WALKTHROUGH BRIDGE ══════════ */}
      <Sequence from={T.walkthroughBridge} durationInFrames={T.dashboardFocus - T.walkthroughBridge}>
        <Center gap={10}>
          <Eyebrow delay={0}>The Platform</Eyebrow>
          <Headline delay={6} size={40}>Here's what that looks like inside.</Headline>
          <Rise delay={22}>
            <div style={{ fontFamily: SANS, fontSize: 26, fontWeight: 700, color: BRAND.goldLight, textAlign: "center" }}>
              Picture this mapped to your own mission.
            </div>
          </Rise>
        </Center>
      </Sequence>

      {/* ══════════ SECTION 4 — DASHBOARD ══════════ */}
      <ScreenSection shot="shot-dashboard3.png" label="The Dashboard — Focus" from={T.dashboardFocus} dur={T.webPlacesCenter - T.dashboardFocus}>
        <div style={{ display: "flex", gap: 14, marginTop: 4, flexWrap: "wrap", justifyContent: "center", maxWidth: 700 }}>
          {[
            { t: "What To Do Next", at: T.whatToDoNext - T.dashboardFocus },
            { t: "Readiness Signals", at: T.readinessSignals - T.dashboardFocus },
            { t: "Relationship Opportunities", at: T.relationshipOpportunities - T.dashboardFocus },
            { t: "Pathway Health", at: T.pathwayHealth - T.dashboardFocus },
          ].map(({ t, at }) => (
            <Sequence key={t} from={at} layout="none">
              <div
                style={{
                  fontFamily: SANS,
                  fontSize: 18,
                  fontWeight: 700,
                  color: BRAND.goldLight,
                  border: `1px solid ${BRAND.gold}`,
                  borderRadius: 999,
                  padding: "6px 16px",
                  opacity: 0.9,
                }}
              >
                {t}
              </div>
            </Sequence>
          ))}
        </div>
      </ScreenSection>

      {/* ══════════ SECTION 5 — OPPORTUNITY WEB ══════════ */}
      <ScreenSection shot="shot-web-clean.png" label="The Opportunity Web" from={T.webPlacesCenter} dur={T.snapshotTurnsMap - T.webPlacesCenter} />

      {/* ══════════ SECTION 6 — OPPORTUNITY WEB SNAPSHOT ══════════ */}
      <ScreenSection shot="shot-snapshot3.png" label="The Snapshot — 30-Day Plan" from={T.snapshotTurnsMap} dur={T.thisIsAnansiAtlas - T.snapshotTurnsMap} />

      {/* ══════════ SECTION 7 — CLOSING CTA (now with price + scarcity) ══════════ */}
      <Sequence from={T.thisIsAnansiAtlas} durationInFrames={WALK_TOTAL - T.thisIsAnansiAtlas}>
        <Center gap={16}>
          <Rise delay={4}>
            <Img src={staticFile("logo-mark.png")} style={{ width: 88, height: 88 }} />
          </Rise>
          <LogoLockup delay={10} />
          <Sequence from={T.weAreCurrentlyInviting - T.thisIsAnansiAtlas} layout="none">
            <Rise delay={0}>
              <div style={{ fontFamily: SANS, fontSize: 23, fontWeight: 700, color: BRAND.white, textAlign: "center", maxWidth: 740 }}>
                Now inviting a limited group of mission-driven organizations to the Founding Atlas Partners Pilot.
              </div>
            </Rise>
          </Sequence>
          <Sequence from={T.weAreCurrentlyInviting - T.thisIsAnansiAtlas + 90} layout="none">
            <Rise delay={0}>
              <div style={{ fontFamily: SANS, fontSize: 30, fontWeight: 900, color: BRAND.goldLight, textAlign: "center" }}>
                $150/month — locked for life, while founding seats remain.
              </div>
            </Rise>
          </Sequence>
          <Sequence from={T.applyAt - T.thisIsAnansiAtlas} layout="none">
            <CTAButton delay={0}>Apply Now</CTAButton>
          </Sequence>
          <Sequence from={T.applyAt - T.thisIsAnansiAtlas + 10} layout="none">
            <Rise delay={0}>
              <div style={{ fontFamily: SANS, fontSize: 26, fontWeight: 700, color: BRAND.goldLight, letterSpacing: "0.04em" }}>
                {SIGNUP_URL}
              </div>
            </Rise>
          </Sequence>
        </Center>
      </Sequence>

      <SceneDissolve
        boundaries={[
          T.cascadeFunders, T.challenge, T.evenStrong, T.thatIsTheProblem, T.anansiAtlasHelps, T.notGenericList,
          T.notAnotherDatabase, T.clearerWay, T.walkthroughBridge, T.dashboardFocus, T.webPlacesCenter,
          T.snapshotTurnsMap, T.thisIsAnansiAtlas,
        ]}
      />
      <Subtitles captions={CAPTIONS} />
    </NavyBG>
  );
};
