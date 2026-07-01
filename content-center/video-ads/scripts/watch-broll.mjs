// Watches public/broll/ (and public/*.mp3, public/music/) for new/changed files and
// automatically re-renders whichever composition uses them — no "tell me it's in" step.
//
//   node scripts/watch-broll.mjs
//
// Leave this running in a terminal tab while you generate assets in ElevenLabs. Drop a
// file in public/broll/ with the expected name (see ELEVENLABS-ASSETS.md) and it renders
// automatically a couple seconds later. Ctrl+C to stop.
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import chokidar from "chokidar";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

// filename (relative to public/) -> which composition(s) to rebuild when it changes.
const TRIGGERS = {
  "broll/hands-typing.mp4": ["ProductWalkthrough"],
  "broll/problem.mp4": ["ProductWalkthrough"],
  "broll/laptop-office.mp4": ["ProductWalkthrough"],
  "broll/laptop-office.jpg": ["ProductWalkthrough"],
  "product-walkthrough-vo.mp3": ["ProductWalkthrough"],
};

let building = false;
let pending = new Set();

async function rebuild() {
  if (building) return;
  building = true;
  const ids = [...new Set([...pending].flatMap((f) => TRIGGERS[f] || []))];
  pending.clear();
  for (const id of ids) {
    console.log(`\n🔄 Change detected → rendering ${id}...`);
    try {
      execFileSync("node", ["scripts/build.mjs", id], { cwd: ROOT, stdio: "inherit" });
      console.log(`✅ ${id} re-rendered → out/${id}.mp4`);
    } catch (e) {
      console.error(`✗ ${id} failed to render:`, e.message);
    }
  }
  building = false;
  if (pending.size) rebuild(); // catch anything that landed while we were building
}

const watchPaths = Object.keys(TRIGGERS).map((f) => path.join(ROOT, "public", f));
console.log("👀 Watching for B-roll / VO changes:");
for (const f of Object.keys(TRIGGERS)) console.log("  -", f);
console.log("\nDrop files into public/broll/ (or regenerate VO into public/) — renders happen automatically.\n");

chokidar
  .watch(watchPaths, { ignoreInitial: true, awaitWriteFinish: { stabilityThreshold: 800 } })
  .on("add", (p) => {
    const rel = path.relative(path.join(ROOT, "public"), p).replace(/\\/g, "/");
    console.log(`+ ${rel}`);
    pending.add(rel);
    rebuild();
  })
  .on("change", (p) => {
    const rel = path.relative(path.join(ROOT, "public"), p).replace(/\\/g, "/");
    console.log(`~ ${rel}`);
    pending.add(rel);
    rebuild();
  });
