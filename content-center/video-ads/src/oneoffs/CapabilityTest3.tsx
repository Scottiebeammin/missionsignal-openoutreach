import React from "react";
import { AbsoluteFill, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import * as d3 from "d3";
import * as THREE from "three";
import gsap from "gsap";
import { BRAND } from "../brand";
import { Eyebrow, GsapRise, LottieAsset, NavyBG, SANS } from "../components";

/**
 * ⚠️ THROWAWAY TEST #3 — not part of the ads pipeline. Demonstrates all four systems
 * LAYERED and running SIMULTANEOUSLY in one continuous scene (not sequential beats like
 * CapabilityTest/CapabilityTest2): Three.js rotates quietly in the background the whole
 * time, D3 draws the score ring geometry, a GSAP tween counts the number inside it, and
 * a Lottie sparkle lands as the payoff the moment it completes. Every layer reads the
 * SAME useCurrentFrame() — that's what keeps four independent systems in perfect sync.
 *
 * This is a real, usable pattern — a "Readiness Score reveal" moment we could actually
 * drop into ProductWalkthrough or FullExplainer, not just a tech demo.
 */
const TOTAL = 300; // 10s

// ── Background layer: Three.js, quiet and atmospheric, never the focal point ──
const ThreeBackdrop: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const canvasRef = React.useRef<HTMLCanvasElement>(null);
  const sceneRef = React.useRef<{ renderer: THREE.WebGLRenderer; scene: THREE.Scene; camera: THREE.PerspectiveCamera; mesh: THREE.Mesh } | null>(null);

  React.useLayoutEffect(() => {
    if (!canvasRef.current) return;
    if (!sceneRef.current) {
      const renderer = new THREE.WebGLRenderer({ canvas: canvasRef.current, alpha: true, antialias: true });
      renderer.setSize(700, 700, false);
      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
      camera.position.z = 4.6;
      const geo = new THREE.IcosahedronGeometry(1.9, 0);
      const mat = new THREE.MeshBasicMaterial({ color: 0xd4a017, wireframe: true, transparent: true, opacity: 0.28 });
      const mesh = new THREE.Mesh(geo, mat);
      scene.add(mesh);
      sceneRef.current = { renderer, scene, camera, mesh };
    }
    const { renderer, scene, camera, mesh } = sceneRef.current;
    const t = frame / fps;
    mesh.rotation.y = t * 0.35; // slow, ambient — a backdrop, not a focal point
    mesh.rotation.x = t * 0.12;
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
      <canvas ref={canvasRef} width={700} height={700} style={{ width: 700, height: 700 }} />
    </AbsoluteFill>
  );
};

// ── Mid layer: D3 draws the ring geometry (pure math, no DOM) ──
const ScoreRingSvg: React.FC<{ progress: number }> = ({ progress }) => {
  const arcGen = d3.arc<void, unknown>().innerRadius(140).outerRadius(164).startAngle(0).cornerRadius(6);
  const track = arcGen({ endAngle: Math.PI * 2 } as never) as string;
  const fill = arcGen({ endAngle: progress * Math.PI * 2 } as never) as string;
  return (
    <svg width={400} height={400} viewBox="0 0 400 400" style={{ position: "absolute" }}>
      <g transform="translate(200,200)">
        <path d={track} fill="rgba(255,255,255,0.08)" />
        <path d={fill} fill={BRAND.gold} />
      </g>
    </svg>
  );
};

// ── Inside the ring: GSAP tween drives the number (data, not CSS) ──
const ScoreNumber: React.FC<{ to: number; startFrame: number; durationInFrames: number }> = ({ to, startFrame, durationInFrames }) => {
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
    <div style={{ fontFamily: "serif", fontWeight: 600, fontSize: 108, color: BRAND.white, lineHeight: 1 }}>
      {Math.round(state.target.val)}
    </div>
  );
};

export const CapabilityTest3: React.FC = () => {
  const frame = useCurrentFrame();
  const ringProgress = interpolate(frame, [40, 220], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const sparkleOpacity = interpolate(frame, [200, 220], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <NavyBG>
      {/* Layer 1 — Three.js, quiet backdrop, whole duration */}
      <ThreeBackdrop />

      {/* Layer 2 — GSAP kinetic label, enters early with overshoot */}
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: 140 }}>
        <GsapRise delay={12} durationInFrames={24} ease="back.out(2)">
          <Eyebrow>Readiness Score</Eyebrow>
        </GsapRise>
      </AbsoluteFill>

      {/* Layer 3 — D3 ring + GSAP-driven number, centered, both reading the same frame */}
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <ScoreRingSvg progress={ringProgress} />
        <ScoreNumber to={92} startFrame={40} durationInFrames={180} />
      </AbsoluteFill>

      {/* Layer 4 — Lottie sparkle, the payoff, lands right as the ring completes */}
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: sparkleOpacity }}>
        <LottieAsset src={staticFile("lottie/gold-pulse.json")} width={460} height={460} loop />
      </AbsoluteFill>

      {/* Caption — proves every layer is reading the same clock */}
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: 90 }}>
        <div style={{ fontFamily: SANS, fontSize: 22, color: BRAND.muted, textAlign: "center", maxWidth: 640 }}>
          Three.js · D3 · GSAP · Lottie — four systems, one frame clock.
        </div>
      </AbsoluteFill>
    </NavyBG>
  );
};

export const CAPABILITY_TEST_3_TOTAL = TOTAL;
