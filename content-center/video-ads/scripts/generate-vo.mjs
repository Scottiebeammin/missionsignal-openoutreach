// Auto-generate ElevenLabs voiceover for the ads.
// - Auto-pulls the voice ID by NAME from your ElevenLabs account (no hardcoded IDs).
// - Writes MP3s into public/ for Remotion to use.
//
// The key is read from a local .env file (gitignored) or the environment:
//   put  ELEVENLABS_API_KEY=sk_...  in content-center/video-ads/.env   then:
//   node scripts/generate-vo.mjs            # all ads
//   node scripts/generate-vo.mjs PilotSignup   # one ad
import "./_env.mjs"; // loads .env → process.env before we read the key
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { ADS, VOICE_SETTINGS } from "../ads.config.mjs";

const __dir = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dir, "..");
const KEY = process.env.ELEVENLABS_API_KEY;

if (!KEY) {
  console.error("✗ No ELEVENLABS_API_KEY found. Put it in content-center/video-ads/.env  (ELEVENLABS_API_KEY=sk_...)");
  process.exit(1);
}

const only = process.argv.slice(2);

async function listVoices() {
  const r = await fetch("https://api.elevenlabs.io/v1/voices", { headers: { "xi-api-key": KEY } });
  if (!r.ok) throw new Error(`voices list failed: ${r.status} ${await r.text()}`);
  const data = await r.json();
  return data.voices.map((v) => ({ id: v.voice_id, name: v.name.trim() }));
}

// Match a config voice ("Christopher") against full ElevenLabs names
// ("Christopher - optimistic storyteller") by exact match, then name-prefix, then first-word.
function resolveVoiceId(voices, wanted) {
  const w = wanted.trim().toLowerCase();
  return (
    voices.find((v) => v.name.toLowerCase() === w) ||
    voices.find((v) => v.name.toLowerCase().startsWith(w)) ||
    voices.find((v) => v.name.toLowerCase().split(/[\s\-–]+/)[0] === w)
  )?.id;
}

async function tts(voiceId, text, outPath) {
  const r = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`, {
    method: "POST",
    headers: { "xi-api-key": KEY, "content-type": "application/json", accept: "audio/mpeg" },
    body: JSON.stringify({ text, ...VOICE_SETTINGS }),
  });
  if (!r.ok) throw new Error(`TTS failed: ${r.status} ${await r.text()}`);
  fs.writeFileSync(outPath, Buffer.from(await r.arrayBuffer()));
}

const voices = await listVoices();
console.log(`Found ${voices.length} voices in your account.`);
fs.mkdirSync(path.join(ROOT, "public"), { recursive: true });

for (const ad of ADS) {
  if (only.length && !only.includes(ad.id)) continue;
  if (ad.reuseAudioFrom) {
    console.log(`… ${ad.id} reuses ${ad.reuseAudioFrom}'s VO — nothing to generate.`);
    continue;
  }
  const voiceId = resolveVoiceId(voices, ad.voice);
  if (!voiceId) {
    console.error(`✗ ${ad.id}: voice "${ad.voice}" not found in your ElevenLabs account (check My Voices / spelling).`);
    continue;
  }
  const text = ad.script.join(" ");
  const out = path.join(ROOT, "public", ad.audioOut);
  process.stdout.write(`… ${ad.id} → ${ad.audioOut} (voice: ${ad.voice}) `);
  await tts(voiceId, text, out);
  console.log(`✓ ${(fs.statSync(out).size / 1024).toFixed(0)} KB`);
}
console.log("Done. Full ads (kind: remotion) can now render with:  node scripts/build.mjs");
console.log("voiceover-only ads: drop the generated MP3 into your editor for that day's talking-head/b-roll clip.");
