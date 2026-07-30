// Generate the vision film's three-stem score via the ElevenLabs Music API.
//
// Replaces the interim 80s film-bed.mp3 (looped 4x — the loop seam was audible in a
// quiet room, and PIPELINE.md flags an unresolved licence question on Artlist tracks;
// ElevenLabs generations carry commercial use on the account's paid plan).
//
// Stem lengths derive from the film's act boundaries (B[] in AnansiVisionFilm.tsx,
// 10,920f total @ 30fps) plus a tail for the crossfades:
//   minimal  Act I-II   0    -> 4110f = 137s  -> 142s generated
//   build    Act III    4110 -> 7230f = 104s  -> 110s generated
//   resolve  Act IV-V   7230 -> 10920f = 123s -> 126s generated
//
// Prompt intent mirrors the brief: hopeful, premium, cinematic, never dramatic.
// Instrumental only — narration owns every word in this film.
//
//   node scripts/gen-music-stems.mjs
import "./_env.mjs";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const KEY = process.env.ELEVENLABS_API_KEY;

const STEMS = [
  {
    name: "stem-minimal",
    ms: 145_000,
    prompt:
      // v2: v1 said "opens near-silent" and the model delivered 8s of literal digital
      // silence at the head — which made the film's 5s open dead air. The composition's
      // own volume envelope handles the fade-in; the stem must be audible from 0:00.
      "Minimal cinematic ambient score for a premium executive brand film. Soft felt piano " +
      "and warm sustained strings audible from the very first second — begins immediately, " +
      "no silent intro, no long fade-in. Slow, spacious, contemplative, hopeful. Around 62 " +
      "BPM. No drums, no percussion, no vocals. Starts gentle and sparse, grows very " +
      "gradually in warmth and fullness. Apple keynote / documentary opening register. " +
      "Instrumental only.",
  },
  {
    name: "stem-build",
    ms: 110_000,
    prompt:
      "Building cinematic underscore for a premium technology brand film. Warm piano motif over " +
      "swelling strings, soft pulsing synth bass, light rhythmic momentum entering midway — felt, " +
      "not flashy. Optimistic and assured, steadily rising energy without ever becoming dramatic " +
      "or epic. Around 80 BPM. No vocals, no big drums, no trailer hits. Reaches a warm confident " +
      "peak and holds it. Instrumental only.",
  },
  {
    name: "stem-resolve",
    ms: 126_000,
    prompt:
      "Resolving cinematic score for the final act of a premium executive film. Opens sparse and " +
      "questioning — solo piano with air and silence between phrases — then slowly warms into " +
      "gentle hopeful strings and a settled, quietly triumphant final resolution that fades to a " +
      "single sustained warm chord. Emotional but restrained, never sentimental or dramatic. " +
      "Around 66 BPM. No drums, no vocals. Instrumental only.",
  },
];

for (const s of STEMS) {
  process.stdout.write(`${s.name} (${s.ms / 1000}s)… `);
  const r = await fetch("https://api.elevenlabs.io/v1/music?output_format=mp3_44100_192", {
    method: "POST",
    headers: { "xi-api-key": KEY, "content-type": "application/json" },
    body: JSON.stringify({ prompt: s.prompt, music_length_ms: s.ms }),
  });
  if (!r.ok) {
    console.error(`FAILED ${r.status}: ${(await r.text()).slice(0, 300)}`);
    process.exit(1);
  }
  const buf = Buffer.from(await r.arrayBuffer());
  const out = path.join(ROOT, "public", "music", `${s.name}.mp3`);
  fs.writeFileSync(out, buf);
  console.log(`✓ ${(buf.length / 1024 / 1024).toFixed(1)} MB -> public/music/${s.name}.mp3`);
}
console.log("all stems generated");
