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
  Eyebrow,
  HyperFrames,
  NavyBG,
  NodeField,
  OrbWeb,
  Rise,
  SANS,
  SERIF,
  SceneDissolve,
  ThreadRule,
  makePrng,
} from "../components";
import {
  FMTS,
  Fmt,
  FmtCtx,
  LaptopShell,
  PreviewProfileScreen,
  ScatterField,
  UniversalEndCard,
  useFmt,
} from "./AnansiUniversalCommercial";

// ============================================================================
// CAMPAIGN VARIATIONS — two genuinely different universal commercials.
//
//   A · THE VISIBILITY PROBLEM (~63s)  confusion → visibility → clarity → action
//   B · IMAGINE YOUR ORGANIZATION HERE (~66s)  curiosity → personalization →
//       possibility → action, laptop-first structure
//
// Both share the brand logo open/close and core product claims; hook, first
// visual, structure, pacing, and music mix are distinct per the variation brief.
// ============================================================================

const easeOut3 = (t: number) => {
  const c = Math.min(1, Math.max(0, t));
  return 1 - Math.pow(1 - c, 3);
};

// Shared short logo open (75f) — same grammar as the primary, tightened.
const LogoOpenShort: React.FC = () => {
  const frame = useCurrentFrame();
  const fmt = useFmt();
  const K = fmt.K;
  const emblemIn = easeOut3((frame - 18) / 22);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <ThreadRule from={[28, 50]} to={[72, 50]} at={2} draw={20} hold={70} out={0} opacity={0.5} />
      <NodeField w={fmt.W} h={fmt.H} count={9} at={8} fadeIn={24} opacity={0.15} />
      {emblemIn > 0 ? (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 22 * K,
            opacity: emblemIn,
            transform: `scale(${0.93 + 0.07 * emblemIn})`,
          }}
        >
          <Img src={staticFile("anansi-emblem-785.png")} style={{ width: 120 * K, height: 120 * K }} />
          <div
            style={{
              fontFamily: SANS,
              fontWeight: 800,
              fontSize: 27 * K,
              letterSpacing: "0.26em",
              color: BRAND.white,
            }}
          >
            ANANSI ATLAS
          </div>
        </div>
      ) : null}
      <div style={{ position: "absolute", bottom: "24%", width: "100%" }}>
        <Eyebrow delay={40}>The Web of Opportunity</Eyebrow>
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// VARIATION A — THE VISIBILITY PROBLEM
// ---------------------------------------------------------------------------
const LINE_A: [number, number][] = [
  [0, 151],
  [153, 473],
  [481, 611],
  [626, 816],
  [836, 1098],
  [1102, 1249],
  [1272, 1426],
];
const DUR_A = LINE_A.map(([a, b]) => b - a);
const LEAD_A = [18, 22, 20, 28, 25, 20, 25];
const TAIL_A = [12, 12, 35, 18, 18, 15, 40];
const LOGO_A = 75;
const END_A = 150;
const BA: number[] = [0, LOGO_A];
for (let i = 0; i < LINE_A.length; i++) BA.push(BA[BA.length - 1] + LEAD_A[i] + DUR_A[i] + TAIL_A[i]);
BA.push(BA[BA.length - 1] + END_A);
export const VISIBILITY_TOTAL = BA[BA.length - 1]; // 1887f ≈ 62.9s
const VO_AT_A = LINE_A.map((_, i) => BA[i + 1] + LEAD_A[i]);

// Browser-tab cascade for the "forty tabs" beat — a different first-act visual
// from the primary's floating cards.
const TabStack: React.FC = () => {
  const frame = useCurrentFrame();
  const fmt = useFmt();
  const K = fmt.K;
  const TABS = [
    "Grant portal — application",
    "Funder database (page 12)",
    "Board notes.docx",
    "RE: RE: partnership intro",
    "county-programs-FINAL.xlsx",
    "Deadline calendar",
    "readiness-checklist (2023)",
    "Community resource list",
    "RFP guidelines.pdf",
    "…and 31 more tabs",
  ];
  const cx = fmt.kind === "wide" ? 0.5 : 0.5;
  const w = Math.min(760 * K * 1.4, fmt.W * 0.82);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div style={{ width: w, position: "relative" }}>
        {TABS.map((t, i) => {
          const a = easeOut3((frame - i * 9) / 14);
          if (a <= 0) return null;
          const last = i === TABS.length - 1;
          return (
            <div
              key={t}
              style={{
                position: "relative",
                marginTop: i === 0 ? 0 : 10 * K,
                marginLeft: (i % 3) * 26 * K,
                width: w - (i % 3) * 40 * K,
                background: last ? "rgba(212,160,23,0.12)" : "rgba(23,40,79,0.94)",
                border: last
                  ? `1px solid ${BRAND.gold}`
                  : "1px solid rgba(159,176,198,0.32)",
                borderRadius: 9,
                padding: `${13 * K}px ${18 * K}px`,
                opacity: a * (0.55 + 0.45 * (i / TABS.length)),
                transform: `translateY(${(1 - a) * 18}px) translateX(${cx}px)`,
                display: "flex",
                alignItems: "center",
                gap: 12 * K,
                boxShadow: "0 8px 22px rgba(0,0,0,0.3)",
              }}
            >
              <div
                style={{
                  width: 9 * K,
                  height: 9 * K,
                  borderRadius: 999,
                  background: last ? BRAND.goldLight : BRAND.muted,
                  flexShrink: 0,
                }}
              />
              <div
                style={{
                  fontFamily: SANS,
                  fontWeight: last ? 800 : 600,
                  fontSize: 20 * K,
                  color: last ? BRAND.goldLight : BRAND.ink,
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {t}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// Threads that try to connect and fail — the "can't see how it connects" beat.
const FailedThreads: React.FC = () => {
  const fmt = useFmt();
  const PAIRS: [[number, number], [number, number], number][] = [
    [[20, 30], [46, 42], 6],
    [[78, 26], [55, 45], 26],
    [[26, 72], [48, 55], 46],
    [[80, 70], [58, 56], 66],
  ];
  return (
    <AbsoluteFill>
      <ScatterField freezeAt={0} dimFrom={70} />
      {PAIRS.map(([f, t, at], i) => (
        <ThreadRule
          key={i}
          from={f}
          to={t}
          at={at}
          draw={26}
          hold={4}
          out={22}
          opacity={0.5}
          color={BRAND.muted}
        />
      ))}
      <div style={{ position: "absolute", bottom: fmt.kind === "vert" ? "20%" : "13%", width: "100%" }}>
        <Eyebrow delay={92}>Almost connected — never quite</Eyebrow>
      </div>
    </AbsoluteFill>
  );
};

const AOrbTurn: React.FC = () => {
  const frame = useCurrentFrame();
  const fmt = useFmt();
  const progress = easeOut3((frame - 10) / 80);
  const orbScale = (fmt.kind === "wide" ? 0.74 : 0.6) * (0.97 + 0.03 * progress);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div style={{ position: "relative", width: 1080, height: 1080, transform: `scale(${orbScale})` }}>
        <OrbWeb progress={progress} />
      </div>
      <div style={{ position: "absolute", top: fmt.kind === "vert" ? "12%" : "8%", width: "100%" }}>
        <Eyebrow delay={26}>The whole ecosystem, in view</Eyebrow>
      </div>
    </AbsoluteFill>
  );
};

const A_SPOT = ["FUNDING PATHWAYS", "STRATEGIC PARTNERS", "GOVERNMENT PROGRAMS", "READINESS — HONESTLY"];

const AProfileSpot: React.FC = () => {
  const frame = useCurrentFrame();
  const fmt = useFmt();
  const K = fmt.K;
  const stop = Math.min(3, Math.floor(Math.max(0, frame - 40) / 56));
  const a = easeOut3(((frame - 40) % 56) / 14);
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", inset: 0, transform: "translateY(-34px)" }}>
        <LaptopShell push={false}>
          <PreviewProfileScreen fast portrait={fmt.kind === "vert"} spotlight={40} />
        </LaptopShell>
      </div>
      {frame >= 40 ? (
        <div
          style={{
            position: "absolute",
            bottom: fmt.kind === "vert" ? "17%" : "3.6%",
            width: "100%",
            textAlign: "center",
            fontFamily: SANS,
            fontWeight: 800,
            fontSize: 26 * K,
            letterSpacing: "0.2em",
            color: BRAND.goldLight,
            opacity: a,
          }}
        >
          {A_SPOT[stop]}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

const AClarity: React.FC = () => {
  const fmt = useFmt();
  return (
    <AbsoluteFill>
      <HyperFrames
        words={[
          { word: "COMPLEXITY IN.", hold: 44 },
          { word: "CLARITY OUT.", hold: 46, color: BRAND.goldLight },
        ]}
        at={8}
        size={fmt.kind === "wide" ? 120 : 76}
        enter={12}
        exit={12}
        gap={6}
      />
      <div style={{ position: "absolute", bottom: fmt.kind === "vert" ? "22%" : "16%", width: "100%" }}>
        <Eyebrow delay={140}>A practical plan for what to do next</Eyebrow>
      </div>
    </AbsoluteFill>
  );
};

const AClose: React.FC = () => {
  const frame = useCurrentFrame();
  const fmt = useFmt();
  const vignette = interpolate(frame, [150, 219], [0, 0.45], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill>
      <LaptopShell>
        <PreviewProfileScreen populated portrait={fmt.kind === "vert"} />
      </LaptopShell>
      <AbsoluteFill style={{ background: `rgba(6,10,22,${vignette})` }} />
    </AbsoluteFill>
  );
};

const SCENES_A: [React.FC, number, number][] = [
  [LogoOpenShort, BA[0], BA[1]],
  [() => <ScatterField extra />, BA[1], BA[2]],
  [TabStack, BA[2], BA[3]],
  [FailedThreads, BA[3], BA[4]],
  [AOrbTurn, BA[4], BA[5]],
  [AProfileSpot, BA[5], BA[6]],
  [AClarity, BA[6], BA[7]],
  [AClose, BA[7], BA[8]],
  [() => <UniversalEndCard dur={END_A} />, BA[8], BA[9]],
];

// ---------------------------------------------------------------------------
// VARIATION B — IMAGINE YOUR ORGANIZATION HERE
// ---------------------------------------------------------------------------
const LINE_B: [number, number][] = [
  [0, 163],
  [170, 406],
  [417, 600],
  [612, 765],
  [776, 1102],
  [1103, 1375],
  [1379, 1472],
];
const DUR_B = LINE_B.map(([a, b]) => b - a);
const LEAD_B = [20, 25, 22, 25, 25, 25, 30];
const TAIL_B = [15, 18, 18, 20, 18, 20, 45];
const LOGO_B = 70;
const END_B = 150;
const BB: number[] = [0, LOGO_B];
for (let i = 0; i < LINE_B.length; i++) BB.push(BB[BB.length - 1] + LEAD_B[i] + DUR_B[i] + TAIL_B[i]);
BB.push(BB[BB.length - 1] + END_B);
export const IMAGINE_TOTAL = BB[BB.length - 1]; // 1972f ≈ 65.7s
const VO_AT_B = LINE_B.map((_, i) => BB[i + 1] + LEAD_B[i]);

const INPUTS = [
  ["Mission", "What you exist to do"],
  ["Location", "Where you serve"],
  ["Population", "Who you serve"],
  ["Goals", "What's next for you"],
  ["Capacity", "Where you are today"],
];

const InputsScreen: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <div
      style={{
        width: 1600,
        height: 1000,
        background: `linear-gradient(180deg, #0f2048 0%, ${BRAND.navy} 70%)`,
        fontFamily: SANS,
        padding: "60px 90px",
        display: "flex",
        flexDirection: "column",
        gap: 26,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <Img src={staticFile("anansi-emblem-785.png")} style={{ width: 34, height: 34 }} />
        <div style={{ fontWeight: 800, fontSize: 21, letterSpacing: "0.2em", color: BRAND.white }}>
          ANANSI ATLAS
        </div>
        <div style={{ flex: 1 }} />
        <div
          style={{
            fontWeight: 800,
            fontSize: 15,
            letterSpacing: "0.16em",
            color: BRAND.goldLight,
            border: `1px solid ${BRAND.gold}`,
            borderRadius: 999,
            padding: "7px 18px",
          }}
        >
          BUILD YOUR PROFILE
        </div>
      </div>
      <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 46, color: BRAND.white, marginTop: 8 }}>
        Start with what makes you, you.
      </div>
      {INPUTS.map(([label, hint], i) => {
        const a = easeOut3((frame - 26 - i * 22) / 18);
        const filled = easeOut3((frame - 40 - i * 22) / 24);
        if (a <= 0) return null;
        return (
          <div
            key={label}
            style={{
              opacity: a,
              transform: `translateY(${(1 - a) * 16}px)`,
              display: "flex",
              alignItems: "center",
              gap: 24,
              background: "rgba(23,40,79,0.7)",
              border: `1px solid ${filled > 0.9 ? BRAND.gold : "rgba(159,176,198,0.28)"}`,
              borderRadius: 14,
              padding: "22px 28px",
            }}
          >
            <div style={{ fontWeight: 800, fontSize: 25, color: BRAND.white, width: 210 }}>{label}</div>
            <div style={{ flex: 1, position: "relative", height: 12 }}>
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  borderRadius: 6,
                  background: "rgba(159,176,198,0.16)",
                }}
              />
              <div
                style={{
                  position: "absolute",
                  top: 0,
                  bottom: 0,
                  left: 0,
                  width: `${filled * (58 + (i % 3) * 14)}%`,
                  borderRadius: 6,
                  background: `linear-gradient(90deg, ${BRAND.gold}, ${BRAND.goldLight})`,
                }}
              />
            </div>
            <div style={{ fontWeight: 600, fontSize: 19, color: BRAND.muted, width: 260, textAlign: "right" }}>
              {hint}
            </div>
          </div>
        );
      })}
    </div>
  );
};

const BLaptopOpen: React.FC = () => {
  const fmt = useFmt();
  return (
    <LaptopShell push={false}>
      <PreviewProfileScreen fast portrait={fmt.kind === "vert"} />
    </LaptopShell>
  );
};

const BInputs: React.FC = () => {
  const fmt = useFmt();
  if (fmt.kind === "vert") {
    // Portrait: inputs render as a full-width card stack (no laptop bezel)
    return (
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div
          style={{
            width: 1000,
            transform: "scale(0.98)",
            borderRadius: 16,
            overflow: "hidden",
            border: "1px solid rgba(159,176,198,0.35)",
          }}
        >
          <div style={{ transform: "scale(0.625)", transformOrigin: "top left", width: 1600, height: 625 }}>
            <InputsScreen />
          </div>
        </div>
      </AbsoluteFill>
    );
  }
  return (
    <LaptopShell push={false}>
      <InputsScreen />
    </LaptopShell>
  );
};

// The mission-change beat: same screen, different mission/geography → the web
// visibly re-forms (different seed re-rolls every fit bar).
const BChange: React.FC = () => {
  const frame = useCurrentFrame();
  const fmt = useFmt();
  const swap = interpolate(frame, [88, 112], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const portrait = fmt.kind === "vert";
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ opacity: 1 - swap }}>
        <LaptopShell push={false}>
          <PreviewProfileScreen
            populated
            portrait={portrait}
            subtitle="Youth development  •  One county"
            seed={41}
          />
        </LaptopShell>
      </AbsoluteFill>
      <AbsoluteFill style={{ opacity: swap }}>
        <LaptopShell push={false}>
          <PreviewProfileScreen
            populated
            portrait={portrait}
            subtitle="Housing  •  Statewide"
            seed={87}
          />
        </LaptopShell>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const MiniWeb: React.FC<{ seed: number; size: number }> = ({ seed, size }) => {
  const rnd = makePrng(seed);
  const c = size / 2;
  return (
    <svg width={size} height={size}>
      {Array.from({ length: 6 }).map((_, i) => {
        const a = (i / 6) * Math.PI * 2 - Math.PI / 2 + rnd() * 0.4;
        const r = size * (0.26 + rnd() * 0.18);
        const x = c + Math.cos(a) * r;
        const y = c + Math.sin(a) * r;
        return (
          <g key={i}>
            <line x1={c} y1={c} x2={x} y2={y} stroke={BRAND.gold} strokeWidth={1.2} strokeOpacity={0.6} />
            <circle cx={x} cy={y} r={4} fill={BRAND.goldLight} fillOpacity={0.9} />
          </g>
        );
      })}
      <circle cx={c} cy={c} r={6} fill={BRAND.goldLight} />
    </svg>
  );
};

const EXAMPLES = [
  ["A youth program", "serving one county", 11],
  ["A housing nonprofit", "working statewide", 52],
  ["An arts organization", "in three cities", 93],
] as const;

const BExamples: React.FC = () => {
  const frame = useCurrentFrame();
  const fmt = useFmt();
  const K = fmt.K;
  const vertical = fmt.kind === "vert";
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div
        style={{
          display: "flex",
          flexDirection: vertical ? "column" : "row",
          gap: 34 * K,
          padding: "0 60px",
        }}
      >
        {EXAMPLES.map(([a, b, seed], i) => {
          const app = easeOut3((frame - 20 - i * 70) / 22);
          if (app <= 0) return null;
          return (
            <div
              key={a}
              style={{
                opacity: app,
                transform: `translateY(${(1 - app) * 24}px)`,
                // three across must fit the frame: 3×440 + gaps ≈ 1390 < 1920 (wide),
                // and ≈ 3×308 + gaps < 1080 on square/4:5 via K
                width: vertical ? 720 : 440 * K,
                background: "rgba(23,40,79,0.8)",
                border: "1px solid rgba(159,176,198,0.3)",
                borderRadius: 18,
                padding: `${28 * K}px ${30 * K}px`,
                display: "flex",
                alignItems: "center",
                gap: 26 * K,
              }}
            >
              <MiniWeb seed={seed} size={110 * K} />
              <div>
                <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 33 * K, color: BRAND.white }}>
                  {a}
                </div>
                <div style={{ fontFamily: SANS, fontWeight: 600, fontSize: 23 * K, color: BRAND.muted, marginTop: 6 }}>
                  {b}
                </div>
                <div
                  style={{
                    fontFamily: SANS,
                    fontWeight: 800,
                    fontSize: 15 * K,
                    letterSpacing: "0.18em",
                    color: BRAND.goldLight,
                    marginTop: 12 * K,
                  }}
                >
                  A DIFFERENT WEB
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const BDeliverable: React.FC = () => {
  const fmt = useFmt();
  return (
    <LaptopShell>
      <PreviewProfileScreen populated portrait={fmt.kind === "vert"} spotlight={30} />
    </LaptopShell>
  );
};

const BTypoClose: React.FC = () => {
  const fmt = useFmt();
  const K = fmt.K;
  const LINES = ["Your mission.", "Your location.", "Your opportunity web."];
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div style={{ textAlign: "center" }}>
        {LINES.map((l, i) => (
          <Rise key={l} delay={16 + i * 26}>
            <div
              style={{
                fontFamily: SERIF,
                fontWeight: 600,
                fontSize: (i === 2 ? 88 : 72) * K,
                lineHeight: 1.25,
                color: i === 2 ? BRAND.goldLight : BRAND.white,
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

const SCENES_B: [React.FC, number, number][] = [
  [LogoOpenShort, BB[0], BB[1]],
  [BLaptopOpen, BB[1], BB[2]],
  [BInputs, BB[2], BB[3]],
  [BLaptopOpen, BB[3], BB[4]],
  [BChange, BB[4], BB[5]],
  [BExamples, BB[5], BB[6]],
  [BDeliverable, BB[6], BB[7]],
  [BTypoClose, BB[7], BB[8]],
  [() => <UniversalEndCard dur={END_B} />, BB[8], BB[9]],
];

// ---------------------------------------------------------------------------
// Assembly
// ---------------------------------------------------------------------------
const VO_PAD = 5;
const VO_FADE = 4;
const slicesFor = (LINE: [number, number][], VO_AT: number[]) =>
  LINE.map(([s, e], i) => {
    const prevEnd = i > 0 ? LINE[i - 1][1] : 0;
    const nextStart = i < LINE.length - 1 ? LINE[i + 1][0] : e + 2 * VO_PAD;
    const padL = Math.min(VO_PAD, Math.floor((s - prevEnd) / 2));
    const padR = Math.min(VO_PAD, Math.floor((nextStart - e) / 2));
    return { from: s - padL, to: e + padR, at: VO_AT[i] - padL };
  });

const VariationFilm: React.FC<{
  fmt: Fmt;
  scenes: [React.FC, number, number][];
  slices: { from: number; to: number; at: number }[];
  voSrc: string;
  total: number;
  bridgeAt: number | null;
  music: "A" | "B";
}> = ({ fmt, scenes, slices, voSrc, total, bridgeAt, music }) => {
  const cuts = scenes.slice(1).map(([, from]) => from).filter((f) => f !== bridgeAt);
  return (
    <FmtCtx.Provider value={fmt}>
      <NavyBG w={fmt.W} h={fmt.H} threads={0.7}>
        {scenes.map(([Scene, from, to], i) => (
          <Sequence key={i} from={from} durationInFrames={to - from}>
            <Scene />
          </Sequence>
        ))}
        <SceneDissolve boundaries={cuts} />
        {bridgeAt !== null ? <ActBridge boundaries={[bridgeAt]} w={fmt.W} h={fmt.H} /> : null}

        {slices.map((s, i) => (
          <Sequence key={`vo${i}`} from={s.at} durationInFrames={s.to - s.from}>
            <Audio
              src={staticFile(voSrc)}
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

        {music === "A" ? (
          <>
            {/* minimal → resolve, handing off in the pre-product gap */}
            <Sequence from={0} durationInFrames={1060}>
              <Audio
                src={staticFile("music/stem-minimal.mp3")}
                volume={(f) =>
                  interpolate(f, [0, 50, 1000, 1060], [0, 0.5, 0.5, 0], {
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                  })
                }
              />
            </Sequence>
            <Sequence from={1000} durationInFrames={total - 1000}>
              <Audio
                src={staticFile("music/stem-resolve.mp3")}
                volume={(f) =>
                  interpolate(f, [0, 60, total - 1000 - 70, total - 1000], [0, 0.55, 0.55, 0], {
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                  })
                }
              />
            </Sequence>
          </>
        ) : (
          <>
            {/* build → resolve, warmer and more forward-moving from the start */}
            <Sequence from={0} durationInFrames={1400}>
              <Audio
                src={staticFile("music/stem-build.mp3")}
                volume={(f) =>
                  interpolate(f, [0, 50, 1340, 1400], [0, 0.46, 0.46, 0], {
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                  })
                }
              />
            </Sequence>
            <Sequence from={1340} durationInFrames={total - 1340}>
              <Audio
                src={staticFile("music/stem-resolve.mp3")}
                volume={(f) =>
                  interpolate(f, [0, 60, total - 1340 - 70, total - 1340], [0, 0.55, 0.55, 0], {
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                  })
                }
              />
            </Sequence>
          </>
        )}
      </NavyBG>
    </FmtCtx.Provider>
  );
};

const SL_A = slicesFor(LINE_A, VO_AT_A);
const SL_B = slicesFor(LINE_B, VO_AT_B);

const VisFilm: React.FC<{ fmt: Fmt }> = ({ fmt }) => (
  <VariationFilm
    fmt={fmt}
    scenes={SCENES_A}
    slices={SL_A}
    voSrc="anansi-universal-visibility-vo.mp3"
    total={VISIBILITY_TOTAL}
    bridgeAt={BA[4]}
    music="A"
  />
);
const ImagFilm: React.FC<{ fmt: Fmt }> = ({ fmt }) => (
  <VariationFilm
    fmt={fmt}
    scenes={SCENES_B}
    slices={SL_B}
    voSrc="anansi-universal-imagine-vo.mp3"
    total={IMAGINE_TOTAL}
    bridgeAt={null}
    music="B"
  />
);

export const AnansiUniversalVisibility: React.FC = () => <VisFilm fmt={FMTS.wide} />;
export const AnansiUniversalVisibility9x16: React.FC = () => <VisFilm fmt={FMTS.vert} />;
export const AnansiUniversalVisibility4x5: React.FC = () => <VisFilm fmt={FMTS.fourfive} />;
export const AnansiUniversalVisibility1x1: React.FC = () => <VisFilm fmt={FMTS.square} />;
export const AnansiUniversalImagine: React.FC = () => <ImagFilm fmt={FMTS.wide} />;
export const AnansiUniversalImagine9x16: React.FC = () => <ImagFilm fmt={FMTS.vert} />;
export const AnansiUniversalImagine4x5: React.FC = () => <ImagFilm fmt={FMTS.fourfive} />;
export const AnansiUniversalImagine1x1: React.FC = () => <ImagFilm fmt={FMTS.square} />;
