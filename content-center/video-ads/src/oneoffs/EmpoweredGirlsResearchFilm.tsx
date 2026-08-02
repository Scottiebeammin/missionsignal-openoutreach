import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { BRAND } from "../brand";
import {
  ActBridge,
  Caption,
  CTAButton,
  Eyebrow,
  NavyBG,
  NodeField,
  OrbWeb,
  Rise,
  SANS,
  SERIF,
  SceneDissolve,
  ScreenshotPanel,
  Subtitles,
  ThreadRule,
} from "../components";
import { FMTS, FmtCtx, PreviewProfileScreen } from "./AnansiUniversalCommercial";

// ============================================================================
// CAMPAIGN VIDEO 3 — EMPOWERED GIRLS ORLANDO / ORANGE COUNTY RESEARCH FILM
// (~4:47, 1920×1080). A personalized research presentation demonstrating the
// depth of Anansi Atlas research around one real organization.
//
// ACCURACY SPINE — every claim on screen or in VO traces to the source log
// (ANANSI_ATLAS_VIDEO_CAMPAIGN/14_SOURCE_LOG/). EGI identity verified against
// Sunbiz + empoweredgirlsinc.org; the mission quote is their own site language.
// Funders/partners/government are POTENTIALLY ALIGNED framings only. The
// workspace screens (hd-*.png) are EGI's real Anansi Atlas workspace —
// authorized by Scott 2026-07-29. EGI impact figures deliberately absent.
// ============================================================================

const easeOut3 = (t: number) => {
  const c = Math.min(1, Math.max(0, t));
  return 1 - Math.pow(1 - c, 3);
};

// Measured via `node scripts/vo-line-slices.mjs EmpoweredGirlsResearchFilm`
const LINE: [number, number][] = [
  [0, 535],
  [546, 887],
  [899, 1264],
  [1278, 1870],
  [1875, 2405],
  [2411, 3100],
  [3120, 3327],
  [3359, 4028],
  [4038, 4711],
  [4715, 5263],
  [5266, 5744],
  [5759, 5972],
  [5981, 6438],
  [6447, 7009],
  [7018, 7403],
];
const DUR = LINE.map(([a, b]) => b - a);
const TITLE = 240;
const END_CARD = 200;
const LEAD = [30, 25, 25, 30, 35, 30, 25, 30, 25, 30, 40, 25, 25, 35, 30];
const TAIL = [20, 25, 30, 40, 25, 25, 45, 25, 25, 35, 20, 20, 35, 40, 60];

const B: number[] = [0, TITLE];
for (let i = 0; i < LINE.length; i++) B.push(B[B.length - 1] + LEAD[i] + DUR[i] + TAIL[i]);
B.push(B[B.length - 1] + END_CARD);
export const EGI_FILM_TOTAL = B[B.length - 1]; // 8594f ≈ 4:46 @30fps
const VO_AT = LINE.map((_, i) => B[i + 1] + LEAD[i]);

const VO_PAD = 5;
const VO_FADE = 4;
const SLICE = LINE.map(([s, e], i) => {
  const prevEnd = i > 0 ? LINE[i - 1][1] : 0;
  const nextStart = i < LINE.length - 1 ? LINE[i + 1][0] : e + 2 * VO_PAD;
  const padL = Math.min(VO_PAD, Math.floor((s - prevEnd) / 2));
  const padR = Math.min(VO_PAD, Math.floor((nextStart - e) / 2));
  return { from: s - padL, to: e + padR, at: VO_AT[i] - padL };
});

const ORB = 1080;
// Bare transform div collapses AbsoluteFill children to 0×0 — explicit box required.
const OrbWebBox: React.FC<{ scale: number; progress: number }> = ({ scale, progress }) => (
  <div style={{ position: "relative", width: ORB, height: ORB, transform: `scale(${scale})` }}>
    <OrbWeb progress={progress} />
  </div>
);

// ---------------------------------------------------------------------------
// Shared building blocks
// ---------------------------------------------------------------------------
const SourceTag: React.FC<{ children: React.ReactNode; delay?: number }> = ({ children, delay = 0 }) => (
  <Rise delay={delay}>
    <div
      style={{
        fontFamily: SANS,
        fontWeight: 700,
        fontSize: 17,
        letterSpacing: "0.14em",
        color: BRAND.muted,
        textAlign: "center",
      }}
    >
      {children}
    </div>
  </Rise>
);

type PathwayCard = { org: string; program: string; note: string };
const PathwayCards: React.FC<{
  cards: PathwayCard[];
  chip: string;
  sourceLine: string;
  startAt?: number;
}> = ({ cards, chip, sourceLine, startAt = 30 }) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div style={{ display: "flex", gap: 40, padding: "0 90px" }}>
        {cards.map((c, i) => {
          const a = easeOut3((frame - startAt - i * 55) / 24);
          if (a <= 0) return null;
          return (
            <div
              key={c.org}
              style={{
                opacity: a,
                transform: `translateY(${(1 - a) * 28}px)`,
                width: 520,
                background: "rgba(23,40,79,0.85)",
                border: "1px solid rgba(159,176,198,0.3)",
                borderRadius: 18,
                padding: "34px 36px",
                display: "flex",
                flexDirection: "column",
                gap: 16,
              }}
            >
              <div
                style={{
                  fontFamily: SANS,
                  fontWeight: 800,
                  fontSize: 19,
                  letterSpacing: "0.16em",
                  color: BRAND.muted,
                }}
              >
                {c.org}
              </div>
              <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 34, color: BRAND.white, lineHeight: 1.15 }}>
                {c.program}
              </div>
              <div style={{ fontFamily: SANS, fontWeight: 600, fontSize: 22, color: BRAND.ink, lineHeight: 1.4 }}>
                {c.note}
              </div>
              <div
                style={{
                  alignSelf: "flex-start",
                  fontFamily: SANS,
                  fontWeight: 800,
                  fontSize: 14,
                  letterSpacing: "0.14em",
                  color: BRAND.goldLight,
                  border: `1px dashed ${BRAND.gold}`,
                  borderRadius: 999,
                  padding: "7px 16px",
                  marginTop: 4,
                }}
              >
                {chip}
              </div>
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", bottom: "7%", width: "100%" }}>
        <SourceTag delay={startAt + 140}>{sourceLine}</SourceTag>
      </div>
    </AbsoluteFill>
  );
};

const ShotScene: React.FC<{ src: string; label: string; dur: number; chip?: string }> = ({
  src,
  label,
  dur,
  chip,
}) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
    <ScreenshotPanel src={staticFile(src)} label={label} durationInFrames={dur} width={1330} />
    {chip ? (
      // plain absolute wrapper OUTSIDE Rise — Rise's transform creates a containing
      // block, so an absolute chip inside it anchors to the wrong box
      <div style={{ position: "absolute", top: 54, right: 90 }}>
        <Rise delay={20}>
          <div
            style={{
              fontFamily: SANS,
              fontWeight: 800,
              fontSize: 18,
              letterSpacing: "0.16em",
              color: BRAND.goldLight,
              border: `1px solid ${BRAND.gold}`,
              borderRadius: 999,
              padding: "9px 20px",
              background: "rgba(13,27,61,0.85)",
              whiteSpace: "nowrap",
            }}
          >
            {chip}
          </div>
        </Rise>
      </div>
    ) : null}
  </AbsoluteFill>
);

// ---------------------------------------------------------------------------
// Scenes
// ---------------------------------------------------------------------------
const S01Title: React.FC = () => {
  const frame = useCurrentFrame();
  const emblemIn = easeOut3((frame - 24) / 26);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <ThreadRule from={[26, 42]} to={[74, 42]} at={4} draw={26} hold={220} out={0} opacity={0.5} />
      <NodeField w={1920} h={1080} count={9} at={12} fadeIn={32} opacity={0.15} />
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 24, marginTop: -120 }}>
        {emblemIn > 0 ? (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 22,
              opacity: emblemIn,
              transform: `scale(${0.93 + 0.07 * emblemIn})`,
            }}
          >
            <Img src={staticFile("anansi-emblem-785.png")} style={{ width: 116, height: 116 }} />
            <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 27, letterSpacing: "0.26em", color: BRAND.white }}>
              ANANSI ATLAS
            </div>
          </div>
        ) : null}
        <Eyebrow delay={58}>The Web of Opportunity</Eyebrow>
      </div>
      <div style={{ position: "absolute", bottom: "22%", width: "100%", textAlign: "center" }}>
        <Rise delay={110}>
          <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 64, color: BRAND.white }}>
            Empowered Girls
          </div>
        </Rise>
        <Rise delay={132}>
          <div
            style={{
              marginTop: 14,
              fontFamily: SANS,
              fontWeight: 800,
              fontSize: 23,
              letterSpacing: "0.22em",
              color: BRAND.goldLight,
              textTransform: "uppercase",
            }}
          >
            Orlando / Orange County Opportunity Research Film
          </div>
        </Rise>
      </div>
    </AbsoluteFill>
  );
};

const PROGRAMS = ["Life skills", "Mentorship", "Health & wellness", "Academic empowerment"];

const S02Mission: React.FC = () => {
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <NodeField w={1920} h={1080} count={11} seed={14} at={0} fadeIn={40} opacity={0.13} />
      <div style={{ textAlign: "center" }}>
        <Eyebrow delay={20}>Orlando · Florida</Eyebrow>
        <Rise delay={40}>
          <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 110, color: BRAND.white, marginTop: 20 }}>
            Empowered Girls
          </div>
        </Rise>
        <Rise delay={70}>
          <div
            style={{
              fontFamily: SANS,
              fontWeight: 800,
              fontSize: 21,
              letterSpacing: "0.2em",
              color: BRAND.muted,
              marginTop: 18,
            }}
          >
            FOUNDED 2018 · ORANGE COUNTY, FLORIDA
          </div>
        </Rise>
        <div style={{ display: "flex", gap: 18, justifyContent: "center", marginTop: 48 }}>
          {PROGRAMS.map((p, i) => (
            <Rise key={p} delay={130 + i * 60}>
              <div
                style={{
                  fontFamily: SANS,
                  fontWeight: 700,
                  fontSize: 26,
                  color: BRAND.ink,
                  background: "rgba(23,40,79,0.9)",
                  border: `1px solid ${BRAND.gold}`,
                  borderRadius: 999,
                  padding: "14px 30px",
                }}
              >
                {p}
              </div>
            </Rise>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

const S03Quote: React.FC = () => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
    <div style={{ maxWidth: 1340, textAlign: "center" }}>
      <Rise delay={20}>
        <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 120, color: BRAND.gold, lineHeight: 0.6 }}>
          "
        </div>
      </Rise>
      <Rise delay={34}>
        <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 52, color: BRAND.white, lineHeight: 1.35 }}>
          Empowering girls to grow into confident, capable women through life skills, mentorship, and
          programs that help them overcome barriers and achieve success.
        </div>
      </Rise>
      <div style={{ marginTop: 40 }}>
        <SourceTag delay={130}>THEIR MISSION · EMPOWEREDGIRLSINC.ORG</SourceTag>
      </div>
    </div>
  </AbsoluteFill>
);

const CountUp: React.FC<{ to: number; at: number; dur?: number; size?: number }> = ({
  to,
  at,
  dur = 60,
  size = 150,
}) => {
  const frame = useCurrentFrame();
  const p = easeOut3((frame - at) / dur);
  const v = Math.round(to * p);
  return (
    <div
      style={{
        fontFamily: SERIF,
        fontWeight: 600,
        fontSize: size,
        color: BRAND.white,
        letterSpacing: "-0.01em",
        fontVariantNumeric: "tabular-nums",
        opacity: p > 0 ? 1 : 0,
      }}
    >
      {v.toLocaleString("en-US")}
    </div>
  );
};

const S04County: React.FC = () => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
    <div style={{ textAlign: "center" }}>
      <Eyebrow delay={16}>Children under 18 in Orange County</Eyebrow>
      <div style={{ display: "flex", justifyContent: "center" }}>
        <CountUp to={322533} at={40} dur={70} />
      </div>
      <div style={{ display: "flex", gap: 26, justifyContent: "center", marginTop: 36 }}>
        <Rise delay={150}>
          <div
            style={{
              fontFamily: SANS,
              fontWeight: 800,
              fontSize: 30,
              color: BRAND.goldLight,
              border: `1px solid ${BRAND.gold}`,
              borderRadius: 999,
              padding: "16px 34px",
            }}
          >
            1 IN 5 RESIDENTS
          </div>
        </Rise>
        <Rise delay={210}>
          <div
            style={{
              fontFamily: SANS,
              fontWeight: 800,
              fontSize: 30,
              color: BRAND.white,
              border: "1px solid rgba(159,176,198,0.4)",
              borderRadius: 999,
              padding: "16px 34px",
            }}
          >
            ~1 IN 6 BELOW THE POVERTY LINE
          </div>
        </Rise>
      </div>
      <div style={{ marginTop: 44 }}>
        <SourceTag delay={250}>U.S. CENSUS BUREAU · AMERICAN COMMUNITY SURVEY 2024</SourceTag>
      </div>
    </div>
  </AbsoluteFill>
);

const ConfBar: React.FC<{ pct: number; label: string; at: number; gold?: boolean }> = ({
  pct,
  label,
  at,
  gold = false,
}) => {
  const frame = useCurrentFrame();
  const p = easeOut3((frame - at) / 55);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 26, opacity: p > 0 ? 1 : 0 }}>
      <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 26, color: BRAND.muted, width: 250, textAlign: "right" }}>
        {label}
      </div>
      <div style={{ width: 760, height: 30, borderRadius: 8, background: "rgba(159,176,198,0.15)", overflow: "hidden" }}>
        <div
          style={{
            height: "100%",
            width: `${pct * p}%`,
            borderRadius: 8,
            background: gold
              ? `linear-gradient(90deg, ${BRAND.gold}, ${BRAND.goldLight})`
              : "rgba(159,176,198,0.55)",
          }}
        />
      </div>
      <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 46, color: gold ? BRAND.goldLight : BRAND.white, width: 140 }}>
        {Math.round(pct * p)}%
      </div>
    </div>
  );
};

const S05Girls: React.FC = () => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
    <div style={{ display: "flex", flexDirection: "column", gap: 30, alignItems: "center" }}>
      <Eyebrow delay={14}>Girls who describe themselves as confident — 5th grade</Eyebrow>
      <ConfBar pct={86} label="2017" at={40} />
      <ConfBar pct={68} label="2023" at={95} gold />
      <div style={{ marginTop: 6 }}>
        <SourceTag delay={170}>THE GIRLS' INDEX · RULING OUR EXPERIENCES (2023) · 17,000+ GIRLS SURVEYED</SourceTag>
      </div>
      <Rise delay={300}>
        <div
          style={{
            marginTop: 30,
            fontFamily: SERIF,
            fontWeight: 600,
            fontSize: 46,
            color: BRAND.white,
            textAlign: "center",
          }}
        >
          And an estimated <span style={{ color: BRAND.goldLight }}>1 in 3</span> young people grow up
          without a mentor.
        </div>
      </Rise>
      <SourceTag delay={340}>MENTOR · "THE MENTORING EFFECT" (NATIONAL ESTIMATE, 2014)</SourceTag>
      <Rise delay={470}>
        <div
          style={{
            marginTop: 26,
            fontFamily: SANS,
            fontWeight: 800,
            fontSize: 24,
            letterSpacing: "0.2em",
            color: BRAND.goldLight,
          }}
        >
          THIS IS THE FIELD EMPOWERED GIRLS STANDS IN
        </div>
      </Rise>
    </div>
  </AbsoluteFill>
);

const ECO_LABELS = ["FUNDERS", "SCHOOLS", "GOVERNMENT", "COMMUNITY", "BUSINESSES", "PEOPLE"];

const S06Ecosystem: React.FC = () => {
  const frame = useCurrentFrame();
  const progress = easeOut3((frame - 16) / 110);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <OrbWebBox scale={0.76 * (0.97 + 0.03 * progress)} progress={progress} />
      <div style={{ position: "absolute", top: "8%", width: "100%" }}>
        <Eyebrow delay={30}>No mission exists in isolation</Eyebrow>
      </div>
      <div
        style={{
          position: "absolute",
          bottom: "8%",
          width: "100%",
          display: "flex",
          justifyContent: "center",
          gap: 20,
        }}
      >
        {ECO_LABELS.map((l, i) => (
          <Rise key={l} delay={200 + i * 40}>
            <div
              style={{
                fontFamily: SANS,
                fontWeight: 800,
                fontSize: 19,
                letterSpacing: "0.16em",
                color: BRAND.muted,
              }}
            >
              {l}
              {i < ECO_LABELS.length - 1 ? <span style={{ color: BRAND.gold, marginLeft: 20 }}>·</span> : null}
            </div>
          </Rise>
        ))}
      </div>
    </AbsoluteFill>
  );
};

const S07Funding: React.FC = () => (
  <PathwayCards
    chip="POTENTIALLY ALIGNED · CONFIRM ELIGIBILITY"
    sourceLine="VERIFIED ON OFFICIAL PROGRAM PAGES · JULY 2026 · FULL SOURCE LOG IN THE RESEARCH PACKET"
    cards={[
      {
        org: "CENTRAL FLORIDA FOUNDATION",
        program: "Grassroots Grants",
        note: "Youth development is a named priority area, sized for grassroots organizations.",
      },
      {
        org: "DR. PHILLIPS CHARITIES",
        program: "Legacy Microgrant Program",
        note: "Built for smaller Orange & Osceola nonprofits; Children & Youth is a named focus.",
      },
      {
        org: "PUBLIX SUPER MARKETS CHARITIES",
        program: "Youth & Education Support",
        note: "Youth programs and education support requests accepted year-round.",
      },
    ]}
  />
);

const S08Doorways: React.FC = () => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
    <div style={{ textAlign: "center" }}>
      <Rise delay={20}>
        <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 84, color: BRAND.white }}>
          Not commitments.
        </div>
      </Rise>
      <Rise delay={70}>
        <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 96, color: BRAND.goldLight, marginTop: 10 }}>
          Doorways.
        </div>
      </Rise>
    </div>
  </AbsoluteFill>
);

const S09Partners: React.FC = () => (
  <PathwayCards
    chip="MAY WARRANT OUTREACH"
    sourceLine="OCPS.NET · OSI.UCF.EDU · EBI.ROLLINS.EDU · VERIFIED JULY 2026"
    cards={[
      {
        org: "ORANGE COUNTY PUBLIC SCHOOLS",
        program: "Partners in Education",
        note: "The district's formal front door for organizations working inside schools.",
      },
      {
        org: "UNIVERSITY OF CENTRAL FLORIDA",
        program: "Volunteer UCF",
        note: "Connects student volunteers with 200+ community agencies.",
      },
      {
        org: "ROLLINS COLLEGE",
        program: "Edyth Bush Institute",
        note: "Capacity-building workshops and cohorts for Orange County nonprofits.",
      },
    ]}
  />
);

const S10Government: React.FC = () => (
  <PathwayCards
    chip="POSSIBLE PATHWAY · ELIGIBILITY TO CONFIRM"
    sourceLine="OCFL.NET · ORANGECOUNTYFL.NET · ORLANDO.GOV · VERIFIED JULY 2026"
    cards={[
      {
        org: "ORANGE COUNTY",
        program: "Citizens' Commission for Children",
        note: "Annual review process recommending county funds for youth- and family-serving nonprofits.",
      },
      {
        org: "ORANGE COUNTY",
        program: "Community Development Block Grants",
        note: "Public-service funding for programs serving qualifying families.",
      },
      {
        org: "CITY OF ORLANDO",
        program: "Neighborhood Initiatives",
        note: "Place-based youth programs delivered through nonprofit partners.",
      },
    ]}
  />
);

const S11Readiness: React.FC = () => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
    <ShotScene src="screenshots/hd-readiness.png" label="anansiatlas.com — readiness" dur={B[11] - B[10]} chip="READ THE WAY A FUNDER WOULD" />
    <div style={{ position: "absolute", bottom: "5.5%", width: "100%" }}>
      <Rise delay={380}>
        <div
          style={{
            fontFamily: SANS,
            fontWeight: 800,
            fontSize: 24,
            letterSpacing: "0.2em",
            color: BRAND.goldLight,
            textAlign: "center",
          }}
        >
          NOT AS CRITICISM — AS PREPARATION
        </div>
      </Rise>
    </div>
  </AbsoluteFill>
);

const S12Workspace: React.FC = () => {
  const frame = useCurrentFrame();
  const len = B[12] - B[11];
  const swap = interpolate(frame, [Math.round(len * 0.52), Math.round(len * 0.52) + 24], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ opacity: 1 - swap }}>
        <ShotScene src="screenshots/hd-dashboard.png" label="anansiatlas.com — Empowered Girls workspace" dur={len} chip="LIVE IN PRODUCTION" />
      </AbsoluteFill>
      <AbsoluteFill style={{ opacity: swap }}>
        <ShotScene src="screenshots/hd-web.png" label="anansiatlas.com — the Opportunity Web" dur={len} chip="LIVE IN PRODUCTION" />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const S13Decisions: React.FC = () => (
  <ShotScene src="screenshots/hd-ecosystem.png" label="anansiatlas.com — ecosystem view" dur={B[13] - B[12]} />
);

const PLAN = [
  "Confirm eligibility for the strongest funding pathways",
  "Open the school partnership conversation",
  "Assemble the readiness documents outreach will ask for",
];

const S14Plan: React.FC = () => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
    <div style={{ width: 1180 }}>
      <Eyebrow delay={16}>30-Day Action Plan</Eyebrow>
      <div style={{ display: "flex", flexDirection: "column", gap: 26, marginTop: 46 }}>
        {PLAN.map((p, i) => (
          <Rise key={p} delay={60 + i * 90}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 30,
                background: "rgba(23,40,79,0.85)",
                border: "1px solid rgba(159,176,198,0.3)",
                borderRadius: 18,
                padding: "30px 38px",
              }}
            >
              <div
                style={{
                  fontFamily: SERIF,
                  fontWeight: 600,
                  fontSize: 52,
                  color: BRAND.goldLight,
                  width: 62,
                  flexShrink: 0,
                }}
              >
                {i + 1}
              </div>
              <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 34, color: BRAND.white, lineHeight: 1.3 }}>
                {p}
              </div>
            </div>
          </Rise>
        ))}
      </div>
      <Rise delay={350}>
        <div
          style={{
            marginTop: 40,
            fontFamily: SANS,
            fontWeight: 800,
            fontSize: 22,
            letterSpacing: "0.2em",
            color: BRAND.muted,
            textAlign: "center",
          }}
        >
          SMALL STEPS · IN THE RIGHT ORDER
        </div>
      </Rise>
    </div>
  </AbsoluteFill>
);

const LaptopCard: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
    <div
      style={{
        width: 1484,
        borderRadius: 18,
        padding: 12,
        background: "#0a1226",
        border: "1px solid rgba(159,176,198,0.35)",
        boxShadow: "0 40px 120px rgba(0,0,0,0.55), 0 0 60px rgba(212,160,23,0.08)",
      }}
    >
      <div style={{ width: 1460, height: 1460 * (1000 / 1600), overflow: "hidden", borderRadius: 8 }}>
        <div style={{ transform: "scale(0.9125)", transformOrigin: "top left" }}>{children}</div>
      </div>
    </div>
  </AbsoluteFill>
);

const S15Transfer: React.FC = () => {
  const frame = useCurrentFrame();
  const swap = interpolate(frame, [300, 330], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ opacity: 1 - swap }}>
        <LaptopCard>
          <PreviewProfileScreen
            populated
            title="EMPOWERED GIRLS"
            subtitle="Orlando / Orange County, Florida"
            chip="OPPORTUNITY PROFILE"
            seed={23}
          />
        </LaptopCard>
      </AbsoluteFill>
      <AbsoluteFill style={{ opacity: swap }}>
        <LaptopCard>
          <PreviewProfileScreen populated seed={41} />
        </LaptopCard>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const S16Close: React.FC = () => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
    <NodeField w={1920} h={1080} count={11} seed={5} at={0} fadeIn={40} opacity={0.15} />
    <div style={{ textAlign: "center" }}>
      <Rise delay={16}>
        <Img
          src={staticFile("anansi-emblem-785.png")}
          style={{ width: 110, height: 110, display: "block", margin: "0 auto" }}
        />
      </Rise>
      <Rise delay={40}>
        <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 64, color: BRAND.white, marginTop: 30 }}>
          See the whole web.
        </div>
      </Rise>
      <Rise delay={200}>
        <div
          style={{
            marginTop: 34,
            fontFamily: SANS,
            fontWeight: 800,
            fontSize: 26,
            letterSpacing: "0.14em",
            color: BRAND.goldLight,
          }}
        >
          (321) 780-6335 · ANANSIATLAS.COM
        </div>
      </Rise>
    </div>
  </AbsoluteFill>
);

const S17EndCard: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeOut = interpolate(frame, [END_CARD - 28, END_CARD], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 90 }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 20 }}>
          <Rise delay={4}>
            <Img
              src={staticFile("anansi-emblem-785.png")}
              style={{ width: 100, height: 100, display: "block", margin: "0 auto" }}
            />
          </Rise>
          <Rise delay={12}>
            <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 46, color: BRAND.white, textAlign: "center" }}>
              See your whole web of opportunity.
            </div>
          </Rise>
          <CTAButton delay={24}>VISIT ANANSIATLAS.COM</CTAButton>
          <Rise delay={36}>
            <div
              style={{
                fontFamily: SERIF,
                fontWeight: 600,
                fontSize: 30,
                color: BRAND.goldLight,
                textAlign: "center",
              }}
            >
              or book a meeting
            </div>
          </Rise>
          <Rise delay={46}>
            <div
              style={{
                fontFamily: SANS,
                fontWeight: 600,
                fontSize: 21,
                color: BRAND.muted,
                textAlign: "center",
                lineHeight: 1.7,
              }}
            >
              cal.com/marcus-scott-br7maf/founder-walkthrough
              <br />
              marcus@anansiatlas.com · (321) 780-6335
            </div>
          </Rise>
          <Rise delay={58}>
            <div
              style={{
                marginTop: 6,
                fontFamily: SERIF,
                fontWeight: 600,
                fontSize: 30,
                color: BRAND.goldLight,
              }}
            >
              Your organization could be next.
            </div>
          </Rise>
        </div>
        <Rise delay={30}>
          <div
            style={{
              background: BRAND.white,
              borderRadius: 18,
              padding: 22,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 10,
            }}
          >
            <Img src={staticFile("qr-founder-walkthrough.png")} style={{ width: 250, height: 250 }} />
            <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 15, letterSpacing: "0.1em", color: "#17284f" }}>
              SCAN TO BOOK
            </div>
          </div>
        </Rise>
      </div>
      <AbsoluteFill style={{ background: `rgba(4,7,16,${fadeOut})`, pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// Captions
// ---------------------------------------------------------------------------
const cap = (i: number, fromFrac: number, toFrac: number, text: string): Caption => ({
  text,
  from: Math.round(VO_AT[i] + DUR[i] * fromFrac),
  duration: Math.round(DUR[i] * (toFrac - fromFrac)),
});
const CAPTIONS: Caption[] = [
  cap(0, 0, 0.42, "In Orlando, Florida, there is an organization that believes every girl deserves to grow into a confident, capable woman."),
  cap(0, 0.42, 1, "Empowered Girls, founded in 2018, works with girls across Orange County through life skills, mentorship, health and wellness, and academics infused with empowerment."),
  cap(1, 0, 1, "Their mission, in their own words: empowering girls to grow into confident, capable women through life skills, mentorship, and programs that help them overcome barriers and achieve success."),
  cap(2, 0, 0.5, "The work happens in a county of real scale. Orange County is home to more than 322,000 children — about one in five residents."),
  cap(2, 0.5, 1, "And about one in six of those children lives below the poverty line."),
  cap(3, 0, 0.45, "Nationally, the picture for girls is just as urgent. By fifth grade, only 68% of girls describe themselves as confident — down from 86% six years earlier."),
  cap(3, 0.45, 1, "And by one national estimate, one in three young people reach adulthood without ever having a mentor. This is the field Empowered Girls stands in."),
  cap(4, 0, 0.55, "But no mission exists in isolation. Around this work is a larger ecosystem — funders, schools, government programs, community organizations, businesses, and people —"),
  cap(4, 0.55, 1, "who may already be aligned with what Empowered Girls is building. Anansi Atlas exists to map exactly that."),
  cap(5, 0, 0.35, "Start with funding. In Central Florida, the pathways potentially aligned with girls' youth development are real and specific."),
  cap(5, 0.35, 0.7, "A community foundation whose grassroots grants name youth development as a priority. A local charity with a microgrant program built for smaller organizations."),
  cap(5, 0.7, 1, "And corporate giving from the region's largest employers, with youth and education programs that accept applications year-round."),
  cap(6, 0, 1, "None of these are commitments. Every one is a doorway — worth researching, worth confirming, worth a conversation."),
  cap(7, 0, 0.42, "Then, partners. Orange County Public Schools runs a formal Partners in Education program — the front door for organizations that work inside schools."),
  cap(7, 0.42, 1, "The University of Central Florida connects student volunteers to more than two hundred community agencies. And Rollins College runs an institute whose entire purpose is strengthening Orange County nonprofits."),
  cap(8, 0, 0.45, "Government has doorways of its own. Orange County's Citizens' Commission for Children reviews funding for youth-serving nonprofits every year."),
  cap(8, 0.45, 1, "Community Development Block Grants support programs for families who need them most. And the City of Orlando builds neighborhood initiatives through nonprofit partners."),
  cap(9, 0, 0.5, "And alongside opportunity, an honest look inward. The platform reads readiness the way a funder would — program documentation, outcome tracking, partnership materials —"),
  cap(9, 0.5, 1, "and shows where an organization is strong, and where to strengthen next. Not as criticism. As preparation."),
  cap(10, 0, 0.5, "All of it comes together here. This is Empowered Girls' actual workspace in Anansi Atlas — live in production today."),
  cap(10, 0.5, 1, "Their mission at the center. Around it, the funders. The partners. The government pathways. The resources. The readiness."),
  cap(11, 0, 1, "From here, research becomes decisions. What to pursue. Who to call. What to prepare. In order, starting now."),
  cap(12, 0, 0.5, "It ends in a plan — a thirty-day sequence of clear next actions. Confirm eligibility for the strongest funding pathways."),
  cap(12, 0.5, 1, "Open the school partnership conversation. Assemble the readiness documents that outreach will ask for. Small steps, in the right order."),
  cap(13, 0, 0.45, "This is the web surrounding Empowered Girls — built around their mission, their location, the girls they serve, their priorities, and their capacity today."),
  cap(13, 0.45, 1, "Every organization's web looks different. That is the point. Anansi Atlas helps nonprofit leaders see what surrounds their mission, and decide what to do next."),
  cap(14, 0, 0.55, "Your mission is already surrounded by people, resources, pathways, and possibilities. The next step is seeing how they connect."),
  cap(14, 0.55, 1, "Call us, or visit anansiatlas.com. Your organization could be next."),
];

// ---------------------------------------------------------------------------
// Film
// ---------------------------------------------------------------------------
const SCENES: [React.FC, number, number][] = [
  [S01Title, B[0], B[1]],
  [S02Mission, B[1], B[2]],
  [S03Quote, B[2], B[3]],
  [S04County, B[3], B[4]],
  [S05Girls, B[4], B[5]],
  [S06Ecosystem, B[5], B[6]],
  [S07Funding, B[6], B[7]],
  [S08Doorways, B[7], B[8]],
  [S09Partners, B[8], B[9]],
  [S10Government, B[9], B[10]],
  [S11Readiness, B[10], B[11]],
  [S12Workspace, B[11], B[12]],
  [S13Decisions, B[12], B[13]],
  [S14Plan, B[13], B[14]],
  [S15Transfer, B[14], B[15]],
  [S16Close, B[15], B[16]],
  [S17EndCard, B[16], B[17]],
];

const VO_SRC = "egi-research-film-vo.mp3";

const Film: React.FC<{ captions?: boolean }> = ({ captions = false }) => {
  const fmt = FMTS.wide;
  const cuts = SCENES.slice(1)
    .map(([, from]) => from)
    .filter((f) => f !== B[5]);
  return (
    <FmtCtx.Provider value={fmt}>
      <NavyBG w={1920} h={1080} threads={0.7}>
        {SCENES.map(([Scene, from, to], i) => (
          <Sequence key={i} from={from} durationInFrames={to - from}>
            <Scene />
          </Sequence>
        ))}
        <SceneDissolve boundaries={cuts} />
        {/* the web draws through the "no mission exists in isolation" turn */}
        <ActBridge boundaries={[B[5]]} w={1920} h={1080} />

        {SLICE.map((s, i) => (
          <Sequence key={`vo${i}`} from={s.at} durationInFrames={s.to - s.from}>
            <Audio
              src={staticFile(VO_SRC)}
              startFrom={s.from}
              endAt={s.to}
              volume={(f) =>
                interpolate(f, [0, VO_FADE, s.to - s.from - VO_FADE, s.to - s.from], [0, 1, 1, 0], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                })
              }
            />
          </Sequence>
        ))}

        {/* minimal (mission/context) → build (ecosystem/research) → resolve (readiness→close);
            crossfades sit inside measured speech gaps, never on act turns */}
        <Sequence from={0} durationInFrames={2918}>
          <Audio
            src={staticFile("music/stem-minimal.mp3")}
            volume={(f) =>
              interpolate(f, [0, 60, 2858, 2918], [0, 0.5, 0.5, 0], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              })
            }
          />
        </Sequence>
        <Sequence from={2858} durationInFrames={3151}>
          <Audio
            src={staticFile("music/stem-build.mp3")}
            volume={(f) =>
              interpolate(f, [0, 60, 3091, 3151], [0, 0.48, 0.48, 0], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              })
            }
          />
        </Sequence>
        <Sequence from={5934} durationInFrames={EGI_FILM_TOTAL - 5934}>
          <Audio
            src={staticFile("music/stem-resolve.mp3")}
            volume={(f) =>
              interpolate(
                f,
                [0, 60, EGI_FILM_TOTAL - 5934 - 80, EGI_FILM_TOTAL - 5934],
                [0, 0.52, 0.52, 0],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              )
            }
          />
        </Sequence>

        {captions ? <Subtitles captions={CAPTIONS} /> : null}
      </NavyBG>
    </FmtCtx.Provider>
  );
};

export const EmpoweredGirlsResearchFilm: React.FC = () => <Film />;
export const EmpoweredGirlsResearchFilmCaptioned: React.FC = () => <Film captions />;
