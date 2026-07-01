// Render every ad to MP4, wiring in its VO if the audio file exists.
//   node scripts/build.mjs                # render all
//   node scripts/build.mjs PilotSignup    # render one
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { ADS } from "../ads.config.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const only = process.argv.slice(2);
fs.mkdirSync(path.join(ROOT, "out"), { recursive: true });

for (const ad of ADS) {
  if (only.length && !only.includes(ad.id)) continue;
  const hasVO = fs.existsSync(path.join(ROOT, "public", ad.audioOut));
  const out = path.join("out", `${ad.id}.mp4`);
  const args = ["remotion", "render", ad.id, out];
  if (hasVO) args.push(`--props=${JSON.stringify({ audioSrc: ad.audioOut })}`);
  console.log(`Rendering ${ad.id}${hasVO ? " (with VO)" : " (silent — no VO file yet)"} → ${out}`);
  execFileSync("npx", args, { cwd: ROOT, stdio: "inherit" });
}
