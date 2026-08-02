# Quality-Control Checklist (run before delivery; results in delivery notes)
## Accuracy & safety
- [ ] `grep -ri "bam\|architects"` across new .tsx/configs/captions → zero hits in campaign assets
- [ ] EGI facts match source log (name, 2018, mission quote, programs, geography)
- [ ] All Orlando/OC claims sourced; attributions visible on screen (ACS, Girls' Index, MENTOR)
- [ ] No funder/partner presented as committed; every card carries a confirm-eligibility chip
- [ ] No guaranteed-funding language anywhere; no EGI impact figures; no endorsement implication
- [ ] Universal versions contain zero EGI/BAM/county-specific figures
## Brand & craft
- [ ] Official emblem (anansi-emblem-785.png) opens AND closes every video; never distorted/recolored
- [ ] Tagline exact: "See your whole web of opportunity." (short form "See the whole web." only in film registers)
- [ ] Preview profile populated (never an empty template); differs per variation seed
- [ ] No teal/rose in film registers; no watermark
## Contact & links
- [ ] anansiatlas.com live; cal.com/marcus-scott-br7maf/founder-walkthrough live; QR scans to it
- [ ] marcus@anansiatlas.com and (321) 780-6335 as verified; NO social handles (none exist)
## Technical (per export)
- [ ] ffprobe: duration/streams sane; h264+aac
- [ ] Frame extraction: logo open, centerpiece, end card all populated (no 20-30KB empty frames)
- [ ] volumedetect: VO present, music under VO, no clipping; end fade to silence
- [ ] Captions inside safe margins (9:16: ≥300px bottom clearance); SRT counts match caption plans
