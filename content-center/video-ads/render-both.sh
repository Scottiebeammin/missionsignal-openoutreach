#!/bin/bash
cd "$(dirname "$0")"
echo "START $(date)"
echo "=== MASTER ==="
npx remotion render AnansiVisionFilm out/AnansiVisionFilm.mp4 --timeout=240000 2>&1 | tail -40
echo "=== CAPTIONED ==="
npx remotion render AnansiVisionFilmCaptioned out/AnansiVisionFilmCaptioned.mp4 --timeout=240000 2>&1 | tail -40
echo "=== DONE $(date) ==="
ls -la out/
