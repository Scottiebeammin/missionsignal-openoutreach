#!/bin/bash
cd "$(dirname "$0")"
echo "START $(date)"
echo "=== CAPTIONED ==="
npx remotion render AnansiVisionFilmCaptioned out/AnansiVisionFilmCaptioned.mp4 --timeout=240000 2>&1 | tail -40
echo "=== DONE $(date) ==="
ls -la out/
