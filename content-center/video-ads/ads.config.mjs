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
];

// ElevenLabs voice settings (tuned for an awake, credible business read — not sleepy).
export const VOICE_SETTINGS = {
  model_id: "eleven_multilingual_v2",
  voice_settings: { stability: 0.5, similarity_boost: 0.75, style: 0.3, use_speaker_boost: true },
};
