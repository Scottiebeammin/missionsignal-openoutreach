// Single source of truth for the automated pipeline:
// which ad uses which ElevenLabs voice, the VO script, the output audio file,
// and the date it should auto-build on (pulled from the July content calendar).
//
// Voices are resolved by NAME against your ElevenLabs account ("My Voices"),
// so the pipeline auto-pulls the right voice — no voice IDs to hardcode.

export const ADS = [
  {
    id: "PlatformShowcase",
    voice: "Christopher",
    audioOut: "showcase-vo.mp3",
    scheduledDate: "2026-07-08", // hero Platform Walkthrough drop (see 07-content-calendar-july-2026.md)
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
    voice: "Jackson",
    audioOut: "pilot-vo.mp3",
    scheduledDate: "2026-07-16", // pilot announcement (see July calendar)
    script: [
      "Applications are open for the Founding Atlas Partners Pilot.",
      "We're selecting nineteen nonprofit and mission-driven organizations.",
      "Each partner receives a guided Opportunity Web Snapshot, a forty-five minute walkthrough, and the living platform.",
      "A hundred and fifty dollars a month, locked for life, for the first twenty organizations.",
      "Nineteen seats remain. Apply now at anansi atlas dot com, slash anansi atlas.",
    ],
  },
];

// ElevenLabs voice settings (tuned for an awake, credible business read — not sleepy).
export const VOICE_SETTINGS = {
  model_id: "eleven_multilingual_v2",
  voice_settings: { stability: 0.5, similarity_boost: 0.75, style: 0.3, use_speaker_boost: true },
};
