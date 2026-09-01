// Generate ONE narration line as its own audio file, with character alignment.
//
// Why this exists (2026-09-01): adding a scene to a finished film used to mean
// regenerating the whole VO master, and ElevenLabs is nondeterministic — every existing
// take changes, so every measured beat in the film has to be re-derived and the
// approved performance is gone. That is what the July 29 note means by "fixing it after
// costs a full VO regeneration plus a re-derivation of every timing."
//
// Generating the new line as a SEPARATE file keeps all existing takes byte-identical.
// The composition plays it as its own <Audio> instead of a slice of the master, so only
// the new scene is new audio.
//
// Same voice and same VOICE_SETTINGS as the parent ad, so the language lock
// (eleven_turbo_v2_5 + language_code "en") that stops mid-take language drift applies
// here too — a one-off line is exactly where that would go unnoticed.
//
// Usage:
//   node scripts/gen-vo-line.mjs <adId> <outBasename> "<the line>"
// Example:
//   node scripts/gen-vo-line.mjs AnansiVisionFilm anansi-vision-film-local-vo "State money..."
import "./_env.mjs";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { ADS, VOICE_SETTINGS } from "../ads.config.mjs";

const __dir = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dir, "..");
const KEY = process.env.ELEVENLABS_API_KEY;
const [adId, outBase, ...textParts] = process.argv.slice(2);
const text = textParts.join(" ").trim();

if (!adId || !outBase || !text) {
  console.error('Usage: node scripts/gen-vo-line.mjs <adId> <outBasename> "<the line>"');
  process.exit(1);
}
if (!KEY) {
  console.error("ELEVENLABS_API_KEY missing — put it in content-center/video-ads/.env");
  process.exit(1);
}
const ad = ADS.find((a) => a.id === adId);
if (!ad) {
  console.error(`Ad "${adId}" not found in ads.config.mjs — needed for the voice.`);
  process.exit(1);
}

const voicesRes = await fetch("https://api.elevenlabs.io/v1/voices", {
  headers: { "xi-api-key": KEY },
});
const voices = (await voicesRes.json()).voices.map((v) => ({ id: v.voice_id, name: v.name.trim() }));
const wanted = ad.voice.trim().toLowerCase();
const voiceId = (
  voices.find((v) => v.name.toLowerCase() === wanted) ||
  voices.find((v) => v.name.toLowerCase().startsWith(wanted)) ||
  voices.find((v) => v.name.toLowerCase().split(/[\s\-–]+/)[0] === wanted)
)?.id;
if (!voiceId) {
  console.error(`Voice "${ad.voice}" not found on this account.`);
  process.exit(1);
}

const r = await fetch(
  `https://api.elevenlabs.io/v1/text-to-speech/${voiceId}/with-timestamps`,
  {
    method: "POST",
    headers: { "xi-api-key": KEY, "content-type": "application/json", accept: "application/json" },
    body: JSON.stringify({ text, ...VOICE_SETTINGS }),
  },
);
if (!r.ok) {
  console.error(`TTS failed: ${r.status} ${await r.text()}`);
  process.exit(1);
}

const data = await r.json();
fs.writeFileSync(path.join(ROOT, "public", `${outBase}.mp3`), Buffer.from(data.audio_base64, "base64"));
fs.writeFileSync(
  path.join(ROOT, "public", `${outBase}.alignment.json`),
  JSON.stringify(data.alignment, null, 2),
);

// The composition needs the length in FRAMES, so print it rather than making the next
// person convert it by hand — that conversion is where an off-by-one desync starts.
const ends = data.alignment.character_end_times_seconds;
const seconds = ends[ends.length - 1];
const FPS = 30;
console.log(`✓ ${outBase}.mp3  voice=${ad.voice}  ${text.length} chars`);
console.log(`✓ ${outBase}.alignment.json`);
console.log(`  spoken length: ${seconds.toFixed(3)}s = ${Math.ceil(seconds * FPS)} frames @ ${FPS}fps`);
