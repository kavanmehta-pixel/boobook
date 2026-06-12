# Technical limitations

## AIS-only limitations

- Public/source AIS data cannot detect a vessel that never transmits AIS.
- AIS gaps can be caused by coverage, data filtering, reception failure, terrain, equipment failure or intentional disabling.
- Impossible speeds can be caused by data errors or track stitching, not just spoofing.
- Rendezvous candidates require contextual review; proximity alone is not suspicious enough.

## RF/TDOA limitations

- TDOA requires the same emission to be heard by at least three sensor nodes.
- VHF/AIS is line-of-sight constrained and coverage depends on antenna height, receiver quality, sea state, ducting and terrain.
- The current RF demo is geometry/timing simulation only.
- Radar detection is not v1. X/S-band detection needs a separate RF front-end and field validation.
- Timing-budget CEP is not real-world CEP; multipath, survey error and GDOP will increase error.

## Product limitation

Boobook is a cueing and validation layer. It reduces search area and prioritises analyst review. It is not a replacement for patrol assets, SAR, EO/SAR satellite imagery, boarding, or lawful investigation.
