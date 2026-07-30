// Derive the per-line [srcFrom, srcTo] frame table that a timestamped film's LINE
// array needs, straight from the ElevenLabs alignment JSON.
//
// Films with silent passages (AnansiVisionFilm, BamOrlandoFilm) can't lay one
// continuous MP3 across the timeline — they slice the master per line with
// <Audio startFrom endAt>. Those slice points used to be read off the alignment
// by hand. This prints them.
//
// Usage: node scripts/vo-line-slices.mjs <adId> [fps]
import "./_env.mjs";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { ADS } from "../ads.config.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const adId = process.argv[2];
const FPS = Number(process.argv[3] ?? 30);
const ad = ADS.find((a) => a.id === adId);
if (!ad) {
  console.error(`Ad "${adId}" not found in ads.config.mjs`);
  process.exit(1);
}

const alignPath = path.join(ROOT, "public", ad.audioOut.replace(/\.mp3$/, ".alignment.json"));
if (!fs.existsSync(alignPath)) {
  console.error(`No alignment JSON at ${alignPath} — run gen-vo-timestamped.mjs ${adId} first.`);
  process.exit(1);
}
const align = JSON.parse(fs.readFileSync(alignPath, "utf8"));
const starts = align.character_start_times_seconds;
const ends = align.character_end_times_seconds;

// gen-vo-timestamped.mjs sends script.join(" "), so line i occupies a known
// character span of that joined string. Guard the assumption before trusting it.
const joined = ad.script.join(" ");
if (joined.length !== align.characters.length) {
  console.error(
    `Alignment length ${align.characters.length} != script length ${joined.length}. ` +
      `The alignment is stale — regenerate it.`,
  );
  process.exit(1);
}

const rows = [];
let cursor = 0;
ad.script.forEach((line, i) => {
  const a = cursor;
  const b = cursor + line.length - 1;
  cursor += line.length + 1; // +1 for the join space
  rows.push({
    i,
    from: Math.floor(starts[a] * FPS),
    to: Math.ceil(ends[b] * FPS),
    head: line.slice(0, 46).replace(/\s+/g, " "),
  });
});

const total = ends[ends.length - 1];
console.log(`// ${ad.audioOut} — ${total.toFixed(1)}s master, ${FPS}fps, ${rows.length} lines`);
console.log("const LINE: [number, number][] = [");
for (const r of rows) {
  const dur = ((r.to - r.from) / FPS).toFixed(1);
  console.log(
    `  [${String(r.from).padStart(5)}, ${String(r.to).padStart(5)}], `.padEnd(22) +
      `// S${String(r.i + 2).padStart(2, "0")} ${dur}s  ${r.head}`,
  );
}
console.log("];");

// Gaps between lines are silence in the master — useful when choosing per-scene LEADs.
const gaps = rows.slice(1).map((r, k) => ((r.from - rows[k].to) / FPS).toFixed(2));
console.log(`\n// inter-line gaps (s): ${gaps.join(", ")}`);
console.log(`// summed speech: ${(rows.reduce((s, r) => s + (r.to - r.from), 0) / FPS).toFixed(1)}s`);
