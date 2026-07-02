import React from "react";
import { AbsoluteFill, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import * as d3 from "d3";
import * as THREE from "three";
import { BRAND } from "../brand";
import { Eyebrow, LogoLockup, LottieAsset, NavyBG, Rise, SANS, SceneDissolve } from "../components";

/**
 * ⚠️ THROWAWAY TEST #2 — not part of the ads pipeline. Demonstrates D3, Three.js, and
 * Lottie (the "other 3" from BRAND-TEMPLATE.md §0d), each with the CORRECT integration
 * pattern for Remotion. See CapabilityTest.tsx for the GSAP showcase.
 */

const Center: React.FC<{ children: React.ReactNode; gap?: number }> = ({ children, gap = 24 }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap }}>
    {children}
  </AbsoluteFill>
);

// ── Beat 1: D3 — the RIGHT way to use it in React/Remotion ──────────────────────────
// d3-shape's arc() is a PURE FUNCTION: data in, SVG path string out. No DOM, no refs,
// no effects needed — call it straight in the render body, exactly like interpolate().
// This is the D3 equivalent of the GSAP seek-mode lesson: d3-selection (.attr(), DOM
// manipulation, real-time .transition()) is the WRONG mode for Remotion/React — it
// fights the virtual DOM and doesn't seek. d3-shape/d3-scale/d3-interpolate (pure math)
// is the RIGHT mode — deterministic, frame-exact, just like everything else here.
const SeatsProgressRing: React.FC<{ filled: number; total: number; progress: number }> = ({ filled, total, progress }) => {
  const animatedFilled = filled * progress;
  const arcGen = d3
    .arc<void, unknown>()
    .innerRadius(150)
    .outerRadius(178)
    .startAngle(0)
    .cornerRadius(6);
  const trackPath = arcGen({ endAngle: (total / total) * Math.PI * 2 } as never) as string;
  const fillPath = arcGen({ endAngle: (animatedFilled / total) * Math.PI * 2 } as never) as string;

  return (
    <svg width={400} height={400} viewBox="0 0 400 400">
      <g transform="translate(200,200)">
        <path d={trackPath} fill="rgba(255,255,255,0.08)" />
        <path d={fillPath} fill={BRAND.gold} />
        <text textAnchor="middle" dy={-6} fontFamily="serif" fontWeight={600} fontSize={72} fill={BRAND.white}>
          {Math.round(animatedFilled)}
        </text>
        <text textAnchor="middle" dy={28} fontFamily={SANS} fontWeight={800} fontSize={18} letterSpacing="0.1em" fill={BRAND.goldLight}>
          OF {total} SEATS
        </text>
      </g>
    </svg>
  );
};

// ── Beat 2: Three.js — the RIGHT way to use it in Remotion ───────────────────────────
// The renderer/scene/mesh are created ONCE inside useLayoutEffect (not useEffect — same
// ordering lesson the GSAP bug taught us), and rotation is set as a PURE FUNCTION of
// `frame`, never via requestAnimationFrame or a real-time Clock. The WRONG mode would be
// calling .rotation.y += delta inside a rAF loop — that's wall-clock time, exactly like
// GSAP's ticker, and equally non-deterministic under Remotion's out-of-order rendering.
const ThreeMark: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const canvasRef = React.useRef<HTMLCanvasElement>(null);
  const sceneRef = React.useRef<{ renderer: THREE.WebGLRenderer; scene: THREE.Scene; camera: THREE.PerspectiveCamera; mesh: THREE.Mesh } | null>(null);

  React.useLayoutEffect(() => {
    if (!canvasRef.current) return;
    if (!sceneRef.current) {
      const renderer = new THREE.WebGLRenderer({ canvas: canvasRef.current, alpha: true, antialias: true });
      renderer.setSize(420, 420, false);
      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
      camera.position.z = 4.2;
      const geo = new THREE.IcosahedronGeometry(1.35, 0);
      const mat = new THREE.MeshBasicMaterial({ color: 0xd4a017, wireframe: true, transparent: true, opacity: 0.9 });
      const mesh = new THREE.Mesh(geo, mat);
      scene.add(mesh);
      sceneRef.current = { renderer, scene, camera, mesh };
    }
    const { renderer, scene, camera, mesh } = sceneRef.current;
    const t = frame / fps; // deterministic — purely a function of frame, never real time
    mesh.rotation.y = t * 0.9;
    mesh.rotation.x = t * 0.35;
    renderer.render(scene, camera);
  }, [frame, fps]);

  React.useEffect(() => {
    return () => {
      sceneRef.current?.renderer.dispose();
      sceneRef.current = null;
    };
  }, []);

  return <canvas ref={canvasRef} width={420} height={420} style={{ width: 420, height: 420 }} />;
};

export const CapabilityTest2: React.FC = () => {
  return (
    <NavyBG>
      {/* Beat 1 — D3: a live "seats filled" progress ring, 0-180 */}
      <Sequence from={0} durationInFrames={180}>
        <RingBeat />
      </Sequence>

      {/* Beat 2 — Three.js: a subtle rotating 3D accent, 180-390 */}
      <Sequence from={180} durationInFrames={210}>
        <Center gap={18}>
          <Eyebrow>Three.js — A Dimensional Accent</Eyebrow>
          <ThreeMark />
          <Rise delay={20}>
            <div style={{ fontFamily: SANS, fontSize: 22, color: BRAND.muted, textAlign: "center", maxWidth: 500 }}>
              Rotation is a pure function of frame — never real time. Deterministic, just like GSAP.
            </div>
          </Rise>
        </Center>
      </Sequence>

      {/* Beat 3 — Lottie: a real, hand-authored .json asset, fetched + rendered, 390-540 */}
      <Sequence from={390} durationInFrames={150}>
        <Center gap={18}>
          <Eyebrow>Lottie — A Real .json Asset</Eyebrow>
          <LottieAsset src={staticFile("lottie/gold-pulse.json")} width={320} height={320} loop />
          <Rise delay={20}>
            <div style={{ fontFamily: SANS, fontSize: 22, color: BRAND.muted, textAlign: "center", maxWidth: 500 }}>
              Fetched from public/lottie/, decoded, and rendered — the real pipeline, not a mockup.
            </div>
          </Rise>
        </Center>
      </Sequence>

      {/* Beat 4 — close */}
      <Sequence from={540} durationInFrames={120}>
        <Center>
          <LogoLockup delay={6} />
        </Center>
      </Sequence>

      <SceneDissolve boundaries={[180, 390, 540]} />
    </NavyBG>
  );
};

const RingBeat: React.FC = () => {
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [10, 150], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <Center gap={18}>
      <Eyebrow>D3 — Live Progress Geometry</Eyebrow>
      <SeatsProgressRing filled={19} total={20} progress={progress} />
    </Center>
  );
};
