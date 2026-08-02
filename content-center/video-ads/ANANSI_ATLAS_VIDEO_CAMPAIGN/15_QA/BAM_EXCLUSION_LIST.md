# BAM Orlando Exclusion List

Everything below contains Black Architects in the Making (BAM) Orlando material — real prospect data, board-room only. **None of it may appear in any campaign deliverable.**

## Files that must NOT be sourced
- `public/screenshots/bam-dashboard.png`, `bam-ecosystem.png`, `bam-opps-default.png`, `bam-opps-peersize.png`, `bam-readiness.png`, `bam-web.png`
- `public/screenshots/bamv-dashboard.png`, `bamv-web.png`
- `public/bam-orlando-film-vo.mp3` + `.alignment.json`
- `out/BamOrlandoFilm.mp4`, `out/BamOrlandoFilmCaptioned.mp4`, `out/BamOrlandoPresentation-Wide.mp4`, `out/AnansiVisionFilmBAM.mp4`
- `src/oneoffs/BamOrlandoFilm.tsx`, `BamOrlandoPresentation.tsx`, and the `AnansiVisionFilmBAM` composition/ShotCtx variant

## BAM-specific facts that must not leak into narration or on-screen text
- BAM's name, program details, architecture/design focus, their workspace figures, their $5,000 peer-grant band, anything from project 18

## QC check before every export
```
strings on final scripts + grep -i "bam\|architects" across new .tsx / captions / configs
```
Verified absent from all three campaign videos before delivery.
