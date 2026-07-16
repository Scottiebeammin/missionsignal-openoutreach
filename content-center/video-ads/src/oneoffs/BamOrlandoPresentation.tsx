import React from "react";
import { AbsoluteFill, Audio, Img, Sequence, staticFile, useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { BRAND } from "../brand";
import {
  Caption,
  Eyebrow,
  Headline,
  LogoLockup,
  NavyBG,
  ProgressRail,
  Rise,
  SANS,
  SERIF,
  SceneDissolve,
  Subtitles,
} from "../components";
import { CHAPTERS, FUNNEL, OFFER, ORG, PEERS } from "../data/bamOrlandoFacts";

export type Props = {
  audioSrc?: string | null;
};

/**
 * BOARD PRESENTATION — Black Architects in the Making (BAM) Orlando.
 *
 * A prospect-specific pitch, not a product ad: it opens on THEIR org, walks the
 * three-number funnel (pool -> your lane -> your first check), shows real 990
 * grants to real peers their size, states plainly what Atlas WON'T claim, then
 * makes the ask and mentions the sister chapters.
 *
 * Every figure comes from src/data/bamOrlandoFacts.ts (sourced, see that file).
 * Deliberately data-driven rather than screenshot-driven — the numbers are the
 * story, and their live workspace is the follow-on demo.
 *
 * Timing follows the ProductWalkthrough/DashboardWalkthrough method: frames are
 * split across the 6 narration lines proportional to word count (278 words at
 * ~144 wpm = ~115.8s = 3475f). Re-derive if the script changes.
 */
const LEAD = 60; // 2s silent cold-open before narration
//                 s0    s1    s2     s3     s4     s5
// words:          42    47    56     44     48     41   (278 total)
const L = [0, 525, 1112, 1814, 2363, 2963, 3475].map((f) => f + LEAD);
export const BAM_TOTAL = L[6];

const CAPTIONS: Caption[] = [
  {
    text: `This is ${ORG.name}, ${ORG.city}. Founded ${ORG.founded}. Over 300 students. 87 volunteers. ${ORG.raised} raised last year — every dollar from your community. I built this from your website and public tax filings. Nothing you're about to see is a guess.`,
    from: L[0], duration: L[1] - L[0],
  },
  {
    text: "You already know the problem. You're doing the work. The money exists. But finding out who actually funds architecture pathways for students of color in Orange County means nights of Googling — and you don't have a grant writer. So the money stays invisible. Not missing. Invisible.",
    from: L[1], duration: L[2] - L[1],
  },
  {
    text: "Fifty-six million dollars flowed into Orange County nonprofits — 653 foundations, straight from IRS filings. That's the pool. Twenty point six million of that went to organizations your size — 229 foundations, 994 grants. That's your lane. And the typical grant to an org your size? Five thousand dollars.",
    from: L[2], duration: L[3] - L[2],
  },
  {
    text: "Here's what that actually looks like. Black History Project — five thousand. Love Our Youth — five thousand. Page 15 — five thousand. Real organizations. Your size. Your county. Getting real checks. These aren't projections — they're tax filings.",
    from: L[3], duration: L[4] - L[3],
  },
  {
    text: "A few things this won't do. It won't tell you the University of Florida is an organization like you — they're not, and most tools will show you that. It won't show a grant unless you can click through to the source. And it won't promise to get you funded — you still write the ask. Verified means verified.",
    from: L[4], duration: L[5] - L[4],
  },
  {
    text: "A hundred and fifty a month. Founding rate, locked for life — one of our first twenty partners. And what I built for Orlando isn't Orlando-specific. The same map exists for Broward and Miami. The ceiling isn't this room.",
    from: L[5], duration: L[6] - L[5],
  },
];

/** `lift` raises content off the bottom so it clears the subtitle card (~300px tall). */
const Center: React.FC<{ children: React.ReactNode; gap?: number; lift?: number }> = ({
  children, gap = 22, lift = 0,
}) => (
  <AbsoluteFill
    style={{
      alignItems: "center", justifyContent: "center", flexDirection: "column",
      gap, paddingBottom: lift,
    }}
  >
    {children}
  </AbsoluteFill>
);

/** A stat chip — their own numbers, handed back to them. */
const Stat: React.FC<{ value: string; label: string; delay?: number }> = ({ value, label, delay = 0 }) => (
  <Rise delay={delay}>
    <div style={{ textAlign: "center", padding: "0 18px" }}>
      <div style={{ fontFamily: SERIF, fontSize: 54, fontWeight: 700, color: BRAND.goldLight, lineHeight: 1 }}>{value}</div>
      <div style={{ fontFamily: SANS, fontSize: 17, color: BRAND.muted, marginTop: 8, letterSpacing: "0.06em" }}>{label}</div>
    </div>
  </Rise>
);

/** Big money number that counts up — the funnel's hero beat. */
const CountUpMoney: React.FC<{ target: number; display: string; delay?: number; color?: string }> = ({
  target, display, delay = 0, color = BRAND.goldLight,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 200, mass: 0.9 } });
  // Count toward the real figure, then snap to the formatted display string.
  const done = s > 0.985;
  const shown = done
    ? display
    : target >= 1_000_000
      ? `$${((target * s) / 1_000_000).toFixed(1)}M`
      : `$${Math.round(target * s).toLocaleString()}`;
  return (
    <div style={{ fontFamily: SERIF, fontSize: 150, fontWeight: 700, color, lineHeight: 1, letterSpacing: "-0.02em" }}>
      {shown}
    </div>
  );
};

/** One rung of the funnel: the number, what it is, and the plain-English caption. */
const FunnelStep: React.FC<{ index: number; from: number; dur: number }> = ({ index, from, dur }) => {
  const step = FUNNEL[index];
  const color = step.tone === "teal" ? "#5eead4" : BRAND.goldLight;
  return (
    <Sequence from={from} durationInFrames={dur}>
      <Center gap={14}>
        <Eyebrow delay={0}>{`${index + 1} of 3`}</Eyebrow>
        <Rise delay={6}>
          <CountUpMoney target={step.amountRaw} display={step.amount} delay={8} color={color} />
        </Rise>
        <Rise delay={22}>
          <div style={{ fontFamily: SANS, fontSize: 30, color: BRAND.ink, textAlign: "center", padding: "0 80px", lineHeight: 1.3 }}>
            {step.label}
          </div>
        </Rise>
        <Rise delay={30}>
          <div style={{ fontFamily: SANS, fontSize: 20, color: BRAND.muted, letterSpacing: "0.06em" }}>{step.sub}</div>
        </Rise>
        <Rise delay={40}>
          <div
            style={{
              marginTop: 10, padding: "10px 26px", borderRadius: 999,
              background: step.tone === "teal" ? "rgba(94,234,212,0.12)" : "rgba(212,160,23,0.14)",
              border: `1px solid ${color}55`,
              fontFamily: SANS, fontWeight: 800, fontSize: 24, color,
            }}
          >
            {step.caption}
          </div>
        </Rise>
      </Center>
    </Sequence>
  );
};

/** A real 990 grant to a real peer — the emotional beat. */
const PeerRow: React.FC<{ org: string; amount: string; delay: number }> = ({ org, amount, delay }) => (
  <Rise delay={delay}>
    <div
      style={{
        display: "flex", alignItems: "center", justifyContent: "space-between", gap: 26,
        width: 760, padding: "14px 24px", borderRadius: 12,
        background: "rgba(255,255,255,0.04)", border: "1px solid rgba(212,160,23,0.18)",
      }}
    >
      <div style={{ fontFamily: SANS, fontSize: 26, color: BRAND.ink }}>{org}</div>
      <div style={{ fontFamily: SERIF, fontSize: 34, fontWeight: 700, color: BRAND.goldLight }}>{amount}</div>
    </div>
  </Rise>
);

export const BamOrlandoPresentation: React.FC<Props> = ({ audioSrc }) => {
  return (
    <NavyBG>
      {audioSrc ? (
        <Sequence from={LEAD}>
          <Audio src={staticFile(audioSrc)} />
        </Sequence>
      ) : null}
      <ProgressRail totalFrames={BAM_TOTAL} />

      {/* S0 — THEIR org, their numbers, handed back to them. */}
      <Sequence from={0} durationInFrames={L[1]}>
        <Center gap={18}>
          <Rise delay={0}>
            <Img src={staticFile("logo-mark.png")} style={{ width: 72, height: 72 }} />
          </Rise>
          <Eyebrow delay={6}>{`Built for ${ORG.city} · from your own filings`}</Eyebrow>
          <Headline delay={12} size={58}>{ORG.name}</Headline>
          <Rise delay={20}>
            <div style={{ fontFamily: SANS, fontSize: 22, color: BRAND.muted, textAlign: "center", padding: "0 130px", lineHeight: 1.45 }}>
              {ORG.mission}
            </div>
          </Rise>
          <div style={{ display: "flex", gap: 8, marginTop: 18 }}>
            <Stat value={ORG.students} label="students since 2018" delay={30} />
            <Stat value={ORG.volunteers} label="volunteers" delay={38} />
            <Stat value={ORG.raised} label="raised last year" delay={46} />
          </div>
        </Center>
      </Sequence>

      {/* S1 — The problem: not missing. Invisible. */}
      <Sequence from={L[1]} durationInFrames={L[2] - L[1]}>
        <Center gap={26}>
          <Eyebrow delay={0}>The problem you already live</Eyebrow>
          <Headline delay={8} size={62}>The money isn't missing.</Headline>
          <Rise delay={40}>
            <div style={{ fontFamily: SERIF, fontSize: 96, fontWeight: 700, color: BRAND.gold, letterSpacing: "-0.02em" }}>
              It's invisible.
            </div>
          </Rise>
          <Rise delay={58}>
            <div style={{ fontFamily: SANS, fontSize: 24, color: BRAND.muted, textAlign: "center", padding: "0 150px", lineHeight: 1.5 }}>
              You're doing the work. The funders exist. But nobody has the nights to find them — and you don't have a grant writer.
            </div>
          </Rise>
        </Center>
      </Sequence>

      {/* S2 — THE FUNNEL: three true numbers (the heart of the pitch). */}
      <FunnelStep index={0} from={L[2]} dur={(L[3] - L[2]) * 0.34} />
      <FunnelStep index={1} from={L[2] + (L[3] - L[2]) * 0.34} dur={(L[3] - L[2]) * 0.33} />
      <FunnelStep index={2} from={L[2] + (L[3] - L[2]) * 0.67} dur={(L[3] - L[2]) * 0.33} />

      {/* S3 — The receipts: real peers, real checks. */}
      <Sequence from={L[3]} durationInFrames={L[4] - L[3]}>
        <Center gap={10} lift={300}>
          <Eyebrow delay={0}>Orgs your size · Orange County</Eyebrow>
          <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 8 }}>
            {PEERS.slice(0, 5).map((p, i) => (
              <PeerRow key={p.org} org={p.org} amount={p.amount} delay={10 + i * 9} />
            ))}
          </div>
          <Rise delay={72}>
            <div style={{ fontFamily: SANS, fontSize: 22, color: BRAND.muted, marginTop: 10, letterSpacing: "0.05em" }}>
              Not projections. Tax filings.
            </div>
          </Rise>
        </Center>
      </Sequence>

      {/* S4 — The honesty: what this will NOT claim. */}
      <Sequence from={L[4]} durationInFrames={L[5] - L[4]}>
        <Center gap={22}>
          <Eyebrow delay={0}>What this won't do</Eyebrow>
          <Rise delay={8}>
            <div style={{ display: "flex", flexDirection: "column", gap: 16, width: 800 }}>
              {[
                "Won't call a $350M university “an org like you.”",
                "Won't show a grant you can't click through and verify.",
                "Won't promise to get you funded. You still write the ask.",
              ].map((t, i) => (
                <Rise key={t} delay={14 + i * 12}>
                  <div
                    style={{
                      display: "flex", alignItems: "center", gap: 16, padding: "16px 24px",
                      borderRadius: 12, background: "rgba(255,255,255,0.04)",
                      border: "1px solid rgba(255,255,255,0.10)",
                      fontFamily: SANS, fontSize: 25, color: BRAND.ink,
                    }}
                  >
                    <span style={{ color: BRAND.rose, fontSize: 28, fontWeight: 800 }}>✕</span>
                    {t}
                  </div>
                </Rise>
              ))}
            </div>
          </Rise>
          <Rise delay={64}>
            <div
              style={{
                marginTop: 8, padding: "12px 30px", borderRadius: 999,
                background: "rgba(15,118,110,0.16)", border: `1px solid ${BRAND.teal}`,
                fontFamily: SANS, fontWeight: 800, fontSize: 27, color: "#5eead4",
              }}
            >
              ✓ Verified means verified.
            </div>
          </Rise>
        </Center>
      </Sequence>

      {/* S5 — The ask + the ceiling isn't this room. */}
      <Sequence from={L[5]} durationInFrames={BAM_TOTAL - L[5]}>
        <Center gap={16}>
          <Rise delay={0}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
              <span style={{ fontFamily: SERIF, fontSize: 132, fontWeight: 700, color: BRAND.goldLight, lineHeight: 1 }}>
                {OFFER.price}
              </span>
              <span style={{ fontFamily: SANS, fontSize: 34, color: BRAND.muted }}>{OFFER.cadence}</span>
            </div>
          </Rise>
          <Rise delay={14}>
            <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 27, color: BRAND.gold, letterSpacing: "0.04em" }}>
              {OFFER.terms}
            </div>
          </Rise>
          <Rise delay={22}>
            <div style={{ fontFamily: SANS, fontSize: 22, color: BRAND.muted }}>{OFFER.cohort}</div>
          </Rise>

          <Rise delay={40}>
            <div style={{ display: "flex", gap: 12, marginTop: 26 }}>
              {CHAPTERS.map((c) => (
                <div
                  key={c}
                  style={{
                    padding: "10px 26px", borderRadius: 999,
                    background: c === "Orlando" ? "rgba(212,160,23,0.18)" : "rgba(255,255,255,0.04)",
                    border: `1px solid ${c === "Orlando" ? BRAND.gold : "rgba(255,255,255,0.14)"}`,
                    fontFamily: SANS, fontWeight: 700, fontSize: 22,
                    color: c === "Orlando" ? BRAND.goldLight : BRAND.muted,
                  }}
                >
                  {c}
                </div>
              ))}
            </div>
          </Rise>
          <Rise delay={54}>
            <div style={{ fontFamily: SERIF, fontSize: 34, color: BRAND.ink, marginTop: 12 }}>
              The ceiling isn't this room.
            </div>
          </Rise>
          <Rise delay={70}>
            <LogoLockup delay={0} />
          </Rise>
        </Center>
      </Sequence>

      <SceneDissolve
        boundaries={[
          L[1], L[2],
          L[2] + (L[3] - L[2]) * 0.34,
          L[2] + (L[3] - L[2]) * 0.67,
          L[3], L[4], L[5],
        ]}
      />
      <Subtitles captions={CAPTIONS} />
    </NavyBG>
  );
};

/** YOUTUBE / BOARDROOM 16:9 WIDE CUT — square content centered in a branded backdrop. */
export const BamOrlandoPresentationWide: React.FC<Props> = ({ audioSrc }) => {
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
      <div style={{ position: "absolute", left: (1920 - 1080) / 2, top: 0, width: 1080, height: 1080, overflow: "hidden" }}>
        <BamOrlandoPresentation audioSrc={audioSrc} />
      </div>
      <div style={{ position: "absolute", left: (1920 - 1080) / 2 - 2, top: 0, width: 240, height: 1080, background: `linear-gradient(90deg, ${BRAND.navy} 0%, rgba(13,27,61,0) 100%)` }} />
      <div style={{ position: "absolute", right: (1920 - 1080) / 2 - 2, top: 0, width: 240, height: 1080, background: `linear-gradient(270deg, ${BRAND.navy} 0%, rgba(13,27,61,0) 100%)` }} />
    </AbsoluteFill>
  );
};
