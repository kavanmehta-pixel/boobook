# Boobook MDA — Investor MVP

**Sovereign Australian maritime intelligence layer.**  
AIS source-data anomaly detection today. Passive RF/TDOA validation next.

> **Honest scope:** This repo proves the reproducible analytics workflow on source AIS data.  
> It does **not** claim live passive-RF dark-vessel detection yet.

---

## What this MVP does

| Layer | Status |
|---|---|
| Normalise AMSA/CTS-style AIS data | ✅ Working |
| Detect AIS gaps, impossible speed, loitering, rendezvous, zone presence | ✅ Working |
| Generate reproducible artefacts: alerts.csv, vessels.csv, tracks.geojson | ✅ Working |
| Self-contained investor dashboard | ✅ Working |
| RF/TDOA simulation (planning layer) | ✅ Working |
| Live SDR capture | ⬜ Next milestone |
| 3-node controlled TDOA test | ⬜ Phase 2 |
| Choke-point field deployment | ⬜ Phase 3 |

---

## Quick start (no hardware needed)

```bash
# Install
pip install -e ".[dev]"

# Run all tests (27 tests)
make test

# Full demo: AIS validation + dashboard + RF simulation
make demo

# Or step by step:
make validate-ais   # normalise sample data, generate alerts
make dashboard      # build HTML dashboard
make coverage       # RF cluster coverage summary
make rf-demo        # TDOA simulation
```

Open `artifacts/demo/Boobook_Investor_Dashboard.html` in any browser.

---

## Using real AMSA/CTS data

1. Download a vessel traffic dataset from [AMSA Spatial](https://operations.amsa.gov.au/Spatial/DataServices/DigitalData)
2. Save to `data/raw/`
3. Run:

```bash
PYTHONPATH=src python -m boobook.cli validate-ais data/raw/YOUR_FILE.csv --out data/processed/live
PYTHONPATH=src python -m boobook.cli dashboard --processed data/processed/live --out artifacts/live_dashboard.html
```

ZIP files containing a CSV are also accepted.

---

## Repo layout

```
src/boobook/
  ingest/
    amsa_cts.py         Raw AMSA/CTS CSV/ZIP normalisation + column aliasing
    live_ais.py         Future pyais SDR decoder hook
  analytics/
    ais_anomaly.py      5 detection rules: gaps / speed / loitering / rendezvous / zone
  dashboard/
    export.py           Self-contained HTML dashboard generator
  rf/
    coverage.py         Choke-point radio-horizon + TDOA viability
    gcc_phat.py         GCC-PHAT TDOA timing estimator
    tdoa_solver.py      Hyperbolic position solver + CEP
    simulate.py         Deterministic RF/TDOA planning simulation
  cli.py                boobook {validate-ais, dashboard, coverage, rf-demo, demo}
  config.py             Cluster definitions + monitoring zones

data/sample/            133-row synthetic AIS dataset (Torres Strait, 9 vessels, all alert types)
data/processed/         Generated artefacts (gitignored for live data)
artifacts/              Dashboard + RF simulation outputs
tests/                  27 pytest tests (all rules, edge cases, integration)
docs/                   Demo script, source repos, limitations, validation plan
```

---

## Alert types

| Type | Trigger | Typical score |
|---|---|---|
| `AIS_GAP` | Silence > 2h (configurable) | 55–95 |
| `IMPOSSIBLE_SPEED` | Implied speed > 45 kn — AIS spoofing indicator | 70–98 |
| `LOITERING` | > 2h within 5 km radius at < 3 kn avg — IUU fishing pattern | 60–88 |
| `RENDEZVOUS_CANDIDATE` | Two vessels < 2 km apart within 30 min window | 65–78 |
| `SENSITIVE_ZONE` | Vessel inside configured monitoring zone | 52 |

All scores are 0–100. All alerts are hedged: anomalies flag for human review, not proof of illegality.

---

## What it does not claim

- Does **not** prove passive RF capture from real SDR hardware
- Does **not** prove dark-vessel detection
- Does **not** record or analyse voice/content (metadata only architecture)
- Does **not** allege illegal activity from AIS anomalies alone
- Does **not** claim regional/continental coverage — RF concept is choke-point cluster monitoring
- Ground-based VHF/AIS LOS is ~35–50 km; TDOA requires ≥3 nodes hearing the same emitter

---

## Funding and grant reality

DIDG is **not** core R&D/prototyping funding. Defence guidance says applications are likely ineligible for product development, prototyping, R&D, or non-recurring engineering. Core technical validation is funded via pre-seed, customer pilots, and RDTI where eligible. RDTI is in arrears — not upfront cash.

---

## Investor framing

> Boobook currently validates the maritime analytics workflow on AIS source data —  
> flagging the same behaviours an enforcement analyst cares about.  
> The product becomes materially stronger when AIS anomalies are fused with  
> independent passive RF detections inside instrumented choke points.  
> Next milestone: live Sydney Harbour AIS capture via RTL-SDR.  
> Then: controlled 3-node TDOA test.  
> Then: one paid AFMA/ABF pilot.

---

## Compliance posture

Receive-only architecture. Any live RF phase must be metadata-only (no voice/content capture), reviewed against ACMA licensing requirements and the TIA Act before field deployment. Legal review required per deployment before any live operation.
