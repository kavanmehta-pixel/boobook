# Ninox Investor MVP — Run Report

Generated: 2026-06-12

## What was fixed

- Integrated the AIS source-data validation dashboard into the main Ninox package.
- Replaced loose scripts with a proper `src/ninox` Python package.
- Added reproducible CLI commands: `validate-ais`, `dashboard`, `coverage`, `rf-demo`, `demo`.
- Added robust AMSA/CTS-style CSV/ZIP normalisation.
- Added AIS anomaly validation rules for gaps, impossible speed, loitering, rendezvous candidates and sensitive-zone context.
- Added dashboard artifact generation from processed CSV/GeoJSON outputs.
- Added RF/TDOA simulation modules and tests.
- Added source-repo map, investor demo script, technical limitations, compliance notes and 90-day validation plan.
- Included existing fixed deck/model/research artifacts under `artifacts/`.

## Verification

Clean editable install tested:

```bash
python -m pip install -e ".[dev]"
ninox --help
ninox validate-ais data/sample/sample_ais_events.csv --out /tmp/ninox_processed
ninox dashboard --processed /tmp/ninox_processed --out /tmp/ninox_dashboard.html
ninox rf-demo --out /tmp/ninox_rf
python -m pytest
```

Result:

```text
7 passed
```

## Investor-safe status

This is a working source-data validation MVP. It is not live passive RF proof yet. The correct demo line is:

> Ninox validates the maritime analytics workflow on AIS source data today. The next proof point is live AIS capture via SDR, then controlled three-node TDOA, then RF/AIS mismatch detection inside an instrumented choke point.
