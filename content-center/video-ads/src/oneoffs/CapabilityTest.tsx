import React from "react";
import { AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig } from "remotion";
import gsap from "gsap";
import { BRAND } from "../brand";
import { GsapRise, LogoLockup, NavyBG, SANS, SERIF, SceneDissolve } from "../components";

/**
 * ⚠️ THROWAWAY TEST — not part of the ads pipeline, not registered in ads.config.mjs,
 * not scheduled. Built purely to demonstrate the newly installed GSAP + skills system
 * (see BRAND-TEMPLATE.md §0d). Delete or keep as a reference once reviewed.
 *
 * Demonstrates, back to back:
 *  1. Kinetic typography — word-by-word GSAP stagger with a real "back" overshoot
 *  2. Staggered elastic card reveal — GSAP elastic ease (a look interpolate()/spring() can't match)
 *  3. A GSAP TWEEN driving raw data (not just CSS) — a 0→92 counter, seeked deterministically
 *  4. A hand-built shine-sweep + particle "payoff" accent (the Lottie slot — see note below)
 *  5. Logo lockup close
 *
 * Every animated piece here uses the REQUIRED Remotion+GSAP pattern: `paused: true` timelines,
 * manually seeked via `tl.time()` / `tl.progress()` from useCurrentFrame() — never GSAP's own
 * ticker. See GsapRise in components.tsx for the reference implementation this file follows.
 */

const Center: React.FC<{ children: React.ReactNode; gap?: number }> = ({ children, gap = 24 }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap }}>
    {children}
  </AbsoluteFill>
);

// ── Beat 1: kinetic typography — split into words, each a GsapRise with overshoot ──
const KineticHeadline: React.FC<{ text: string }> = ({ text }) => {
  const words = text.split(" ");
  return (
    <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "0 20px", maxWidth: 900 }}>
      {words.map((w, i) => (
        <GsapRise key={i} delay={i * 6} durationInFrames={22} ease="back.out(2.2)">
          <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 68, color: i === words.length - 1 ? BRAND.goldLight : BRAND.white }}>
            {w}
          </div>
        </GsapRise>
      ))}
    </div>
  );
};

// ── Beat 2: staggered card reveal with a visible elastic settle ──
const ElasticCard: React.FC<{ title: string; sub: string; delay: number }> = ({ title, sub, delay }) => (
  <GsapRise delay={delay} durationInFrames={30} ease="elastic.out(1, 0.55)">
    <div
      style={{
        width: 620,
        background: "rgba(255,255,255,0.04)",
        border: `1px solid ${BRAND.gold}55`,
        borderRadius: 20,
        padding: "22px 30px",
      }}
    >
      <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 34, color: BRAND.white }}>{title}</div>
      <div style={{ fontFamily: SANS, fontSize: 22, color: BRAND.muted, marginTop: 4 }}>{sub}</div>
    </div>
  </GsapRise>
);

// ── Beat 3: a GSAP TWEEN driving a raw number (not CSS) — proves GSAP can animate data ──
const GsapCounter: React.FC<{ to: number; durationInFrames: number }> = ({ to, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  // No DOM ref needed (animates a plain object, not CSS) — so timeline + seek both happen
  // synchronously during render via a lazy useState initializer. Avoids the create-in-
  // useEffect/seek-in-useLayoutEffect ordering bug fixed in GsapRise (components.tsx).
  const [state] = React.useState(() => {
    const target = { val: 0 };
    const tl = gsap.timeline({ paused: true }).to(target, { val: to, duration: durationInFrames / fps, ease: "power2.out" });
    return { target, tl };
  });
  state.tl.time(frame / fps); // deterministic seek, driven by Remotion's own frame clock

  return (
    <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 200, color: BRAND.goldLight, lineHeight: 1 }}>
      {Math.round(state.target.val)}
    </div>
  );
};

// ── Beat 4: hand-built shine-sweep + radiating particles (the "Lottie slot") ──
// Note: real Lottie JSON (from lottiefiles.com) drops straight into <LottieAsset src=.../>
// once exported from Scott's connected account — see BRAND-TEMPLATE.md §0d. This native
// SVG+GSAP version proves the payoff-moment *pattern* without depending on an external asset.
const ShinePayoff: React.FC<{ durationInFrames: number }> = ({ durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const gradRef = React.useRef<SVGLinearGradientElement>(null);
  const particleRefs = React.useRef<(SVGCircleElement | null)[]>([]);
  const tlRef = React.useRef<gsap.core.Timeline | null>(null);

  // Creation + first seek merged into one synchronous useLayoutEffect — same fix as
  // GsapRise (components.tsx): refs aren't attached until layout-effect time, and
  // creating the timeline in useEffect (post-paint) left the very first frame captured
  // at its un-seeked "from" state.
  React.useLayoutEffect(() => {
    if (!tlRef.current) {
      const tl = gsap.timeline({ paused: true });
      if (gradRef.current) {
        tl.fromTo(gradRef.current, { attr: { x1: "-40%", x2: "0%" } }, { attr: { x1: "100%", x2: "140%" }, duration: 0.9, ease: "power1.inOut" }, 0.1);
      }
      particleRefs.current.forEach((p, i) => {
        if (!p) return;
        tl.fromTo(
          p,
          { attr: { r: 0 }, opacity: 0 },
          { attr: { r: 5 + (i % 3) * 2 }, opacity: 1, duration: 0.25, ease: "back.out(3)" },
          0.15 + i * 0.05,
        ).to(p, { opacity: 0, duration: 0.4, ease: "power1.in" }, 0.5 + i * 0.05);
      });
      tlRef.current = tl;
    }
    tlRef.current.time(frame / fps);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [frame, fps]);

  React.useEffect(() => {
    return () => {
      tlRef.current?.kill();
      tlRef.current = null;
    };
  }, []);

  const particles = Array.from({ length: 10 }).map((_, i) => {
    const a = (i / 10) * Math.PI * 2;
    return { x: 300 + Math.cos(a) * 220, y: 90 + Math.sin(a) * 90 };
  });

  return (
    <svg width={600} height={180} viewBox="0 0 600 180" style={{ overflow: "visible" }}>
      <defs>
        <linearGradient ref={gradRef} id="shine" x1="-40%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="transparent" />
          <stop offset="50%" stopColor="#ffffff" stopOpacity="0.85" />
          <stop offset="100%" stopColor="transparent" />
        </linearGradient>
      </defs>
      <rect x={50} y={50} width={500} height={80} rx={40} fill={BRAND.gold} />
      <rect x={50} y={50} width={500} height={80} rx={40} fill="url(#shine)" />
      <text x={300} y={100} textAnchor="middle" fontFamily={SANS} fontWeight={900} fontSize={30} fill="#171007">
        Built with GSAP + Remotion
      </text>
      {particles.map((p, i) => (
        <circle
          key={i}
          ref={(el) => {
            particleRefs.current[i] = el;
          }}
          cx={p.x}
          cy={p.y}
          r={0}
          fill={BRAND.goldLight}
          opacity={0}
        />
      ))}
    </svg>
  );
};

export const CapabilityTest: React.FC = () => {
  return (
    <NavyBG>
      {/* Beat 1 — kinetic typography, 0-150 */}
      <Sequence from={0} durationInFrames={150}>
        <Center>
          <KineticHeadline text="This is what GSAP can do." />
        </Center>
      </Sequence>

      {/* Beat 2 — staggered elastic cards, 150-330 */}
      <Sequence from={150} durationInFrames={180}>
        <Center gap={16}>
          <ElasticCard delay={0} title="Elastic Overshoot" sub="Anticipation → overshoot → settle, not a flat fade." />
          <ElasticCard delay={10} title="Real Stagger" sub="Each card a few frames behind the last." />
          <ElasticCard delay={20} title="Frame-Exact" sub="Seeked deterministically — never GSAP's own ticker." />
        </Center>
      </Sequence>

      {/* Beat 3 — GSAP-driven counter, 330-480 */}
      <Sequence from={330} durationInFrames={150}>
        <Center gap={10}>
          <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 24, letterSpacing: "0.2em", textTransform: "uppercase", color: BRAND.goldLight }}>
            Readiness Score
          </div>
          <GsapCounter to={92} durationInFrames={110} />
        </Center>
      </Sequence>

      {/* Beat 4 — shine + particle payoff, 480-600 */}
      <Sequence from={480} durationInFrames={120}>
        <Center>
          <ShinePayoff durationInFrames={120} />
        </Center>
      </Sequence>

      {/* Beat 5 — logo close, 600-720 */}
      <Sequence from={600} durationInFrames={120}>
        <Center>
          <LogoLockup delay={6} />
        </Center>
      </Sequence>

      <SceneDissolve boundaries={[150, 330, 480, 600]} />
    </NavyBG>
  );
};
