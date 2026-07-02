import React from "react";
import { AbsoluteFill, Audio, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import * as THREE from "three";
import { BRAND, SIGNUP_URL } from "../brand";
import {
  AnimatedLogoReveal,
  Caption,
  CTAButton,
  Eyebrow,
  LogoLockup,
  NavyBG,
  OrbWeb,
  ProgressRail,
  Rise,
  SANS,
  SERIF,
  SceneDissolve,
  ScreenshotPanel,
  Subtitles,
} from "../components";

/**
 * "THE WEB OF OPPORTUNITY" — the Anansi Atlas cinematic launch film (Scott's full brief).
 * Nine scenes that evolve into one another; the approved globe prototype is the hero
 * visual (Scenes 4 + 8/9); the Pinterest reference elements are woven throughout:
 * gradient-mesh atmosphere (brand-adapted gold/teal), glassmorphism scatter windows,
 * moody glowing-laptop platform beat, and flipping numbered cards for the Snapshot.
 * Voice: Christopher (~70.6s). Timing derived from the measured VO word counts.
 */

const LEAD = 90; // 3s silent particle open before narration begins
const B = [0, 77, 413, 684, 994, 1253, 1434, 1614, 1886, 2118].map((f) => f + LEAD);
export const FILM_TOTAL = B[9];

const CAPTIONS: Caption[] = [
  { text: "Every mission is surrounded by opportunity.", from: B[0], duration: B[1] - B[0] },
  { text: "Opportunities exist — they're just scattered across dozens of places.", from: B[1], duration: B[2] - B[1] },
  { text: "Fragmented opportunity means missed funding, partnerships, and momentum.", from: B[2], duration: B[3] - B[2] },
  { text: "That's why we built Anansi Atlas — opportunity intelligence for mission-driven organizations.", from: B[3], duration: B[4] - B[3] },
  { text: "Your entire opportunity ecosystem, understood in one place.", from: B[4], duration: B[5] - B[4] },
  { text: "See hidden connections. Focus on the opportunities that matter most.", from: B[5], duration: B[6] - B[5] },
  { text: "The Snapshot turns it all into a clear 30-day action plan.", from: B[6], duration: B[7] - B[6] },
  { text: "Become a Founding Atlas Partner — help shape what comes next.", from: B[7], duration: B[8] - B[7] },
  { text: "Join today, while seats remain — anansiatlas.com", from: B[8], duration: B[9] - B[8] },
];

const Center: React.FC<{ children: React.ReactNode; gap?: number }> = ({ children, gap = 22 }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap }}>
    {children}
  </AbsoluteFill>
);

// Seeded PRNG — deterministic scatter everywhere (no Math.random in render paths).
function makePrng(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Gradient mesh atmosphere (Pinterest ref #1, brand-adapted: gold/teal on navy)
// ─────────────────────────────────────────────────────────────────────────────
const GradientMesh: React.FC<{ opacity?: number }> = ({ opacity = 0.5 }) => {
  const frame = useCurrentFrame();
  const t = frame / 30;
  const blobs = [
    { color: "212,160,23", x: 22 + Math.sin(t * 0.21) * 6, y: 24 + Math.cos(t * 0.17) * 5, r: 34 },
    { color: "15,118,110", x: 76 + Math.sin(t * 0.16 + 2) * 7, y: 68 + Math.cos(t * 0.19 + 1) * 6, r: 38 },
    { color: "35,87,137", x: 55 + Math.sin(t * 0.13 + 4) * 8, y: 30 + Math.cos(t * 0.15 + 3) * 7, r: 30 },
  ];
  return (
    <AbsoluteFill style={{ opacity, filter: "blur(70px)" }}>
      {blobs.map((b, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: `${b.x - b.r / 2}%`,
            top: `${b.y - b.r / 2}%`,
            width: `${b.r}%`,
            height: `${b.r}%`,
            borderRadius: "50%",
            background: `radial-gradient(circle, rgba(${b.color},0.55) 0%, rgba(${b.color},0) 70%)`,
          }}
        />
      ))}
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 1 — Logo Open: particles converge, threads connect, the wordmark forms
// ─────────────────────────────────────────────────────────────────────────────
const PARTICLES = (() => {
  const rand = makePrng(20260702);
  return Array.from({ length: 26 }, (_, i) => {
    const homeAngle = (i / 26) * Math.PI * 2;
    const homeR = 190 + (i % 3) * 60;
    return {
      startX: 540 + (rand() - 0.5) * 1400,
      startY: 540 + (rand() - 0.5) * 1400,
      homeX: 540 + Math.cos(homeAngle) * homeR,
      homeY: 540 + Math.sin(homeAngle) * homeR,
    };
  });
})();

const ParticleLogoOpen: React.FC = () => {
  const frame = useCurrentFrame();
  const conv = interpolate(frame, [5, 85], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const ease = 1 - Math.pow(1 - conv, 3); // cubic ease-out
  const lineOp = interpolate(frame, [55, 95], [0, 0.4], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const webFade = interpolate(frame, [120, 165], [1, 0.25], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const pts = PARTICLES.map((p) => ({ x: p.startX + (p.homeX - p.startX) * ease, y: p.startY + (p.homeY - p.startY) * ease }));
  return (
    <AbsoluteFill>
      <svg width={1080} height={1080} viewBox="0 0 1080 1080" style={{ opacity: webFade }}>
        {pts.map((a, i) =>
          pts.slice(i + 1).map((b, j) => {
            const d = Math.hypot(a.x - b.x, a.y - b.y);
            if (d > 260) return null;
            return <line key={`${i}-${j}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={BRAND.gold} strokeWidth={1} strokeOpacity={lineOp * (1 - d / 260)} />;
          }),
        )}
        {pts.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r={3.2} fill={BRAND.goldLight} opacity={0.35 + 0.65 * ease} />
        ))}
      </svg>
      {/* the web becomes the wordmark */}
      {frame >= 95 ? <AnimatedLogoReveal delay={95} /> : null}
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 2 — The Problem: glassmorphism windows multiplying (calm → overwhelming)
// ─────────────────────────────────────────────────────────────────────────────
const WINDOWS = [
  { label: "Grant Portal", sub: "Deadline in 12 days", x: 12, y: 16, w: 320 },
  { label: "Funder Directory", sub: "412 results", x: 56, y: 10, w: 300 },
  { label: "Inbox", sub: "47 unread", x: 30, y: 34, w: 280 },
  { label: "Partners_v3.xlsx", sub: "Last edited 6 months ago", x: 62, y: 44, w: 330 },
  { label: "County RFP Portal", sub: "3 open notices", x: 8, y: 56, w: 300 },
  { label: "Community Board", sub: "New volunteer posting", x: 42, y: 62, w: 310 },
  { label: "Annual Report Draft", sub: "Comments (18)", x: 18, y: 76, w: 290 },
  { label: "Foundation Newsletter", sub: "LOI window open", x: 58, y: 78, w: 320 },
];

const GlassWindow: React.FC<{ label: string; sub: string; w: number; delay: number; drift: number }> = ({ label, sub, w, delay, drift }) => {
  const frame = useCurrentFrame();
  const appear = interpolate(frame - delay, [0, 16], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const float = Math.sin((frame + drift * 60) / 46) * 6;
  return (
    <div
      style={{
        width: w,
        opacity: appear,
        transform: `translateY(${(1 - appear) * 22 + float}px)`,
        background: "rgba(255,255,255,0.055)",
        border: "1px solid rgba(255,255,255,0.14)",
        borderRadius: 14,
        padding: "16px 20px",
        backdropFilter: "blur(12px)",
        boxShadow: "0 18px 44px rgba(0,0,0,0.3)",
      }}
    >
      <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 22, color: BRAND.white }}>{label}</div>
      <div style={{ fontFamily: SANS, fontSize: 17, color: BRAND.muted, marginTop: 3 }}>{sub}</div>
    </div>
  );
};

const ProblemScene: React.FC<{ durationInFrames: number }> = ({ durationInFrames }) => {
  const frame = useCurrentFrame();
  const pullBack = interpolate(frame, [0, durationInFrames], [1.06, 0.94], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill>
      <GradientMesh opacity={0.32} />
      <AbsoluteFill style={{ transform: `scale(${pullBack})` }}>
        {WINDOWS.map((w, i) => (
          <div key={w.label} style={{ position: "absolute", left: `${w.x}%`, top: `${w.y}%` }}>
            <GlassWindow label={w.label} sub={w.sub} w={w.w} delay={12 + i * 26} drift={i} />
          </div>
        ))}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 3 — Why It Matters: opportunities fade into darkness
// ─────────────────────────────────────────────────────────────────────────────
const FADING = [
  { title: "Youth Program Grant", sub: "Deadline passed", at: 0.1 },
  { title: "Partnership Invitation", sub: "Expired", at: 0.35 },
  { title: "Capacity-Building Fund", sub: "Window closed", at: 0.6 },
];

const FadingScene: React.FC<{ durationInFrames: number }> = ({ durationInFrames }) => {
  const frame = useCurrentFrame();
  const darken = interpolate(frame, [0, durationInFrames], [0, 0.55], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill>
      <Center gap={20}>
        {FADING.map((f, i) => {
          const start = f.at * durationInFrames;
          const gone = interpolate(frame - start, [0, 46], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (
            <div
              key={f.title}
              style={{
                width: 620,
                opacity: gone,
                filter: `blur(${(1 - gone) * 8}px) saturate(${gone})`,
                transform: `translateY(${(1 - gone) * 30}px)`,
                background: "rgba(255,255,255,0.05)",
                border: `1px solid rgba(212,160,23,${0.35 * gone})`,
                borderRadius: 16,
                padding: "22px 28px",
              }}
            >
              <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 32, color: BRAND.white }}>{f.title}</div>
              <div style={{ fontFamily: SANS, fontSize: 21, color: BRAND.rose, marginTop: 4, fontWeight: 700 }}>{f.sub}</div>
            </div>
          );
        })}
      </Center>
      <AbsoluteFill style={{ background: `rgba(2,6,14,${darken})` }} />
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// SCENES 4 + 8/9 — the GLOBE (approved prototype, extracted + parameterized)
// ─────────────────────────────────────────────────────────────────────────────
const CITY_NODES: { lat: number; lon: number }[] = [
  { lat: 40, lon: -74 }, { lat: 34, lon: -118 }, { lat: 28, lon: -81 }, { lat: 51, lon: 0 },
  { lat: 48, lon: 2 }, { lat: 6, lon: 3 }, { lat: -1, lon: 37 }, { lat: 25, lon: 55 },
  { lat: 19, lon: 73 }, { lat: 1, lon: 104 }, { lat: 35, lon: 140 }, { lat: -23, lon: -46 },
];
const CITY_ARCS: [number, number][] = [
  [2, 0], [0, 1], [0, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 8], [8, 9], [9, 10], [2, 11], [11, 5], [10, 1],
];
// extra "partner" lights for Scene 8 — orgs joining the network
const PARTNER_NODES: { lat: number; lon: number }[] = [
  { lat: 33, lon: -84 }, { lat: 41, lon: -87 }, { lat: 45, lon: -122 }, { lat: 52, lon: 13 },
  { lat: -33, lon: 18 }, { lat: 12, lon: 77 }, { lat: -37, lon: 144 }, { lat: 14, lon: -90 },
];

function toVec3(lat: number, lon: number, r: number): THREE.Vector3 {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);
  return new THREE.Vector3(-r * Math.sin(phi) * Math.cos(theta), r * Math.cos(phi), r * Math.sin(phi) * Math.sin(theta));
}

const LANDMASS_BLOBS = [
  { x: 0.18, y: 0.32, r: 0.05 }, { x: 0.24, y: 0.4, r: 0.04 }, { x: 0.15, y: 0.5, r: 0.06 },
  { x: 0.46, y: 0.22, r: 0.04 }, { x: 0.52, y: 0.3, r: 0.05 }, { x: 0.5, y: 0.45, r: 0.06 },
  { x: 0.58, y: 0.6, r: 0.04 }, { x: 0.72, y: 0.28, r: 0.06 }, { x: 0.8, y: 0.4, r: 0.05 },
  { x: 0.78, y: 0.65, r: 0.04 }, { x: 0.3, y: 0.65, r: 0.05 }, { x: 0.35, y: 0.78, r: 0.04 },
];

function buildEarthTexture(): THREE.CanvasTexture {
  const size = 2048;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size / 2;
  const ctx = canvas.getContext("2d")!;
  ctx.fillStyle = "#071224";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  const rand = makePrng(1148910692);
  for (const b of LANDMASS_BLOBS) {
    const cx = b.x * canvas.width, cy = b.y * canvas.height;
    const rx = b.r * canvas.width, ry = b.r * canvas.height * 0.7;
    const dots = Math.floor(rx * ry * 0.05);
    for (let i = 0; i < dots; i++) {
      const a = rand() * Math.PI * 2, rr = Math.sqrt(rand());
      const bright = rand();
      ctx.fillStyle = bright > 0.85 ? "rgba(243,221,140,0.95)" : bright > 0.5 ? "rgba(120,160,220,0.75)" : "rgba(70,110,180,0.5)";
      ctx.beginPath();
      ctx.arc(cx + Math.cos(a) * rr * rx, cy + Math.sin(a) * rr * ry, bright > 0.85 ? 2.2 : 1.4, 0, Math.PI * 2);
      ctx.fill();
    }
  }
  const tex = new THREE.CanvasTexture(canvas);
  tex.needsUpdate = true;
  return tex;
}

type GlobeRefs = {
  renderer: THREE.WebGLRenderer;
  scene: THREE.Scene;
  camera: THREE.PerspectiveCamera;
  globe: THREE.Group;
  arcTubes: THREE.Mesh[];
  nodeSprites: THREE.Sprite[];
  partnerSprites: THREE.Sprite[];
  dust: THREE.Points;
};

/** The approved globe. partnersAt: local frame when partner orgs start lighting up (Scene 8).
 *  pullBackAt: local frame when the camera starts a slow retreat (Scene 9 close). */
const GlobeWeb: React.FC<{ partnersAt?: number; pullBackAt?: number; durationInFrames: number }> = ({ partnersAt, pullBackAt, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const canvasRef = React.useRef<HTMLCanvasElement>(null);
  const ref = React.useRef<GlobeRefs | null>(null);

  React.useLayoutEffect(() => {
    if (!canvasRef.current) return;
    if (!ref.current) {
      const renderer = new THREE.WebGLRenderer({ canvas: canvasRef.current, alpha: true, antialias: true });
      renderer.setSize(1080, 1080, false);
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
      camera.position.set(0, 1.0, 5.3);

      const globe = new THREE.Group();
      globe.position.y = -1.35;
      scene.add(globe);

      const R = 1.6;
      const earthTex = buildEarthTexture();
      earthTex.colorSpace = THREE.SRGBColorSpace;
      globe.add(new THREE.Mesh(new THREE.SphereGeometry(R, 48, 48), new THREE.MeshBasicMaterial({ map: earthTex })));
      globe.add(new THREE.Mesh(new THREE.SphereGeometry(R * 1.004, 24, 16), new THREE.MeshBasicMaterial({ color: 0xd4a017, wireframe: true, transparent: true, opacity: 0.12 })));

      // halo
      const haloCanvas = document.createElement("canvas");
      haloCanvas.width = 512;
      haloCanvas.height = 512;
      const hg = haloCanvas.getContext("2d")!;
      const haloGrad = hg.createRadialGradient(256, 256, 150, 256, 256, 256);
      haloGrad.addColorStop(0, "rgba(140,190,255,0.34)");
      haloGrad.addColorStop(0.35, "rgba(212,175,55,0.16)");
      haloGrad.addColorStop(1, "rgba(212,175,55,0)");
      hg.fillStyle = haloGrad;
      hg.fillRect(0, 0, 512, 512);
      const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(haloCanvas), transparent: true, depthWrite: false }));
      halo.scale.set(R * 2.45, R * 2.45, 1);
      halo.position.y = -1.35;
      scene.add(halo);

      // dust
      const dustRand = makePrng(38898);
      const dustPos = new Float32Array(140 * 3);
      for (let i = 0; i < 140; i++) {
        dustPos[i * 3] = (dustRand() - 0.5) * 9;
        dustPos[i * 3 + 1] = dustRand() * 5 - 1.4;
        dustPos[i * 3 + 2] = (dustRand() - 0.5) * 6;
      }
      const dustGeo = new THREE.BufferGeometry();
      dustGeo.setAttribute("position", new THREE.BufferAttribute(dustPos, 3));
      const dustCanvas = document.createElement("canvas");
      dustCanvas.width = 32;
      dustCanvas.height = 32;
      const dgc = dustCanvas.getContext("2d")!;
      const dGrad = dgc.createRadialGradient(16, 16, 0, 16, 16, 16);
      dGrad.addColorStop(0, "rgba(243,221,140,1)");
      dGrad.addColorStop(1, "rgba(243,221,140,0)");
      dgc.fillStyle = dGrad;
      dgc.fillRect(0, 0, 32, 32);
      const dust = new THREE.Points(dustGeo, new THREE.PointsMaterial({ map: new THREE.CanvasTexture(dustCanvas), color: 0xf3dd8c, size: 0.05, transparent: true, opacity: 0.5, depthWrite: false }));
      scene.add(dust);

      // glow sprite factory
      const glowMat = () => {
        const c = document.createElement("canvas");
        c.width = 64;
        c.height = 64;
        const g = c.getContext("2d")!;
        const grad = g.createRadialGradient(32, 32, 0, 32, 32, 32);
        grad.addColorStop(0, "rgba(255,235,180,1)");
        grad.addColorStop(0.4, "rgba(212,160,23,0.9)");
        grad.addColorStop(1, "rgba(212,160,23,0)");
        g.fillStyle = grad;
        g.fillRect(0, 0, 64, 64);
        return new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false });
      };

      const nodeSprites = CITY_NODES.map((n) => {
        const s = new THREE.Sprite(glowMat());
        s.position.copy(toVec3(n.lat, n.lon, R * 1.02));
        s.scale.set(0.13, 0.13, 1);
        globe.add(s);
        return s;
      });
      const partnerSprites = PARTNER_NODES.map((n) => {
        const s = new THREE.Sprite(glowMat());
        s.position.copy(toVec3(n.lat, n.lon, R * 1.02));
        s.scale.set(0, 0, 1);
        globe.add(s);
        return s;
      });

      const arcTubes = CITY_ARCS.map(([a, b], i) => {
        const pa = toVec3(CITY_NODES[a].lat, CITY_NODES[a].lon, R * 1.015);
        const pb = toVec3(CITY_NODES[b].lat, CITY_NODES[b].lon, R * 1.015);
        const span = pa.distanceTo(pb) / (2 * R);
        const lift = R * Math.min(1.17, 1.04 + 0.2 * span);
        const mid = pa.clone().add(pb).multiplyScalar(0.5).normalize().multiplyScalar(lift);
        const curve = new THREE.QuadraticBezierCurve3(pa, mid, pb);
        const tube = new THREE.Mesh(
          new THREE.TubeGeometry(curve, 64, 0.006 + (i % 3) * 0.002, 8, false),
          new THREE.MeshBasicMaterial({ color: 0xf3dd8c, transparent: true, opacity: 0.55 }),
        );
        globe.add(tube);
        return tube;
      });

      scene.add(new THREE.AmbientLight(0xffffff, 1));
      ref.current = { renderer, scene, camera, globe, arcTubes, nodeSprites, partnerSprites, dust };
    }

    const { renderer, scene, camera, globe, arcTubes, nodeSprites, partnerSprites, dust } = ref.current;
    const t = frame / fps;

    const dist = pullBackAt !== undefined ? 5.3 + Math.max(0, frame - pullBackAt) * 0.012 : 5.3;
    const orbitAngle = t * 0.4;
    camera.position.x = Math.sin(orbitAngle) * dist;
    camera.position.z = Math.cos(orbitAngle) * dist;
    camera.position.y = 1.0;
    camera.lookAt(0, -0.15, 0);
    globe.rotation.y = t * 0.12;
    dust.rotation.y = t * 0.015;

    arcTubes.forEach((tube, i) => {
      const start = 8 + i * 5;
      const prog = Math.min(1, Math.max(0, (frame - start) / 24));
      const geo = tube.geometry as THREE.BufferGeometry;
      geo.setDrawRange(0, Math.floor((geo.index ? geo.index.count : 0) * prog));
      (tube.material as THREE.MeshBasicMaterial).opacity = 0.55 * Math.min(1, prog * 3);
    });
    nodeSprites.forEach((s, i) => {
      const grow = Math.min(1, Math.max(0, (frame - (6 + i * 4)) / 12));
      const breathe = 1 + Math.sin(t * 2.2 + i * 1.7) * 0.1;
      s.scale.set(0.13 * grow * breathe, 0.13 * grow * breathe, 1);
    });
    partnerSprites.forEach((s, i) => {
      if (partnersAt === undefined) return;
      const grow = Math.min(1, Math.max(0, (frame - (partnersAt + i * 9)) / 14));
      const breathe = 1 + Math.sin(t * 2.6 + i * 2.1) * 0.14;
      s.scale.set(0.17 * grow * breathe, 0.17 * grow * breathe, 1);
    });

    renderer.render(scene, camera);
  }, [frame, fps, partnersAt, pullBackAt, durationInFrames]);

  React.useEffect(() => {
    return () => {
      ref.current?.renderer.dispose();
      ref.current = null;
    };
  }, []);

  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <canvas ref={canvasRef} width={1080} height={1080} style={{ width: 1080, height: 1080 }} />
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 5 — The Platform: moody glowing laptop-esque screen (Pinterest ref #2)
// ─────────────────────────────────────────────────────────────────────────────
const KPI: React.FC<{ label: string; value: string; delay: number; right?: boolean }> = ({ label, value, delay, right }) => (
  <Rise delay={delay}>
    <div
      style={{
        background: "rgba(255,255,255,0.06)",
        border: "1px solid rgba(212,160,23,0.35)",
        borderRadius: 16,
        padding: "18px 26px",
        backdropFilter: "blur(10px)",
        textAlign: right ? "right" : "left",
        boxShadow: "0 16px 44px rgba(0,0,0,0.45)",
      }}
    >
      <div style={{ fontFamily: SANS, fontSize: 17, fontWeight: 800, letterSpacing: "0.12em", textTransform: "uppercase", color: BRAND.goldLight }}>{label}</div>
      <div style={{ fontFamily: SERIF, fontSize: 44, fontWeight: 600, color: BRAND.white, lineHeight: 1.1 }}>{value}</div>
    </div>
  </Rise>
);

const PlatformScene: React.FC<{ durationInFrames: number }> = ({ durationInFrames }) => {
  const frame = useCurrentFrame();
  const glow = 0.5 + Math.sin(frame / 22) * 0.12;
  return (
    <AbsoluteFill>
      <GradientMesh opacity={0.4} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ position: "relative" }}>
          <div
            style={{
              position: "absolute",
              inset: -46,
              borderRadius: 40,
              background: `radial-gradient(ellipse at center, rgba(212,160,23,${glow * 0.35}) 0%, rgba(35,87,137,0.12) 50%, transparent 75%)`,
              filter: "blur(28px)",
            }}
          />
          <ScreenshotPanel src={staticFile("screenshots/dashboard.png")} label="anansiatlas.com/dashboard" durationInFrames={durationInFrames} width={780} panY={[0, -14]} />
        </div>
      </AbsoluteFill>
      <AbsoluteFill style={{ justifyContent: "center", paddingLeft: 40 }}>
        <div style={{ width: 250 }}>
          <KPI label="Readiness" value="92" delay={26} />
        </div>
      </AbsoluteFill>
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "flex-end", paddingRight: 40 }}>
        <div style={{ width: 280 }}>
          <KPI label="Opportunities" value="53" delay={40} right />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 7 — Snapshot: flipping numbered cards (Pinterest ref #3)
// ─────────────────────────────────────────────────────────────────────────────
const FLIPS = [
  { num: "01", title: "Recommended Funders", sub: "Ranked by mission fit" },
  { num: "02", title: "Potential Partners", sub: "Who opens which doors" },
  { num: "03", title: "Next Steps", sub: "Your 30-day action plan" },
];

const FlipCard: React.FC<{ num: string; title: string; sub: string; delay: number }> = ({ num, title, sub, delay }) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame - delay, [0, 34], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const eased = 1 - Math.pow(1 - p, 3);
  const rot = 180 * eased; // number face → content face
  const showBack = rot > 90;
  return (
    <div style={{ perspective: 1200, width: 300, height: 360 }}>
      <div style={{ position: "relative", width: "100%", height: "100%", transformStyle: "preserve-3d", transform: `rotateY(${rot}deg)` }}>
        {/* front: the big numeral */}
        <div
          style={{
            position: "absolute", inset: 0, backfaceVisibility: "hidden",
            background: "linear-gradient(160deg, #16294f 0%, #0d1b3d 100%)",
            border: "1px solid rgba(212,160,23,0.4)", borderRadius: 22,
            display: "flex", alignItems: "center", justifyContent: "center",
            visibility: showBack ? "hidden" : "visible",
          }}
        >
          <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 130, color: BRAND.goldLight }}>{num}</div>
        </div>
        {/* back: the content */}
        <div
          style={{
            position: "absolute", inset: 0, backfaceVisibility: "hidden", transform: "rotateY(180deg)",
            background: "linear-gradient(160deg, rgba(212,160,23,0.16) 0%, #0d1b3d 60%)",
            border: "1px solid rgba(212,160,23,0.55)", borderRadius: 22,
            display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
            padding: 26, textAlign: "center", gap: 10,
            visibility: showBack ? "visible" : "hidden",
          }}
        >
          <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 17, letterSpacing: "0.14em", color: BRAND.goldLight }}>{num}</div>
          <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 33, color: BRAND.white, lineHeight: 1.15 }}>{title}</div>
          <div style={{ fontFamily: SANS, fontSize: 20, color: BRAND.muted }}>{sub}</div>
        </div>
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// THE FILM
// ─────────────────────────────────────────────────────────────────────────────
export const WebOfOpportunityFilm: React.FC<{ audioSrc?: string | null }> = ({ audioSrc }) => {
  return (
    <NavyBG>
      {audioSrc ? (
        <Sequence from={LEAD}>
          <Audio src={staticFile(audioSrc)} />
        </Sequence>
      ) : null}
      <ProgressRail totalFrames={FILM_TOTAL} />

      {/* SCENE 1 — Logo Open (silent lead + first line) */}
      <Sequence from={0} durationInFrames={B[1]}>
        <ParticleLogoOpen />
      </Sequence>

      {/* SCENE 2 — The Problem */}
      <Sequence from={B[1]} durationInFrames={B[2] - B[1]}>
        <ProblemScene durationInFrames={B[2] - B[1]} />
      </Sequence>

      {/* SCENE 3 — Why It Matters */}
      <Sequence from={B[2]} durationInFrames={B[3] - B[2]}>
        <FadingScene durationInFrames={B[3] - B[2]} />
      </Sequence>

      {/* SCENE 4 — Introducing Anansi Atlas: THE GLOBE */}
      <Sequence from={B[3]} durationInFrames={B[4] - B[3]}>
        <GlobeWeb durationInFrames={B[4] - B[3]} />
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: 120 }}>
          <Rise delay={30}>
            <Eyebrow>The Web of Opportunity</Eyebrow>
          </Rise>
        </AbsoluteFill>
      </Sequence>

      {/* SCENE 5 — The Platform */}
      <Sequence from={B[4]} durationInFrames={B[5] - B[4]}>
        <PlatformScene durationInFrames={B[5] - B[4]} />
      </Sequence>

      {/* SCENE 6 — The Opportunity Web (our core 2D motif) */}
      <Sequence from={B[5]} durationInFrames={B[6] - B[5]}>
        <OrbWebScene />
      </Sequence>

      {/* SCENE 7 — Snapshot: flipping cards */}
      <Sequence from={B[6]} durationInFrames={B[7] - B[6]}>
        <GradientMesh opacity={0.28} />
        <Center gap={0}>
          <div style={{ display: "flex", gap: 34 }}>
            {FLIPS.map((f, i) => (
              <FlipCard key={f.num} {...f} delay={12 + i * 22} />
            ))}
          </div>
        </Center>
      </Sequence>

      {/* SCENES 8 + 9 — Founding Partners on the globe, then the pull-back close */}
      <Sequence from={B[7]} durationInFrames={FILM_TOTAL - B[7]}>
        <GlobeWeb durationInFrames={FILM_TOTAL - B[7]} partnersAt={30} pullBackAt={B[8] - B[7]} />
        {/* Scene 8 overlay: seats */}
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: 110 }}>
          <Rise delay={16}>
            <Eyebrow>Founding Atlas Partners</Eyebrow>
          </Rise>
          <Rise delay={34}>
            <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 58, color: BRAND.white, marginTop: 12 }}>
              19 Seats Remaining
            </div>
          </Rise>
        </AbsoluteFill>
        {/* Scene 9 overlay: logo + CTA, arrives with the final line */}
        <Sequence from={B[8] - B[7]} durationInFrames={FILM_TOTAL - B[8]}>
          <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: 130, gap: 22, flexDirection: "column" }}>
            <LogoLockup delay={8} />
            <CTAButton delay={22}>Become a Founding Partner</CTAButton>
            <Rise delay={32}>
              <div style={{ fontFamily: SANS, fontSize: 27, fontWeight: 700, color: BRAND.goldLight, letterSpacing: "0.04em" }}>{SIGNUP_URL}</div>
            </Rise>
          </AbsoluteFill>
        </Sequence>
      </Sequence>

      <SceneDissolve boundaries={[B[1], B[2], B[3], B[4], B[5], B[6], B[7]]} />
      <Subtitles captions={CAPTIONS} />
    </NavyBG>
  );
};

const OrbWebScene: React.FC = () => {
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [0, 110], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill>
      <GradientMesh opacity={0.25} />
      <OrbWeb progress={progress} />
    </AbsoluteFill>
  );
};
