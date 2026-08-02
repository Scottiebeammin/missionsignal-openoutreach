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
  Subtitles,
  ThreadRule,
  makePrng,
} from "../components";

// ============================================================================
// CAMPAIGN VIDEO 1 — THE UNIVERSAL ANANSI ATLAS COMMERCIAL (~80.5s)
//
// National audience: any US nonprofit leader. Deliberately NO Empowered Girls,
// NO BAM, NO county figures — the promise is "this could be built around MY
// organization." Story: scattered information → connected opportunity web →
// YOUR ORGANIZATION HERE preview profile → verified CTA card.
//
// Beat map is COMPUTED from the measured VO line table (vo-line-slices.mjs) —
// same idiom as AnansiVisionFilm. Every re-generation of the VO master requires
// re-running the measurement and updating LINE below.
// ============================================================================

const easeOut3 = (t: number) => {
  const c = Math.min(1, Math.max(0, t));
  return 1 - Math.pow(1 - c, 3);
};

// ---------------------------------------------------------------------------
// Format context — one film, four native canvases. Layouts read `fmt`, never
// window math. kind: wide 1920×1080 · vert 1080×1920 · fourfive 1080×1350 ·
// square 1080×1080. Type scales by K (width-driven).
// ---------------------------------------------------------------------------
export type FmtKind = "wide" | "vert" | "fourfive" | "square";
export type Fmt = { W: number; H: number; kind: FmtKind; K: number };
export const FMTS: Record<FmtKind, Fmt> = {
  wide: { W: 1920, H: 1080, kind: "wide", K: 1 },
  vert: { W: 1080, H: 1920, kind: "vert", K: 0.66 },
  fourfive: { W: 1080, H: 1350, kind: "fourfive", K: 0.66 },
  square: { W: 1080, H: 1080, kind: "square", K: 0.64 },
};
export const FmtCtx = createContext<Fmt>(FMTS.wide);
export const useFmt = () => useContext(FmtCtx);

// ---------------------------------------------------------------------------
// VO line table — measured from anansi-universal-commercial-vo.mp3 (62.6s master)
// via `node scripts/vo-line-slices.mjs AnansiUniversalCommercial`.
// ---------------------------------------------------------------------------
const LINE: [number, number][] = [
  [0, 166], //   S02  you are already doing the work…
  [179, 507], // S03  every organization operates inside…
  [521, 792], // S04  the problem is not always…
  [809, 1004], // S05 anansi atlas turns that scattered…
  [1013, 1229], // S06 your profile is built around…
  [1240, 1439], // S07 you receive more than a list…
  [1445, 1636], // S08 whether you serve one neighborhood…
  [1645, 1880], // S09 your mission is already surrounded…
];
const DUR = LINE.map(([a, b]) => b - a);

const LOGO_OPEN = 90; // S01 — silent brand open
const END_CARD = 165; // S10 — silent contact card
const LEAD = [20, 25, 25, 30, 25, 20, 20, 25];
const TAIL = [15, 15, 30, 20, 20, 15, 15, 40];

const B: number[] = [0, LOGO_OPEN];
for (let i = 0; i < LINE.length; i++) {
  B.push(B[B.length - 1] + LEAD[i] + DUR[i] + TAIL[i]);
}
B.push(B[B.length - 1] + END_CARD);
export const UNIVERSAL_TOTAL = B[B.length - 1]; // 2416f = 80.5s @30fps

const VO_AT = LINE.map((_, i) => B[i + 1] + LEAD[i]);

// De-clicked VO slices — padded into the master's inter-line gaps, volume-ramped
// so the waveform starts and ends at zero (raw startFrom/endAt cuts click).
const VO_PAD = 5;
const VO_FADE = 4;
const SLICE = LINE.map(([s, e], i) => {
  const prevEnd = i > 0 ? LINE[i - 1][1] : 0;
  const nextStart = i < LINE.length - 1 ? LINE[i + 1][0] : e + 2 * VO_PAD;
  const padL = Math.min(VO_PAD, Math.floor((s - prevEnd) / 2));
  const padR = Math.min(VO_PAD, Math.floor((nextStart - e) / 2));
  return { from: s - padL, to: e + padR, at: VO_AT[i] - padL };
});

// ---------------------------------------------------------------------------
// The scattered field — shared card positions so S02→S05 read as one continuous
// space. x/y are % of frame; the same field works on every canvas.
// ---------------------------------------------------------------------------
type ScatterCard = {
  label: string;
  x: number;
  y: number;
  rot: number;
  delay: number;
  big?: boolean;
};
const SCATTER: ScatterCard[] = [
  { label: "FUNDERS", x: 18, y: 24, rot: -5, delay: 0, big: true },
  { label: "PARTNERS", x: 72, y: 20, rot: 4, delay: 8, big: true },
  { label: "PROGRAMS", x: 44, y: 14, rot: -2, delay: 16, big: true },
  { label: "RESOURCES", x: 26, y: 66, rot: 3, delay: 24, big: true },
  { label: "DEADLINES", x: 68, y: 64, rot: -4, delay: 32, big: true },
  { label: "GRANT PORTAL", x: 8, y: 44, rot: 6, delay: 40 },
  { label: "EMAIL THREADS", x: 86, y: 42, rot: -6, delay: 48 },
  { label: "NOTES", x: 38, y: 82, rot: 2, delay: 56 },
  { label: "BROWSER TABS", x: 56, y: 40, rot: -3, delay: 64 },
  { label: "RESEARCH DOCS", x: 84, y: 80, rot: 5, delay: 72 },
];

export const ScatterField: React.FC<{
  freezeAt?: number; // local frame when drift stops (S04)
  dimFrom?: number;
  extra?: boolean; // S04 piles on more cards
}> = ({ freezeAt, dimFrom, extra = false }) => {
  const frame = useCurrentFrame();
  const fmt = useFmt();
  const K = fmt.K;
  const t = frame / 30;
  const freeze =
    freezeAt === undefined
      ? 1
      : interpolate(frame, [freezeAt - 20, freezeAt], [1, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
  const dim =
    dimFrom === undefined
      ? 0
      : interpolate(frame, [dimFrom, dimFrom + 25], [0, 0.42], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
  const extras: ScatterCard[] = extra
    ? [
        { label: "SPREADSHEET (2023)", x: 50, y: 58, rot: -7, delay: 10 },
        { label: "CONFLICTING PRIORITIES", x: 34, y: 36, rot: 4, delay: 22 },
        { label: "MISSED CONNECTION", x: 62, y: 78, rot: -2, delay: 34 },
      ]
    : [];
  return (
    <AbsoluteFill>
      {[...SCATTER, ...extras].map((c, i) => {
        const a = easeOut3((frame - c.delay) / 22);
        if (a <= 0) return null;
        const floatX = Math.sin(t * 0.5 + i * 1.7) * 8 * freeze;
        const floatY = Math.cos(t * 0.4 + i * 2.3) * 6 * freeze;
        const w = (c.big ? 250 : 205) * K;
        return (
          <div
            key={c.label}
            style={{
              position: "absolute",
              left: `${c.x}%`,
              top: `${c.y}%`,
              width: w,
              transform: `translate(-50%,-50%) translate(${floatX}px, ${
                floatY + (1 - a) * 26
              }px) rotate(${c.rot}deg)`,
              opacity: a,
              background: "rgba(23,40,79,0.92)",
              border: `1px solid rgba(159,176,198,0.35)`,
              borderRadius: 10 * K,
              padding: `${14 * K}px ${16 * K}px`,
              boxShadow: "0 12px 32px rgba(0,0,0,0.35)",
            }}
          >
            <div
              style={{
                fontFamily: SANS,
                fontWeight: 800,
                fontSize: (c.big ? 21 : 16) * K,
                letterSpacing: "0.14em",
                color: c.big ? BRAND.goldLight : BRAND.muted,
              }}
            >
              {c.label}
            </div>
            <div
              style={{
                marginTop: 10 * K,
                height: 6 * K,
                width: "84%",
                borderRadius: 4,
                background: "rgba(159,176,198,0.28)",
              }}
            />
            <div
              style={{
                marginTop: 7 * K,
                height: 6 * K,
                width: "58%",
                borderRadius: 4,
                background: "rgba(159,176,198,0.2)",
              }}
            />
          </div>
        );
      })}
      {dim > 0 ? (
        <AbsoluteFill style={{ background: `rgba(6,10,22,${dim})` }} />
      ) : null}
    </AbsoluteFill>
  );
};

// Threads that connect the scattered cards during S03 — drawn between actual
// card positions so the connection is literal, not decorative.
const CONNECTIONS: [number, number, number][] = [
  // [fromCard, toCard, at]
  [0, 2, 40],
  [2, 1, 75],
  [0, 5, 110],
  [1, 6, 145],
  [3, 7, 180],
  [4, 9, 215],
  [3, 4, 250],
  [2, 8, 285],
];

// ---------------------------------------------------------------------------
// The preview-profile screen — the commercial's centerpiece. A live, populated
// product-register screen (NOT a wireframe: profiles are a real, shipped
// deliverable). Generalized labels only — no fabricated org-specific findings.
// Designed at 1600×1000 (landscape) / 1000×1250 (portrait), scaled to fit.
// ---------------------------------------------------------------------------
const SECTION_CARDS = [
  {
    title: "Aligned Funding Pathways",
    rows: ["Community foundations", "Corporate giving programs", "Public grant programs"],
  },
  {
    title: "Potential Strategic Partners",
    rows: ["Schools & universities", "Community organizations", "Local businesses"],
  },
  {
    title: "Government & Public Programs",
    rows: ["City pathways", "County pathways", "State pathways"],
  },
  {
    title: "Local & Regional Resources",
    rows: ["Capacity building", "Volunteer networks", "Training programs"],
  },
  {
    title: "Readiness Findings",
    rows: ["Strengths to build on", "Gaps worth closing", "Honest, not generic"],
  },
  {
    title: "30-Day Action Plan",
    rows: ["1 · Clarify the priority", "2 · Confirm eligibility", "3 · Begin outreach"],
  },
];

const OVERVIEW_STATS = ["Mission", "Population Served", "Service Area", "Priority Goals"];

const FitBar: React.FC<{ pct: number; delay: number }> = ({ pct, delay }) => {
  const frame = useCurrentFrame();
  const p = easeOut3((frame - delay) / 30) * pct;
  return (
    <div
      style={{
        height: 7,
        borderRadius: 4,
        background: "rgba(159,176,198,0.18)",
        overflow: "hidden",
        flex: 1,
      }}
    >
      <div
        style={{
          height: "100%",
          width: `${p}%`,
          borderRadius: 4,
          background: `linear-gradient(90deg, ${BRAND.gold}, ${BRAND.goldLight})`,
        }}
      />
    </div>
  );
};

export const PreviewProfileScreen: React.FC<{
  populated?: boolean; // true → everything visible from frame 0 (S07/S09)
  spotlight?: number; // local frame when the spotlight pass begins (S07)
  portrait?: boolean;
  fast?: boolean; // social pacing — halve the populate stagger
  title?: string;
  subtitle?: string;
  chip?: string;
  seed?: number; // different seed → visibly different fit bars ("never the same twice")
}> = ({
  populated = false,
  spotlight,
  portrait = false,
  fast = false,
  title = "YOUR ORGANIZATION HERE",
  subtitle = "Your Mission  •  Your Location",
  chip = "PREVIEW PROFILE",
  seed = 41,
}) => {
  const frame = useCurrentFrame();
  const d = (n: number) => (populated ? 0 : fast ? Math.round(n * 0.45) : n);
  const W = portrait ? 1000 : 1600;
  const H = portrait ? 1250 : 1000;
  const rnd = makePrng(seed);
  const pcts = SECTION_CARDS.map(() => 55 + rnd() * 38);

  // Spotlight pass: four stops, ~52f each — funding → partners → readiness → plan.
  const STOPS = [0, 1, 4, 5];
  const stop =
    spotlight === undefined
      ? -1
      : Math.min(3, Math.floor(Math.max(0, frame - spotlight) / 52));
  const litCard = spotlight !== undefined && frame >= spotlight ? STOPS[stop] : -1;

  return (
    <div
      style={{
        width: W,
        height: H,
        background: `linear-gradient(180deg, #0f2048 0%, ${BRAND.navy} 70%)`,
        fontFamily: SANS,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      {/* app chrome */}
      <div
        style={{
          height: 62,
          display: "flex",
          alignItems: "center",
          gap: 14,
          padding: "0 28px",
          background: "rgba(6,12,26,0.55)",
          borderBottom: "1px solid rgba(212,160,23,0.25)",
          flexShrink: 0,
        }}
      >
        <Img src={staticFile("anansi-emblem-785.png")} style={{ width: 30, height: 30 }} />
        <div style={{ fontWeight: 800, fontSize: 19, letterSpacing: "0.2em", color: BRAND.white }}>
          ANANSI ATLAS
        </div>
        <div style={{ flex: 1 }} />
        <div
          style={{
            fontWeight: 800,
            fontSize: 14,
            letterSpacing: "0.16em",
            color: BRAND.goldLight,
            border: `1px solid ${BRAND.gold}`,
            borderRadius: 999,
            padding: "6px 16px",
          }}
        >
          {chip}
        </div>
      </div>

      {/* header */}
      <div style={{ padding: portrait ? "26px 34px 6px" : "30px 44px 8px", flexShrink: 0 }}>
        <Rise delay={d(8)}>
          <div
            style={{
              fontFamily: SERIF,
              fontWeight: 600,
              fontSize: portrait ? 46 : 54,
              color: BRAND.white,
              letterSpacing: "-0.01em",
            }}
          >
            {title}
          </div>
        </Rise>
        <Rise delay={d(18)}>
          <div style={{ marginTop: 8, fontSize: portrait ? 22 : 25, fontWeight: 600, color: BRAND.muted }}>
            {subtitle}
          </div>
        </Rise>
        {/* overview strip */}
        <div style={{ display: "flex", gap: 12, marginTop: 20, flexWrap: "wrap" }}>
          {OVERVIEW_STATS.map((s, i) => (
            <Rise key={s} delay={d(34 + i * 9)}>
              <div
                style={{
                  border: "1px solid rgba(159,176,198,0.3)",
                  borderRadius: 999,
                  padding: "8px 18px",
                  fontSize: 16,
                  fontWeight: 700,
                  color: BRAND.ink,
                  background: "rgba(23,40,79,0.6)",
                }}
              >
                {s}
                <span style={{ color: BRAND.gold, marginLeft: 8 }}>●</span>
              </div>
            </Rise>
          ))}
        </div>
      </div>

      {/* section grid */}
      <div
        style={{
          flex: 1,
          display: "grid",
          gridTemplateColumns: portrait ? "1fr 1fr" : "1fr 1fr 1fr",
          gap: 18,
          padding: portrait ? "18px 34px 30px" : "20px 44px 36px",
        }}
      >
        {SECTION_CARDS.map((card, ci) => {
          const lit = litCard === ci;
          return (
            <Rise key={card.title} delay={d(70 + ci * 16)}>
              <div
                style={{
                  height: "100%",
                  background: lit ? "rgba(212,160,23,0.10)" : "rgba(23,40,79,0.7)",
                  border: lit
                    ? `1.5px solid ${BRAND.gold}`
                    : "1px solid rgba(159,176,198,0.24)",
                  borderRadius: 14,
                  padding: "18px 20px",
                  boxShadow: lit ? `0 0 34px rgba(212,160,23,0.25)` : undefined,
                  display: "flex",
                  flexDirection: "column",
                  gap: 12,
                }}
              >
                <div
                  style={{
                    fontWeight: 800,
                    fontSize: portrait ? 19 : 21,
                    letterSpacing: "0.03em",
                    color: lit ? BRAND.goldLight : BRAND.white,
                  }}
                >
                  {card.title}
                </div>
                {card.rows.map((r, ri) => (
                  <div key={r} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div
                      style={{
                        fontSize: portrait ? 15 : 17,
                        fontWeight: 600,
                        color: BRAND.muted,
                        width: portrait ? 150 : 190,
                        flexShrink: 0,
                      }}
                    >
                      {r}
                    </div>
                    <FitBar pct={pcts[ci] - ri * 9} delay={d(86 + ci * 16 + ri * 6)} />
                  </div>
                ))}
              </div>
            </Rise>
          );
        })}
      </div>
    </div>
  );
};

// Laptop shell hosting a live screen. Wide canvases get the bezel + base;
// portrait canvases get a clean device card (a tiny laptop reads as clutter
// at 1080 wide).
export const LaptopShell: React.FC<{ push?: boolean; children: React.ReactNode }> = ({
  push = true,
  children,
}) => {
  const frame = useCurrentFrame();
  const fmt = useFmt();
  const scaleIn = 0.985 + 0.015 * easeOut3(frame / 24);
  const drift = push ? interpolate(frame, [0, 300], [1, 1.035], { extrapolateRight: "clamp" }) : 1;
  const isPortrait = fmt.kind === "vert";
  const screenW = isPortrait ? 1000 : fmt.kind === "wide" ? 1460 : 980;
  const innerW = isPortrait ? 1000 : 1600;
  const innerH = isPortrait ? 1250 : 1000;
  const k = screenW / innerW;
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div style={{ transform: `scale(${scaleIn * drift})` }}>
        <div
          style={{
            width: screenW + 24,
            borderRadius: 18,
            padding: 12,
            background: "#0a1226",
            border: "1px solid rgba(159,176,198,0.35)",
            boxShadow: "0 40px 120px rgba(0,0,0,0.55), 0 0 60px rgba(212,160,23,0.08)",
          }}
        >
          <div style={{ width: screenW, height: innerH * k, overflow: "hidden", borderRadius: 8 }}>
            <div style={{ transform: `scale(${k})`, transformOrigin: "top left" }}>{children}</div>
          </div>
        </div>
        {!isPortrait ? (
          <div
            style={{
              margin: "0 auto",
              width: screenW * 1.14,
              height: 16,
              borderRadius: "0 0 18px 18px",
              background: "linear-gradient(180deg, #1a2949, #0a1226)",
            }}
          />
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

// OrbWeb collapses to 0×0 inside a bare transform div (AbsoluteFill children) —
// wrap with explicit box. See memory: remotion-absolutefill-transform-collapse.
const ORB = 1080;
const OrbWebBox: React.FC<{ scale: number; progress: number }> = ({ scale, progress }) => (
  <div style={{ position: "relative", width: ORB, height: ORB, transform: `scale(${scale})` }}>
    <OrbWeb progress={progress} />
  </div>
);

// ---------------------------------------------------------------------------
// Scenes
// ---------------------------------------------------------------------------
const S01LogoOpen: React.FC = () => {
  const frame = useCurrentFrame();
  const fmt = useFmt();
  const K = fmt.K;
  const emblemIn = easeOut3((frame - 26) / 26);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <ThreadRule from={[26, 50]} to={[74, 50]} at={4} draw={26} hold={80} out={0} opacity={0.5} />
      <NodeField w={fmt.W} h={fmt.H} count={9} at={14} fadeIn={30} opacity={0.16} />
      {emblemIn > 0 ? (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 26 * K,
            opacity: emblemIn,
            transform: `scale(${0.92 + 0.08 * emblemIn})`,
          }}
        >
          <Img
            src={staticFile("anansi-emblem-785.png")}
            style={{ width: 132 * K, height: 132 * K }}
          />
          <div
            style={{
              fontFamily: SANS,
              fontWeight: 800,
              fontSize: 30 * K,
              letterSpacing: "0.26em",
              color: BRAND.white,
            }}
          >
            ANANSI ATLAS
          </div>
        </div>
      ) : null}
      <div style={{ position: "absolute", bottom: "26%", width: "100%" }}>
        <Eyebrow delay={52}>The Web of Opportunity</Eyebrow>
      </div>
    </AbsoluteFill>
  );
};

const S02Hook: React.FC = () => <ScatterField />;

const S03Ecosystem: React.FC = () => (
  <AbsoluteFill>
    <ScatterField />
    {CONNECTIONS.map(([a, b, at]) => (
      <ThreadRule
        key={`${a}-${b}`}
        from={[SCATTER[a].x, SCATTER[a].y]}
        to={[SCATTER[b].x, SCATTER[b].y]}
        at={at}
        draw={34}
        hold={400}
        out={40}
        opacity={0.55}
        dots
      />
    ))}
  </AbsoluteFill>
);

const S04Problem: React.FC = () => {
  const fmt = useFmt();
  return (
    <AbsoluteFill>
      <ScatterField extra freezeAt={200} dimFrom={230} />
      <div
        style={{
          position: "absolute",
          bottom: fmt.kind === "vert" ? "20%" : "12%",
          width: "100%",
        }}
      >
        <Eyebrow delay={244}>How does it all connect?</Eyebrow>
      </div>
    </AbsoluteFill>
  );
};

const S05ProductIntro: React.FC = () => {
  const frame = useCurrentFrame();
  const fmt = useFmt();
  const K = fmt.K;
  const progress = easeOut3((frame - 14) / 90);
  const orbScale = (fmt.kind === "wide" ? 0.78 : 0.62) * (0.97 + 0.03 * progress);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <OrbWebBox scale={orbScale} progress={progress} />
      <div style={{ position: "absolute", top: fmt.kind === "vert" ? "13%" : "9%", width: "100%" }}>
        <Rise delay={20}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 18 * K,
            }}
          >
            <Img
              src={staticFile("anansi-emblem-785.png")}
              style={{ width: 46 * K, height: 46 * K }}
            />
            <div
              style={{
                fontFamily: SANS,
                fontWeight: 800,
                fontSize: 30 * K,
                letterSpacing: "0.26em",
                color: BRAND.white,
              }}
            >
              ANANSI ATLAS
            </div>
          </div>
        </Rise>
      </div>
      <div
        style={{ position: "absolute", bottom: fmt.kind === "vert" ? "16%" : "8%", width: "100%" }}
      >
        <Eyebrow delay={90}>One clear view</Eyebrow>
      </div>
    </AbsoluteFill>
  );
};

const S06PreviewProfile: React.FC = () => {
  const fmt = useFmt();
  return (
    <LaptopShell>
      <PreviewProfileScreen portrait={fmt.kind === "vert"} />
    </LaptopShell>
  );
};

const SPOTLIGHT_LABELS = [
  "WHERE TO FOCUS",
  "WHO COULD HELP",
  "WHAT MAY BE HOLDING YOU BACK",
  "WHAT TO DO NEXT",
];

const S07DecisionSupport: React.FC = () => {
  const frame = useCurrentFrame();
  const fmt = useFmt();
  const K = fmt.K;
  const stop = Math.min(3, Math.floor(Math.max(0, frame - 16) / 52));
  const a = easeOut3(((frame - 16) % 52) / 14);
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", inset: 0, transform: "translateY(-34px)" }}>
        <LaptopShell push={false}>
          <PreviewProfileScreen populated portrait={fmt.kind === "vert"} spotlight={16} />
        </LaptopShell>
      </div>
      {frame >= 16 ? (
        <div
          style={{
            position: "absolute",
            bottom: fmt.kind === "vert" ? "17%" : "3.6%",
            width: "100%",
            textAlign: "center",
            fontFamily: SANS,
            fontWeight: 800,
            fontSize: 27 * K,
            letterSpacing: "0.2em",
            color: BRAND.goldLight,
            opacity: a,
          }}
        >
          {SPOTLIGHT_LABELS[stop]}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

const MISSIONS = [
  "Youth development",
  "Housing",
  "Education",
  "Health",
  "Workforce",
  "Veterans",
  "Arts & culture",
  "Environment",
  "Family support",
];
const RING_LABELS = ["ONE NEIGHBORHOOD", "AN ENTIRE STATE", "ACROSS THE COUNTRY"];

const S08National: React.FC = () => {
  const frame = useCurrentFrame();
  const fmt = useFmt();
  const K = fmt.K;
  const cx = fmt.W / 2;
  const cy = fmt.H / 2;
  const base = Math.min(fmt.W, fmt.H);
  const RADII = [base * 0.17, base * 0.29, base * 0.41];
  const rnd = makePrng(7);
  return (
    <AbsoluteFill>
      <svg width={fmt.W} height={fmt.H} style={{ position: "absolute" }}>
        {RADII.map((r, i) => {
          const p = easeOut3((frame - 8 - i * 14) / 34);
          return (
            <circle
              key={r}
              cx={cx}
              cy={cy}
              r={r * p}
              fill="none"
              stroke={BRAND.gold}
              strokeOpacity={0.32 - i * 0.06}
              strokeWidth={1.4}
            />
          );
        })}
        <circle cx={cx} cy={cy} r={9} fill={BRAND.goldLight} />
      </svg>
      <div
        style={{
          position: "absolute",
          left: cx,
          top: cy + 26,
          transform: "translateX(-50%)",
          fontFamily: SANS,
          fontWeight: 800,
          fontSize: 20 * K,
          letterSpacing: "0.2em",
          color: BRAND.goldLight,
          opacity: easeOut3((frame - 10) / 20),
        }}
      >
        YOUR MISSION
      </div>
      {RING_LABELS.map((l, i) => (
        <div
          key={l}
          style={{
            position: "absolute",
            left: cx,
            top: cy - RADII[i] - 26 * K,
            transform: "translateX(-50%)",
            fontFamily: SANS,
            fontWeight: 800,
            fontSize: 17 * K,
            letterSpacing: "0.22em",
            color: BRAND.muted,
            opacity: easeOut3((frame - 26 - i * 14) / 22) * 0.9,
          }}
        >
          {l}
        </div>
      ))}
      {MISSIONS.map((m, i) => {
        const ring = RADII[i % 3];
        // +0.55 base offset keeps every chip clear of the 12-o'clock ring labels
        const ang = (i / MISSIONS.length) * Math.PI * 2 - Math.PI / 2 + 0.55 + rnd() * 0.4;
        const x = cx + Math.cos(ang) * ring;
        const y = cy + Math.sin(ang) * ring;
        const a = easeOut3((frame - 46 - i * 11) / 20);
        if (a <= 0) return null;
        return (
          <div
            key={m}
            style={{
              position: "absolute",
              left: x,
              top: y,
              transform: `translate(-50%,-50%) translateY(${(1 - a) * 18}px)`,
              opacity: a,
              fontFamily: SANS,
              fontWeight: 700,
              fontSize: 19 * K,
              color: BRAND.ink,
              background: "rgba(23,40,79,0.9)",
              border: "1px solid rgba(212,160,23,0.5)",
              borderRadius: 999,
              padding: `${8 * K}px ${18 * K}px`,
              whiteSpace: "nowrap",
            }}
          >
            {m}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

const S09Close: React.FC = () => {
  const frame = useCurrentFrame();
  const fmt = useFmt();
  const vignette = interpolate(frame, [230, 300], [0, 0.5], {
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

export const UniversalEndCard: React.FC<{ dur?: number }> = ({ dur = END_CARD }) => {
  const frame = useCurrentFrame();
  const fmt = useFmt();
  const K = fmt.K;
  const fadeOut = interpolate(frame, [dur - 30, dur], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 22 * K,
        }}
      >
        <Rise delay={4}>
          <Img
            src={staticFile("anansi-emblem-785.png")}
            style={{ width: 110 * K, height: 110 * K, display: "block", margin: "0 auto" }}
          />
        </Rise>
        <Rise delay={12}>
          <div
            style={{
              fontFamily: SERIF,
              fontWeight: 600,
              fontSize: 52 * K,
              color: BRAND.white,
              textAlign: "center",
              padding: "0 60px",
            }}
          >
            See your whole web of opportunity.
          </div>
        </Rise>
        <CTAButton delay={26}>VISIT ANANSIATLAS.COM</CTAButton>
        <Rise delay={38}>
          <div
            style={{
              fontFamily: SERIF,
              fontWeight: 600,
              fontSize: 32 * K,
              color: BRAND.goldLight,
              textAlign: "center",
            }}
          >
            or book a meeting
          </div>
        </Rise>
        <Rise delay={48}>
          <div
            style={{
              fontFamily: SANS,
              fontWeight: 600,
              fontSize: 22 * K,
              color: BRAND.muted,
              textAlign: "center",
              lineHeight: 1.7,
            }}
          >
            cal.com/marcus-scott-br7maf/founder-walkthrough
            <br />
            marcus@anansiatlas.com
          </div>
        </Rise>
      </div>
      <AbsoluteFill style={{ background: `rgba(4,7,16,${fadeOut})`, pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// Captions (Captioned master only)
// ---------------------------------------------------------------------------
const cap = (i: number, fromFrac: number, toFrac: number, text: string): Caption => ({
  text,
  from: Math.round(VO_AT[i] + DUR[i] * fromFrac),
  duration: Math.round(DUR[i] * (toFrac - fromFrac)),
});
const CAPTIONS: Caption[] = [
  cap(0, 0, 0.36, "You are already doing the work."),
  cap(0, 0.36, 1, "But the opportunities surrounding your mission are scattered everywhere."),
  cap(1, 0, 0.44, "Every organization operates inside a larger opportunity ecosystem —"),
  cap(1, 0.44, 1, "funders, partners, government pathways, community resources, risks, and next steps."),
  cap(2, 0, 0.38, "The problem is not always finding another opportunity."),
  cap(2, 0.38, 1, "It is understanding how everything connects — and knowing what you're ready to pursue."),
  cap(3, 0, 1, "Anansi Atlas turns that scattered information into one clear view of the opportunity web surrounding your mission."),
  cap(4, 0, 0.5, "Your profile is built around your mission, your location,"),
  cap(4, 0.5, 1, "the people you serve, your goals, and your current capacity."),
  cap(5, 0, 0.3, "You receive more than a list."),
  cap(5, 0.3, 1, "You see where to focus, who could help, what may be holding you back, and what to do next."),
  cap(6, 0, 0.5, "Whether you serve one neighborhood, an entire state,"),
  cap(6, 0.5, 1, "or communities across the country, your opportunity web is unique."),
  cap(7, 0, 0.42, "Your mission is already surrounded by opportunity."),
  cap(7, 0.42, 1, "Anansi Atlas helps you see the whole web — and decide what to do next."),
];

// ---------------------------------------------------------------------------
// Film
// ---------------------------------------------------------------------------
const SCENES: [React.FC, number, number][] = [
  [S01LogoOpen, B[0], B[1]],
  [S02Hook, B[1], B[2]],
  [S03Ecosystem, B[2], B[3]],
  [S04Problem, B[3], B[4]],
  [S05ProductIntro, B[4], B[5]],
  [S06PreviewProfile, B[5], B[6]],
  [S07DecisionSupport, B[6], B[7]],
  [S08National, B[7], B[8]],
  [S09Close, B[8], B[9]],
  [UniversalEndCard, B[9], B[10]],
];

const VO_SRC = "anansi-universal-commercial-vo.mp3";

const Film: React.FC<{ fmt: Fmt; captions?: boolean }> = ({ fmt, captions = false }) => {
  return (
    <FmtCtx.Provider value={fmt}>
      <NavyBG w={fmt.W} h={fmt.H} threads={0.7}>
        {SCENES.map(([Scene, from, to], i) => (
          <Sequence key={i} from={from} durationInFrames={to - from}>
            <Scene />
          </Sequence>
        ))}

        {/* dissolves on plain cuts; the web draws THROUGH the scatter→product cut */}
        <SceneDissolve boundaries={[B[1], B[2], B[3], B[5], B[6], B[7], B[8], B[9]]} />
        <ActBridge boundaries={[B[4]]} w={fmt.W} h={fmt.H} />

        {/* VO — padded, volume-ramped slices of the single master take */}
        {SLICE.map((s, i) => (
          <Sequence key={`vo${i}`} from={s.at} durationInFrames={s.to - s.from}>
            <Audio
              src={staticFile(VO_SRC)}
              startFrom={s.from}
              endAt={s.to}
              volume={(f) =>
                interpolate(
                  f,
                  [0, VO_FADE, s.to - s.from - VO_FADE, s.to - s.from],
                  [0, 1, 1, 0],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                )
              }
            />
          </Sequence>
        ))}

        {/* score — minimal → build → resolve; crossfades inside measured speech gaps */}
        <Sequence from={0} durationInFrames={1015}>
          <Audio
            src={staticFile("music/stem-minimal.mp3")}
            volume={(f) =>
              interpolate(f, [0, 60, 955, 1015], [0, 0.5, 0.5, 0], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              })
            }
          />
        </Sequence>
        <Sequence from={955} durationInFrames={1021}>
          <Audio
            src={staticFile("music/stem-build.mp3")}
            volume={(f) =>
              interpolate(f, [0, 60, 961, 1021], [0, 0.5, 0.5, 0], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              })
            }
          />
        </Sequence>
        <Sequence from={1936} durationInFrames={UNIVERSAL_TOTAL - 1936}>
          <Audio
            src={staticFile("music/stem-resolve.mp3")}
            volume={(f) =>
              interpolate(
                f,
                [0, 60, UNIVERSAL_TOTAL - 1936 - 70, UNIVERSAL_TOTAL - 1936],
                [0, 0.55, 0.55, 0],
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

export const AnansiUniversalCommercial: React.FC = () => <Film fmt={FMTS.wide} />;
export const AnansiUniversalCommercialCaptioned: React.FC = () => (
  <Film fmt={FMTS.wide} captions />
);
export const AnansiUniversal9x16: React.FC = () => <Film fmt={FMTS.vert} />;
export const AnansiUniversal4x5: React.FC = () => <Film fmt={FMTS.fourfive} />;
export const AnansiUniversal1x1: React.FC = () => <Film fmt={FMTS.square} />;
