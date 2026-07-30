import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { BRAND, NODES, SIZE } from "../brand";
import { NavyBG, OrbWeb, SANS, SERIF } from "../components";

export type CarouselProps = {
  slideIndex: number; // 0 = cover, 1-6 = one per NODES entry
};

const DESCRIPTIONS: Record<(typeof NODES)[number], string> = {
  FUNDERS: "Aligned capital — funders ranked by fit, not an endless list.",
  PARTNERS: "The organizations you build with to become competitive.",
  GOVERNMENT: "Public-sector pathways — city, county, and workforce lanes.",
  RESOURCES: "Community assets — capacity, technology, and volunteer support.",
  READINESS: "Where you're strong vs. where you're exposed, scored honestly.",
  PATHWAYS: "Your practical next moves — not a to-do avalanche.",
};

const SLIDE_LABELS: Record<(typeof NODES)[number], string> = {
  FUNDERS: "Funders",
  PARTNERS: "Partners",
  GOVERNMENT: "Government",
  RESOURCES: "Resources",
  READINESS: "Readiness",
  PATHWAYS: "Pathways",
};

/** Small hexagon diagram with one node highlighted gold/glowing, the rest dimmed. Mirrors the
 *  OrbWeb layout (same angles) at a smaller carousel-friendly scale. */
const MiniHex: React.FC<{ activeIndex: number }> = ({ activeIndex }) => {
  const cx = 540;
  const cy = 540;
  const R = 230;
  return (
    <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`}>
      {NODES.map((_, i) => {
        const a = (i / NODES.length) * Math.PI * 2 - Math.PI / 2;
        const nx = cx + Math.cos(a) * R;
        const ny = cy + Math.sin(a) * R;
        const active = i === activeIndex;
        return (
          <line key={`l${i}`} x1={cx} y1={cy} x2={nx} y2={ny} stroke={BRAND.gold} strokeWidth={active ? 4 : 2} strokeOpacity={active ? 0.85 : 0.25} />
        );
      })}
      <circle cx={cx} cy={cy} r={54} fill={BRAND.navy2} stroke={BRAND.gold} strokeWidth={2} strokeOpacity={0.6} />
      <text x={cx} y={cy - 4} fill={BRAND.goldLight} fontSize={15} fontWeight={800} fontFamily={SANS} textAnchor="middle" letterSpacing="1">
        YOUR
      </text>
      <text x={cx} y={cy + 16} fill={BRAND.goldLight} fontSize={15} fontWeight={800} fontFamily={SANS} textAnchor="middle" letterSpacing="1">
        MISSION
      </text>
      {NODES.map((label, i) => {
        const a = (i / NODES.length) * Math.PI * 2 - Math.PI / 2;
        const nx = cx + Math.cos(a) * R;
        const ny = cy + Math.sin(a) * R;
        const active = i === activeIndex;
        const w = 26 + label.length * (active ? 16 : 13);
        const h = active ? 56 : 44;
        return (
          <g key={`n${i}`}>
            <rect
              x={nx - w / 2}
              y={ny - h / 2}
              width={w}
              height={h}
              rx={h / 2}
              fill={active ? BRAND.gold : BRAND.navy2}
              stroke={active ? BRAND.goldLight : BRAND.gold}
              strokeOpacity={active ? 1 : 0.35}
              strokeWidth={2}
            />
            <text
              x={nx}
              y={ny + (active ? 7 : 5)}
              fill={active ? "#171007" : BRAND.muted}
              fontSize={active ? 22 : 16}
              fontWeight={active ? 900 : 700}
              fontFamily={SANS}
              textAnchor="middle"
              letterSpacing="1"
            >
              {label}
            </text>
          </g>
        );
      })}
    </svg>
  );
};

/** JULY CONTENT CALENDAR — Thu Jul 2 six-node Opportunity Web carousel (7 slides): cover +
 *  one slide per node. Highest-reach format per the calendar ("seeds the whole month"). Static
 *  stills — rendered once per slideIndex via `remotion still`. */
export const Jul02Carousel: React.FC<CarouselProps> = ({ slideIndex }) => {
  if (slideIndex === 0) {
    return (
      <NavyBG>
        <AbsoluteFill style={{ opacity: 0.9 }}>
          <div style={{ position: "absolute", inset: 0, transform: "scale(0.56) translateY(-220px)" }}>
            <OrbWeb progress={1} />
          </div>
        </AbsoluteFill>
        <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(13,27,61,0) 0%, rgba(13,27,61,0) 52%, rgba(13,27,61,0.9) 68%, rgba(13,27,61,0.98) 100%)" }} />
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: 70, flexDirection: "column", gap: 16 }}>
          <Img src={staticFile("logo-mark.png")} style={{ width: 60, height: 60 }} />
          <div
            style={{
              fontFamily: SANS,
              fontWeight: 900,
              fontSize: 22,
              letterSpacing: "0.16em",
              textTransform: "uppercase",
              color: BRAND.goldLight,
            }}
          >
            The Web of Opportunity
          </div>
        </AbsoluteFill>
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: 90, flexDirection: "column", gap: 26 }}>
          <div style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 54, color: BRAND.white, textAlign: "center", lineHeight: 1.15, maxWidth: 860, textShadow: "0 8px 30px rgba(0,0,0,0.6)" }}>
            Stop thinking in grant lists.
            <br />
            <span style={{ color: BRAND.goldLight }}>Start thinking in opportunity webs.</span>
          </div>
          <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 22, letterSpacing: "0.08em", color: BRAND.white, opacity: 0.85 }}>
            Swipe to see all six →
          </div>
        </AbsoluteFill>
      </NavyBG>
    );
  }

  const node = NODES[slideIndex - 1];
  const num = String(slideIndex).padStart(2, "0");

  return (
    <NavyBG>
      <AbsoluteFill style={{ opacity: 0.5 }}>
        <MiniHex activeIndex={slideIndex - 1} />
      </AbsoluteFill>
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(13,27,61,0.15) 0%, rgba(13,27,61,0.55) 55%, rgba(13,27,61,0.94) 100%)" }} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: 80, flexDirection: "column", gap: 6 }}>
        <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: 26, letterSpacing: "0.2em", color: BRAND.gold, opacity: 0.8 }}>
          {num} / 06
        </div>
      </AbsoluteFill>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: 140, flexDirection: "column", gap: 22 }}>
        <div style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 96, color: BRAND.white, textAlign: "center", textShadow: "0 8px 30px rgba(0,0,0,0.6)" }}>
          {SLIDE_LABELS[node]}
        </div>
        <div style={{ fontFamily: SANS, fontSize: 28, fontWeight: 600, color: BRAND.goldLight, textAlign: "center", maxWidth: 780, lineHeight: 1.4 }}>
          {DESCRIPTIONS[node]}
        </div>
      </AbsoluteFill>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: 50 }}>
        <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 20, letterSpacing: "0.08em", color: BRAND.white, opacity: 0.6 }}>
          {slideIndex < 6 ? "Swipe →" : "anansiatlas.com"}
        </div>
      </AbsoluteFill>
    </NavyBG>
  );
};
