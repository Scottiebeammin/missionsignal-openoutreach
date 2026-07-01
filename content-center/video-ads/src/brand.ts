// Anansi Atlas brand tokens — keep in sync with content-center/00-brand-brief.md
export const BRAND = {
  navy: "#0d1b3d",
  navy2: "#17284f",
  charcoal: "#101826",
  gold: "#d4a017",
  goldLight: "#f3dd8c",
  teal: "#0f766e",
  tealSoft: "#e9f6f3",
  goldSoft: "#fff6e2",
  ink: "#f4f7fb",
  muted: "#9fb0c6",
  rose: "#c46a3d",
  white: "#ffffff",
} as const;

export const FPS = 30;
export const SIZE = 1080; // square 1:1 — best for LinkedIn feed

export const SIGNUP_URL = "anansiatlas.com/anansi-atlas";

// The six Opportunity Web nodes (product node vocabulary)
export const NODES = [
  "FUNDERS",
  "PARTNERS",
  "GOVERNMENT",
  "RESOURCES",
  "READINESS",
  "PATHWAYS",
] as const;
