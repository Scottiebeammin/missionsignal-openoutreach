// Data schema for the product-walkthrough video (see the campaign brief + BRAND-TEMPLATE.md).
// Edit content here without touching the composition — each section renders itself.
// Screenshots live in public/screenshots/ (real UI, captured off the Creative Display profile).

export type WalkSection = {
  id: string;
  label: string; // short on-screen section label
  value: string; // one-sentence value line
  shot: string; // screenshot filename in public/screenshots/
  tone: "teal" | "gold"; // accent (teal = strength/product, gold = gap/urgency)
  vo: string; // voiceover line for this beat (also becomes the subtitle)
};

// Act 3 — the dashboard walkthrough, section by section.
export const WALK_SECTIONS: WalkSection[] = [
  {
    id: "mission",
    label: "Your Mission Profile",
    value: "It all starts with your mission — everything maps back to it.",
    shot: "organization.png",
    tone: "teal",
    vo: "It starts with your mission. Everything maps back to it.",
  },
  {
    id: "snapshot",
    label: "Opportunity Web Snapshot",
    value: "Your executive brief opens with a ranked 30-day action plan.",
    shot: "snapshot.png",
    tone: "gold",
    vo: "Your Opportunity Web Snapshot opens with a 30-day action plan, ranked for your mission.",
  },
  {
    id: "funders",
    label: "Funders",
    value: "Aligned funders, ranked by fit — not an endless list.",
    shot: "funding.png",
    tone: "teal",
    vo: "Aligned funders, ranked by fit — not an endless list to sort through.",
  },
  {
    id: "partners",
    label: "Partners",
    value: "The partners who make your applications competitive.",
    shot: "partners.png",
    tone: "teal",
    vo: "The partners who make your applications competitive, mapped right beside your funders.",
  },
  {
    id: "government",
    label: "Government Pathways",
    value: "Public-sector lanes — city, county, and workforce.",
    shot: "government.png",
    tone: "teal",
    vo: "Government pathways — the public-sector lanes most teams never have time to find.",
  },
  {
    id: "resources",
    label: "Community Resources",
    value: "Capacity-building, technology, and volunteer support.",
    shot: "resources.png",
    tone: "teal",
    vo: "Community resources — capacity, technology, and volunteer support to strengthen your work.",
  },
  {
    id: "readiness",
    label: "Readiness Gaps",
    value: "Scored honestly — teal where you're strong, gold where there's a gap.",
    shot: "readiness.png",
    tone: "gold",
    vo: "Your readiness, scored honestly — where you're strong, and exactly where to improve.",
  },
  {
    id: "risks",
    label: "Strategic Risks",
    value: "What could slow you down — flagged before it costs a quarter.",
    shot: "snapshot.png",
    tone: "gold",
    vo: "Strategic risks — flagged early, before they cost you a quarter.",
  },
  {
    id: "capital",
    label: "Routes to Capital",
    value: "A living pipeline — from spotted, to submitted, to won.",
    shot: "pipeline.png",
    tone: "teal",
    vo: "Routes to capital — a living pipeline that carries every opportunity from spotted to won.",
  },
  {
    id: "next",
    label: "Practical Next Steps",
    value: "One clear next move — not a to-do avalanche.",
    shot: "dashboard.png",
    tone: "gold",
    vo: "And practical next steps — one clear move to make next, not a to-do avalanche.",
  },
];
