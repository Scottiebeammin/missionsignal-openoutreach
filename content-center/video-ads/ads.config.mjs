// Single source of truth for the automated pipeline:
// which ad/post uses which ElevenLabs voice, the VO script, the output audio file,
// and the date it should auto-build on — kept in sync with the "Voice Needed" column
// in 07-content-calendar-july-2026.md.
//
// Voices are resolved by NAME against your ElevenLabs account ("My Voices"),
// so the pipeline auto-pulls the right voice — no voice IDs to hardcode.
//
// kind: "remotion"       -> full ad composition exists in src/ads/*, scheduler renders the MP4.
// kind: "voiceover-only" -> no Remotion composition yet for this calendar post; the scheduler
//                           still auto-generates the MP3 (drop it into whatever tool cuts that
//                           day's talking-head/b-roll clip). Build a Remotion comp later to
//                           fully automate the video too.
// reuseAudioFrom: "<id>" -> this date needs no new VO; it re-cuts an earlier date's audio.

export const ADS = [
  {
    id: "PlatformShowcase",
    kind: "remotion",
    voice: "Christopher",
    audioOut: "showcase-vo.mp3",
    scheduledDate: "2026-07-08", // hero Platform Walkthrough drop
    script: [
      "Your next opportunity is already out there.",
      "It's just scattered — across funder portals, emails, spreadsheets, and relationships.",
      "Anansi Atlas maps the web of opportunity around your mission: funders, partners, government pathways, resources, and readiness.",
      "Your Opportunity Web Snapshot shows your strongest asset, your biggest gap, and the single highest-leverage move to make next.",
      "Anansi Atlas. Apply for a founding seat at anansi atlas dot com, slash anansi atlas.",
    ],
  },
  {
    id: "PilotSignup",
    kind: "remotion",
    voice: "Jackson",
    audioOut: "pilot-vo.mp3",
    scheduledDate: "2026-07-18", // Jackson full-VO animated offer card (Jul 16 is a text/graphic post, not video)
    script: [
      "Applications are open for the Founding Atlas Partners Pilot.",
      "We're selecting nineteen nonprofit and mission-driven organizations.",
      "Each partner receives a guided Opportunity Web Snapshot, a forty-five minute walkthrough, and the living platform.",
      "A hundred and fifty dollars a month, locked for life, for the first twenty organizations.",
      "Nineteen seats remain. Apply now at anansi atlas dot com, slash anansi atlas.",
    ],
  },
  {
    id: "Jul10-SnapshotClip",
    kind: "remotion",
    voice: "Siren",
    audioOut: "jul10-siren.mp3",
    scheduledDate: "2026-07-10", // optional screen b-roll under the Fri Jul 10 talking-head short
    script: [
      "The Opportunity Web Snapshot leads with a summary and a 30-day action plan — not a search result.",
      "That's the difference between information and direction.",
    ],
  },
  {
    id: "Jul11-Repurpose",
    kind: "voiceover-only",
    reuseAudioFrom: "PlatformShowcase", // re-cut of the Jul 8 walkthrough — no new VO to generate
    scheduledDate: "2026-07-11",
  },
  {
    id: "Jul17-EndorsementOutro",
    kind: "remotion",
    voice: "Jackson",
    audioOut: "jul17-jackson.mp3",
    scheduledDate: "2026-07-17", // optional outro line on the founder endorsement video's closing card
    script: [
      "Founding Partners lock in one hundred and fifty dollars a month, for life.",
      "Apply at anansi atlas dot com, slash anansi atlas.",
    ],
  },
  {
    id: "Jul24-ListVsMap",
    kind: "remotion",
    voice: "Siren",
    audioOut: "jul24-siren.mp3",
    scheduledDate: "2026-07-24", // screen segment for the "list vs. map" split-screen short
    script: [
      "One page. One clear move.",
      "Funders, partners, and government pathways — mapped around your mission, with readiness scored and a single top move to make next.",
    ],
  },
  {
    id: "Jul25-SnapshotScroll",
    kind: "remotion",
    voice: "Giselle",
    audioOut: "jul25-giselle.mp3",
    scheduledDate: "2026-07-25", // full VO for the Snapshot scroll-through repurpose
    script: [
      "Your Snapshot doesn't bury the point. It opens with a 30-day action plan, ranked for your mission.",
      "Teal marks strength. Gold marks a gap. One page. One clear move.",
      "Included in the founding pilot.",
    ],
  },
  {
    id: "Jul31-ClosingOutro",
    kind: "remotion",
    voice: "Jackson",
    audioOut: "jul31-jackson.mp3",
    scheduledDate: "2026-07-31", // optional outro line on the founder closing video's card
    script: [
      "The Founding Atlas Partners pilot is nearly full.",
      "One hundred and fifty dollars a month, locked for life. Apply or message me today.",
    ],
  },

  // ── One-off flagship commercials (no scheduledDate → the scheduler ignores them;
  //    `npm run vo` still generates their narration, `npm run build` renders them). ──
  {
    id: "PremiumShowcase",
    kind: "remotion",
    oneOff: true,
    voice: "Christopher",
    audioOut: "premium-showcase-vo.mp3",
    script: [
      "Every mission is surrounded by opportunity.",
      "The problem was never opportunity. It was visibility.",
      "This is Anansi Atlas.",
      "Your Dashboard opens with one clear next move.",
      "Your Opportunity Web maps your mission at the center.",
      "Your Snapshot opens with a 30-day action plan.",
      "Founding Atlas Partners aren't just customers. They're the first twenty organizations shaping this platform — a rate locked in for life.",
      "If you're ready to stop guessing, join the family.",
      "Apply at anansi atlas dot com, slash anansi atlas.",
    ],
  },
  {
    id: "ProductWalkthrough",
    kind: "remotion",
    oneOff: true,
    voice: "Christopher",
    audioOut: "product-walkthrough-vo.mp3", // "From Scattered Opportunity to Focused Action" (~90s, flowing narration)
    script: [
      "Every nonprofit is surrounded by opportunity — funders who'd say yes, partners who'd open doors, public dollars already earmarked for work like yours.",
      "The hard part was never that opportunity didn't exist. It's that it was scattered — across browser tabs, spreadsheets, and inboxes, with no one quite sure what to chase first.",
      "Anansi Atlas changes that. You start by telling us about your mission — who you serve, and what you're building. From there, the platform maps the entire web of opportunity around it.",
      "Your Opportunity Web Snapshot opens with a clear, thirty-day action plan, ranked specifically for your mission.",
      "Scroll deeper, and you'll find the funders who are actually aligned with your work, the partners who make your applications stronger, and the local government pathways most teams never have time to uncover.",
      "We surface the community resources that build your capacity, and score your readiness honestly, so you know exactly where you're strong, and where there's a gap to close.",
      "Every risk that could slow you down gets flagged early, and every opportunity worth pursuing moves into a living pipeline — carried from first spotted, all the way to won.",
      "The result is simple. Instead of chasing scattered leads, your team always knows exactly where to focus next.",
      "We're opening the Founding Atlas Partners Pilot to nineteen to twenty mission-driven organizations.",
      "Apply today at anansi atlas dot com, slash anansi atlas.",
    ],
  },
  {
    id: "FullExplainer",
    kind: "remotion",
    oneOff: true,
    voice: "Christopher",
    audioOut: "full-explainer-vo.mp3",
    script: [
      "What if the funders, partners, and public dollars already aligned with your mission weren't hiding — they were just never mapped?",
      "Most nonprofit teams do this work in forty browser tabs. A funder database here. An email thread there. A spreadsheet somebody built two years ago that only one person still understands. Deadlines get missed. Warm partners go uncontacted. It's not a lack of effort. It's a lack of a system built to hold all of it in one place.",
      "This is Anansi Atlas — a nonprofit opportunity intelligence platform. We call it the Web of Opportunity, because every mission sits at the center of one: aligned funders, potential partners, government pathways, and community resources, all already there, waiting to be seen clearly enough to act on.",
      "Here's what that looks like in practice. Your Dashboard is home base. It opens with a single card: What To Do Next — one highest-leverage action, not a to-do list. Around it, health scores for Readiness, Partners, Pathways, and Opportunities. Upcoming deadlines are flagged before they're urgent. A busy executive director can open this for sixty seconds each morning and know exactly where to spend the day.",
      "Click into the Opportunity Web, and you'll see your mission at the center — literally. Six nodes orbit it: Funders, Partners, Government, Resources, Readiness, and Pathways. This is the actual shape of your opportunity landscape, mapped instead of scattered. Nothing here is guesswork. It's built from real research on your mission.",
      "Your Opportunity Web Snapshot is the executive brief. It opens with a plain-language summary and a thirty-day action plan, ranked specifically for your mission — not a wall of grants with no context. Below that: your top funder and partner pathways, ranked by fit. Your Readiness, scored honestly — teal where you're strong, gold where there's a gap. And your Risks and Gaps, so you see what could slow you down before it costs you a quarter. A list tells you what exists. A Snapshot tells you what to do next, in order, starting today.",
      "When an opportunity is worth pursuing, it moves into your Pipeline — a living board that carries it from spotted to submitted to won. Partners and Sponsorship maps the funders and organizations already aligned with your mission. And Resources surfaces the capacity-building, technology, and volunteer support that strengthens your readiness before you ever apply.",
      "We built Anansi Atlas because we believe mission-driven work shouldn't lose to logistics. The opportunity around your mission was never the problem. Seeing it clearly, and knowing what to do about it first, was. That's what this platform gives you back — time, clarity, and a system that keeps working even on the weeks you don't have time to look.",
      "We're opening the Founding Atlas Partners Pilot to twenty mission-driven organizations — a rate locked in for life, a Snapshot built around your actual mission, and a personal walkthrough with our team. If this is the system your organization has been missing, don't wait for the standard rate. Register now at anansi atlas dot com, slash anansi atlas, and let's map your web of opportunity today.",
    ],
  },
];

// ElevenLabs voice settings (tuned for an awake, credible business read — not sleepy).
export const VOICE_SETTINGS = {
  model_id: "eleven_multilingual_v2",
  voice_settings: { stability: 0.5, similarity_boost: 0.75, style: 0.3, use_speaker_boost: true },
};
