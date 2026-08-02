import React, { createContext, useContext } from "react";
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
import { CTAButton, NavyBG, NodeField, Rise, SANS, SERIF, ThreadRule } from "../components";
import { PreviewProfileScreen } from "./AnansiUniversalCommercial";

// ============================================================================
// SOCIAL VARIATIONS — two genuinely different 30s cuts (not recuts of primary).
//
//   A · GRANTS ARE ONLY ONE PART — opens on a grant-search screen, pulls back
//       to reveal the wider web around it. CTA: Preview Your Organization.
//   B · YOUR ORGANIZATION HERE — opens on the laptop, animated inputs, rapid
//       populate. CTA: Book a Founder Walkthrough.
//
// One VO master (anansi-social30-vars-vo.mp3): lines 0-3 = A, lines 4-7 = B.
// ============================================================================

const easeOut3 = (t: number) => {
  const c = Math.min(1, Math.max(0, t));
  return 1 - Math.pow(1 - c, 3);
};

type FmtKind = "vert" | "fourfive" | "square";
type Fmt = { W: number; H: number; kind: FmtKind; K: number };
const FMTS: Record<FmtKind, Fmt> = {
  vert: { W: 1080, H: 1920, kind: "vert", K: 1 },
  fourfive: { W: 1080, H: 1350, kind: "fourfive", K: 0.88 },
  square: { W: 1080, H: 1080, kind: "square", K: 0.8 },
};
const FmtCtx = createContext<Fmt>(FMTS.vert);
const useFmt = () => useContext(FmtCtx);

// Measured via `node scripts/vo-line-slices.mjs AnansiSocial30Vars` (38.5s master).
const LINE: [number, number][] = [
  [0, 84],
  [90, 319],
  [336, 531],
  [540, 598],
  [615, 692],
  [698, 959],
  [973, 1081],
  [1094, 1154],
];
export const SOCIAL30_VAR_TOTAL = 900;
const VO_SRC = "anansi-social30-vars-vo.mp3";
const VO_FADE = 4;

const voSlice = (idx: number, at: number) => {
  const [s, e] = LINE[idx];
  const from = Math.max(0, s - 4);
  const to = e + 4;
  return { from, to, at: at - (s - from) };
};

const LogoSting: React.FC = () => {
  const frame = useCurrentFrame();
  const fmt = useFmt();
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <ThreadRule from={[30, 50]} to={[70, 50]} at={0} draw={10} hold={24} out={0} opacity={0.5} />
      <Img
        src={staticFile("anansi-emblem-785.png")}
        style={{ width: 124 * fmt.K, height: 124 * fmt.K, opacity: easeOut3(frame / 7) }}
      />
    </AbsoluteFill>
  );
};

// A mock grant-search screen — deliberately generic (no real funder names).
const GRANT_ROWS = [
  ["Youth Program Grant — Round 2", "$25,000", "Due in 18 days"],
  ["Community Impact Fund", "$10,000", "Due in 31 days"],
  ["Education Initiative Grant", "$50,000", "Rolling"],
  ["Capacity Building Award", "$5,000", "Due in 9 days"],
  ["Regional Partnership Grant", "$15,000", "Due in 44 days"],
];

const GrantSearchScreen: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <div
      style={{
        width: 1000,
        height: 1250,
        background: `linear-gradient(180deg, #0f2048 0%, ${BRAND.navy} 70%)`,
        fontFamily: SANS,
        padding: "44px 44px",
        display: "flex",
        flexDirection: "column",
        gap: 20,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 16,
          background: "rgba(6,12,26,0.6)",
          border: "1px solid rgba(159,176,198,0.35)",
          borderRadius: 999,
          padding: "18px 28px",
        }}
      >
        <div style={{ width: 20, height: 20, borderRadius: 999, border: `2.5px solid ${BRAND.muted}` }} />
        <div style={{ fontWeight: 600, fontSize: 26, color: BRAND.muted }}>grant search…</div>
      </div>
      <div style={{ fontWeight: 800, fontSize: 21, letterSpacing: "0.14em", color: BRAND.muted }}>
        128 RESULTS
      </div>
      {GRANT_ROWS.map((r, i) => {
        const a = easeOut3((frame - 8 - i * 7) / 12);
        if (a <= 0) return null;
        return (
          <div
            key={r[0]}
            style={{
              opacity: a,
              transform: `translateY(${(1 - a) * 14}px)`,
              background: "rgba(23,40,79,0.85)",
              border: "1px solid rgba(159,176,198,0.28)",
              borderRadius: 14,
              padding: "24px 28px",
            }}
          >
            <div style={{ fontWeight: 800, fontSize: 27, color: BRAND.ink }}>{r[0]}</div>
            <div style={{ display: "flex", gap: 26, marginTop: 10 }}>
              <div style={{ fontWeight: 800, fontSize: 23, color: BRAND.goldLight }}>{r[1]}</div>
              <div style={{ fontWeight: 600, fontSize: 23, color: BRAND.muted }}>{r[2]}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

// The pull-back: the grant screen shrinks into ONE node of a larger labeled web.
const ORBIT_LABELS = ["PARTNERS", "GOV PATHWAYS", "RESOURCES", "FUNDERS", "RISKS", "NEXT STEPS"];

const PullBack: React.FC = () => {
  const frame = useCurrentFrame();
  const fmt = useFmt();
  const K = fmt.K;
  const shrink = easeOut3(frame / 50);
  const scale = 0.62 - 0.47 * shrink; // ends small enough to read as one node
  const cx = 50;
  const cy = fmt.kind === "vert" ? 44 : 48;
  const spread = fmt.kind === "vert" ? 31 : 26;
  return (
    <AbsoluteFill>
      <NodeField w={fmt.W} h={fmt.H} count={10} seed={17} at={30} fadeIn={30} opacity={0.13} />
      {ORBIT_LABELS.map((l, i) => {
        const a = (i / ORBIT_LABELS.length) * Math.PI * 2 - Math.PI / 2;
        const x = cx + Math.cos(a) * spread * 0.92;
        const y = cy + (Math.sin(a) * spread * 0.92 * fmt.W) / fmt.H;
        const app = easeOut3((frame - 40 - i * 10) / 16);
        return (
          <React.Fragment key={l}>
            <ThreadRule from={[cx, cy]} to={[x, y]} at={36 + i * 10} draw={20} hold={400} out={40} opacity={0.55} dots />
            {app > 0 ? (
              <div
                style={{
                  position: "absolute",
                  left: `${x}%`,
                  top: `${y}%`,
                  transform: "translate(-50%,-50%)",
                  opacity: app,
                  fontFamily: SANS,
                  fontWeight: 800,
                  fontSize: 24 * K,
                  letterSpacing: "0.14em",
                  color: BRAND.ink,
                  background: "rgba(23,40,79,0.92)",
                  border: `1px solid ${BRAND.gold}`,
                  borderRadius: 999,
                  padding: `${9 * K}px ${20 * K}px`,
                }}
              >
                {l}
              </div>
            ) : null}
          </React.Fragment>
        );
      })}
      {/* grant screen shrinking into the center node */}
      <div
        style={{
          position: "absolute",
          left: `${cx}%`,
          top: `${cy}%`,
          transform: `translate(-50%,-50%) scale(${scale})`,
          borderRadius: 16,
          overflow: "hidden",
          border: `1.5px solid ${shrink > 0.8 ? BRAND.gold : "rgba(159,176,198,0.4)"}`,
          boxShadow: `0 0 ${40 * shrink}px rgba(212,160,23,${0.25 * shrink})`,
        }}
      >
        <GrantSearchScreen />
      </div>
      <div
        style={{
          position: "absolute",
          left: `${cx}%`,
          top: `${cy + (fmt.kind === "vert" ? 8 : 11)}%`,
          transform: "translateX(-50%)",
          fontFamily: SANS,
          fontWeight: 800,
          fontSize: 21 * K,
          letterSpacing: "0.18em",
          color: BRAND.goldLight,
          opacity: interpolate(frame, [52, 66], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
        }}
      >
        GRANTS — ONE NODE OF MANY
      </div>
    </AbsoluteFill>
  );
};

const ProfileScene: React.FC<{ title?: string; subtitle?: string; showInputs?: boolean }> = ({
  title,
  subtitle,
  showInputs = false,
}) => {
  const frame = useCurrentFrame();
  const fmt = useFmt();
  const portrait = true;
  const innerW = 1000;
  const innerH = 1250;
  const maxW = fmt.W * 0.92;
  const maxH = fmt.H * 0.78;
  const k = Math.min(maxW / innerW, maxH / innerH);
  const scaleIn = 0.97 + 0.03 * easeOut3(frame / 18);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div
        style={{
          width: innerW * k + 20,
          borderRadius: 16,
          padding: 10,
          background: "#0a1226",
          border: "1px solid rgba(159,176,198,0.35)",
          boxShadow: "0 30px 100px rgba(0,0,0,0.55), 0 0 50px rgba(212,160,23,0.08)",
          transform: `scale(${scaleIn})`,
        }}
      >
        <div style={{ width: innerW * k, height: innerH * k, overflow: "hidden", borderRadius: 8 }}>
          <div style={{ transform: `scale(${k})`, transformOrigin: "top left" }}>
            <PreviewProfileScreen portrait={portrait} fast title={title} subtitle={subtitle} />
          </div>
        </div>
      </div>
      {showInputs ? (
        <div
          style={{
            position: "absolute",
            bottom: fmt.kind === "vert" ? "8%" : "4%",
            display: "flex",
            gap: 14 * fmt.K,
          }}
        >
          {["YOUR MISSION", "YOUR LOCATION", "YOUR CAPACITY"].map((c, i) => (
            <Rise key={c} delay={86 + i * 18}>
              <div
                style={{
                  fontFamily: SANS,
                  fontWeight: 800,
                  fontSize: 21 * fmt.K,
                  letterSpacing: "0.12em",
                  color: BRAND.goldLight,
                  border: `1px solid ${BRAND.gold}`,
                  borderRadius: 999,
                  padding: `${9 * fmt.K}px ${20 * fmt.K}px`,
                  background: "rgba(13,27,61,0.85)",
                }}
              >
                {c}
              </div>
            </Rise>
          ))}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

const BigText: React.FC<{ lines: string[]; delay?: number; gold?: number }> = ({
  lines,
  delay = 0,
  gold = 1,
}) => {
  const fmt = useFmt();
  const K = fmt.K;
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div style={{ textAlign: "center", padding: "0 60px" }}>
        {lines.map((l, i) => (
          <Rise key={l} delay={delay + i * 7}>
            <div
              style={{
                fontFamily: SANS,
                fontWeight: 900,
                fontSize: 60 * K,
                lineHeight: 1.16,
                color: i === gold ? BRAND.goldLight : BRAND.white,
                textShadow: "0 4px 30px rgba(0,0,0,0.55)",
              }}
            >
              {l}
            </div>
          </Rise>
        ))}
      </div>
    </AbsoluteFill>
  );
};

const EndCard: React.FC<{ cta: string; dur: number }> = ({ cta, dur }) => {
  const frame = useCurrentFrame();
  const fmt = useFmt();
  const K = fmt.K;
  const fade = interpolate(frame, [dur - 18, dur], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 24 * K }}>
        <Rise delay={2}>
          <Img
            src={staticFile("anansi-emblem-785.png")}
            style={{ width: 120 * K, height: 120 * K, display: "block", margin: "0 auto" }}
          />
        </Rise>
        <Rise delay={8}>
          <div
            style={{
              fontFamily: SERIF,
              fontWeight: 600,
              fontSize: 54 * K,
              color: BRAND.white,
              textAlign: "center",
              padding: "0 70px",
              lineHeight: 1.15,
            }}
          >
            See your whole web of opportunity.
          </div>
        </Rise>
        <CTAButton delay={20}>{cta}</CTAButton>
        <Rise delay={30}>
          <div
            style={{
              fontFamily: SERIF,
              fontWeight: 600,
              fontSize: 34 * K,
              color: BRAND.goldLight,
              textAlign: "center",
            }}
          >
            or book a meeting
          </div>
        </Rise>
        <Rise delay={40}>
          <div
            style={{
              fontFamily: SANS,
              fontWeight: 600,
              fontSize: 21 * K,
              color: BRAND.muted,
              textAlign: "center",
            }}
          >
            cal.com/marcus-scott-br7maf/founder-walkthrough
          </div>
        </Rise>
      </div>
      <AbsoluteFill style={{ background: `rgba(4,7,16,${fade})`, pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};

type SocialCaption = { text: string; from: number; duration: number };
const SocialCaptions: React.FC<{ captions: SocialCaption[] }> = ({ captions }) => {
  const frame = useCurrentFrame();
  const fmt = useFmt();
  const K = fmt.K;
  const active = captions.find((c) => frame >= c.from && frame < c.from + c.duration);
  if (!active) return null;
  const opacity = interpolate(frame - active.from, [0, 6], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: fmt.kind === "vert" ? 300 : 130,
      }}
    >
      <div
        style={{
          maxWidth: fmt.W * 0.86,
          opacity,
          background: "rgba(6,12,26,0.8)",
          border: "1px solid rgba(212,160,23,0.4)",
          borderRadius: 16,
          padding: `${16 * K}px ${28 * K}px`,
          fontFamily: SANS,
          fontSize: 36 * K,
          fontWeight: 700,
          color: BRAND.white,
          textAlign: "center",
          lineHeight: 1.28,
        }}
      >
        {active.text}
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// Variation A — GRANTS ARE ONLY ONE PART
// ---------------------------------------------------------------------------
const GrantsFilm: React.FC<{ fmt: Fmt }> = ({ fmt }) => {
  const slices = [
    voSlice(0, 30),
    voSlice(1, 160),
    voSlice(2, 412),
    voSlice(3, 660),
  ];
  const captions: SocialCaption[] = [
    { text: "Grants are only one part of your opportunity web.", from: 30, duration: 116 },
    { text: "Around your mission are potential partners, government pathways,", from: 160, duration: 118 },
    { text: "community resources, funders, risks, and next steps.", from: 278, duration: 116 },
    { text: "Anansi Atlas brings those connections into one clear opportunity profile —", from: 412, duration: 106 },
    { text: "built around your organization.", from: 518, duration: 96 },
    { text: "See your whole web of opportunity.", from: 660, duration: 80 },
  ];
  return (
    <FmtCtx.Provider value={fmt}>
      <NavyBG w={fmt.W} h={fmt.H} threads={0.7}>
        <Sequence from={0} durationInFrames={24}>
          <LogoSting />
        </Sequence>
        {/* grant screen, full and busy */}
        <Sequence from={24} durationInFrames={126}>
          <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
            <div style={{ transform: `scale(${fmt.kind === "vert" ? 0.9 : 0.62})`, borderRadius: 16, overflow: "hidden", border: "1px solid rgba(159,176,198,0.4)" }}>
              <GrantSearchScreen />
            </div>
          </AbsoluteFill>
        </Sequence>
        {/* the pull-back reveal */}
        <Sequence from={150} durationInFrames={250}>
          <PullBack />
        </Sequence>
        <Sequence from={400} durationInFrames={240}>
          <ProfileScene />
        </Sequence>
        <Sequence from={640} durationInFrames={260}>
          <EndCard cta="VISIT ANANSIATLAS.COM" dur={260} />
        </Sequence>

        {slices.map((s, i) => (
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
        <Audio
          src={staticFile("music/stem-minimal.mp3")}
          volume={(f) =>
            interpolate(f, [0, 30, 800, 900], [0, 0.5, 0.5, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            })
          }
        />
        <SocialCaptions captions={captions} />
      </NavyBG>
    </FmtCtx.Provider>
  );
};

// ---------------------------------------------------------------------------
// Variation B — YOUR ORGANIZATION HERE
// ---------------------------------------------------------------------------
const YourOrgFilm: React.FC<{ fmt: Fmt }> = ({ fmt }) => {
  const slices = [
    voSlice(4, 30),
    voSlice(5, 190),
    voSlice(6, 492),
    voSlice(7, 668),
  ];
  const captions: SocialCaption[] = [
    { text: "Potential funders. Strategic partners. Government pathways.", from: 190, duration: 130 },
    { text: "Community resources. Readiness gaps. And a practical plan for what to do next.", from: 320, duration: 131 },
    { text: "Built around your mission, your location, and your current capacity.", from: 492, duration: 108 },
  ];
  return (
    <FmtCtx.Provider value={fmt}>
      <NavyBG w={fmt.W} h={fmt.H} threads={0.7}>
        <Sequence from={0} durationInFrames={24}>
          <LogoSting />
        </Sequence>
        {/* laptop + question — scrim keeps the display type legible over the card */}
        <Sequence from={24} durationInFrames={156}>
          <ProfileScene showInputs />
          <AbsoluteFill style={{ background: "rgba(6,10,22,0.58)" }} />
          <BigText lines={["WHAT WOULD ANANSI ATLAS", "REVEAL AROUND YOUR MISSION?"]} delay={8} />
        </Sequence>
        {/* rapid populate */}
        <Sequence from={180} durationInFrames={300}>
          <ProfileScene />
        </Sequence>
        {/* full profile push */}
        <Sequence from={480} durationInFrames={170}>
          <ProfileScene />
        </Sequence>
        <Sequence from={650} durationInFrames={100}>
          <BigText lines={["YOUR ORGANIZATION", "COULD BE HERE."]} delay={4} />
        </Sequence>
        <Sequence from={750} durationInFrames={150}>
          <EndCard cta="VISIT ANANSIATLAS.COM" dur={150} />
        </Sequence>

        {slices.map((s, i) => (
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
        <Audio
          src={staticFile("music/stem-resolve.mp3")}
          volume={(f) =>
            interpolate(f, [0, 30, 800, 900], [0, 0.5, 0.5, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            })
          }
        />
        <SocialCaptions captions={captions} />
      </NavyBG>
    </FmtCtx.Provider>
  );
};

export const AnansiSocial30Grants: React.FC = () => <GrantsFilm fmt={FMTS.vert} />;
export const AnansiSocial30Grants4x5: React.FC = () => <GrantsFilm fmt={FMTS.fourfive} />;
export const AnansiSocial30Grants1x1: React.FC = () => <GrantsFilm fmt={FMTS.square} />;
export const AnansiSocial30YourOrg: React.FC = () => <YourOrgFilm fmt={FMTS.vert} />;
export const AnansiSocial30YourOrg4x5: React.FC = () => <YourOrgFilm fmt={FMTS.fourfive} />;
export const AnansiSocial30YourOrg1x1: React.FC = () => <YourOrgFilm fmt={FMTS.square} />;
