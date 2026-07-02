import React from "react";
import { AbsoluteFill, Audio, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import * as d3 from "d3";
import * as THREE from "three";
import gsap from "gsap";
import { BRAND, SIGNUP_URL } from "../brand";
import {
  Caption,
  CTAButton,
  Eyebrow,
  Headline,
  LogoLockup,
  LottieAsset,
  NavyBG,
  Rise,
  SANS,
  SceneDissolve,
  Subtitles,
} from "../components";

/**
 * "19 of 20 Seats" — Anansi Atlas's FIRST LinkedIn post. Built with the layered
 * GSAP+D3+Three.js+Lottie stat-reveal pattern proven in CapabilityTest3, wrapped in the
 * full brand system (real copy, Subtitles, dissolves, CTA). Square, LinkedIn-native,
 * autoplay-muted-safe (every beat readable from captions alone). Voice: Jackson.
 */
export type Props = { audioSrc?: string | null };

// Timing derived from the actual ~18s Jackson VO's word count (proportional split —
// same method as ProductWalkthrough/PremiumShowcase). Re-run this math if the script
// in ads.config.mjs changes: bounds = [0,79,317,449,541] for the 4 script lines.
const TOTAL = 541; // ~18s @ 30fps
const S1_END = 79;
const S2_END = 317;
const S3_END = 449;

const CAPTIONS: Caption[] = [
  { text: "Founding Atlas Partners applications are open.", from: 0, duration: S1_END },
  { text: "19 of 20 seats are already claimed — just one spot left.", from: S1_END, duration: S2_END - S1_END },
  { text: "$150 a month — locked for life.", from: S2_END, duration: S3_END - S2_END },
  { text: "Apply now before the founding cohort closes.", from: S3_END, duration: TOTAL - S3_END },
];

const Center: React.FC<{ children: React.ReactNode; gap?: number }> = ({ children, gap = 22 }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap }}>
    {children}
  </AbsoluteFill>
);

// ── Quiet 3D backdrop — atmosphere, never the focal point ──
const ThreeBackdrop: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const canvasRef = React.useRef<HTMLCanvasElement>(null);
  const sceneRef = React.useRef<{ renderer: THREE.WebGLRenderer; scene: THREE.Scene; camera: THREE.PerspectiveCamera; mesh: THREE.Mesh } | null>(null);

  React.useLayoutEffect(() => {
    if (!canvasRef.current) return;
    if (!sceneRef.current) {
      const renderer = new THREE.WebGLRenderer({ canvas: canvasRef.current, alpha: true, antialias: true });
      renderer.setSize(760, 760, false);
      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
      camera.position.z = 4.6;
      const geo = new THREE.IcosahedronGeometry(2.0, 0);
      const mat = new THREE.MeshBasicMaterial({ color: 0xd4a017, wireframe: true, transparent: true, opacity: 0.22 });
      const mesh = new THREE.Mesh(geo, mat);
      scene.add(mesh);
      sceneRef.current = { renderer, scene, camera, mesh };
    }
    const { renderer, scene, camera, mesh } = sceneRef.current;
    const t = frame / fps;
    mesh.rotation.y = t * 0.3;
    mesh.rotation.x = t * 0.1;
    renderer.render(scene, camera);
  }, [frame, fps]);

  React.useEffect(() => {
    return () => {
      sceneRef.current?.renderer.dispose();
      sceneRef.current = null;
    };
  }, []);

  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <canvas ref={canvasRef} width={760} height={760} style={{ width: 760, height: 760 }} />
    </AbsoluteFill>
  );
};

// ── D3 ring geometry — pure math, no DOM ──
const SeatsRingSvg: React.FC<{ progress: number }> = ({ progress }) => {
  const arcGen = d3.arc<void, unknown>().innerRadius(148).outerRadius(174).startAngle(0).cornerRadius(6);
  const track = arcGen({ endAngle: Math.PI * 2 } as never) as string;
  const fill = arcGen({ endAngle: progress * Math.PI * 2 } as never) as string;
  return (
    <svg width={420} height={420} viewBox="0 0 420 420" style={{ position: "absolute" }}>
      <g transform="translate(210,210)">
        <path d={track} fill="rgba(255,255,255,0.08)" />
        <path d={fill} fill={BRAND.gold} />
      </g>
    </svg>
  );
};

// ── GSAP-driven seat count (real tween on data, not CSS) ──
const SeatsNumber: React.FC<{ to: number; startFrame: number; durationInFrames: number }> = ({ to, startFrame, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const [state] = React.useState(() => {
    const target = { val: 0 };
    const tl = gsap.timeline({ paused: true }).to(target, { val: to, duration: durationInFrames / fps, ease: "power2.out" });
    return { target, tl };
  });
  const localFrame = Math.max(0, frame - startFrame);
  state.tl.time(localFrame / fps);

  return (
    <div style={{ fontFamily: "serif", fontWeight: 600, fontSize: 116, color: BRAND.white, lineHeight: 1 }}>
      {Math.round(state.target.val)}
    </div>
  );
};

export const PilotSeatsReveal: React.FC<Props> = ({ audioSrc }) => {
  const frame = useCurrentFrame();
  const ringProgress = interpolate(frame, [S1_END + 20, S2_END - 20], [0, 19 / 20], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const sparkleOpacity = interpolate(frame, [S2_END - 30, S2_END], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <NavyBG>
      {audioSrc ? <Audio src={staticFile(audioSrc)} /> : null}

      {/* S1 — hook */}
      <Sequence from={0} durationInFrames={S1_END}>
        <Center>
          <Eyebrow>Founding Atlas Partners</Eyebrow>
          <Headline delay={8} size={58}>Applications are open.</Headline>
        </Center>
      </Sequence>

      {/* S2 — the stat reveal, layered */}
      <Sequence from={S1_END} durationInFrames={S2_END - S1_END}>
        <ThreeBackdrop />
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: 96 }}>
          <Rise delay={6}>
            <Eyebrow>Seats Claimed</Eyebrow>
          </Rise>
        </AbsoluteFill>
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
          <SeatsRingSvg progress={ringProgress} />
          <SeatsNumber to={19} startFrame={S1_END + 20} durationInFrames={S2_END - S1_END - 40} />
        </AbsoluteFill>
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: sparkleOpacity }}>
          <LottieAsset src={staticFile("lottie/gold-pulse.json")} width={480} height={480} loop />
        </AbsoluteFill>
      </Sequence>

      {/* S3 — the offer */}
      <Sequence from={S2_END} durationInFrames={S3_END - S2_END}>
        <Center gap={12}>
          <Headline delay={6} size={78}>$150 / month</Headline>
          <Rise delay={18}>
            <div style={{ fontFamily: SANS, fontSize: 28, fontWeight: 700, color: BRAND.goldLight }}>Locked for life</div>
          </Rise>
        </Center>
      </Sequence>

      {/* S4 — CTA */}
      <Sequence from={S3_END} durationInFrames={TOTAL - S3_END}>
        <Center gap={30}>
          <LogoLockup delay={6} />
          <CTAButton delay={20}>Apply Before Seats Close</CTAButton>
          <Rise delay={30}>
            <div style={{ fontFamily: SANS, fontSize: 26, fontWeight: 700, color: BRAND.goldLight, letterSpacing: "0.04em" }}>
              {SIGNUP_URL}
            </div>
          </Rise>
        </Center>
      </Sequence>

      <SceneDissolve boundaries={[S1_END, S2_END, S3_END]} />
      <Subtitles captions={CAPTIONS} />
    </NavyBG>
  );
};

export const PILOT_SEATS_REVEAL_TOTAL = TOTAL;
