// Auto-build any ad whose scheduledDate (from ads.config.mjs / the July calendar)
// matches today — generating its ElevenLabs VO, then rendering the final MP4.
// Designed to be run once a day by cron/launchd (see README).
//
//   node scripts/build-scheduled.mjs                 # builds ads due today
//   ADS_DATE=2026-07-08 node scripts/build-scheduled.mjs   # dry-run a specific date
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { ADS } from "../ads.config.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const today = process.env.ADS_DATE || new Date().toISOString().slice(0, 10);

const due = ADS.filter((a) => a.scheduledDate === today);
if (due.length === 0) {
  console.log(`[${today}] Nothing on the calendar for today. Nothing to build.`);
  process.exit(0);
}

const needsGeneration = due.some((a) => !a.reuseAudioFrom);
if (needsGeneration && !process.env.ELEVENLABS_API_KEY) {
  console.error(`[${today}] ${due.length} item(s) due but ELEVENLABS_API_KEY is not set — cannot generate VO.`);
  process.exit(1);
}

fs.mkdirSync(path.join(ROOT, "out"), { recursive: true });

for (const ad of due) {
  if (ad.reuseAudioFrom) {
    // Re-cut of an earlier date's VO — nothing new to generate; just confirm the source exists.
    const src = ADS.find((a) => a.id === ad.reuseAudioFrom);
    const srcPath = path.join(ROOT, "public", src?.audioOut || "");
    if (src && fs.existsSync(srcPath)) {
      console.log(`[${today}] ${ad.id} reuses ${ad.reuseAudioFrom}'s VO (${src.audioOut}) — ready to re-cut in your editor.`);
    } else {
      console.warn(`[${today}] ${ad.id} wants to reuse ${ad.reuseAudioFrom}'s VO, but ${src?.audioOut} doesn't exist yet — generate that ad first.`);
    }
    continue;
  }

  console.log(`[${today}] Building ${ad.id} (voice: ${ad.voice})`);
  // 1) auto-pull voice + generate VO
  execFileSync("node", ["scripts/generate-vo.mjs", ad.id], { cwd: ROOT, stdio: "inherit" });

  if (ad.kind !== "remotion") {
    console.log(`[${today}] ✓ VO ready at public/${ad.audioOut} — no Remotion composition for this post yet; drop it into your editor for that day's clip.`);
    continue;
  }

  // 2) render final MP4 with VO + subtitles, stamped with the date
  const out = path.join("out", `${today}-${ad.id}.mp4`);
  execFileSync("npx", ["remotion", "render", ad.id, out, `--props=${JSON.stringify({ audioSrc: ad.audioOut })}`], {
    cwd: ROOT,
    stdio: "inherit",
  });
  console.log(`[${today}] ✓ ${out}`);
}
console.log(`[${today}] Done — ${due.length} item(s) processed.`);
