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
  CTAButton,
  NavyBG,
  NodeField,
  Rise,
  SANS,
  SERIF,
  ThreadRule,
} from "../components";
import { PreviewProfileScreen } from "./AnansiUniversalCommercial";

// ============================================================================
// CAMPAIGN VIDEO 2 — 30-SECOND SOCIAL AD (native 9:16, 900f)
//
// One idea: you don't have an opportunity problem, you have a visibility
// problem. Captions burned throughout (autoplay-muted feeds). Hook variants
// B/C/D are voiced in the SAME master take (lines 6-8) so every cut shares one
// VO; the Alt version drops the sting, keeps a corner mark, and reveals the
// full logo only at the end.
// ============================================================================

const easeOut3 = (t: number) => {
  const c = Math.min(1, Math.max(0, t));
  return 1 - Math.pow(1 - c, 3);
};

type FmtKind = "vert" | "fourfive" | "square" | "wide";
type Fmt = { W: number; H: number; kind: FmtKind; K: number };
const FMTS: Record<FmtKind, Fmt> = {
  vert: { W: 1080, H: 1920, kind: "vert", K: 1 },
  fourfive: { W: 1080, H: 1350, kind: "fourfive", K: 0.88 },
  square: { W: 1080, H: 1080, kind: "square", K: 0.8 },
  wide: { W: 1920, H: 1080, kind: "wide", K: 0.86 },
};
const FmtCtx = createContext<Fmt>(FMTS.vert);
const useFmt = () => useContext(FmtCtx);

// Measured via `node scripts/vo-line-slices.mjs AnansiSocial30` (30.6s master).
// 0-4 = body (hook A), 5-7 = alternate hooks B/C/D.
const LINE: [number, number][] = [
  [0, 77],
  [86, 138],
  [142, 368],
  [377, 529],
  [556, 619],
  [625, 701], // hook B
  [713, 800], // hook C
  [807, 917], // hook D
];

export const SOCIAL30_TOTAL = 900;
const VO_SRC = "anansi-social30-vo.mp3";
const VO_FADE = 4;

// Scene boundaries (with sting). The Alt cut shifts everything up by STING.
const STING = 30;
const S = {
  hook: [STING, 150],
  reframe: [150, 270],
  promise: [270, 550],
  profile: [550, 760],
  close: [760, 900],
} as const;

const HOOK_TEXT: Record<string, [string, string]> = {
  A: ["YOU MAY NOT HAVE", "AN OPPORTUNITY PROBLEM."],
  B: ["WHAT OPPORTUNITIES ARE HIDING", "AROUND YOUR MISSION?"],
  C: ["GRANTS ARE ONLY ONE PART", "OF YOUR OPPORTUNITY WEB."],
  D: ["YOUR NEXT OPPORTUNITY MAY", "ALREADY BE CONNECTED."],
};
const HOOK_LINE: Record<string, number> = { A: 0, B: 5, C: 6, D: 7 };

// Flash-stack cards for the hook — quick 1-2s visual changes, mobile-scaled.
const FLASH = [
  { label: "GRANT PORTAL", x: 30, y: 26, rot: -6, at: 0 },
  { label: "PARTNER LIST", x: 70, y: 22, rot: 5, at: 8 },
  { label: "GOV PROGRAMS", x: 26, y: 66, rot: 4, at: 16 },
  { label: "EMAILS", x: 72, y: 62, rot: -5, at: 24 },
  { label: "DEADLINES", x: 50, y: 44, rot: -2, at: 32, big: true },
  { label: "BROWSER TABS", x: 38, y: 82, rot: 3, at: 40 },
  { label: "RESEARCH DOCS", x: 66, y: 84, rot: -4, at: 48 },
];

const FlashCards: React.FC<{ freeze?: boolean; dim?: number }> = ({ freeze = false, dim = 0 }) => {
  const frame = useCurrentFrame();
  const fmt = useFmt();
  const K = fmt.K;
  const t = frame / 30;
  const wob = freeze ? 0 : 1;
  return (
    <AbsoluteFill>
      {FLASH.map((c, i) => {
        const a = easeOut3((frame - c.at) / 10);
        if (a <= 0) return null;
        return (
          <div
            key={c.label}
            style={{
              position: "absolute",
              left: `${c.x}%`,
              top: `${c.y}%`,
              width: (c.big ? 300 : 250) * K,
              transform: `translate(-50%,-50%) rotate(${c.rot}deg) translate(${
                Math.sin(t * 0.7 + i * 2) * 6 * wob
              }px, ${(1 - a) * 30}px)`,
              opacity: a,
              background: "rgba(23,40,79,0.94)",
              border: "1px solid rgba(159,176,198,0.4)",
              borderRadius: 12,
              padding: `${18 * K}px ${20 * K}px`,
              boxShadow: "0 14px 40px rgba(0,0,0,0.4)",
            }}
          >
            <div
              style={{
                fontFamily: SANS,
                fontWeight: 800,
                fontSize: (c.big ? 27 : 22) * K,
                letterSpacing: "0.12em",
                color: c.big ? BRAND.goldLight : BRAND.muted,
              }}
            >
              {c.label}
            </div>
            <div
              style={{
                marginTop: 12 * K,
                height: 7 * K,
                width: "80%",
                borderRadius: 4,
                background: "rgba(159,176,198,0.3)",
              }}
            />
          </div>
        );
      })}
      {dim > 0 ? <AbsoluteFill style={{ background: `rgba(6,10,22,${dim})` }} /> : null}
    </AbsoluteFill>
  );
};

const BigText: React.FC<{ lines: [string, string]; delay?: number; accentSecond?: boolean }> = ({
  lines,
  delay = 0,
  accentSecond = true,
}) => {
  const fmt = useFmt();
  const K = fmt.K;
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div style={{ textAlign: "center", padding: "0 60px" }}>
        <Rise delay={delay}>
          <div
            style={{
              fontFamily: SANS,
              fontWeight: 900,
              fontSize: 62 * K,
              lineHeight: 1.14,
              letterSpacing: "0.01em",
              color: BRAND.white,
              textShadow: "0 4px 30px rgba(0,0,0,0.55)",
            }}
          >
            {lines[0]}
          </div>
        </Rise>
        <Rise delay={delay + 7}>
          <div
            style={{
              fontFamily: SANS,
              fontWeight: 900,
              fontSize: 62 * K,
              lineHeight: 1.14,
              letterSpacing: "0.01em",
              color: accentSecond ? BRAND.goldLight : BRAND.white,
              textShadow: "0 4px 30px rgba(0,0,0,0.55)",
            }}
          >
            {lines[1]}
          </div>
        </Rise>
      </div>
    </AbsoluteFill>
  );
};

const WEB_LABELS = ["FUNDERS", "PARTNERS", "RESOURCES", "PATHWAYS", "READINESS"];

const PromiseWeb: React.FC = () => {
  const frame = useCurrentFrame();
  const fmt = useFmt();
  const K = fmt.K;
  const cx = 50;
  const cy = fmt.kind === "vert" ? 46 : 50;
  const spread = fmt.kind === "vert" ? 30 : 24;
  const pts = WEB_LABELS.map((_, i) => {
    const a = (i / WEB_LABELS.length) * Math.PI * 2 - Math.PI / 2;
    return [cx + Math.cos(a) * spread * 0.9, cy + (Math.sin(a) * spread * 0.9 * fmt.W) / fmt.H];
  });
  return (
    <AbsoluteFill>
      <NodeField w={fmt.W} h={fmt.H} count={11} seed={31} at={0} fadeIn={24} opacity={0.14} />
      {pts.map((p, i) => (
        <ThreadRule
          key={i}
          from={[cx, cy]}
          to={[p[0], p[1]]}
          at={14 + i * 12}
          draw={22}
          hold={400}
          out={40}
          opacity={0.6}
          dots
        />
      ))}
      <div
        style={{
          position: "absolute",
          left: `${cx}%`,
          top: `${cy}%`,
          transform: "translate(-50%,-50%)",
          width: 15 * K,
          height: 15 * K,
          borderRadius: 999,
          background: BRAND.goldLight,
          boxShadow: `0 0 30px ${BRAND.gold}`,
          opacity: easeOut3(frame / 14),
        }}
      />
      {pts.map((p, i) => {
        const a = easeOut3((frame - 30 - i * 12) / 16);
        if (a <= 0) return null;
        return (
          <div
            key={WEB_LABELS[i]}
            style={{
              position: "absolute",
              left: `${p[0]}%`,
              top: `${p[1]}%`,
              transform: "translate(-50%,-50%)",
              opacity: a,
              fontFamily: SANS,
              fontWeight: 800,
              fontSize: 25 * K,
              letterSpacing: "0.16em",
              color: BRAND.ink,
              background: "rgba(23,40,79,0.92)",
              border: `1px solid ${BRAND.gold}`,
              borderRadius: 999,
              padding: `${10 * K}px ${22 * K}px`,
            }}
          >
            {WEB_LABELS[i]}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

const ProfileScene: React.FC = () => {
  const frame = useCurrentFrame();
  const fmt = useFmt();
  const portrait = fmt.kind === "vert" || fmt.kind === "fourfive";
  const innerW = portrait ? 1000 : 1600;
  const innerH = portrait ? 1250 : 1000;
  const maxW = fmt.W * (portrait ? 0.92 : 0.72);
  const maxH = fmt.H * 0.78;
  const k = Math.min(maxW / innerW, maxH / innerH);
  const scaleIn = 0.97 + 0.03 * easeOut3(frame / 20);
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
            <PreviewProfileScreen portrait={portrait} fast />
          </div>
        </div>
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

// Mobile caption strip — larger and higher than the long-form Subtitles bar,
// inside 9:16 platform-safe margins.
type SocialCaption = { text: string; from: number; duration: number };
const SocialCaptions: React.FC<{ captions: SocialCaption[] }> = ({ captions }) => {
  const frame = useCurrentFrame();
  const fmt = useFmt();
  const K = fmt.K;
  const active = captions.find((c) => frame >= c.from && frame < c.from + c.duration);
  if (!active) return null;
  const local = frame - active.from;
  const opacity = interpolate(local, [0, 6], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: fmt.kind === "vert" ? 300 : fmt.kind === "wide" ? 70 : 130,
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

const LogoSting: React.FC = () => {
  const frame = useCurrentFrame();
  const fmt = useFmt();
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <ThreadRule from={[30, 50]} to={[70, 50]} at={0} draw={12} hold={30} out={0} opacity={0.5} />
      <Img
        src={staticFile("anansi-emblem-785.png")}
        style={{ width: 130 * fmt.K, height: 130 * fmt.K, opacity: easeOut3(frame / 8) }}
      />
    </AbsoluteFill>
  );
};

const voSlice = (idx: number, at: number) => {
  const [s, e] = LINE[idx];
  const from = Math.max(0, s - 4);
  const to = e + 4;
  return { from, to, at: at - (s - from) };
};

const Film: React.FC<{ fmt: Fmt; hook?: "A" | "B" | "C" | "D"; sting?: boolean; cta?: string }> = ({
  fmt,
  hook = "A",
  sting = true,
  cta = "VISIT ANANSIATLAS.COM", // Scott 2026-07-31: CTA = visit the website, or book a meeting
}) => {
  const off = sting ? 0 : -STING; // Alt cut: hook starts immediately
  const hookIdx = HOOK_LINE[hook];
  const hookSlice = voSlice(hookIdx, S.hook[0] + off + 6);
  const slices = [
    hookSlice,
    voSlice(1, S.reframe[0] + off + 8),
    voSlice(2, S.promise[0] + off + 10),
    voSlice(3, S.profile[0] + off + 12),
    voSlice(4, S.close[0] + off + 12),
  ];
  const hookDur = LINE[hookIdx][1] - LINE[hookIdx][0];

  // Hook + reframe scenes carry their spoken words as full-frame display type,
  // so the caption strip runs only from the promise scene onward — a duplicate
  // bar under identical giant text is noise, not accessibility.
  const captions: SocialCaption[] = [
    { text: "Anansi Atlas maps the funders, partners, resources,", from: S.promise[0] + off + 10, duration: 113 },
    { text: "government pathways, and readiness gaps surrounding your mission.", from: S.promise[0] + off + 123, duration: S.promise[1] - S.promise[0] - 123 },
    { text: "Then it turns that research into clear priorities,", from: S.profile[0] + off + 12, duration: 84 },
    { text: "and a practical 30-day action plan.", from: S.profile[0] + off + 96, duration: S.profile[1] - S.profile[0] - 96 },
    { text: "See your whole web of opportunity.", from: S.close[0] + off + 12, duration: 80 },
  ];

  const endDur = S.close[1] + (sting ? 0 : STING) - S.close[0] - (sting ? 0 : 0);

  return (
    <FmtCtx.Provider value={fmt}>
      <NavyBG w={fmt.W} h={fmt.H} threads={0.7}>
        {sting ? (
          <Sequence from={0} durationInFrames={STING}>
            <LogoSting />
          </Sequence>
        ) : null}

        <Sequence from={S.hook[0] + off} durationInFrames={S.hook[1] - S.hook[0]}>
          <FlashCards />
          <BigText lines={HOOK_TEXT[hook]} delay={6} />
        </Sequence>

        <Sequence from={S.reframe[0] + off} durationInFrames={S.reframe[1] - S.reframe[0]}>
          <FlashCards freeze dim={0.5} />
          <BigText lines={["YOU MAY HAVE", "A VISIBILITY PROBLEM."]} delay={4} />
        </Sequence>

        <Sequence from={S.promise[0] + off} durationInFrames={S.promise[1] - S.promise[0]}>
          <PromiseWeb />
        </Sequence>

        <Sequence from={S.profile[0] + off} durationInFrames={S.profile[1] - S.profile[0]}>
          <ProfileScene />
        </Sequence>

        <Sequence from={S.close[0] + off} durationInFrames={endDur}>
          <EndCard cta={cta} dur={endDur} />
        </Sequence>

        {/* corner mark when there's no opening sting */}
        {!sting ? (
          <div
            style={{
              position: "absolute",
              top: 44,
              right: 44,
              opacity: 0.9,
            }}
          >
            <Img src={staticFile("anansi-emblem-785.png")} style={{ width: 64, height: 64 }} />
          </div>
        ) : null}

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
          src={staticFile("music/stem-build.mp3")}
          volume={(f) =>
            interpolate(f, [0, 30, 800, 900], [0, 0.42, 0.42, 0], {
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

export const AnansiSocial30: React.FC = () => <Film fmt={FMTS.vert} hook="A" />;
export const AnansiSocial30HookB: React.FC = () => <Film fmt={FMTS.vert} hook="B" />;
export const AnansiSocial30HookC: React.FC = () => <Film fmt={FMTS.vert} hook="C" />;
export const AnansiSocial30HookD: React.FC = () => <Film fmt={FMTS.vert} hook="D" />;
export const AnansiSocial30Alt: React.FC = () => <Film fmt={FMTS.vert} hook="A" sting={false} />;
export const AnansiSocial30FourFive: React.FC = () => <Film fmt={FMTS.fourfive} hook="A" />;
export const AnansiSocial30Square: React.FC = () => <Film fmt={FMTS.square} hook="A" />;
export const AnansiSocial30Wide: React.FC = () => <Film fmt={FMTS.wide} hook="A" />;
