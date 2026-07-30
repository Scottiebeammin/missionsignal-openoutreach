// Derive LINE[] (frames into the master VO mp3) from the ElevenLabs alignment JSON,
// then check every line fits its scene given the film's B[] cuts and LEAD[] pauses.
//
// This exists because EVERY narration edit invalidates every measured timing in the
// film. Re-run it after `node scripts/gen-vo-timestamped.mjs AnansiVisionFilm`, paste
// the printed LINE[] into src/oneoffs/AnansiVisionFilm.tsx, and only trust the render
// if the fit check passes.
//
//   node scripts/derive-vo-lines.mjs
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { ADS } from "../ads.config.mjs";

const FPS = 30;
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const al = JSON.parse(fs.readFileSync(path.join(ROOT, "public/anansi-vision-film-vo.alignment.json"), "utf8"));
const lines = ADS.find((a) => a.id === "AnansiVisionFilm").script;
const text = lines.join(" ");

if (text.length !== al.characters.length) {
  console.error(`MISMATCH: script ${text.length} chars vs alignment ${al.characters.length} — regenerate the VO first`);
  process.exit(1);
}
const st = al.character_start_times_seconds;
const en = al.character_end_times_seconds;

// Mirrored from AnansiVisionFilm.tsx — keep in sync when either changes.
const B = [0, 150, 810, 1440, 1830, 2130, 2910, 3660, 4110, 4560, 5370, 6060, 6810, 7230, 7680, 8430, 9240, 9870, 10920];
const LEAD = [60, 60, 70, 60, 70, 40, 60, 30, 80, 70, 40, 60, 70, 90, 90, 70, 60];

let cur = 0;
const out = [];
lines.forEach((ln, i) => {
  const start = cur;
  const end = cur + ln.length; // exclusive
  cur = end + 1;               // +1 for the space join
  out.push([Math.floor(st[start] * FPS), Math.ceil(en[end - 1] * FPS), i, ln]);
});

console.log("const LINE: [number, number][] = [");
out.forEach(([f0, f1, i, ln]) => {
  console.log(`  [${f0}, ${f1}],`.padEnd(20) + ` // S${String(i + 2).padStart(2, "0")} ${ln.slice(0, 32)}…`);
});
console.log("];");

console.log("\n── FIT CHECK ────────────────────────────────────────────────");
let bad = 0;
out.forEach(([f0, f1, i]) => {
  const dur = f1 - f0;
  const cap = B[i + 2] - B[i + 1];
  const need = LEAD[i] + dur;
  const slack = cap - need;
  if (slack < 0) bad++;
  const flag = slack < 0 ? "✗ OVERFLOW" : slack < 40 ? "⚠ tight" : "ok";
  console.log(
    `S${String(i + 2).padStart(2, "0")} dur=${String(dur).padStart(4)}f lead=${String(LEAD[i]).padStart(3)} ` +
    `need=${String(need).padStart(4)} cap=${String(cap).padStart(4)} slack=${String(slack).padStart(5)} ${flag}`
  );
});
const total = en[en.length - 1];
const masterFrames = Math.ceil(total * FPS);
console.log(`\nmaster VO: ${total.toFixed(1)}s (${masterFrames}f)  |  film: ${(B[18] / FPS).toFixed(0)}s  |  speech ${(total / (B[18] / FPS) * 100).toFixed(0)}%`);
console.log(`MASTER_FRAMES = ${masterFrames}  <- paste into AnansiVisionFilm.tsx`);
console.log(bad === 0 ? "✓ every line fits its scene" : `✗ ${bad} overflow(s)`);
