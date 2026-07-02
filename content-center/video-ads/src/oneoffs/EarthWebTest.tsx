import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import * as THREE from "three";
import { BRAND } from "../brand";
import { NavyBG, SANS } from "../components";

/**
 * ⚠️ PROTOTYPE — de-risking the "rotating globe with glowing gold arcs" hero visual
 * from the cinematic launch-film brief BEFORE committing it to a real video. Not part
 * of the ads pipeline. If this hits the bar, we build the real version into
 * PremiumShowcase's Scene 4 ("Introducing Anansi Atlas"); if not, we fall back to the
 * 2D OrbWeb diagram as the hero visual instead.
 *
 * Deliberately STYLIZED, not a literal photo-real Earth: a dark sphere with a subtle
 * abstract "landmass" texture (procedurally drawn once, fixed coordinates — no
 * Math.random() in the render path, so every render is pixel-identical) + a lat/long
 * wireframe grid (echoes our existing brand grid motif) + glowing gold arcs connecting
 * fixed points, progressively drawing on. Camera orbits as a pure function of frame —
 * same deterministic discipline as every other Three.js piece we've built this session.
 */
const TOTAL = 240; // 8s

// Fixed points around the globe (lat, lon in degrees) — deterministic, not random.
// 12 "cities" for a denser, more organic web than the original 6 continents.
const NODES: { lat: number; lon: number }[] = [
  { lat: 40, lon: -74 }, // New York
  { lat: 34, lon: -118 }, // Los Angeles
  { lat: 28, lon: -81 }, // Orlando — home
  { lat: 51, lon: 0 }, // London
  { lat: 48, lon: 2 }, // Paris
  { lat: 6, lon: 3 }, // Lagos
  { lat: -1, lon: 37 }, // Nairobi
  { lat: 25, lon: 55 }, // Dubai
  { lat: 19, lon: 73 }, // Mumbai
  { lat: 1, lon: 104 }, // Singapore
  { lat: 35, lon: 140 }, // Tokyo
  { lat: -23, lon: -46 }, // São Paulo
];
// Arcs — mostly regional short-hops (they hug the surface and feel like flight trails)
// plus a few long-hauls. [from, to] indices into NODES.
const ARCS: [number, number][] = [
  [2, 0], // Orlando → New York
  [0, 1], // NY → LA
  [0, 3], // NY → London (long haul)
  [3, 4], // London → Paris
  [4, 5], // Paris → Lagos
  [5, 6], // Lagos → Nairobi
  [6, 7], // Nairobi → Dubai
  [7, 8], // Dubai → Mumbai
  [8, 9], // Mumbai → Singapore
  [9, 10], // Singapore → Tokyo
  [2, 11], // Orlando → São Paulo
  [11, 5], // São Paulo → Lagos (long haul)
  [10, 1], // Tokyo → LA (long haul)
];

function toVec3(lat: number, lon: number, r: number): THREE.Vector3 {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);
  return new THREE.Vector3(-r * Math.sin(phi) * Math.cos(theta), r * Math.cos(phi), r * Math.sin(phi) * Math.sin(theta));
}

// Procedural "landmass" texture — fixed blob coordinates (deterministic, drawn once on mount).
const LANDMASS_BLOBS = [
  { x: 0.18, y: 0.32, r: 0.05 }, { x: 0.24, y: 0.4, r: 0.04 }, { x: 0.15, y: 0.5, r: 0.06 },
  { x: 0.46, y: 0.22, r: 0.04 }, { x: 0.52, y: 0.3, r: 0.05 }, { x: 0.5, y: 0.45, r: 0.06 },
  { x: 0.58, y: 0.6, r: 0.04 }, { x: 0.72, y: 0.28, r: 0.06 }, { x: 0.8, y: 0.4, r: 0.05 },
  { x: 0.78, y: 0.65, r: 0.04 }, { x: 0.3, y: 0.65, r: 0.05 }, { x: 0.35, y: 0.78, r: 0.04 },
];
// Seeded LCG so the dot scatter is DETERMINISTIC (same every render) without Math.random().
function makePrng(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

function buildEarthTexture(): THREE.CanvasTexture {
  const size = 2048;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size / 2;
  const ctx = canvas.getContext("2d")!;
  ctx.fillStyle = "#071224";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  // Continents as glowing DOT FIELDS (city-lights-from-space look, per the Pinterest
  // earth reference) — not painted blobs. Dots scatter inside each landmass region.
  const rand = makePrng(1148910692);
  for (const b of LANDMASS_BLOBS) {
    const cx = b.x * canvas.width;
    const cy = b.y * canvas.height;
    const rx = b.r * canvas.width;
    const ry = b.r * canvas.height * 0.7;
    const dots = Math.floor(rx * ry * 0.05);
    for (let i = 0; i < dots; i++) {
      const a = rand() * Math.PI * 2;
      const rr = Math.sqrt(rand());
      const x = cx + Math.cos(a) * rr * rx;
      const y = cy + Math.sin(a) * rr * ry;
      const bright = rand();
      ctx.fillStyle = bright > 0.85 ? "rgba(243,221,140,0.95)" : bright > 0.5 ? "rgba(120,160,220,0.75)" : "rgba(70,110,180,0.5)";
      ctx.beginPath();
      ctx.arc(x, y, bright > 0.85 ? 2.2 : 1.4, 0, Math.PI * 2);
      ctx.fill();
    }
  }
  const tex = new THREE.CanvasTexture(canvas);
  tex.needsUpdate = true;
  return tex;
}

type SceneRefs = {
  renderer: THREE.WebGLRenderer;
  scene: THREE.Scene;
  camera: THREE.PerspectiveCamera;
  globe: THREE.Group;
  arcTubes: THREE.Mesh[];
  arcCurves: THREE.QuadraticBezierCurve3[];
  pulseSprites: THREE.Sprite[];
  nodeSprites: THREE.Sprite[];
  dust: THREE.Points;
};

const EarthWeb: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const canvasRef = React.useRef<HTMLCanvasElement>(null);
  const ref = React.useRef<SceneRefs | null>(null);

  React.useLayoutEffect(() => {
    if (!canvasRef.current) return;
    if (!ref.current) {
      const renderer = new THREE.WebGLRenderer({ canvas: canvasRef.current, alpha: true, antialias: true });
      renderer.setSize(900, 900, false);
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
      camera.position.set(0, 1.0, 5.3);

      const globe = new THREE.Group();
      globe.position.y = -1.35; // horizon composition — the planet's crown rises from the lower third (per the earth reference)
      scene.add(globe);

      const R = 1.6;
      const earthTex = buildEarthTexture();
      earthTex.colorSpace = THREE.SRGBColorSpace; // CanvasTexture defaults to NoColorSpace — without this the
      // dark navy gets reinterpreted as linear and washes out lighter than authored (found in this prototype).
      const sphereGeo = new THREE.SphereGeometry(R, 48, 48);
      const sphereMat = new THREE.MeshBasicMaterial({ map: earthTex });
      globe.add(new THREE.Mesh(sphereGeo, sphereMat));

      // lat/long wireframe grid — echoes the brand's polar-grid motif
      const gridGeo = new THREE.SphereGeometry(R * 1.004, 24, 16);
      const gridMat = new THREE.MeshBasicMaterial({ color: 0xd4a017, wireframe: true, transparent: true, opacity: 0.12 });
      globe.add(new THREE.Mesh(gridGeo, gridMat));

      // atmospheric halo — a big radial-gradient sprite BEHIND the globe. (A BackSide
      // sphere at flat opacity read as a hard gray ring, not a glow — replaced.)
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
      const haloTex = new THREE.CanvasTexture(haloCanvas);
      const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: haloTex, transparent: true, depthWrite: false }));
      halo.scale.set(R * 2.45, R * 2.45, 1); // must fade out INSIDE the viewport — larger and its edge shows as a square
      halo.position.y = -1.35; // track the lowered globe
      scene.add(halo); // in scene (not globe group) so it always faces camera, doesn't spin

      // ambient floating dust — tiny deterministic particles drifting above the planet
      // (per the earth reference: the space around the globe feels alive, not empty)
      const dustRand = makePrng(38898);
      const dustCount = 140;
      const dustPos = new Float32Array(dustCount * 3);
      for (let i = 0; i < dustCount; i++) {
        dustPos[i * 3] = (dustRand() - 0.5) * 9;
        dustPos[i * 3 + 1] = dustRand() * 5 - 1.4;
        dustPos[i * 3 + 2] = (dustRand() - 0.5) * 6;
      }
      const dustGeo = new THREE.BufferGeometry();
      dustGeo.setAttribute("position", new THREE.BufferAttribute(dustPos, 3));
      // circular soft sprite for each particle — raw Points render as SQUARES otherwise
      const dustCanvas = document.createElement("canvas");
      dustCanvas.width = 32;
      dustCanvas.height = 32;
      const dg = dustCanvas.getContext("2d")!;
      const dGrad = dg.createRadialGradient(16, 16, 0, 16, 16, 16);
      dGrad.addColorStop(0, "rgba(243,221,140,1)");
      dGrad.addColorStop(1, "rgba(243,221,140,0)");
      dg.fillStyle = dGrad;
      dg.fillRect(0, 0, 32, 32);
      const dustMat = new THREE.PointsMaterial({
        map: new THREE.CanvasTexture(dustCanvas),
        color: 0xf3dd8c,
        size: 0.05,
        transparent: true,
        opacity: 0.5,
        depthWrite: false,
      });
      const dust = new THREE.Points(dustGeo, dustMat);
      scene.add(dust);

      // node points (city lights)
      const spriteMat = () => {
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
      const nodeSprites: THREE.Sprite[] = NODES.map((n) => {
        const s = new THREE.Sprite(spriteMat());
        const p = toVec3(n.lat, n.lon, R * 1.02);
        s.position.copy(p);
        s.scale.set(0.13, 0.13, 1);
        globe.add(s);
        return s;
      });

      // arcs — thin TUBE strands that HUG the surface like flight trails: the apex lift
      // scales with arc length (short hops stay low, long hauls rise), instead of every
      // arc ballooning to the same tall hoop. Draw-on reveal via index drawRange.
      const arcCurves: THREE.QuadraticBezierCurve3[] = [];
      const arcTubes: THREE.Mesh[] = ARCS.map(([a, b], i) => {
        const pa = toVec3(NODES[a].lat, NODES[a].lon, R * 1.015);
        const pb = toVec3(NODES[b].lat, NODES[b].lon, R * 1.015);
        const span = pa.distanceTo(pb) / (2 * R); // 0..1 — how far around the globe
        const lift = R * Math.min(1.17, 1.04 + 0.2 * span); // hugging for short hops, capped so long hauls never balloon into hoops
        const mid = pa.clone().add(pb).multiplyScalar(0.5).normalize().multiplyScalar(lift);
        const curve = new THREE.QuadraticBezierCurve3(pa, mid, pb); // no endpoint overshoot (CatmullRom made loop-de-loops at nodes)
        arcCurves.push(curve);
        const radius = 0.006 + (i % 3) * 0.002; // subtle thickness variety
        const geo = new THREE.TubeGeometry(curve, 64, radius, 8, false);
        const mat = new THREE.MeshBasicMaterial({ color: 0xf3dd8c, transparent: true, opacity: 0.55 });
        const tube = new THREE.Mesh(geo, mat);
        globe.add(tube);
        return tube;
      });

      // traveling energy pulses — one bright light per arc, riding along the curve after
      // it finishes drawing ("energy flowing through the network", per the film brief)
      const pulseSprites: THREE.Sprite[] = arcCurves.map(() => {
        const s = new THREE.Sprite(spriteMat());
        s.scale.set(0.09, 0.09, 1);
        s.visible = false;
        globe.add(s);
        return s;
      });

      const light = new THREE.AmbientLight(0xffffff, 1);
      scene.add(light);

      ref.current = { renderer, scene, camera, globe, arcTubes, arcCurves, pulseSprites, nodeSprites, dust };
    }

    const { renderer, scene, camera, globe, arcTubes, arcCurves, pulseSprites, nodeSprites, dust } = ref.current;
    const t = frame / fps;

    // camera slow orbit — pure function of frame
    const orbitAngle = t * 0.28;
    camera.position.x = Math.sin(orbitAngle) * 5.3;
    camera.position.z = Math.cos(orbitAngle) * 5.3;
    camera.lookAt(0, -0.15, 0); // aim just above the crown of the lowered globe

    globe.rotation.y = t * 0.08; // slow ambient spin
    dust.rotation.y = t * 0.015; // dust drifts slower than the globe — parallax depth

    // progressively reveal each arc (draw-on), staggered — drawRange over the tube's
    // INDEX buffer (triangles are ordered along the tube length, so this sweeps cleanly)
    const ARC_START = (i: number) => 15 + i * 9;
    const ARC_DRAW = 38;
    arcTubes.forEach((tube, i) => {
      const localProgress = Math.min(1, Math.max(0, (frame - ARC_START(i)) / ARC_DRAW));
      const geo = tube.geometry as THREE.BufferGeometry;
      const totalIndices = geo.index ? geo.index.count : 0;
      geo.setDrawRange(0, Math.floor(totalIndices * localProgress));
      (tube.material as THREE.MeshBasicMaterial).opacity = 0.55 * Math.min(1, localProgress * 3);
    });

    // energy pulses — once an arc is fully drawn, a bright light rides back and forth
    // along it forever ("energy flowing through the network")
    pulseSprites.forEach((s, i) => {
      const doneFrame = ARC_START(i) + ARC_DRAW;
      if (frame < doneFrame) {
        s.visible = false;
        return;
      }
      s.visible = true;
      const speed = 0.35 + (i % 4) * 0.08; // varied speeds so pulses don't march in lockstep
      const phase = i * 0.37;
      const raw = (t * speed + phase) % 2;
      const along = raw < 1 ? raw : 2 - raw; // ping-pong 0→1→0
      s.position.copy(arcCurves[i].getPointAt(along));
    });

    // node lights grow in as the web reaches them, then breathe gently
    nodeSprites.forEach((s, i) => {
      const arriveFrame = 12 + i * 7;
      const grow = Math.min(1, Math.max(0, (frame - arriveFrame) / 12));
      const breathe = 1 + Math.sin(t * 2.2 + i * 1.7) * 0.1;
      s.scale.set(0.13 * grow * breathe, 0.13 * grow * breathe, 1);
    });

    renderer.render(scene, camera);
  }, [frame, fps]);

  React.useEffect(() => {
    return () => {
      ref.current?.renderer.dispose();
      ref.current = null;
    };
  }, []);

  return <canvas ref={canvasRef} width={900} height={900} style={{ width: 900, height: 900 }} />;
};

export const EarthWebTest: React.FC = () => {
  return (
    <NavyBG>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <EarthWeb />
      </AbsoluteFill>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: 70 }}>
        <div style={{ fontFamily: SANS, fontSize: 24, color: BRAND.muted, textAlign: "center", maxWidth: 640 }}>
          Prototype — the Web of Opportunity, made global. Deterministic camera orbit + progressive arc reveal.
        </div>
      </AbsoluteFill>
    </NavyBG>
  );
};

export const EARTH_WEB_TEST_TOTAL = TOTAL;
