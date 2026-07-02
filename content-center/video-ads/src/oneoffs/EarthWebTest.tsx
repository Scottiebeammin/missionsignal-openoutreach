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
const NODES: { lat: number; lon: number }[] = [
  { lat: 38, lon: -97 }, // North America
  { lat: 51, lon: 10 }, // Europe
  { lat: -1, lon: 37 }, // Africa
  { lat: 35, lon: 105 }, // Asia
  { lat: -25, lon: 135 }, // Oceania
  { lat: -15, lon: -55 }, // South America
];
// Arcs connecting node pairs (indices into NODES) — a spanning "web", not every pair.
const ARCS: [number, number][] = [
  [0, 1],
  [1, 2],
  [1, 3],
  [3, 4],
  [0, 5],
  [2, 5],
  [3, 0],
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
      camera.position.set(0, 1.1, 6.2);

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
        s.scale.set(0.22, 0.22, 1);
        globe.add(s);
        return s;
      });

      // arcs — TUBE geometry (not 1px THREE.Line, which reads as a faint scratch).
      // Tubes have real thickness, catch the eye as glowing strands, and their indexed
      // triangles are ordered along the tube's length — so setDrawRange() on the index
      // buffer gives us a clean progressive "draw-on" reveal, frame-deterministically.
      const arcTubes: THREE.Mesh[] = ARCS.map(([a, b]) => {
        const pa = toVec3(NODES[a].lat, NODES[a].lon, R * 1.02);
        const pb = toVec3(NODES[b].lat, NODES[b].lon, R * 1.02);
        const mid = pa.clone().add(pb).multiplyScalar(0.5).normalize().multiplyScalar(R * 1.28);
        const curve = new THREE.CatmullRomCurve3([pa, mid, pb]);
        const geo = new THREE.TubeGeometry(curve, 60, 0.012, 8, false);
        const mat = new THREE.MeshBasicMaterial({ color: 0xf3dd8c, transparent: true, opacity: 0.95 });
        const tube = new THREE.Mesh(geo, mat);
        globe.add(tube);
        return tube;
      });

      const light = new THREE.AmbientLight(0xffffff, 1);
      scene.add(light);

      ref.current = { renderer, scene, camera, globe, arcTubes, nodeSprites, dust };
    }

    const { renderer, scene, camera, globe, arcTubes, nodeSprites, dust } = ref.current;
    const t = frame / fps;

    // camera slow orbit — pure function of frame
    const orbitAngle = t * 0.28;
    camera.position.x = Math.sin(orbitAngle) * 6.2;
    camera.position.z = Math.cos(orbitAngle) * 6.2;
    camera.lookAt(0, -0.15, 0); // aim just above the crown of the lowered globe

    globe.rotation.y = t * 0.08; // slow ambient spin
    dust.rotation.y = t * 0.015; // dust drifts slower than the globe — parallax depth

    // progressively reveal each arc (draw-on), staggered — drawRange over the tube's
    // INDEX buffer (triangles are ordered along the tube length, so this sweeps cleanly)
    arcTubes.forEach((tube, i) => {
      const startFrame = 20 + i * 14;
      const drawFrames = 45;
      const localProgress = Math.min(1, Math.max(0, (frame - startFrame) / drawFrames));
      const geo = tube.geometry as THREE.BufferGeometry;
      const totalIndices = geo.index ? geo.index.count : 0;
      geo.setDrawRange(0, Math.floor(totalIndices * localProgress));
      (tube.material as THREE.MeshBasicMaterial).opacity = 0.95 * Math.min(1, localProgress * 3);
    });

    // pulsing node lights, staggered to land as their arcs complete
    nodeSprites.forEach((s, i) => {
      const arriveFrame = 20 + i * 14 + 45;
      const pulse = 1 + Math.sin(Math.max(0, t - arriveFrame / fps) * 3) * 0.12;
      const grow = Math.min(1, Math.max(0, (frame - (arriveFrame - 10)) / 14));
      s.scale.set(0.22 * pulse * grow, 0.22 * pulse * grow, 1);
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
