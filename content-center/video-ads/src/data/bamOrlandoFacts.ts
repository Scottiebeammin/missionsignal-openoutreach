// Board-presentation facts for Black Architects in the Making (BAM) Orlando.
//
// Every number here is real and sourced — pulled from Anansi Atlas against their
// live profile (built from bamorlando.org + their LinkedIn + IRS 990 filings),
// 2026-07-08. Duplicate this file per prospect and re-point the composition.
//
// PROVENANCE (say these out loud if asked):
//  - Org facts .......... bamorlando.org + linkedin.com/company/bamorlando
//  - Pool / lane / peers  IRS 990-PF foundation grant filings, Orange County
//  - Peer set ........... orgs in their sector AND their SIZE band (income < $1M) —
//                         universities are deliberately excluded; a $350M school is
//                         not "an org like you".

export const ORG = {
  name: "Black Architects in the Making",
  city: "Orlando",
  founded: "2018",
  students: "300+",
  studentsThisYear: "135+",
  workshops: "14",
  volunteers: "87",
  raised: "$29,480",
  mission:
    "Enhance and diversify the field of architecture by encouraging students of color to pursue a career path within the profession.",
} as const;

/** The funnel — three true numbers, biggest to most actionable. */
export const FUNNEL = [
  {
    id: "pool",
    amount: "$56.0M",
    amountRaw: 56_039_381,
    label: "flowed into Orange County nonprofits",
    sub: "653 foundations · 2,622 grants",
    caption: "This is the pool.",
    tone: "gold" as const,
  },
  {
    id: "lane",
    amount: "$20.6M",
    amountRaw: 20_606_324,
    label: "went to organizations your size",
    sub: "229 foundations · 994 grants",
    caption: "This is your lane.",
    tone: "gold" as const,
  },
  {
    id: "check",
    amount: "$5,000",
    amountRaw: 5_000,
    label: "the typical grant to an org your size",
    sub: "not a projection — a tax filing",
    caption: "This is your first check.",
    tone: "teal" as const,
  },
];

/** Real 990 grants to real Orange County peers — BAM's actual league. */
export const PEERS = [
  { org: "Black History Project", amount: "$5,000" },
  { org: "Love Our Youth", amount: "$5,000" },
  { org: "Page 15", amount: "$5,000" },
  { org: "Lakemont Elementary PTO", amount: "$5,000" },
  { org: "Orlando Athletic Training Academy", amount: "$5,000" },
  { org: "Pop Warner Little Scholars", amount: "$5,000" },
];

/** The other BAM chapters — the expansion mention, no numbers shown. */
export const CHAPTERS = ["Broward", "Miami", "Orlando"] as const;

export const OFFER = {
  price: "$150",
  cadence: "/month",
  terms: "Founding rate — locked for life",
  cohort: "One of the first 20 partners",
} as const;
