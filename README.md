# 🦉 Boobook — Sovereign Australian Maritime Intelligence

> *We hear what ships can't hide.*

Boobook is a passive RF intelligence layer for Australian maritime enforcement. It detects vessels that go dark — not by trusting their AIS transponder, but by listening for the radio signals every working ship still emits.

**Status: P1 complete. AIS anomaly engine validated. RF simulation done. Seeking RF co-founder.**

---

## What it does

Ships that disable their AIS still emit: VHF radio, marine radar, satellite phones. Boobook's ground-based SDR nodes receive those emissions, correlate them against AIS, and surface prioritised enforcement alerts for AFMA/ABF.

**Current capability (AIS-only validation layer):**
- 5 detection rules: AIS gap, impossible speed (spoofing), loitering, rendezvous, sensitive zone
- Risk scores 0–100 with severity tiers (HIGH/MEDIUM/LOW)
- Full evidence chain + recommended action per alert
- AMSA CTS + NOAA MarineCadastre + GFW ingestors
- GeoJSON track output for map overlays
- Torres Strait / Arafura / Darwin bbox presets

---

## Quick start

```bash
pip install -e .

# Run demo on synthetic AIS data (133 rows, 9 vessels, all 5 alert types)
boobook demo --out artifacts/demo

# Run on your own AIS CSV
boobook validate-ais --input your_ais.csv --out artifacts/output

# Build training data from NOAA (downloads ~300MB)
python scripts/build_training_data.py --source noaa

# Clip to Torres Strait
python scripts/build_training_data.py --source noaa --bbox torres_strait

# Run on AMSA CTS data (download from operations.amsa.gov.au/Spatial/DataServices/DigitalData)
python scripts/build_training_data.py --source amsa --amsa-file your_amsa.csv --bbox torres_strait
```

---

## Sample run output

```
Loaded: 133 rows, 9 vessels
Vessel types: Fishing (73), Cargo (36), Law Enforcement (24)

Alerts: 14  |  HIGH: 7  |  MEDIUM: 2  |  LOW: 5

Alert types:
  AIS_GAP:               5
  SENSITIVE_ZONE:        5
  RENDEZVOUS_CANDIDATE:  2
  IMPOSSIBLE_SPEED:      1
  LOITERING:             1

Top alerts:
  SEA EAGLE      Cargo   IMPOSSIBLE_SPEED  98  HIGH
  NORTHERN PRIDE Fishing AIS_GAP           95  HIGH
  TIMOR CHIEF    Fishing RENDEZVOUS        85  HIGH
  MALITA SEA     Fishing LOITERING         84  HIGH
```

---

## Repo structure

```
src/boobook/
  ingest/
    amsa_cts.py       — AMSA/CTS CSV normaliser (official Australian source)
    noaa_ais.py       — NOAA MarineCadastre ingestor (large-scale stress testing)
    gfw_events.py     — Global Fishing Watch AIS-off/encounter/fishing events
    live_ais.py       — Live AIS via RTL-SDR (Phase 2)
  analytics/
    ais_anomaly.py    — 5 detection rules, risk scoring, GeoJSON output
  rf/
    coverage.py       — Radio horizon + TDOA viability
    gcc_phat.py       — GCC-PHAT cross-correlator
    tdoa_solver.py    — Hyperbolic solver + CEP estimation
    simulate.py       — Deterministic RF simulation
  dashboard/
    export.py         — HTML dashboard generator
  cli.py              — boobook CLI
  config.py           — Sensitive zones, thresholds
  utils_geo.py        — Haversine, implied speed

scripts/
  build_training_data.py  — Dataset pipeline (NOAA, AMSA, GFW)

tests/                    — 50 tests, all passing
data/sample/              — 133-row synthetic AIS (all alert types)
artifacts/sample_run/     — Latest validated run outputs
docs/                     — Technical limitations, legal notes, validation plan
```

---

## Data sources

| Source | Use | Access |
|--------|-----|--------|
| AMSA CTS | Australian sovereign AIS | [operations.amsa.gov.au](https://operations.amsa.gov.au/Spatial/DataServices/DigitalData) |
| NOAA MarineCadastre | Large-scale AIS stress test | Free, no auth |
| Danish Maritime Authority | Chokepoint/strait behaviour | [dma.dk](https://www.dma.dk/safety-at-sea/navigational-information/ais-data) |
| Global Fishing Watch | Fishing/IUU labels, AIS-off events | Free API token required |
| xView3-SAR | Dark vessel SAR labels | Phase 2 |

---

## Tests

```bash
pytest tests/ -v   # 50 tests, ~1s
```

Coverage: AMSA ingest, NOAA ingest, GFW ingest, all 5 anomaly detectors, RF coverage, GCC-PHAT, TDOA solver.

---

## Roadmap

| Phase | Status | Milestone |
|-------|--------|-----------|
| P1 | ✅ Done | AIS engine, AMSA pipeline, TDOA simulation, 50 tests |
| P2 | 🔶 Now | RF co-founder, live AIS via RTL-SDR, 3-node TDOA test |
| P3 | — | First paid AFMA/ABF pilot, Torres Strait deployment |
| P4 | — | $250k+ ARR, seed raise |

---

## Investor site

**[kavanmehta-pixel.github.io/boobook](https://kavanmehta-pixel.github.io/boobook)**

---

## Legal

AIS anomalies are not proof of illegal behaviour. All alerts are cueing signals for human review. Passive receive-only architecture. This system does not intercept vessel communications content.

See `docs/LEGAL_COMPLIANCE_NOTES.md` and `docs/TECHNICAL_LIMITATIONS.md`.

---

*Built by [Attalis Capital](https://attalis.com.au). Seeking RF/signals co-founder — ex-ADF, DSTG, UNSW EE.*
