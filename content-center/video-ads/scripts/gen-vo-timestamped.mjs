// One-off: regenerate a single ad's VO via the ElevenLabs with-timestamps endpoint so we get
// exact character-level alignment (not word-count estimates) for precise scene-to-speech sync.
// Usage: node scripts/gen-vo-timestamped.mjs <adId>
import "./_env.mjs";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { ADS, VOICE_SETTINGS } from "../ads.config.mjs";

const __dir = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dir, "..");
const KEY = process.env.ELEVENLABS_API_KEY;
const adId = process.argv[2];
const ad = ADS.find((a) => a.id === adId);
if (!ad) {
  console.error(`Ad "${adId}" not found in ads.config.mjs`);
  process.exit(1);
}

async function listVoices() {
  const r = await fetch("https://api.elevenlabs.io/v1/voices", { headers: { "xi-api-key": KEY } });
  const data = await r.json();
  return data.voices.map((v) => ({ id: v.voice_id, name: v.name.trim() }));
}
function resolveVoiceId(voices, wanted) {
  const w = wanted.trim().toLowerCase();
  return (
    voices.find((v) => v.name.toLowerCase() === w) ||
    voices.find((v) => v.name.toLowerCase().startsWith(w)) ||
    voices.find((v) => v.name.toLowerCase().split(/[\s\-–]+/)[0] === w)
  )?.id;
}

const voices = await listVoices();
const voiceId = resolveVoiceId(voices, ad.voice);
const text = ad.script.join(" ");

const r = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voiceId}/with-timestamps`, {
  method: "POST",
  headers: { "xi-api-key": KEY, "content-type": "application/json", accept: "application/json" },
  body: JSON.stringify({ text, ...VOICE_SETTINGS }),
});
if (!r.ok) {
  console.error(`TTS failed: ${r.status} ${await r.text()}`);
  process.exit(1);
}
const data = await r.json();
const audioBuf = Buffer.from(data.audio_base64, "base64");
const outAudio = path.join(ROOT, "public", ad.audioOut);
fs.writeFileSync(outAudio, audioBuf);
const outAlign = path.join(ROOT, "public", ad.audioOut.replace(/\.mp3$/, ".alignment.json"));
fs.writeFileSync(outAlign, JSON.stringify(data.alignment, null, 2));
console.log(`✓ audio -> ${outAudio} (${(audioBuf.length / 1024).toFixed(0)} KB)`);
console.log(`✓ alignment -> ${outAlign}`);
console.log(`  text length: ${text.length} chars, alignment chars: ${data.alignment.characters.length}`);
